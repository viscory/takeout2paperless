"""Config loading and validation."""

from __future__ import annotations

import logging
import re
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

    # ── [paths] ────────────────────────────────────────────────────
    input_dir: Path
    output_dir: Path

    # ── [include] ──────────────────────────────────────────────────
    target_extensions: frozenset[str]

    # ── [exclude] ──────────────────────────────────────────────────
    # Unified ban list — every pattern is compiled as a regex and
    # checked against both the filename and the full archive path.
    ban: tuple[Pattern[str], ...]

    # ── [output] ─────────────────────────────────────────────────
    dry_run: bool
    fingerprint: bool
    fingerprint_delimiter: str
    flatten: bool
    collision: str  # "rename" | "skip" | "overwrite"

    # ── [runtime] ────────────────────────────────────────────────
    log_level: str

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

        # ── [paths] ────────────────────────────────────────────────
        paths_cfg = raw.get("paths", {})
        input_dir = _resolve_path(paths_cfg.get("input_dir", "."), anchor)
        output_dir = _resolve_path(paths_cfg.get("output_dir", "paperless_ready"), anchor)

        # ── [include] ──────────────────────────────────────────────
        include_cfg = raw.get("include", {})
        exts = include_cfg.get(
            "extensions",
            [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"],
        )
        if not isinstance(exts, list):
            _logger.warning("include.extensions must be a list, falling back to defaults")
            exts = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

        # ── [exclude] ──────────────────────────────────────────────
        exclude_cfg = raw.get("exclude", {})

        _default_ban = [
            r"(?i)(?:^|/)google photos(?:/|$)",
            r"(?i)(?:^|/)trash(?:/|$)",
        ]
        ban_raw = exclude_cfg.get("patterns", [])
        if isinstance(ban_raw, list):
            entries = [e for e in ban_raw if isinstance(e, str)]
            if not entries:
                entries = list(_default_ban)
        elif isinstance(ban_raw, str):
            entries = [ban_raw]
        else:
            _logger.warning("exclude.patterns must be a string or list, using defaults")
            entries = list(_default_ban)

        compiled: list[Pattern[str]] = []
        for raw_pat in entries:
            try:
                compiled.append(re.compile(raw_pat))
            except re.error as exc:
                _logger.warning("Invalid exclude regex '%s': %s — skipping", raw_pat, exc)

        # ── [output] ───────────────────────────────────────────────
        output_cfg = raw.get("output", {})
        dry_run = bool(output_cfg.get("dry_run", False))
        fingerprint = bool(output_cfg.get("fingerprint", False))

        _delimiter = output_cfg.get("fingerprint_delimiter", "_")
        if not isinstance(_delimiter, str):
            _logger.warning("output.fingerprint_delimiter must be a string, using '_'")
            _delimiter = "_"

        flatten = bool(output_cfg.get("flatten", True))

        _collision = output_cfg.get("collision", "rename")
        if _collision not in ("rename", "skip", "overwrite"):
            _logger.warning("output.collision must be rename/skip/overwrite, using 'rename'")
            _collision = "rename"

        # ── [runtime] ──────────────────────────────────────────────
        runtime_cfg = raw.get("runtime", {})
        _log_level = runtime_cfg.get("log_level", "INFO")
        if _log_level not in ("DEBUG", "INFO", "WARN", "ERROR"):
            _logger.warning("runtime.log_level must be DEBUG/INFO/WARN/ERROR, using 'INFO'")
            _log_level = "INFO"

        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            target_extensions=frozenset(e.lower() for e in exts),
            ban=tuple(compiled),
            dry_run=dry_run,
            fingerprint=fingerprint,
            fingerprint_delimiter=_delimiter,
            flatten=flatten,
            collision=_collision,
            log_level=_log_level,
        )
