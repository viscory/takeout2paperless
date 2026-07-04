"""Entry point — invoked by ``python -m takeout2paperless``."""

from __future__ import annotations

import sys

from rich.console import Console

from takeout2paperless.config import Config
from takeout2paperless.extractor import TakeoutExtractor


def main() -> None:
    config = Config.load("config.toml")

    try:
        TakeoutExtractor(config).run()
    except KeyboardInterrupt:
        Console().print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
