# Conversation & Decision Changelog

> **Rule:** Every conversation with an AI agent about this project is recorded here.
> Append only — do not edit past entries.
> Each entry must include: date, trigger, what happened, what changed, and why.

---

## 2026-07-04 — Entry 001

**Trigger:** User asked to unify exclusion patterns into a single `ban` list (like immich's `ban-file`) and adopt the brain repo's CHANGELOG.md + pre-commit hook workflow.

**What happened:**
- Replaced `[exclude.directories]`, `[exclude.directory_patterns]`, and `[exclude.filename_patterns]` with a single `[exclude] ban = [...]` list.
- Every entry is compiled as a case-insensitive regex and checked against both the filename and the full archive path.
- Removed `name` fields from patterns — the list is just raw strings.
- Updated `config.py` parser, `extractor.py` filtering logic, and both `config.toml` and `example.toml`.
- Updated all tests (`test_config.py`, `test_extractor.py`) for the new `ban` field.
- Created `CHANGELOG.md` and installed the pre-commit hook that enforces a new entry on every commit.

**Files changed:**
- `config.toml`
- `config/example.toml`
- `src/takeout2paperless/config.py`
- `src/takeout2paperless/extractor.py`
- `tests/test_config.py`
- `tests/test_extractor.py`
- `CHANGELOG.md` (created)
- `.git/hooks/pre-commit` (installed)

**Why:** The previous three-section exclusion config was verbose and harder to maintain. A single `ban` list mirrors immich-go's `ban-file` signature, making the mental model consistent across projects. The pre-commit hook ensures every commit is documented with intent (Trigger / What happened / Why), preventing the project from losing context over time.

---

## 2026-07-04 — Entry 002

**Trigger:** User asked to prompt for Paperless consumption after the extraction report finishes.

**What happened:**
- Added `[paperless]` config section with optional `consume_cmd`.
- After `TakeoutExtractor.run()` renders the report, `cli.py` now prompts:
  "Consume extracted files with Paperless? [y/N]" (default No).
- If the user confirms and `consume_cmd` is set, the command runs with `{output_dir}` substituted.
- If `consume_cmd` is not configured, a helpful hint is printed showing how to set it up.
- Prompt is skipped in dry-run mode or when no files were processed.
- Updated `config.py`, `cli.py`, `config.toml`, `example.toml`, and all tests.

**Files changed:**
- `src/takeout2paperless/cli.py`
- `src/takeout2paperless/config.py`
- `config.toml`
- `config/example.toml`
- `tests/test_extractor.py`
- `CHANGELOG.md`

**Why:** Manual extraction is only half the workflow — getting files into Paperless is the goal. A prompt at the end of the run removes the need to remember a separate command. Making it optional (default No) and configurable keeps the tool unopinionated while still convenient for the user's Docker-based Paperless setup.

---

## 2026-07-04 — Entry 003

**Trigger:** User said "fuck the cli" — they want the tool to just extract files without any post-run prompt. They also wanted all directory ban entries converted to proper regex patterns.

**What happened:**
- Reverted `cli.py` back to a simple extractor run — no Paperless prompt.
- Removed `paperless_consume_cmd` from `Config` dataclass and parser entirely.
- Converted all directory names in `ban` to regex patterns using `(?:^|/)name(?:/|$)`.
  This ensures "config" only matches `.config/` or `config/` as a path component,
  not `myconfig.txt` or `reconfigurable`.
- Updated `config.toml` and `example.toml` with the new regex patterns.

**Files changed:**
- `src/takeout2paperless/cli.py`
- `src/takeout2paperless/config.py`
- `config.toml`
- `config/example.toml`
- `CHANGELOG.md`

**Why:** The user wants a simple unix-style tool: do one thing (extract), do it well, exit. No interactive prompts. Regex patterns for directories prevent false positives where a directory name happens to appear inside a filename or another directory name.
