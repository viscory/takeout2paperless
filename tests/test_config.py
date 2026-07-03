"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

from takeout2paperless.config import Config


class TestConfigDefaults:
    """When no config file exists, sensible defaults kick in."""

    def test_load_missing_file(self) -> None:
        cfg = Config.load("/tmp/does_not_exist.toml")
        assert cfg.input_dir == Path(".").resolve()
        assert cfg.output_dir == Path("paperless_ready").resolve()
        assert cfg.dry_run is False
        assert ".pdf" in cfg.target_extensions
        assert "trash" in cfg.exclude_directories
        assert len(cfg.exclude_filename_patterns) == 0

    def test_load_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.toml"
        p.write_text("")
        cfg = Config.load(str(p))
        assert cfg.dry_run is False
        assert len(cfg.exclude_filename_patterns) == 0

    def test_dry_run_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text("dry_run = true\n")
        cfg = Config.load(str(p))
        assert cfg.dry_run is True


class TestConfigOverrides:
    """User-supplied values replace defaults."""

    def test_directories(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('input_dir = "/custom/input"\noutput_dir = "/custom/output"\n')
        cfg = Config.load(str(p))
        assert cfg.input_dir == Path("/custom/input").resolve()
        assert cfg.output_dir == Path("/custom/output").resolve()

    def test_disabled_directory_rule(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude.directories]\n"google photos" = false\ntrash = true\n')
        cfg = Config.load(str(p))
        assert "google photos" not in cfg.exclude_directories
        assert "trash" in cfg.exclude_directories

    def test_filename_patterns(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude.filename_patterns]\nexam = "^\\\\d{4}_.*\\\\.pdf$"\n')
        cfg = Config.load(str(p))
        assert len(cfg.exclude_filename_patterns) == 1
        pat = cfg.exclude_filename_patterns[0]
        assert pat.match("1123_w15_ms_21.pdf")
        assert not pat.match("normal.pdf")

    def test_invalid_regex_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude.filename_patterns]\nbad = "[invalid"\n')
        cfg = Config.load(str(p))
        assert len(cfg.exclude_filename_patterns) == 0

    def test_custom_target_extensions(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('target_extensions = [".pdf"]\n')
        cfg = Config.load(str(p))
        assert cfg.target_extensions == frozenset({".pdf"})
