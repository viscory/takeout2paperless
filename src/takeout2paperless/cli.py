"""Entry point — invoked by ``python -m takeout2paperless``."""

from __future__ import annotations

import subprocess
import sys

from rich.console import Console
from rich.prompt import Confirm

from takeout2paperless.config import Config
from takeout2paperless.extractor import TakeoutExtractor


def main() -> None:
    config = Config.load("config.toml")

    try:
        report = TakeoutExtractor(config).run()
    except KeyboardInterrupt:
        Console().print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)

    # Skip consumption prompt in dry-run mode or if nothing was extracted
    if config.dry_run or report.processed == 0:
        return

    console = Console()
    console.print()
    if Confirm.ask(
        "Consume extracted files with Paperless?",
        default=False,
    ):
        if config.paperless_consume_cmd:
            cmd = config.paperless_consume_cmd.format(output_dir=str(config.output_dir))
            console.print(f"[dim]Running: {cmd}[/dim]")
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as exc:
                console.print(f"[red]Paperless command failed (exit {exc.returncode})[/red]")
                sys.exit(1)
        else:
            console.print(
                "[yellow]No paperless.consume_cmd configured.[/yellow]\n"
                "Set it in config.toml, e.g.:\n"
                "[paperless]\n"
                'consume_cmd = "docker compose -f ~/homelab/paperless-ngx/docker-compose.yml '
                'exec webserver python manage.py document_consumer {output_dir}"'
            )


if __name__ == "__main__":
    main()
