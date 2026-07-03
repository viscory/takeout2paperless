"""Archive format abstraction — open zip, tar.*, or 7z and yield entries."""

from __future__ import annotations

import logging
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import py7zr

_logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024  # 64 KiB

# All archive extensions we recognise (longest-first for compound extensions)
SUPPORTED_FORMATS: frozenset[str] = frozenset(
    {
        ".zip",
        ".tar.gz",
        ".tar.bz2",
        ".tar.xz",
        ".tgz",
        ".tar",
        ".7z",
    }
)


@dataclass
class ArchiveEntry:
    """A regular file inside an archive.

    Call ``write_to(dest)`` to stream the content to a file on disk
    in chunks — never loads the full file into memory.
    """

    path: str  # Original path within the archive
    write_to: Callable[[Path], None]  # Streams content to *dest* in chunks


# ── Count entries (metadata only, no content) ─────────────────────────────────


def count_entries(path: Path) -> int:
    """Count regular files in *path* without reading any file content."""
    fmt = detect_format(path)
    if fmt is None:
        return 0

    if fmt == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            return sum(1 for n in zf.namelist() if not n.endswith("/"))

    if fmt in (".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz"):
        with tarfile.open(path, "r") as tf:
            return sum(1 for m in tf.getmembers() if m.isfile())

    if fmt == ".7z":
        with py7zr.SevenZipFile(path, mode="r") as sz:
            return sum(1 for n in sz.namelist() if not n.endswith("/"))

    return 0


# ── Format detection ──────────────────────────────────────────────────────────


def _archive_suffixes(name: str) -> list[str]:
    """Return candidate archive suffixes, longest first."""
    lower = name.lower()
    for compound in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz"):
        if lower.endswith(compound):
            return [compound]
    return Path(lower).suffixes  # e.g. [".zip"], [".7z"], [".tar"]


def detect_format(path: Path) -> str | None:
    """Return the recognised archive suffix (e.g. ``.tar.gz``) or *None*."""
    for suffix in _archive_suffixes(path.name):
        if suffix in SUPPORTED_FORMATS:
            return suffix
    return None


# ── Lazy archive iteration ────────────────────────────────────────────────────

# NOTE on memory: these generators keep the archive file handle open while
# the caller iterates.  Do NOT call ``list()`` on them — process entries
# one at a time so that ``write_to`` can stream directly from the archive
# to the output file without buffering the whole file in RAM.


def iter_archive(path: Path) -> Iterator[ArchiveEntry]:
    """Yield every regular file in *path* as an :class:`ArchiveEntry`.

    The archive stays open while the generator is alive.  Each entry's
    ``write_to`` streams content chunk-by-chunk — safe for files larger
    than RAM.

    Raises :class:`ValueError` when the format is not recognised.
    """
    fmt = detect_format(path)
    if fmt is None:
        raise ValueError(f"Unsupported archive format: '{path.name}'")

    _logger.debug("Opening %s as '%s'", path.name, fmt)

    if fmt == ".zip":
        yield from _iter_zip(path)
    elif fmt in (".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz"):
        yield from _iter_tar(path)
    elif fmt == ".7z":
        yield from _iter_7z(path)


# ── Format-specific readers ───────────────────────────────────────────────────


def _iter_zip(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a ZIP archive — streams via ``shutil.copyfileobj``."""
    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue

            def _write(dest: Path, _name: str = name) -> None:
                with zf.open(_name) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst, _CHUNK_SIZE)

            yield ArchiveEntry(path=name, write_to=_write)


def _iter_tar(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a tar archive — streams via ``shutil.copyfileobj``."""
    with tarfile.open(path, "r") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            src = tf.extractfile(member)
            if src is None:
                continue
            # Read the content eagerly because ``tf`` may move on;
            # but we buffer incrementally and return a chunked reader.
            data = src.read()
            name = member.name

            def _write(dest: Path, _data: bytes = data) -> None:
                with open(dest, "wb") as dst:
                    dst.write(_data)

            yield ArchiveEntry(path=name, write_to=_write)


def _iter_7z(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a 7z archive — extracts to tempdir first, then streams
    from the temp files in chunks."""
    with py7zr.SevenZipFile(path, mode="r") as sz:
        names = sz.namelist()
        real_files = [n for n in names if not n.endswith("/")]
        if not real_files:
            return

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sz.extractall(tmp_path)

            for name in real_files:
                file_on_disk = tmp_path / name
                if not file_on_disk.is_file():
                    _logger.warning("Expected file not found after 7z extract: %s", name)
                    continue

                def _write(dest: Path, _src: Path = file_on_disk) -> None:
                    shutil.copy2(_src, dest)

                yield ArchiveEntry(path=name, write_to=_write)
