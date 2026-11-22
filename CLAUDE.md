# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A CLI that detects and fixes Chinese (simplified/traditional) kanji misused in Japanese text. All code is in `ja_kanji_lint.py`, which must stay a single file using only the Python 3.11+ standard library. There is no build step, linter config, or package manifest. `README.md` is the user-facing reference for options and detection categories, with English first and Japanese second. Update both halves when behavior changes. User-facing messages and code comments are in Japanese.

## Commands

```bash
# Run the test suite (all cases live in selftest(); exits 0 on pass, 1 on failure)
python3 ja_kanji_lint.py --selftest

# Report on the sample fixtures (exit 1 is expected because they contain errors)
python3 ja_kanji_lint.py testdata

# Preview fixes without writing
python3 ja_kanji_lint.py testdata --diff

# Exercise one function (-B avoids leaving __pycache__ in the repo)
python3 -B -c "import ja_kanji_lint as f; print(f.scan_text('关门と西澤'))"
```

`selftest()` cannot run individual cases. To check one behavior, call the function directly as above.

- Scanning `.` from the repo root reports the README and fixtures, which contain Chinese characters on purpose. In a directory walk, `iter_files` skips the script itself, `DEFAULT_EXCLUDES`, and Git-ignored paths.
- Do not run `--fix` on `testdata/`. The fixtures contain errors on purpose, so copy them elsewhere first.

## Architecture

`main()` runs a linear pipeline: `iter_files` → `FileScanner.classify` → `FileScanner.scan` → report → `print_diff` / `apply_fix`.

**Git integration.** `git_ignored_paths` calls `git ls-files` once per repository. Scanned repositories are untrusted, so every call must keep `core.fsmonitor=false`, because that setting can run arbitrary commands. It also clears `GIT_*` variables so the tool works inside Git hooks. Paths are compared through `_path_key` because macOS Git returns NFC names while the filesystem can return NFD.

**Scan regions.** `scan` computes per-line column spans, and all detection and fixing happens only inside them. Documents use whole lines. Code uses `iter_comment_spans` after `mask_multiline_strings` blanks multi-line strings, unless `--include-strings` selects whole lines. With `--l10n`, translation files use `locale_value_spans`, which excludes keys. `classify` checks `DOC_EXTS` before `EXT_LANG`, so an extension in both (`.tex`) or added through `--ext` is scanned as a whole document, even a code extension like `.py`. `protected_spans` removes URLs, Markdown code and link targets, HTML `href`/`src`, and JSON keys from fixing, but they are still reported.

**Detection and fixing are separate code paths.** The `scan_*` functions produce findings, while `fix_region` produces the rewritten text. A new rule usually needs:
- a change on both sides, with any flag gating both equally (see how `--no-typos` and `--width` are handled);
- an entry in `KIND_LABEL`, because `print_report` raises `KeyError` on an unknown kind.

`apply_spans` applies fixes back to front because a fix can change the text length and would otherwise shift later spans.

**Character tables.**
- `_MAP_SRC` builds `MAP`, the auto-fixed one-to-one pairs.
- `_REVIEW_SRC` and the literal entries form `AMBIGUOUS`, which is report-only, for characters with several candidates or valid Japanese uses (names, old forms).
- `_CHINESE_WORDS` and `_JAPANESE_WORDS` narrow `AMBIGUOUS` by context in `is_ambiguous_use`. Common Japanese kanji such as 机 and 据 are reported only inside listed Chinese words. Japanese words are checked first, so 回数据え置き is not read as 数据 and 若干部分 is not read as 干部.
- `SUSPICIOUS` is report-only, for Chinese function characters.
- `is_simplified_only` also reports characters that are in GB2312 but in neither JIS X 0208/0213 nor Big5.

Never use "not encodable in Shift-JIS" alone as evidence that a character is not Japanese. Real names such as 森鷗外 and 草彅剛 fail that test, and many Taiwanese characters are valid Japanese. Import fails on malformed tokens, self-mappings, conflicting mappings, overlap between `MAP` and the report-only tables, or a `MAP` key that is in cp932 or in both the JIS and Big5 sets.

**Output and exit codes.** Exit status is 2 for errors, 1 for findings in the `--fail-on` kinds (all kinds by default), and 0 otherwise. It is computed before fixes are applied, so a successful `--fix` still returns 1. With `--json`, stdout must contain only JSON, so diffs and backup notices go to stderr.

**File writes.** `apply_fix` writes through a temp file and `os.replace`, preserving permissions, BOMs, UTF-16/32 byte order, and line endings. Keep these guarantees when changing it. `main` skips `*.bak-ja-kanji-lint` in every mode so backups are never rewritten.

**Global state.** `--ext` and `--words` mutate the module-level `DOC_EXTS` and `TYPO_WORDS`, so repeated `main()` calls in one process share those changes.
