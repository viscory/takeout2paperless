"""Core extraction logic."""

from __future__ import annotations

import logging
import string
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from paperless_py.archive import (
    SUPPORTED_FORMATS,
    ArchiveEntry,
    detect_format,
    iter_archive,
)
from paperless_py.reporter import Report

if TYPE_CHECKING:
    from paperless_py.config import Config

_logger = logging.getLogger(__name__)


class TakeoutExtractor:
    """Extract documents from a directory of Takeout archives."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._name_counter: dict[str, int] = defaultdict(int)
        self._seen_paths: set[Path] = set()
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
                self._process_archive(arc, console)
                overall.advance(overall_task)

        self._report.render(console)
        return self._report

    # ── Internals ──────────────────────────────────────────────────

    def _process_archive(self, path: Path, console: Any) -> None:
        """Process a single archive, updating *self._report*."""
        archive_name = path.name

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
                total=None,
            )

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

                out_path = self._resolve_output_path(entry.path)
                if out_path is None:
                    self._report.record_skip("Collision (skip)", entry.path)
                    file_progress.advance(file_task)
                    continue

                try:
                    if not self._config.dry_run:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        entry.write_to(out_path)
                    self._report.record_processed(out_path.name)
                    local_ok += 1
                    _logger.debug("Extracted: %s -> %s", entry.path, out_path.name)
                except Exception:
                    _logger.exception("Error extracting '%s' from '%s'", entry.path, archive_name)
                    self._report.errors += 1

                file_progress.advance(file_task)

        self._report.archive_stats.append({"archive": archive_name, "files": local_ok})

    def _check_entry(self, entry: ArchiveEntry) -> tuple[bool, str]:
        """Decide whether *entry* should be extracted.

        Returns ``(extract?, human_reason)``.
        """
        lower = entry.path.lower()
        name = Path(entry.path).name

        # 1. Unified ban list
        for pat in self._config.ban:
            if pat.search(name) or pat.search(entry.path):
                return False, "Banned pattern"

        # 2. Extension check
        ext = Path(lower).suffix
        if ext not in self._config.target_extensions:
            return False, f"Not a target extension ({ext})"

        return True, "Target document"

    def _resolve_output_path(self, original_name: str) -> Path | None:
        """Build the output path, applying fingerprint, flatten, and collision rules.

        Returns *None* when collision strategy is "skip" and the file already exists.
        """
        p = Path(original_name)
        basename = p.name
        delim = self._config.fingerprint_delimiter

        if self._config.fingerprint:
            parent = p.parent
            if parent and parent != Path("."):
                safe_chars = string.ascii_letters + string.digits + "-_"
                safe = "".join(c if c in safe_chars else delim for c in parent.as_posix())
                basename = f"{safe}{delim}{basename}"

        if self._config.flatten:
            out_path = self._config.output_dir / basename
        else:
            # Preserve original directory structure under output_dir
            out_path = self._config.output_dir / original_name

        if out_path in self._seen_paths:
            # We've already processed this exact path this run
            return self._handle_collision(out_path, basename)

        if not out_path.exists():
            self._seen_paths.add(out_path)
            return out_path

        return self._handle_collision(out_path, basename)

    def _handle_collision(self, out_path: Path, basename: str) -> Path | None:
        """Apply the configured collision strategy."""
        strategy = self._config.collision

        if strategy == "skip":
            return None

        if strategy == "overwrite":
            self._seen_paths.add(out_path)
            return out_path

        # strategy == "rename" (default)
        stem, ext = Path(basename).stem, Path(basename).suffix
        count = self._name_counter[basename]
        self._name_counter[basename] += 1

        if count == 0:
            resolved = out_path
        else:
            resolved = self._config.output_dir / f"{stem}_{count}{ext}"
            if not self._config.flatten:
                resolved = out_path.parent / f"{stem}_{count}{ext}"

        self._seen_paths.add(resolved)
        return resolved
