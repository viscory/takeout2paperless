"""Config loading and validation."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Pattern

_logger = __import__("logging").getLogger(__name__)


def _resolve_path(raw: str, anchor: Path | None = None) -> Path:
    """Resolve *raw* relative to *anchor* (or CWD)."""
    p = Path(raw)
    if not p.is_absolute() and anchor is not None:
        p = anchor / p
    return p.resolve()


@dataclass(frozen=True)
class Config:
    """Immutable validated configuration."""

    # Directories
    input_dir: Path
    output_dir: Path

    # Target extensions (lowercase, with dot)
    target_extensions: frozenset[str]

    # Directory blocklist (lowercase fragments)
    exclude_directories: frozenset[str]

    # Directory regex patterns (compiled, case-insensitive, matched against full path)
    exclude_directory_patterns: tuple[Pattern[str], ...]

    # Filename regex patterns (compiled, case-insensitive)
    exclude_filename_patterns: tuple[Pattern[str], ...]

    # Whether to skip actual file writes
    dry_run: bool

    # Whether to encode the original directory path into the filename
    fingerprint: bool

    # ── Factory ─────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str | Path = "config.toml") -> Config:
        """Load and validate from a TOML file.

        Falls back to sensible defaults when the file is missing
        or a key is absent.
        """
        raw: dict[str, Any] = {}
        p = Path(path)
        if p.is_file():
            try:
                raw = tomllib.loads(p.read_text())
            except (tomllib.TOMLDecodeError, OSError) as exc:
                _logger.warning("Invalid config '%s': %s — using defaults", p, exc)
        else:
            _logger.info("No config found at '%s', using defaults", p)

        anchor = p.parent if p.exists() else None

        # ── [takeout2paperless] ──────────────────────────────────────
        app = raw.get("takeout2paperless", {})
        input_dir = _resolve_path(app.get("input_dir", "."), anchor)
        output_dir = _resolve_path(app.get("output_dir", "paperless_ready"), anchor)
        dry_run = bool(app.get("dry_run", False))
        fingerprint = bool(app.get("fingerprint", False))

        # ── [filter] ─────────────────────────────────────────────────
        filter_cfg = raw.get("filter", {})
        exts = filter_cfg.get(
            "include_extensions",
            [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"],
        )
        if not isinstance(exts, list):
            _logger.warning("filter.include_extensions must be a list, falling back to defaults")
            exts = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

        # ── [exclude] ────────────────────────────────────────────────
        exclude_cfg = raw.get("exclude", {})

        # Directories — built-in defaults when absent/empty
        _default_exclude_dirs = {"google photos", "trash"}
        dirs_raw = exclude_cfg.get("directories", [])
        if isinstance(dirs_raw, list):
            enabled_dirs = {d.lower() for d in dirs_raw if isinstance(d, str)}
            exclude_dirs = (
                frozenset(enabled_dirs) if enabled_dirs else frozenset(_default_exclude_dirs)
            )
        else:
            _logger.warning("exclude.directories must be a list, using defaults")
            exclude_dirs = frozenset(_default_exclude_dirs)

        # Directory patterns
        dir_pats: list[Pattern[str]] = []
        for entry in exclude_cfg.get("directory_patterns", []):
            if not isinstance(entry, dict):
                _logger.warning("directory pattern entry must be a table, skipping")
                continue
            name = entry.get("name", "unnamed")
            raw_pat = entry.get("pattern", "")
            if not isinstance(raw_pat, str):
                _logger.warning("Directory pattern '%s' is not a string, skipping", name)
                continue
            try:
                dir_pats.append(re.compile(raw_pat, re.IGNORECASE))
            except re.error as exc:
                _logger.warning("Invalid regex for '%s': %s — skipping", name, exc)

        # Filename patterns
        filename_pats: list[Pattern[str]] = []
        for entry in exclude_cfg.get("filename_patterns", []):
            if not isinstance(entry, dict):
                _logger.warning("filename pattern entry must be a table, skipping")
                continue
            name = entry.get("name", "unnamed")
            raw_pat = entry.get("pattern", "")
            if not isinstance(raw_pat, str):
                _logger.warning("Filename pattern '%s' is not a string, skipping", name)
                continue
            try:
                filename_pats.append(re.compile(raw_pat, re.IGNORECASE))
            except re.error as exc:
                _logger.warning("Invalid regex for '%s': %s — skipping", name, exc)

        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            target_extensions=frozenset(e.lower() for e in exts),
            exclude_directories=exclude_dirs,
            exclude_directory_patterns=tuple(dir_pats),
            exclude_filename_patterns=tuple(filename_pats),
            dry_run=dry_run,
            fingerprint=fingerprint,
        )
