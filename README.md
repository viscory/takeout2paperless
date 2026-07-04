# paperless-py

Extract documents from Google Takeout archives for import into
[Paperless-ngx](https://docs.paperless-ngx.com/).

Google Takeout dumps everything — documents, photos, videos, Google
Photos metadata — into multi-volume archives with deeply nested
directories.  This tool:

- Scans your Takeout archives in **all formats Google provides**
- Extracts only document files you care about
- Skips unwanted files based on a **single config file**
- Flattens (or preserves) output directories
- Optionally **fingerprints** filenames with their original directory path
- Handles name collisions with rename / skip / overwrite strategies
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
git clone https://github.com/viscory/paperless-py.git
cd paperless-py
uv sync

# Copy the example config and edit it to your needs
cp config/example.toml config.toml

# Run it
uv run python -m paperless_py
# or, from anywhere:
paperless-py --config /path/to/config.toml
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## Configuration

Everything is driven by `config.toml`.  The only CLI argument is an
optional `--config PATH`.

A fully annotated example lives at [`config/example.toml`](config/example.toml) —
copy it and customise.

```toml
# ── Where to read and write ──────────────────────────────────────
[paths]
input_dir = "."
output_dir = "paperless_ready"

# ── What to extract ──────────────────────────────────────────────
[include]
extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"]

# ── What to skip ───────────────────────────────────────────────
[exclude]
patterns = [
    "(?i)(?:^|/)google photos(?:/|$)",
    "(?i)(?:^|/)trash(?:/|$)",
]

# ── How files are written ──────────────────────────────────────
[output]
dry_run = false
fingerprint = false
fingerprint_delimiter = "_"
flatten = true
collision = "rename"

# ── Execution behaviour ────────────────────────────────────────────
[runtime]
log_level = "INFO"
```

### All config keys

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `[paths]` | `input_dir` | string | `"."` | Directory containing your archive files |
| `[paths]` | `output_dir` | string | `"paperless_ready"` | Where to place extracted documents |
| `[include]` | `extensions` | list | `.pdf`, `.docx`, … | File extensions to extract (case-insensitive) |
| `[exclude]` | `patterns` | list of strings | `(?i)google photos`, `(?i)trash` | Regex patterns checked against filename **and** full archive path |
| `[output]` | `dry_run` | boolean | `false` | When `true`, no files are written |
| `[output]` | `fingerprint` | boolean | `false` | Encode original directory path into filename |
| `[output]` | `fingerprint_delimiter` | string | `"_"` | String joining path components when fingerprinting |
| `[output]` | `flatten` | boolean | `true` | When `true`, all files land directly in `output_dir`; when `false`, original directory structure is preserved |
| `[output]` | `collision` | string | `"rename"` | What to do when output filename exists: `rename` (append `_N`), `skip`, or `overwrite` |
| `[runtime]` | `log_level` | string | `"INFO"` | Verbosity: `DEBUG`, `INFO`, `WARN`, `ERROR` |

### Regex notes

- **No global case-insensitive flag** — add `(?i)` at the start of your pattern if you want case-insensitive matching.
- **Directory patterns** should use `(?:^|/)name(?:/|$)` so they match only as path components.
- **Filename patterns** should use `^` anchors to avoid matching inside a full path.

### Example: fingerprint to distinguish sources

```toml
[output]
fingerprint = true
fingerprint_delimiter = "_"
```

```
Takeout/Drive/Documents/report.pdf  →  Takeout_Drive_Documents_report.pdf
Takeout/Drive/Invoices/report.pdf   →  Takeout_Drive_Invoices_report.pdf
```

### Example: preserve directory structure

```toml
[output]
flatten = false
```

```
Takeout/Drive/Documents/report.pdf  →  paperless_ready/Takeout/Drive/Documents/report.pdf
```

### Example: block files by custom naming convention

```toml
[exclude]
patterns = [
    "(?i)^\\d{4}_[a-z]\\d{2}_(?:qp|ms)\\.pdf$",
    "(?i)^thumb_.*\\.jpg$",
]
```

### Example: skip on collision instead of renaming

```toml
[output]
collision = "skip"
```

## Edge cases

- **Dotfiles and extensionless files** — `Path("report").suffix` is `""`, so a file literally named `.pdf` (or one with no extension) never matches `include.extensions` and is silently skipped. Use a regex in `exclude.patterns` if you need to handle such files explicitly.

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
paperless-py/
├── config.toml                 # Your local config (gitignored)
├── config/
│   └── example.toml            # Annotated example with every option explained
├── src/paperless_py/
│   ├── __init__.py
│   ├── __main__.py             # python -m paperless_py
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
