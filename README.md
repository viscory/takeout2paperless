# takeout2paperless

Extract documents from Google Takeout archives (`.zip`) for import into [Paperless-ngx](https://docs.paperless-ngx.com/).

## Why?

Google Takeout dumps everything — documents, photos, videos, Google Photos metadata — into a set of multi-volume zip archives with deeply nested directories. This tool:

- Scans your Takeout folders inside each archive
- Extracts only document files (PDF, Word, Excel, CSV, TXT)
- **Skips media** (photos, videos, Google Photos noise)
- **Skips Trash** — anything under a `Trash` folder
- **Skips exam papers** — Cambridge-style question papers, mark schemes, examiner reports, grade thresholds, etc.
- Flattens the output into a single directory with unique filenames to avoid collisions (e.g. `document.pdf`, `document_1.pdf`)
- Prints a detailed report showing what was processed, skipped (with reasons and examples), and any errors

## Usage

```
uv run python main.py [input_dir] [-o output_dir] [-v]
```

| Argument      | Default             | Description                           |
|---------------|---------------------|---------------------------------------|
| `input_dir`   | `.` (current dir)   | Directory containing your `.zip` files|
| `-o` / `--output` | `paperless_ready` | Where to place extracted documents |
| `-v` / `--verbose` | —              | Enable debug logging                  |

### Example

```bash
# Extract from the current directory
uv run python main.py

# Specify a Takeout directory
uv run python main.py ~/Downloads/Takeout

# Custom output + verbose
uv run python main.py ~/Downloads/Takeout -o ~/Documents/to_import -v
```

## Installation

```bash
git clone https://github.com/viscory/takeout2paperless.git
cd takeout2paperless
uv sync
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## What gets extracted?

| Extension | Included? |
|-----------|-----------|
| `.pdf`    | ✅ (unless it matches an exam paper pattern) |
| `.docx`   | ✅ |
| `.doc`    | ✅ |
| `.xlsx`   | ✅ |
| `.xls`    | ✅ |
| `.csv`    | ✅ |
| `.txt`    | ✅ |
| Everything else | ❌ skipped |

## What gets skipped?

- **Google Photos** — entire `Google Photos/` path
- **Trash** — anything containing `Trash` in the path
- **Exam papers** — files matching `{subject}_{session}_{component}_{paper}.pdf` (e.g. `1123_w15_ms_21.pdf`) for common Cambridge components (question papers, mark schemes, examiner reports, grade thresholds, etc.)
- **All non-document extensions**
