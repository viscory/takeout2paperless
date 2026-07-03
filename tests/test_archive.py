"""Tests for archive format detection and iteration."""

from __future__ import annotations

from pathlib import Path

import pytest

from takeout2paperless.archive import (
    count_entries,
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


class TestCountEntries:
    """count_entries returns file counts without reading content."""

    def test_zip(self, fixtures_dir: Path) -> None:
        assert count_entries(fixtures_dir / "test.zip") == 5

    def test_tar(self, fixtures_dir: Path) -> None:
        assert count_entries(fixtures_dir / "test.tar.gz") == 2

    def test_7z(self, fixtures_dir: Path) -> None:
        assert count_entries(fixtures_dir / "test.7z") == 2

    def test_unsupported_format(self) -> None:
        assert count_entries(Path("/nonexistent/file.pdf")) == 0


class TestIterZip:
    """Iteration over .zip archives — lazy, streaming."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        names = {e.path for e in iter_archive(fixtures_dir / "test.zip")}
        assert len(names) == 5
        assert "Takeout/Drive/report.pdf" in names
        assert "Takeout/Google Photos/image.jpg" in names

    def test_write_to_streams_content(self, fixtures_dir: Path, tmp_path: Path) -> None:
        for entry in iter_archive(fixtures_dir / "test.zip"):
            if entry.path == "Takeout/Drive/report.pdf":
                dest = tmp_path / "report.pdf"
                entry.write_to(dest)
                assert dest.read_bytes() == b"pdf content"
                return
        pytest.fail("report.pdf not found in archive")


class TestIterTar:
    """Iteration over .tar.gz archives — lazy, streaming."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        names = {e.path for e in iter_archive(fixtures_dir / "test.tar.gz")}
        assert len(names) == 2
        assert "Takeout/Drive/letter.pdf" in names

    def test_write_to_streams_content(self, fixtures_dir: Path, tmp_path: Path) -> None:
        for entry in iter_archive(fixtures_dir / "test.tar.gz"):
            if entry.path == "Takeout/Drive/letter.pdf":
                dest = tmp_path / "letter.pdf"
                entry.write_to(dest)
                assert dest.read_bytes() == b"letter pdf"
                return
        pytest.fail("letter.pdf not found in archive")


class TestIter7z:
    """Iteration over .7z archives — lazy, streaming."""

    def test_reads_all_regular_files(self, fixtures_dir: Path) -> None:
        names = {e.path for e in iter_archive(fixtures_dir / "test.7z")}
        assert len(names) == 2
        assert "Takeout/Drive/data.csv" in names

    def test_write_to_streams_content(self, fixtures_dir: Path, tmp_path: Path) -> None:
        for entry in iter_archive(fixtures_dir / "test.7z"):
            if entry.path == "Takeout/Drive/data.csv":
                dest = tmp_path / "data.csv"
                entry.write_to(dest)
                assert dest.read_bytes() == b"csv content"
                return
        pytest.fail("data.csv not found in archive")


class TestIterUnsupported:
    """Unsupported formats should raise ValueError."""

    def test_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported archive format"):
            for _ in iter_archive(Path("/nonexistent/readme.pdf")):
                pass  # pragma: no cover
