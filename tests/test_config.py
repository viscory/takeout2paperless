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
        assert len(cfg.ban) == 2  # built-in defaults
        assert any(p.search("google photos") for p in cfg.ban)
        assert any(p.search("trash") for p in cfg.ban)

    def test_load_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.toml"
        p.write_text("")
        cfg = Config.load(str(p))
        assert cfg.dry_run is False
        assert len(cfg.ban) == 2  # built-in defaults

    def test_dry_run_flag(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text("[takeout2paperless]\ndry_run = true\n")
        cfg = Config.load(str(p))
        assert cfg.dry_run is True


class TestConfigOverrides:
    """User-supplied values replace defaults."""

    def test_directories(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text(
            '[takeout2paperless]\ninput_dir = "/custom/input"\noutput_dir = "/custom/output"\n'
        )
        cfg = Config.load(str(p))
        assert cfg.input_dir == Path("/custom/input").resolve()
        assert cfg.output_dir == Path("/custom/output").resolve()

    def test_ban_list(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\nban = ["exam"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        assert cfg.ban[0].search("exam")

    def test_ban_string(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\nban = "foo"\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        assert cfg.ban[0].search("foobar")

    def test_ban_regex(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\nban = ["^\\\\d{4}_.*\\\\.pdf$"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 1
        pat = cfg.ban[0]
        assert pat.match("1123_w15_ms_21.pdf")
        assert not pat.match("normal.pdf")

    def test_invalid_regex_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[exclude]\nban = ["[invalid"]\n')
        cfg = Config.load(str(p))
        assert len(cfg.ban) == 0

    def test_custom_target_extensions(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.toml"
        p.write_text('[filter]\ninclude_extensions = [".pdf"]\n')
        cfg = Config.load(str(p))
        assert cfg.target_extensions == frozenset({".pdf"})
