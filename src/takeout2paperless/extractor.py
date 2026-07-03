"""Core extraction logic."""

from __future__ import annotations

import logging
import string
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from takeout2paperless.archive import (
    SUPPORTED_FORMATS,
    ArchiveEntry,
    count_entries,
    detect_format,
    iter_archive,
)
from takeout2paperless.reporter import Report

if TYPE_CHECKING:
    from takeout2paperless.config import Config

_logger = logging.getLogger(__name__)


class TakeoutExtractor:
    """Extract documents from a directory of Takeout archives."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._name_counter: dict[str, int] = defaultdict(int)
        self._report = Report(output_dir=str(config.output_dir))

    # ── Public API ─────────────────────────────────────────────────

    def run(self) -> Report:
        """Process all archives in *input_dir* and return the report."""
        self._config.output_dir.mkdir(parents=True, exist_ok=True)

        archives = sorted(
            p for p in self._config.input_dir.iterdir() if detect_format(p) is not None
        )

        if not archives:
            from rich.console import Console

            console = Console(stderr=True)
            console.print(
                f"[red]No supported archives found in[/red] "
                f"[cyan]{self._config.input_dir}[/cyan]\n"
                f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )
            return self._report

        from rich.console import Console
        from rich.progress import (
            BarColumn,
            Progress,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        console = Console()
        console.print(
            f"\n[bold]Found {len(archives)} archive(s)[/bold] "
            f"in [cyan]{self._config.input_dir}[/cyan]\n"
        )

        overall = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )

        with overall:
            overall_task = overall.add_task("Archives", total=len(archives))
            for arc in archives:
                overall.update(
                    overall_task,
                    description=f"Processing [cyan]{arc.name}[/cyan]",
                )
                self._process_archive(arc, console, overall, overall_task)

        self._report.render(console)
        return self._report

    # ── Internals ──────────────────────────────────────────────────

    def _process_archive(
        self, path: Path, console: Any, overall: Any | None = None, overall_task: Any | None = None
    ) -> None:
        """Process a single archive, updating *self._report*."""
        archive_name = path.name

        # Count entries first (metadata only, no content) for the progress bar
        try:
            total = count_entries(path)
        except Exception:
            _logger.exception("Failed to read archive '%s'", archive_name)
            self._report.errors += 1
            return

        if total == 0:
            return

        from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

        local_ok = 0

        file_progress = Progress(
            TextColumn("  [progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )

        with file_progress:
            file_task = file_progress.add_task(
                f"Files in [cyan]{archive_name}[/cyan]",
                total=total,
            )

            # Lazily iterate — never materialise all entries in RAM.
            # The archive handle stays open while we step through;
            # each entry streams its content chunk-by-chunk.
            try:
                entries = iter_archive(path)
            except Exception:
                _logger.exception("Failed to open archive '%s'", archive_name)
                self._report.errors += 1
                return

            for entry in entries:
                file_progress.update(
                    file_task,
                    description=f"  [dim]{entry.path}[/dim]",
                )

                extract, reason = self._check_entry(entry)
                if not extract:
                    self._report.record_skip(reason, entry.path)
                    file_progress.advance(file_task)
                    continue

                out_path = self._unique_path(entry.path)
                try:
                    if not self._config.dry_run:
                        entry.write_to(out_path)
                    self._report.record_processed(out_path.name)
                    local_ok += 1
                    _logger.debug("Extracted: %s -> %s", entry.path, out_path.name)
                except Exception:
                    _logger.exception("Error extracting '%s' from '%s'", entry.path, archive_name)
                    self._report.errors += 1

                file_progress.advance(file_task)
                if overall is not None and overall_task is not None:
                    overall.advance(overall_task, 1 / total if total else 0)

        if overall is not None and overall_task is not None:
            # Ensure we advance any remaining fractional progress
            overall.advance(overall_task, 0)

        self._report.archive_stats.append({"archive": archive_name, "files": local_ok})

    def _check_entry(self, entry: ArchiveEntry) -> tuple[bool, str]:
        """Decide whether *entry* should be extracted.

        Returns ``(extract?, human_reason)``.
        """
        lower = entry.path.lower()
        name = Path(entry.path).name

        # 1. Directory blocklist
        for blocked in self._config.exclude_directories:
            if blocked in lower:
                return False, f"Excluded directory ({blocked})"

        # 2. Extension check
        ext = Path(lower).suffix
        if ext not in self._config.target_extensions:
            return False, f"Not a target extension ({ext})"

        # 3. Filename regex blocklist
        for pat in self._config.exclude_filename_patterns:
            if pat.search(name):
                return False, "Blocked filename pattern"

        return True, "Target document"

    def _unique_path(self, original_name: str) -> Path:
        """Build a flat output path, appending ``_N`` on collisions.

        When ``fingerprint`` is enabled in config, the original directory
        path is encoded into the filename so you can tell where the file
        came from (e.g. ``Takeout_Drive_Documents_report.pdf``).
        """
        p = Path(original_name)
        basename = p.name

        if self._config.fingerprint:
            parent = p.parent
            if parent and parent != Path("."):
                safe = "".join(
                    c if c in string.ascii_letters + string.digits + "-_" else "_"
                    for c in parent.as_posix()
                )
                basename = f"{safe}_{basename}"

        stem, ext = Path(basename).stem, Path(basename).suffix
        count = self._name_counter[basename]
        self._name_counter[basename] += 1

        return self._config.output_dir / (basename if count == 0 else f"{stem}_{count}{ext}")
