"""Archive format abstraction — open zip, tar.*, or 7z and yield entries."""

from __future__ import annotations

import logging
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import py7zr

_logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class ArchiveEntry:
    """A regular file inside an archive."""

    path: str  # Original path within the archive
    read: Callable[[], bytes]  # Thunk that returns the full byte content


# ── Format detection ──────────────────────────────────────────────────────────


def _archive_suffixes(name: str) -> list[str]:
    """Return candidate archive suffixes, longest first."""
    lower = name.lower()
    # Compound extensions must be checked first
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


# ── Archive iteration ─────────────────────────────────────────────────────────


def iter_archive(path: Path) -> Iterator[ArchiveEntry]:
    """Yield every regular file in *path* as :class:`ArchiveEntry`.

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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_reader(data: bytes) -> Callable[[], bytes]:
    """Wrap *data* in a callable so mypy can infer the type."""
    return lambda: data


# ── Format-specific readers ───────────────────────────────────────────────────


def _iter_zip(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a ZIP archive (read-all strategy)."""
    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            yield ArchiveEntry(path=name, read=_make_reader(zf.read(name)))


def _iter_tar(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a tar archive (auto-detects compression)."""
    with tarfile.open(path, "r") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            fobj = tf.extractfile(member)
            if fobj is None:
                continue
            yield ArchiveEntry(path=member.name, read=_make_reader(fobj.read()))


def _iter_7z(path: Path) -> Iterator[ArchiveEntry]:
    """Yield entries from a 7z archive (via tempdir extraction)."""
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
                yield ArchiveEntry(path=name, read=_make_reader(file_on_disk.read_bytes()))
