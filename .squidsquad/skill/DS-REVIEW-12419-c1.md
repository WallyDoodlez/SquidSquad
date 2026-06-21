I now have a thorough understanding of the diff and the surrounding code. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/wizard.py`
- **Line**: 226–227 (the `is_pre_stamp` determination), 31 (`PRE_VERSION_STAMP = "0.0.0"`)
- **Severity**: warning
- **Issue**: The sentinel value `"0.0.0"` used to represent "existing install with no version stamp" is indistinguishable from a legitimate version stamp of `"0.0.0"`. If an install is ever genuinely stamped `"0.0.0"` (e.g., as an initial bootstrap version), `migration_walk_plan` sets `is_pre_stamp=True` and `select_migration_chain` includes all migrations with `to <= target`, re-applying every migration on every installer run.
- **Evidence**: `installed_version()` returns `PRE_VERSION_STAMP` ("0.0.0") in three distinct cases: (a) the stamp line is absent (line 87), (b) the stamp value is empty (line 82, `val or PRE_VERSION_STAMP`), and (c) the config file is unreadable (line 86). In `migration_walk_plan` line 227, `is_pre_stamp = inst == PRE_VERSION_STAMP` cannot distinguish these from case (d) a config that literally reads `- **SquidSquad Version**: 0.0.0`. A genuine stamp of "0.0.0" would cause `is_pre_stamp=True`, treating the install as pre-1.0 and re-walking all migrations.
- **Suggested fix**: Use a sentinel that is not a valid version string, e.g. `None` or a special non-parseable string like `"<unstamped>"`, or return a separate flag from `installed_version`. Alternatively, document that "0.0.0" is a reserved sentinel and must never be used as a real version, then enforce this in `stamp_version`.

---

### Finding 2

- **File**: `references/scripts/wizard.py`
- **Line**: 120–131 (`list_migration_files`)
- **Severity**: warning
- **Issue**: `mig_dir.iterdir()` (line 120) is not wrapped in an exception handler. If the `references/migrations/` directory exists but is unreadable (permissions, filesystem error), `iterdir()` raises `OSError`, which propagates uncaught through `select_migration_chain` → `migration_walk_plan` → `cmd_migration_plan`, crashing the CLI. This violates the "never raises" / "returns `[]` when the directory is absent" degradation pattern established in the function's docstring.
- **Evidence**: The docstring (lines 107–112) says "Returns `[]` when the directory is absent" and the function already guards `mig_dir.is_dir()` returning `[]` when the path doesn't exist. But `is_dir()` returning `True` does not guarantee `iterdir()` will succeed — a readable directory entry with unreadable contents will cause `OSError` (e.g., `PermissionError`). The function does not catch this. The existing codebase at line 761 and line 1668 has the same unguarded `iterdir()` pattern, but those are in different operational contexts (rerun detection, seed copying) where a crash is arguably more acceptable than silently skipping migrations.
- **Suggested fix**: Wrap the `for p in mig_dir.iterdir():` loop in a `try: ... except OSError: return []` (or log and return the partial list). This matches the degradation promise in the docstring.

---

### Finding 3

- **File**: `references/scripts/wizard.py`
- **Line**: 174–177 (`stamp_version` CRLF detection)
- **Severity**: warning
- **Issue**: Newline-style detection only inspects `lines[0]`. If the file has inconsistent line endings (first line uses `\n`, later lines use `\r\n`), the `nl` variable is set to `"\n"` and all replacement/insertion lines use `"\n"`, producing a file with mixed line endings. More concretely, if `lines[0]` is a blank line (e.g., file starts with `\r\n` on a CRLF file), the detection is correct, but if the file starts with a UTF-8 BOM or the first line happens to be the last line (no trailing newline), detection could be wrong.
- **Evidence**: Lines 174–177:
  ```python
  nl = "\n"
  if lines and lines[0].endswith("\r\n"):
      nl = "\r\n"
  ```
  This assumes the first line's line ending represents the entire file. A config.md file is expected to be consistent, but the code's own `splitlines(keepends=True)` preserves whatever is there. The detection is fragile — it only takes one anomalous first line to mis-detect.
- **Suggested fix**: Scan all lines to determine the dominant line ending, or use `text.find("\r\n") != -1` on the raw text before splitting, or check the last line-ending-bearing line rather than exclusively the first. E.g.:
  ```python
  nl = "\r\n" if "\r\n" in text else "\n"
  ```

---

### Finding 4

- **File**: `references/scripts/wizard.py`
- **Line**: 90–103 (`installer_version`), 145–146 (`select_migration_chain`), 228 (`migration_walk_plan`)
- **Severity**: warning
- **Issue**: When `installer_version()` returns `None` (VERSION file missing, empty, or unreadable), `select_migration_chain(inst, None)` is called (line 228 falls through because `is_fresh` is False). Inside `select_migration_chain`, `_version_key(None)` returns `(-1,)` (line 59–60), and the filter condition `inst_k < _version_key(mig["to"]) <= (-1,)` fails for all migrations (no valid version tuple is `<= (-1,)`). The chain is `[]`, and `migration_walk_plan` reports `is_noop=True` with `installer_version: None`. This is operationally correct (don't migrate when target unknown), but the plan collapses two distinct states — "target version unknown" and "everything up to date" — into the same `is_noop=True` signal. The runbook must remember to check `installer_version` separately.
- **Evidence**: At line 103, `installer_version` returns `None` when VERSION is unreadable. At line 228, `chain = [] if is_fresh else select_migration_chain(inst, instlr, base_dir)` — when `instlr` is `None`, this calls `select_migration_chain(inst, None)`. Line 146: `tgt_k = _version_key(None)` → `(-1,)`. Line 149: `if inst_k < _version_key(mig["to"]) <= (-1,)` — this is always False for any valid migration `to` version (which is a tuple of non-negative ints). Chain is empty, `is_noop` becomes True. The runbook consuming `is_noop` alone would incorrectly treat "can't determine target" identically to "no migrations needed."
- **Suggested fix**: Either (a) make `select_migration_chain` return a sentinel (e.g., `None`) when `target` is `None` and have `migration_walk_plan` set a distinct field like `"target_unknown": True`, or (b) have `migration_walk_plan` detect `installer_version is None` and set `is_noop=True` with an additional diagnostic field such as `"error": "installer version unknown"`. This lets the runbook surface the distinction to the operator.

---

### Finding 5

- **File**: `references/scripts/wizard.py`
- **Line**: 81–82 (`installed_version`)
- **Severity**: warning
- **Issue**: The stamp-line value extraction `stripped.split(":", 1)[1].strip()` can inadvertently capture trailing content if a human has annotated the stamp line. For example, `- **SquidSquad Version**: 0.44.0  # was 0.43.0` would yield `val = "0.44.0  # was 0.43.0"`. This string is then passed to `_parse_version` → `_version_key`, which would fail to parse `"0.44.0  # was 0.43.0"` (the last segment `"0  # was 0"` or similar is not an int), returning `(-1,)` — treating the install as junk/pre-everything and causing all migrations to be selected. Since `stamp_version` always writes a clean `- **SquidSquad Version**: <version>` line (line 173), this only matters if a human edits the file, but the consequence is severe (all migrations re-applied).
- **Evidence**: Line 81–82: `val = stripped.split(":", 1)[1].strip()`. This keeps everything after the first `:` on the stamp line. A human adding a trailing comment would cause `_parse_version` to return `None` (because the comment text breaks `int()`), and `_version_key` returns `(-1,)` (pre-everything), causing `select_migration_chain` to include every migration with `to <= target`.
- **Suggested fix**: Split on whitespace after extracting the value, taking only the first token: `val = stripped.split(":", 1)[1].strip().split()[0]` if `val` else `""`. Or validate that the extracted value parses as a version and fall back to `PRE_VERSION_STAMP` if not. This makes `installed_version` robust against human annotations.

---

### Finding 6

- **File**: `references/scripts/wizard.py`
- **Line**: 179–181 (the replace-match loop), 180 (`line.strip().startswith(...)`)
- **Severity**: warning
- **Issue**: The stamp-line matching in `stamp_version` uses `line.strip().startswith("- **SquidSquad Version**:")` (line 180), but the replacement line is constructed as `new_line = f"- **SquidSquad Version**: {version}"` (line 173). If the existing stamp line has different formatting — e.g., extra whitespace, a different bullet style (`*` instead of `-`), or the field name spelled differently — the match will fail, `replaced` stays `False`, and a *second* stamp line is inserted. The file ends up with two version stamps, and `installed_version` reads only the first one it encounters (line 78, the `for` loop returns on first match).
- **Evidence**: Lines 179–181 look for `line.strip().startswith("- **SquidSquad Version**:")`. If the existing line is `* **SquidSquad Version**: 0.44.0` (asterisk bullet) or `- **SquidSquad Version** : 0.44.0` (space before colon), the match fails. The code inserts a new stamp line (lines 184–191), producing duplicate stamps. The `installed_version` reader at line 78–82 returns on the *first* match, so the new stamp is effectively invisible — the old (wrong-format) stamp is read instead. This is a silent failure.
- **Suggested fix**: Broaden the match to handle formatting variance, e.g., `line.strip().startswith("- **SquidSquad Version**")` and then check for `:` after, or use a regex like `r"^\s*[-*]\s+\*\*SquidSquad Version\*\*\s*:"`. This ensures a pre-existing stamp line in any reasonable format is replaced rather than duplicated.

---