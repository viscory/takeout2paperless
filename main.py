#!/usr/bin/env python3
"""
Google Takeout Document Extractor for Paperless-ngx
---------------------------------------------------
Extracts documents from Google Takeout zip archives, skips unwanted files
based on a config file, and outputs a flattened directory for Paperless-ngx.
"""

import argparse
import json
import logging
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

# ─── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "target_extensions": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"],
    "exclude_directories": {
        "google photos": True,
        "trash": True,
    },
    "exclude_filename_patterns": [],
}

OUTPUT_DIR = "paperless_ready"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(config_path="config.json"):
    """Load config from a JSON file, falling back to defaults for missing keys."""
    config = dict(DEFAULT_CONFIG)
    path = Path(config_path)
    if path.is_file():
        with open(path) as f:
            user = json.load(f)
        for key in config:
            if key in user:
                config[key] = user[key]
    else:
        logger.info("No config file found, using defaults")
    return config


# ─── Extractor ────────────────────────────────────────────────────────────────


class TakeoutExtractor:
    def __init__(self, input_dir, config, output_dir=OUTPUT_DIR):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.file_counter = defaultdict(int)
        self.stats = {"processed": 0, "skipped": 0, "errors": 0}
        self.skip_reasons = defaultdict(int)
        self.skip_examples = defaultdict(list)
        self.processed_files = []

        # Config-derived rules
        self.target_extensions = {
            e.lower() for e in config.get("target_extensions", [])
        }

        # Only include directory patterns that are enabled (true)
        self.exclude_dirs = [
            d.lower()
            for d, enabled in config.get("exclude_directories", {}).items()
            if enabled
        ]

        # Compile filename regex patterns
        self.filename_blocklist = [
            re.compile(p, re.IGNORECASE)
            for p in config.get("exclude_filename_patterns", [])
        ]

    def _should_extract(self, filepath):
        """Return (bool, reason) — whether to extract and why."""
        path_lower = filepath.lower()
        filename = Path(filepath).name

        # 1. Check excluded directories
        for d in self.exclude_dirs:
            if d in path_lower:
                return False, f"Excluded path ({d})"

        ext = Path(path_lower).suffix

        # 2. Check target extension
        if ext not in self.target_extensions:
            return False, f"Skipped extension ({ext})"

        # 3. Check filename-based blocklist
        for pat in self.filename_blocklist:
            if pat.search(filename):
                return False, f"Blocked filename pattern ({pat.pattern})"

        return True, "Target document"

    def _get_unique_path(self, original_name):
        """Generate a flat, unique file path to prevent collision."""
        name = Path(original_name).name
        stem, ext = Path(name).stem, Path(name).suffix

        count = self.file_counter[name]
        self.file_counter[name] += 1

        return self.output_dir / (name if count == 0 else f"{stem}_{count}{ext}")

    def run(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Gather all zip files in the target directory
        archives = sorted(
            [f for f in self.input_dir.iterdir() if f.suffix.lower() == ".zip"]
        )

        if not archives:
            logger.error(f"No .zip archive files found in {self.input_dir}")
            return False

        logger.info(f"Found {len(archives)} archive volume(s) to process.")

        for arc in archives:
            logger.info(f"Processing archive: {arc.name}")
            try:
                with zipfile.ZipFile(arc, "r") as z:
                    for member in z.namelist():
                        # Skip directories themselves
                        if member.endswith("/"):
                            continue

                        extract, reason = self._should_extract(member)
                        if not extract:
                            self.stats["skipped"] += 1
                            self.skip_reasons[reason] += 1
                            if len(self.skip_examples[reason]) < 3:
                                self.skip_examples[reason].append(member)
                            continue

                        out_path = self._get_unique_path(member)
                        try:
                            with (
                                z.open(member) as source,
                                open(out_path, "wb") as target,
                            ):
                                target.write(source.read())

                            self.stats["processed"] += 1
                            self.processed_files.append(out_path.name)
                            logger.info(f"  Extracted: {member} -> {out_path.name}")
                        except Exception as e:
                            logger.error(f"  Failed extracting {member}: {e}")
                            self.stats["errors"] += 1
            except Exception as e:
                logger.error(f"Failed to read archive {arc.name}: {e}")
                self.stats["errors"] += 1

        self._print_summary()
        return True

    def _print_summary(self):
        console = Console()
        console.print()

        # ── Stats table ────────────────────────────────────────────────────
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column(style="bold cyan", justify="left")
        stats_table.add_column(justify="right")
        for k, v in self.stats.items():
            stats_table.add_row(k.title(), str(v))
        stats_table.add_row("Output dir", str(self.output_dir))

        # ── Skipped breakdown ──────────────────────────────────────────────
        skip_tree = None
        if self.skip_reasons:
            skip_tree = Tree("[bold yellow]Skipped files[/bold yellow]")
            for reason, count in sorted(self.skip_reasons.items(), key=lambda x: -x[1]):
                branch = skip_tree.add(f"[dim]{reason}[/dim]  ([bold]{count}[/bold])")
                for ex in self.skip_examples.get(reason, []):
                    branch.add(f"[italic]{ex}[/italic]")

        # ── Processed files ────────────────────────────────────────────────
        processed_tree = None
        if self.processed_files:
            label = f"[bold green]Processed files ({len(self.processed_files)})[/bold green]"
            processed_tree = Tree(label)
            show = self.processed_files[:50]
            remainder = len(self.processed_files) - len(show)
            for name in show:
                processed_tree.add(f"[italic]{name}[/italic]")
            if remainder > 0:
                processed_tree.add(f"[dim]… and {remainder} more[/dim]")

        # ── Render ─────────────────────────────────────────────────────────
        report = Table(show_header=False, box=None, padding=(0, 1))
        report.add_row(stats_table)
        if skip_tree:
            report.add_row(skip_tree)
        if processed_tree:
            report.add_row(processed_tree)

        console.print(
            Panel(
                report,
                title="[bold white]Extraction Report[/bold white]",
                border_style="blue",
                padding=(1, 2),
            )
        )
        console.print()


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Extract documents from Google Takeout for Paperless-ngx"
    )
    parser.add_argument(
        "input_dir", nargs="?", default=".", help="Directory containing archives"
    )
    parser.add_argument("-o", "--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    config = load_config(args.config)

    try:
        if TakeoutExtractor(args.input_dir, config, args.output).run():
            return
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")


if __name__ == "__main__":
    main()
