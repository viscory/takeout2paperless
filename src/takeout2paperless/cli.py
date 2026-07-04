"""Entry point — invoked by ``python -m takeout2paperless``."""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console

from takeout2paperless.config import Config
from takeout2paperless.extractor import TakeoutExtractor


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract documents from Google Takeout archives")
    parser.add_argument("--config", default="config.toml", help="Path to config TOML file")
    args = parser.parse_args()

    config = Config.load(args.config)

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
