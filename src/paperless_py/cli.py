"""Entry point — invoked by ``python -m paperless_py``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console

from paperless_py.config import Config
from paperless_py.extractor import TakeoutExtractor


# Config search paths (in priority order)
_CONFIG_PATHS = [
    Path("config.toml"),
    Path.home() / ".config" / "paperless-py" / "config.toml",
    Path.home() / "code" / "paperless-py" / "config.toml",
]


def _find_config() -> Path:
    """Return the first existing config file from the search list."""
    for path in _CONFIG_PATHS:
        if path.exists():
            return path
    # Fall back to the first path (CWD config.toml) even if it doesn't exist;
    # Config.load will use defaults and warn.
    return _CONFIG_PATHS[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract documents from Google Takeout archives")
    parser.add_argument(
        "--config",
        help="Path to config TOML file (overrides auto-discovery)",
    )
    args = parser.parse_args()

    config_path = args.config or _find_config()
    config = Config.load(config_path)

    # Configure logging level from config
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        TakeoutExtractor(config).run()
    except KeyboardInterrupt:
        Console().print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
