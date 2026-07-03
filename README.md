# takeout2paperless

Extract documents from Google Takeout archives for import into
[Paperless-ngx](https://docs.paperless-ngx.com/).

Google Takeout dumps everything — documents, photos, videos, Google
Photos metadata — into multi-volume archives with deeply nested
directories.  This tool:

- Scans your Takeout archives in **all formats Google provides**
- Extracts only document files you care about
- Skips unwanted files based on a **single config file** — no CLI flags
- Flattens output into one directory with unique filenames
- Optionally **fingerprints** filenames with their original directory
  path so you can tell where each file came from
- Prints a detailed summary report

## Supported archive formats

| Format       | Extension(s)                     | Backend            |
|--------------|----------------------------------|--------------------|
| ZIP          | `.zip`                           | `zipfile` (stdlib) |
| TAR (gzip)   | `.tar.gz`, `.tgz`                | `tarfile` (stdlib) |
| TAR (bzip2)  | `.tar.bz2`                       | `tarfile` (stdlib) |
| TAR (xz)     | `.tar.xz`                        | `tarfile` (stdlib) |
| TAR (uncomp) | `.tar`                           | `tarfile` (stdlib) |
| 7-Zip        | `.7z`                            | `py7zr`            |

## Quick start

```bash
git clone https://github.com/viscory/takeout2paperless.git
cd takeout2paperless
uv sync

# Copy the example config and edit it to your needs
cp config/example.toml config.toml

# Run it
uv run python -m takeout2paperless
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## Configuration

Everything is driven by `config.toml` at the project root.  There are
**no command-line arguments**.

A fully annotated example lives at [`config/example.toml`](config/example.toml) —
copy it and customise:

```toml
input_dir = "."
output_dir = "paperless_ready"

target_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

[exclude.directories]
"google photos" = true
trash = true

[exclude.filename_patterns]
# "exam-papers" = "^\\d{4}_[a-z]\\d{2}_(?:qp|ms|er|gt|ir|sy|sr|ci|sm|in|tn|sp|nt|sf)(?:_\\d{1,3})?\\.pdf$"

dry_run = false
fingerprint = false
```

### All config keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `input_dir` | string | `"."` | Directory containing your archive files |
| `output_dir` | string | `"paperless_ready"` | Where to place extracted documents |
| `target_extensions` | list of strings | `.pdf`, `.docx`, … | File extensions to extract (case-insensitive) |
| `[exclude.directories]` | table | — | Map of path fragments to boolean. `true` = skip files whose path contains this fragment. Omit or set to `false` to allow. |
| `[exclude.filename_patterns]` | table | — | Map of named regex patterns. Files whose **filename** matches any pattern are skipped (case-insensitive). |
| `dry_run` | boolean | `false` | When `true`, no files are written. Useful for testing your rules. |
| `fingerprint` | boolean | `false` | When `true`, the original directory path is encoded into the filename (e.g. `Takeout_Drive_Documents_report.pdf`) |

### Example: fingerprint to distinguish sources

```toml
fingerprint = true
```

```
Takeout/Drive/Documents/report.pdf  →  Takeout_Drive_Documents_report.pdf
Takeout/Drive/Invoices/report.pdf   →  Takeout_Drive_Invoices_report.pdf
```

### Example: only block Trash, allow Google Photos

```toml
[exclude.directories]
"google photos" = false
trash = true
```

### Example: block files by custom naming convention

```toml
[exclude.filename_patterns]
"thumbnails" = "^thumb_.*\\.jpg$"
"system-files" = "\\.DS_Store$"
```

## Development

```bash
uv sync --extra dev

# Run tests
uv run pytest -v

# Type-check
uv run mypy src/

# Lint
uv run ruff check src/ tests/
```

## Project layout

```
takeout2paperless/
├── config.toml                 # Your config (loaded at runtime)
├── config/
│   └── example.toml            # Annotated example with every option explained
├── src/takeout2paperless/
│   ├── __init__.py
│   ├── __main__.py             # python -m takeout2paperless
│   ├── config.py               # Config loading & validation (TOML)
│   ├── archive.py              # Unified .zip / .tar.* / .7z reader
│   ├── extractor.py            # Core extraction + fingerprint logic
│   ├── reporter.py             # Rich report rendering
│   └── cli.py                  # Entry point
├── tests/
│   ├── conftest.py             # Generates small archives in all 3 formats
│   ├── test_config.py
│   ├── test_archive.py
│   └── test_extractor.py
└── pyproject.toml
```
