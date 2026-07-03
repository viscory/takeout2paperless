# takeout2paperless

Extract documents from Google Takeout archives (`.zip`) for import into [Paperless-ngx](https://docs.paperless-ngx.com/).

Google Takeout dumps everything — documents, photos, videos, Google Photos metadata — into multi-volume zip archives with deeply nested directories. This tool:

- Scans your Takeout folders inside each archive
- Extracts only document files (PDF, Word, Excel, CSV, TXT)
- Skips unwanted files based on a **config file** — block directories (Google Photos, Trash) and filename regex patterns
- Flattens output into a single directory with unique filenames (e.g. `document.pdf`, `document_1.pdf`)
- Prints a detailed report showing what was processed, skipped (with reasons and examples), and any errors

## Usage

```
uv run python main.py [input_dir] [-o output_dir] [-c config] [-v]
```

| Argument               | Default             | Description                           |
|------------------------|---------------------|---------------------------------------|
| `input_dir`            | `.` (current dir)   | Directory containing your `.zip` files|
| `-o` / `--output`      | `paperless_ready` | Where to place extracted documents    |
| `-c` / `--config`      | `config.json`       | Path to configuration file            |
| `-v` / `--verbose`     | —                   | Enable debug logging                  |

### Examples

```bash
# Extract from the current directory
uv run python main.py

# Specify a Takeout directory
uv run python main.py ~/Downloads/Takeout

# Custom output + custom config
uv run python main.py ~/Downloads/Takeout -o ~/Documents/to_import -c my_config.json

# Verbose logging
uv run python main.py -v
```

## Installation

```bash
git clone https://github.com/viscory/takeout2paperless.git
cd takeout2paperless
uv sync
```

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

## Configuration

All skip rules live in `config.json`:

```json
{
  "target_extensions": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"],
  "exclude_directories": {
    "google photos": true,
    "trash": true
  },
  "exclude_filename_patterns": [
    "^\\d{4}_[a-z]\\d{2}_(?:qp|ms|er|gt|ir|sy|sr|ci|sm|in|tn|sp|nt|sf)(?:_\\d{1,3})?\\.pdf$"
  ]
}
```

| Key | Description |
|-----|-------------|
| `target_extensions` | File extensions to extract. Everything else is skipped. |
| `exclude_directories` | Map of directory names to boolean. Set any to `false` to allow files in that path. |
| `exclude_filename_patterns` | List of regex patterns. Files whose filenames match any pattern are skipped. |

### Example: only block Trash, nothing else

```json
{
  "exclude_directories": {
    "google photos": false,
    "trash": true
  },
  "exclude_filename_patterns": []
}
```

> **Note**: Regex patterns are compiled case-insensitively. Backslashes in JSON need to be escaped (`\\d` instead of `\d`). The `config.json` in this repo contains an example pattern — remove it or replace it with your own.
