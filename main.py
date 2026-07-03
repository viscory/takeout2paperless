#!/usr/bin/env python3
"""
Google Takeout Document Extractor for Paperless-ngx
---------------------------------------------------
- Uses Python's native zipfile module (no extra dependencies required).
- Skips media & Google Photos, flattens output, handles duplicates.
"""

import argparse
import logging
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

# ─── Configuration ──────────────────────────────────────────────────────────────
TARGET_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"}
EXCLUDE_PATHS = ["google photos", "trash"]
OUTPUT_DIR = "paperless_ready"

# Cambridge / CIE style exam papers: e.g. 1123_w15_ms_21.pdf, 9702_s18_qp_12.pdf
QUESTION_PAPER_RE = re.compile(
    r"^\d{4}_[a-z]\d{2}_(?:qp|ms|er|gt|ir|sy|sr|ci|sm|in|tn|sp|nt|sf)(?:_\d{1,3})?\.pdf$",
    re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class TakeoutExtractor:
    def __init__(self, input_dir, output_dir=OUTPUT_DIR):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.file_counter = defaultdict(int)
        self.stats = {"processed": 0, "skipped": 0, "errors": 0}
        self.skip_reasons = defaultdict(int)
        self.skip_examples = defaultdict(list)
        self.processed_examples = []

    def _should_extract(self, filepath):
        """Return bool and reason for extraction."""
        path_lower = filepath.lower()
        filename = Path(filepath).name

        for bad in EXCLUDE_PATHS:
            if bad in path_lower:
                return False, f"Excluded path ({bad})"

        ext = Path(path_lower).suffix
        if ext not in TARGET_EXTENSIONS:
            return False, f"Skipped extension ({ext})"

        if ext == ".pdf" and QUESTION_PAPER_RE.match(filename):
            return False, "Exam paper (qp/ms/er/gt/etc)"

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
                            # Stream directly out of the zip file into the flattened file path
                            with (
                                z.open(member) as source,
                                open(out_path, "wb") as target,
                            ):
                                target.write(source.read())

                            self.stats["processed"] += 1
                            if len(self.processed_examples) < 5:
                                self.processed_examples.append(out_path.name)
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

        # ── Processed samples ──────────────────────────────────────────────
        processed_tree = None
        if self.processed_examples:
            processed_tree = Tree("[bold green]Processed samples[/bold green]")
            for name in self.processed_examples:
                processed_tree.add(f"[italic]{name}[/italic]")

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


def main():
    parser = argparse.ArgumentParser(
        description="Extract documents from Google Takeout for Paperless-ngx"
    )
    parser.get_default = lambda dest: None
    parser.add_argument(
        "input_dir", nargs="?", default=".", help="Directory containing archives"
    )
    parser.add_argument("-o", "--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        if TakeoutExtractor(args.input_dir, args.output).run():
            return
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")


if __name__ == "__main__":
    main()
