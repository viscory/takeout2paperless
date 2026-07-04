"""Extract documents from Google Takeout archives for Paperless-ngx.

Public API:
    Config              — load and validate configuration from TOML
    TakeoutExtractor    — extract documents from archives
    Report              — extraction result summary
    main                — CLI entry point
"""

from takeout2paperless.cli import main
from takeout2paperless.config import Config
from takeout2paperless.extractor import TakeoutExtractor
from takeout2paperless.reporter import Report

__all__ = ["main", "Config", "TakeoutExtractor", "Report"]
