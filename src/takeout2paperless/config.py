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

    # Directory blocklist (lowercase fragments that are enabled)
    exclude_directories: frozenset[str]

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

        input_dir = _resolve_path(raw.get("input_dir", "."), anchor)
        output_dir = _resolve_path(raw.get("output_dir", "paperless_ready"), anchor)

        exts = raw.get(
            "target_extensions",
            [
                ".pdf",
                ".docx",
                ".doc",
                ".xlsx",
                ".xls",
                ".csv",
                ".txt",
            ],
        )
        if not isinstance(exts, list):
            _logger.warning("target_extensions must be a list, falling back to defaults")
            exts = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

        # Exclude directories — built-in defaults when table is empty
        _default_exclude_dirs = {"google photos", "trash"}
        exclude_raw = raw.get("exclude", {})
        dirs_raw = exclude_raw.get("directories", {})
        if not isinstance(dirs_raw, dict):
            _logger.warning("exclude.directories must be a table, ignoring")
            dirs_raw = {}
        enabled_dirs = {
            d.lower() for d, enabled in dirs_raw.items() if isinstance(enabled, bool) and enabled
        }
        # If the user provided an empty table (or omitted it entirely),
        # fall back to built-in defaults.
        exclude_dirs = frozenset(enabled_dirs) if enabled_dirs else frozenset(_default_exclude_dirs)

        # Filename patterns
        pats_raw = exclude_raw.get("filename_patterns", {})
        if not isinstance(pats_raw, dict):
            _logger.warning("exclude.filename_patterns must be a table, ignoring")
            pats_raw = {}
        patterns: list[Pattern[str]] = []
        for name, raw_pat in pats_raw.items():
            if not isinstance(raw_pat, str):
                _logger.warning("Pattern '%s' is not a string, skipping", name)
                continue
            try:
                patterns.append(re.compile(raw_pat, re.IGNORECASE))
            except re.error as exc:
                _logger.warning("Invalid regex for '%s': %s — skipping", name, exc)

        dry_run = bool(raw.get("dry_run", False))
        fingerprint = bool(raw.get("fingerprint", False))

        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            target_extensions=frozenset(e.lower() for e in exts),
            exclude_directories=exclude_dirs,
            exclude_filename_patterns=tuple(patterns),
            dry_run=dry_run,
            fingerprint=fingerprint,
        )
