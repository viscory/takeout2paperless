"""Report data model and rich rendering."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree


@dataclass
class Report:
    """Mutable accumulator for extraction results."""

    processed: int = 0
    skipped: int = 0
    errors: int = 0

    processed_files: list[str] = field(default_factory=list)
    skip_reasons: defaultdict[str, int] = field(default_factory=lambda: defaultdict(int))
    skip_examples: defaultdict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    archive_stats: list[dict[str, str | int]] = field(default_factory=list)
    output_dir: str = ""

    # ── Record helpers ─────────────────────────────────────────────

    def record_processed(self, filename: str) -> None:
        self.processed += 1
        self.processed_files.append(filename)

    def record_skip(self, reason: str, archive_path: str) -> None:
        self.skipped += 1
        self.skip_reasons[reason] += 1
        if len(self.skip_examples[reason]) < 3:
            self.skip_examples[reason].append(archive_path)

    # ── Rendering ──────────────────────────────────────────────────

    def render(self, console: Console) -> None:
        """Print a rich summary panel to *console*."""
        console.print()

        # ── Totals ──────────────────────────────────────────────
        totals = Table(show_header=False, box=None, padding=(0, 2))
        totals.add_column(style="bold cyan", justify="left")
        totals.add_column(justify="right")

        totals.add_row("Processed", str(self.processed))
        totals.add_row("Skipped", str(self.skipped))
        totals.add_row("Errors", str(self.errors))
        totals.add_row("Output dir", self.output_dir)

        # ── Per-archive table ───────────────────────────────────
        per_archive = Table(box=None, padding=(0, 2))
        per_archive.add_column("Archive", style="dim")
        per_archive.add_column("Files extracted", justify="right")
        for a in self.archive_stats:
            per_archive.add_row(str(a["archive"]), str(a["files"]))

        # ── Skipped breakdown (tree) ────────────────────────────
        skip_tree: Optional[Tree] = None
        if self.skip_reasons:
            skip_tree = Tree("[bold yellow]Skipped files[/bold yellow]")
            for reason, count in sorted(self.skip_reasons.items(), key=lambda x: -x[1]):
                branch = skip_tree.add(f"[dim]{reason}[/dim]  ([bold]{count}[/bold])")
                for ex in self.skip_examples.get(reason, []):
                    display = ex if len(ex) <= 70 else "…" + ex[-67:]
                    branch.add(f"[italic]{display}[/italic]")

        # ── Processed samples (tree) ────────────────────────────
        processed_tree: Optional[Tree] = None
        if self.processed_files:
            label = f"[bold green]Processed files ({len(self.processed_files)})[/bold green]"
            processed_tree = Tree(label)
            show = self.processed_files[:50]
            for name in show:
                processed_tree.add(f"[italic]{name}[/italic]")
            if len(self.processed_files) > 50:
                processed_tree.add(f"[dim]… and {len(self.processed_files) - 50} more[/dim]")

        # ── Assemble panel ──────────────────────────────────────
        layout = Table(show_header=False, box=None, padding=(0, 1))
        layout.add_row(totals)
        if self.archive_stats:
            layout.add_row(per_archive)
        if skip_tree:
            layout.add_row(skip_tree)
        if processed_tree:
            layout.add_row(processed_tree)

        console.print(
            Panel(
                layout,
                title="[bold white]Extraction Report[/bold white]",
                border_style="blue",
                padding=(1, 2),
            )
        )
        console.print()
