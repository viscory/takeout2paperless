"""Tests for archive format detection and iteration."""

from __future__ import annotations

from pathlib import Path

import pytest

from takeout2paperless.archive import (
    detect_format,
    iter_archive,
)


class TestDetectFormat:
    """detect_format should recognise all SUPPORTED_FORMATS."""

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("archive.zip", ".zip"),
            ("archive.tar", ".tar"),
            ("archive.tar.gz", ".tar.gz"),
            ("archive.tgz", ".tgz"),
            ("archive.tar.bz2", ".tar.bz2"),
            ("archive.tar.xz", ".tar.xz"),
            ("archive.7z", ".7z"),
            ("takeout-001.zip", ".zip"),
        ],
    )
    def test_recognised(self, name: str, expected: str) -> None:
        assert detect_format(Path(name)) == expected

    @pytest.mark.parametrize(
        "name",
        ["readme.pdf", "image.jpg", "archive.rar", "file"],
    )
    def test_unrecognised(self, name: str) -> None:
        assert detect_format(Path(name)) is None


class TestIterZip:
    """Iteration over .zip archives."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        path = fixtures_dir / "test.zip"
        entries = list(iter_archive(path))
        assert len(entries) == 5
        names = {e.path for e in entries}
        assert "Takeout/Drive/report.pdf" in names
        assert "Takeout/Google Photos/image.jpg" in names

    def test_content_is_readable(self, fixtures_dir: Path) -> None:
        entries = list(iter_archive(fixtures_dir / "test.zip"))
        for e in entries:
            if e.path == "Takeout/Drive/report.pdf":
                assert e.read() == b"pdf content"
                return
        pytest.fail("report.pdf not found")


class TestIterTar:
    """Iteration over .tar.gz archives."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        path = fixtures_dir / "test.tar.gz"
        entries = list(iter_archive(path))
        assert len(entries) == 2
        names = {e.path for e in entries}
        assert "Takeout/Drive/letter.pdf" in names

    def test_content_is_readable(self, fixtures_dir: Path) -> None:
        entries = list(iter_archive(fixtures_dir / "test.tar.gz"))
        for e in entries:
            if e.path == "Takeout/Drive/letter.pdf":
                assert e.read() == b"letter pdf"
                return
        pytest.fail("letter.pdf not found")


class TestIter7z:
    """Iteration over .7z archives."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        path = fixtures_dir / "test.7z"
        entries = list(iter_archive(path))
        assert len(entries) == 2
        names = {e.path for e in entries}
        assert "Takeout/Drive/data.csv" in names

    def test_content_is_readable(self, fixtures_dir: Path) -> None:
        entries = list(iter_archive(fixtures_dir / "test.7z"))
        for e in entries:
            if e.path == "Takeout/Drive/data.csv":
                assert e.read() == b"csv content"
                return
        pytest.fail("data.csv not found")


class TestIterUnsupported:
    """Unsupported formats should raise ValueError."""

    def test_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported archive format"):
            list(iter_archive(Path("/nonexistent/readme.pdf")))
