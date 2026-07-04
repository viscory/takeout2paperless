"""Config loading and validation."""

from __future__ import annotations

import logging
import re
import string
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Pattern

_logger = logging.getLogger(__name__)


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

    # Unified ban list — every pattern is compiled as a regex
    # and checked against both the filename and the full archive path.
    ban: tuple[Pattern[str], ...]

    # Whether to skip actual file writes
    dry_run: bool

    # Whether to encode the original directory path into the filename
    fingerprint: bool

    # Character used to join path components when fingerprinting.
    # Must be a single ASCII letter, digit, hyphen, underscore, or period.
    fingerprint_delimiter: str

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
                with p.open("rb") as f:
                    raw = tomllib.load(f)
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

        # Fingerprint delimiter (any string the user wants)
        _delimiter = app.get("fingerprint_delimiter", "_")
        if not isinstance(_delimiter, str):
            _logger.warning("fingerprint_delimiter must be a string, using '_'")
            _delimiter = "_"

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

        # Default ban patterns — use (?i) for case-insensitive defaults
        # so they work out of the box. User-supplied patterns must include
        # (?i) themselves if they want case-insensitive matching.
        _default_ban = [
            r"(?i)(?:^|/)google photos(?:/|$)",
            r"(?i)(?:^|/)trash(?:/|$)",
        ]
        ban_raw = exclude_cfg.get("ban", [])
        if isinstance(ban_raw, list):
            entries = [e for e in ban_raw if isinstance(e, str)]
            if not entries:
                entries = list(_default_ban)
        elif isinstance(ban_raw, str):
            entries = [ban_raw]
        else:
            _logger.warning("exclude.ban must be a string or list, using defaults")
            entries = list(_default_ban)

        compiled: list[Pattern[str]] = []
        for raw_pat in entries:
            try:
                compiled.append(re.compile(raw_pat))
            except re.error as exc:
                _logger.warning("Invalid ban regex '%s': %s — skipping", raw_pat, exc)

        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            target_extensions=frozenset(e.lower() for e in exts),
            ban=tuple(compiled),
            dry_run=dry_run,
            fingerprint=fingerprint,
            fingerprint_delimiter=_delimiter,
        )
