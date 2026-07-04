"""Tests for the extraction logic and reporting."""

from __future__ import annotations

from pathlib import Path

from takeout2paperless.config import Config
from takeout2paperless.extractor import TakeoutExtractor


class TestExtractorDryRun:
    """In dry-run mode, no files are written."""

    def test_nothing_written(self, tmp_path: Path, fixtures_dir: Path) -> None:
        cfg = Config(
            input_dir=fixtures_dir,
            output_dir=tmp_path / "out",
            target_extensions=frozenset({".pdf", ".xlsx", ".csv"}),
            ban=(),
            dry_run=True,
            fingerprint=False,
        )
        report = TakeoutExtractor(cfg).run()
        assert report.processed > 0
        # Dry-run: no bytes written
        assert not any(cfg.output_dir.iterdir())

    def test_skip_reasons(self, tmp_path: Path, fixtures_dir: Path) -> None:
        cfg = Config(
            input_dir=fixtures_dir,
            output_dir=tmp_path / "out",
            target_extensions=frozenset({".pdf", ".xlsx", ".csv"}),
            ban=(),
            dry_run=True,
            fingerprint=False,
        )
        report = TakeoutExtractor(cfg).run()
        assert report.skipped > 0
        assert sum(report.skip_reasons.values()) == report.skipped


class TestExtractorFiltering:
    """Filter rules work correctly."""

    def test_google_photos_skipped(self, tmp_path: Path, fixtures_dir: Path) -> None:
        cfg = Config(
            input_dir=fixtures_dir,
            output_dir=tmp_path / "out",
            target_extensions=frozenset({".pdf", ".xlsx", ".csv", ".jpg"}),
            ban=(__import__("re").compile("google photos", __import__("re").IGNORECASE),),
            dry_run=True,
            fingerprint=False,
        )
        report = TakeoutExtractor(cfg).run()
        assert report.skip_reasons.get("Banned pattern", 0) > 0

    def test_trash_allowed_when_disabled(self, tmp_path: Path, fixtures_dir: Path) -> None:
        cfg = Config(
            input_dir=fixtures_dir,
            output_dir=tmp_path / "out",
            target_extensions=frozenset({".pdf", ".xlsx", ".csv"}),
            ban=(),
            dry_run=True,
            fingerprint=False,
        )
        report = TakeoutExtractor(cfg).run()
        assert report.skip_reasons.get("Banned pattern", 0) == 0


class TestExtractorIntegration:
    """End-to-end extraction produces correct counts."""

    def test_counts_match(self, tmp_path: Path, fixtures_dir: Path) -> None:
        """Verify known counts against the test fixtures."""
        cfg = Config(
            input_dir=fixtures_dir,
            output_dir=tmp_path / "out",
            target_extensions=frozenset({".pdf", ".xlsx", ".csv"}),
            ban=(
                __import__("re").compile("google photos", __import__("re").IGNORECASE),
                __import__("re").compile("trash", __import__("re").IGNORECASE),
            ),
            dry_run=True,
            fingerprint=False,
        )
        report = TakeoutExtractor(cfg).run()

        # Fixtures overview:
        #  test.zip:      report.pdf, invoice.xlsx, image.jpg, old.pdf, 1123_w15_ms_21.pdf
        #  test.tar.gz:   letter.pdf, draft.xlsx
        #  test.7z:       data.csv, 9702_s18_qp_12.pdf
        #
        # Filters: target_exts={.pdf,.xlsx,.csv}, ban={google photos,trash}
        #
        # Processed: report.pdf, invoice.xlsx, 1123_w15_ms_21.pdf,          = 6
        #            letter.pdf, data.csv, 9702_s18_qp_12.pdf
        # Skipped:   image.jpg(google photos), old.pdf(trash),               = 3
        #            draft.xlsx(trash)
        assert report.processed == 6
        assert report.skipped == 3
