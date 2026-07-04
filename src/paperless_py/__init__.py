"""Extract documents from Google Takeout archives for Paperless-ngx.

Public API:
    Config              — load and validate configuration from TOML
    TakeoutExtractor    — extract documents from archives
    Report              — extraction result summary
    main                — CLI entry point
"""

from paperless_py.cli import main
from paperless_py.config import Config
from paperless_py.extractor import TakeoutExtractor
from paperless_py.reporter import Report

__all__ = ["main", "Config", "TakeoutExtractor", "Report"]
