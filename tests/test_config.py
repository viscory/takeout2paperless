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
        assert len(cfg.ban) == 2
        assert cfg.fingerprint_delimiter == "_"
        assert cfg.flatten is True
        assert cfg.collision == "rename"
        assert cfg.log_level == "INFO"
        assert any(p.search("Takeout/Google Photos/image.jpg") for p in cfg.ban)
        assert any(p.search("Takeout/Trash/old.pdf") for p in cfg.ban)

    def test_load_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.toml"
        p.write_text("")
        cfg = Config.load(str(p))
        assert cfg.dry_run is False
        assert len(cfg.ban) == 2
        assert cfg.flatten is True
        assert cfg.collision == "rename"
        assert cfg.log_level == "INFO"

    def test_dry_run_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text("[output]\ndry_run = true\n")
        cfg = Config.load(str(p))
        assert cfg.dry_run is True


class TestConfigOverrides:
    """User-supplied values replace defaults."""

    def test_paths(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[paths]\ninput_dir = "/custom/input"\noutput_dir = "/custom/output"\n')
        cfg = Config.load(str(p))
        assert cfg.input_dir == Path("/custom/input").resolve()
        assert cfg.output_dir == Path("/custom/output").resolve()

    def test_exclude_patterns(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\npatterns = ["exam"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        assert cfg.ban[0].search("exam")

    def test_exclude_string(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\npatterns = "foo"\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        assert cfg.ban[0].search("foobar")

    def test_exclude_regex(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\npatterns = ["^\\\\d{4}_.*\\\\.pdf$"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        pat = cfg.ban[0]
        assert pat.match("1123_w15_ms_21.pdf")
        assert not pat.match("normal.pdf")

    def test_case_sensitive_exclude(self, tmp_path: Path) -> None:
        """Without (?i), patterns are case-sensitive."""
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\npatterns = ["google photos"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        pat = cfg.ban[0]
        assert pat.search("Takeout/google photos/file.jpg")
        assert not pat.search("Takeout/Google Photos/file.jpg")

    def test_invalid_regex_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\npatterns = ["[invalid"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 0

    def test_custom_extensions(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[include]\nextensions = [".pdf"]\n')
        cfg = Config.load(str(p))
        assert cfg.target_extensions == frozenset({".pdf"})

    def test_fingerprint_delimiter(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[output]\nfingerprint_delimiter = "-"\n')
        cfg = Config.load(str(p))
        assert cfg.fingerprint_delimiter == "-"

    def test_fingerprint_delimiter_non_string_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text("[output]\nfingerprint_delimiter = 123\n")
        cfg = Config.load(str(p))
        assert cfg.fingerprint_delimiter == "_"

    def test_flatten_false(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text("[output]\nflatten = false\n")
        cfg = Config.load(str(p))
        assert cfg.flatten is False

    def test_collision_skip(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[output]\ncollision = "skip"\n')
        cfg = Config.load(str(p))
        assert cfg.collision == "skip"

    def test_collision_invalid_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[output]\ncollision = "bogus"\n')
        cfg = Config.load(str(p))
        assert cfg.collision == "rename"

    def test_log_level(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[runtime]\nlog_level = "DEBUG"\n')
        cfg = Config.load(str(p))
        assert cfg.log_level == "DEBUG"

    def test_log_level_invalid_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[runtime]\nlog_level = "VERBOSE"\n')
        cfg = Config.load(str(p))
        assert cfg.log_level == "INFO"
