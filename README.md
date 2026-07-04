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

| Format       | Extension(s)                     | Backend            | Notes |
|--------------|----------------------------------|--------------------|-------|
| ZIP          | `.zip`                           | `zipfile` (stdlib) | True streaming |
| TAR (gzip)   | `.tar.gz`, `.tgz`                | `tarfile` (stdlib) | True streaming |
| TAR (bzip2)  | `.tar.bz2`                       | `tarfile` (stdlib) | True streaming |
| TAR (xz)     | `.tar.xz`                        | `tarfile` (stdlib) | True streaming |
| TAR (uncomp) | `.tar`                           | `tarfile` (stdlib) | True streaming |
| 7-Zip        | `.7z`                            | `py7zr`            | Extracts to scratch disk first (~1× archive size) |

## Quick start

```bash
git clone https://github.com/viscory/takeout2paperless.git
cd takeout2paperless
uv sync

# Copy the example config and edit it to your needs
cp config/example.toml config.toml

# Run it
uv run python -m takeout2paperless
# or, from anywhere:
takeout2paperless --config /path/to/config.toml
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## Configuration

Everything is driven by `config.toml` at the project root.  There are
**no required command-line arguments** (`--config` is optional).

A fully annotated example lives at [`config/example.toml`](config/example.toml) —
copy it and customise:

```toml
[takeout2paperless]
input_dir = "."
output_dir = "paperless_ready"
dry_run = false
fingerprint = false

[filter]
include_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

[exclude]
ban = [
    # (?i) makes the pattern case-insensitive
    "(?i)(?:^|/)google photos(?:/|$)",
    "(?i)(?:^|/)trash(?:/|$)",
]
```

### All config keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `input_dir` | string | `"."` | Directory containing your archive files |
| `output_dir` | string | `"paperless_ready"` | Where to place extracted documents |
| `fingerprint` | boolean | `false` | Encode original directory path into filename |
| `fingerprint_delimiter` | string | `"_"` | Character joining path components when fingerprinting |
| `dry_run` | boolean | `false` | When `true`, no files are written |
| `filter.include_extensions` | list | `.pdf`, `.docx`, … | File extensions to extract (always case-insensitive) |
| `exclude.ban` | list of strings | `(?i)google photos`, `(?i)trash` | Regex patterns. Checked against filename **and** full archive path. |

### Regex notes

- **No global case-insensitive flag** — if you want case-insensitive matching, add `(?i)` at the start of your pattern.
- **Directory patterns** should use `(?:^|/)name(?:/|$)` so they match only as path components, not substrings inside filenames.
- **Filename patterns** should use `^` anchors to avoid matching inside a full path.

### Example: fingerprint to distinguish sources

```toml
[takeout2paperless]
fingerprint = true
fingerprint_delimiter = "_"
```

```
Takeout/Drive/Documents/report.pdf  →  Takeout_Drive_Documents_report.pdf
Takeout/Drive/Invoices/report.pdf   →  Takeout_Drive_Invoices_report.pdf
```

### Example: block files by custom naming convention

```toml
[exclude]
ban = [
    "(?i)^\\d{4}_[a-z]\\d{2}_(?:qp|ms)\\.pdf$",
    "(?i)^thumb_.*\\.jpg$",
]
```

## Edge cases

- **Dotfiles and extensionless files** — `Path("report").suffix` is `""`, so a file literally named `.pdf` (or one with no extension) never matches `filter.include_extensions` and is silently skipped. This is by design; use a regex in `exclude.ban` if you need to handle such files explicitly.

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
├── config.toml                 # Your local config (gitignored)
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
