"""Test fixtures — generates small archives on the fly."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import py7zr
import pytest


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A directory with small test archives in each supported format."""
    root = tmp_path_factory.mktemp("fixtures")

    # ── .zip ───────────────────────────────────────────────────────
    with zipfile.ZipFile(root / "test.zip", "w") as z:
        z.writestr("Takeout/Drive/report.pdf", "pdf content")
        z.writestr("Takeout/Drive/invoice.xlsx", "xlsx content")
        z.writestr("Takeout/Google Photos/image.jpg", "photo")
        z.writestr("Takeout/Trash/old.pdf", "trash")
        z.writestr("Takeout/Drive/Unorganized/1123_w15_ms_21.pdf", "exam paper")

    # ── .tar.gz ────────────────────────────────────────────────────
    with tarfile.open(root / "test.tar.gz", "w:gz") as t:
        _add_tar(t, "Takeout/Drive/letter.pdf", b"letter pdf")
        _add_tar(t, "Takeout/Trash/draft.xlsx", b"draft")

    # ── .7z ────────────────────────────────────────────────────────
    with py7zr.SevenZipFile(root / "test.7z", "w") as sz:
        sz.writestr(b"csv content", "Takeout/Drive/data.csv")
        sz.writestr(b"exam content", "Takeout/Drive/9702_s18_qp_12.pdf")

    return root


def _add_tar(tf: tarfile.TarFile, name: str, content: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(content)
    tf.addfile(info, io.BytesIO(content))
