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
- `src/paperless_py/config.py`
- `src/paperless_py/extractor.py`
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
- `src/paperless_py/cli.py`
- `src/paperless_py/config.py`
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
- `src/paperless_py/cli.py`
- `src/paperless_py/config.py`
- `config.toml`
- `config/example.toml`
- `CHANGELOG.md`

**Why:** The user wants a simple unix-style tool: do one thing (extract), do it well, exit. No interactive prompts. Regex patterns for directories prevent false positives where a directory name happens to appear inside a filename or another directory name.

---

## 2026-07-04 — Entry 004

**Trigger:** User asked to remove `re.IGNORECASE` (user controls casing via `(?i)`), add customizable `fingerprint_delimiter`, and address all 8 open GitHub issues.

**What happened:**
- Removed global `re.IGNORECASE` from regex compilation. Default patterns now include `(?i)` inline; user patterns must add `(?i)` themselves for case-insensitive matching.
- Added `fingerprint_delimiter` config key with validation (must be a single safe character: a-z, A-Z, 0-9, `-`, `_`, `.`).
- Removed `config.toml` from git tracking (added to `.gitignore`, `git rm --cached`).
- Fixed tar streaming (#2): replaced `src.read()` with temp-file + `shutil.copyfileobj` to avoid loading entire tar members into RAM.
- Fixed 7z metadata copy (#7): changed `shutil.copy2` to `shutil.copyfile` in `_iter_7z`.
- Fixed progress bar math (#5): outer bar now advances by exactly 1 per completed archive instead of fractional per-file increments.
- Fixed double archive open (#4): removed `count_entries` pre-count; file-level progress bar is now indeterminate (`total=None`).
- Added `--config` CLI flag (#6) so the installed console script works from any directory.
- Fixed `__import__("logging")` hack and `tomllib.loads(p.read_text())` (#7): now uses normal `import logging` and `tomllib.load(f)` with bytes.
- Added fingerprint tests (#8): `test_fingerprint_encoding`, `test_fingerprint_delimiter`, `test_collision_avoidance_with_fingerprint`.
- Documented dotfile/extensionless skip and 7z scratch-disk requirement in README.

**Files changed:**
- `src/paperless_py/config.py`
- `src/paperless_py/extractor.py`
- `src/paperless_py/archive.py`
- `src/paperless_py/cli.py`
- `tests/test_config.py`
- `tests/test_extractor.py`
- `.gitignore`
- `README.md`
- `CHANGELOG.md`

**Why:** The user wants full control over regex casing. The delimiter customization makes fingerprint output style configurable. Addressing all 8 GitHub issues cleans up technical debt (streaming, progress math, config leakage, CLI portability) before the tool is used on real multi-GB Takeout archives.

---

## 2026-07-04 — Entry 005

**Trigger:** User said the `fingerprint_delimiter` validation is too restrictive — they don't want to be forced to use `_`.

**What happened:**
- Removed all character restrictions on `fingerprint_delimiter`.
- It now accepts any string (including multi-character tokens like `__` or `→`).
- Only fallback is when the value is not a string at all (e.g. a number).
- Updated tests to verify multi-character delimiters work.
- Updated example.toml and README docs.

**Files changed:**
- `src/paperless_py/config.py`
- `tests/test_config.py`
- `config/example.toml`
- `README.md`
- `CHANGELOG.md`

**Why:** The user wants full freedom. If they want `→` or `__` or `·` as their delimiter, that's their choice. No paternalistic "safe character" restrictions.

---

## 2026-07-04 — Entry 006

**Trigger:** User asked to close the addressed GitHub issues now that fixes are in master.

**What happened:**
- Closed issues #1 through #8 with reference to commit `c9e7001` and the current commit.

**Files changed:**
- GitHub issues (via `gh issue close`)

**Why:** Issues that have been fixed in code should be closed so the tracker reflects reality and future contributors don't waste time re-reporting fixed problems.

---

---

## 2026-07-04 — Entry 008

**Trigger:** User asked to publish paperless-py as a package so `brain/scripts` can depend on it.

**What happened:**
- Exported `Config`, `TakeoutExtractor`, `Report` from `__init__.py` for library use.
- Bumped version to 0.3.0.
- Built wheel and sdist: `uv build`.
- Added `paperless-py` as a path dependency in `brain/scripts/pyproject.toml` via `[tool.uv.sources]`.
- Added `takeout-extract` console script in `brain/scripts` pointing to `paperless_py.cli:main`.
- Verified `uv sync` resolves and installs the package in brain/scripts venv.
- Verified `uv run takeout-extract --help` and `from paperless_py import Config` both work.

**Files changed:**
- `src/paperless_py/__init__.py`
- `pyproject.toml` (version bump)
- `dist/` (wheel + sdist built)
- `brain/scripts/pyproject.toml`

**Why:** The tool started as a standalone script but the user wants to orchestrate it from their brain automation suite. Publishing as a proper package with a public API (`Config`, `TakeoutExtractor`, `Report`) makes it composable — brain scripts can import and drive it programmatically, not just shell out to it.

---

## 2026-07-04 — Entry 007

**Trigger:** User said the config sectioning didn't make sense and asked for better organization, comments, and a few easy new features.

**What happened:**
- Restructured config into 5 logical sections:
  - `[paths]` — input_dir, output_dir
  - `[include]` — extensions
  - `[exclude]` — patterns (renamed from `ban` for clarity)
  - `[output]` — fingerprint, fingerprint_delimiter, flatten, collision, dry_run
  - `[runtime]` — log_level
- Added `flatten` option (default true). When false, original archive directory structure is preserved under output_dir.
- Added `collision` option (rename/skip/overwrite). Handles what happens when an output file already exists.
- Added `log_level` option (DEBUG/INFO/WARN/ERROR). Sets Python logging level at startup.
- Renamed `exclude.ban` → `exclude.patterns` for clarity.
- Moved `dry_run` from `[takeout2paperless]` to `[output]` since it controls output behaviour.
- Updated `config.toml`, `example.toml`, `config.py`, `extractor.py`, `cli.py`, tests, and README.

**Files changed:**
- `src/paperless_py/config.py`
- `src/paperless_py/extractor.py`
- `src/paperless_py/cli.py`
- `config.toml`
- `config/example.toml`
- `tests/test_config.py`
- `tests/test_extractor.py`
- `README.md`
- `CHANGELOG.md`

**Why:** The old `[takeout2paperless]` / `[filter]` / `[exclude]` split was arbitrary. `[paths]`, `[include]`, `[exclude]`, `[output]`, `[runtime]` maps directly to what the user is thinking about: where are my files, what do I want, what do I skip, how should they look, and how should the tool behave. The new features (flatten, collision, log_level) are small additions that significantly improve flexibility without adding complexity.
