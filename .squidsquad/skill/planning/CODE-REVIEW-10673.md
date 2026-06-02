### Finding 1

- **File**: `references/scripts/v2_link_stage.py`
- **Line**: 55 (constant), 58-67 (predicate), 148-149 and 219-220 (call sites)
- **Severity**: warning
- **Issue**: The D2 filter `_is_sub_skill_body_in_instructions` uses a path-prefix check (`posix_path.startswith("references/sub-skills/")`) that cannot distinguish between sub-skill definition files (under `common/` and `roles/<role>/`) and event-mode common fragments (under `common-events/`). Both live under the same `references/sub-skills/` prefix and all such files with `slot: instructions` are dropped. Today this is harmless because common-events fragments do not carry `slot: instructions`, but the filter is structurally over-broad: should a future fragment legitimately use `slot: instructions` under `common-events/`, it would be silently dropped with no diagnostic.
- **Evidence**: `_walk_applicable_paths` (line 171-174) yields `references/sub-skills/common-events/**/*.md` and describes them as “event-mode common fragments … harmless to walk in polling-mode composes too, they're frontmatter-filtered.” The D2 predicate (line 63-67) treats **any** path under `references/sub-skills/` with `slot: instructions` as a sub-skill body. The `common-events` subtree is not excluded even though its contents are not sub-skill definitions. The project philosophy says “don't add error handling for scenarios that can't happen” — but this scenario *can* happen if a `common-events` fragment is given `slot: instructions`, and the resulting silent drop violates the principle that filters should be precise about what they suppress.
- **Suggested fix**: Either (a) narrow the path prefix to exclude `common-events/` explicitly, e.g. check `posix_path.startswith(_SUB_SKILLS_PATH_PREFIX) and "common-events" not in posix_path.split("/")[2:3]`, or (b) document in the module docstring that `common-events` instructions-slot files are also suppressed by design so the over-broadness is intentional and tested.

---

### Finding 2

- **File**: `references/scripts/v2_link_stage.py`
- **Line**: 149 (`_parse_all_applicable_sources`) and 220 (`collect_sources_for_validation`)
- **Severity**: warning
- **Issue**: The D2 sub-skill filter is applied in two independent functions that must stay in lockstep. `_parse_all_applicable_sources` (used by `emit_v2_linked`) and `collect_sources_for_validation` (used by A2f to feed the A2e validator) each contain their own copy of the filtering block:

  ```
  if _is_sub_skill_body_in_instructions(fm.slot, posix_path):
      continue
  ```

  If a future change modifies only one copy (e.g. adding an exception, changing the predicate, or switching to a different filtering approach), the validator and emitter will see different source-record sets. The validator would then greenlight content that the emitter later drops, or reject content that the emitter would have included — breaking the invariant that “the same record list is passed to validate_link_stage (A2e) BEFORE the emit step” (docstring line 270).
- **Evidence**: Lines 148-149 in `_parse_all_applicable_sources` and lines 219-220 in `collect_sources_for_validation` contain identical filtering logic with no shared call path. The two functions duplicate the walk + parse + roles-filter + D2-filter pipeline independently.
- **Suggested fix**: Extract a shared generator (e.g. `_iter_applicable_sources`) that yields `(slot_index, ordinal, posix_path, body, source_path)` and is consumed by both `_parse_all_applicable_sources` and `collect_sources_for_validation`. That way the D2 filter (and all other filters) lives in exactly one place. The current `collect_sources_for_validation` already returns `LinkStageSource` objects that carry `layer`; the shared generator can compute `posix_path` once and both consumers can derive what they need.

---

### Finding 3

- **File**: `tests/test_d2_link_stage_references.py`
- **Line**: 109, 119, 127, 148, 158, 162 (all `l4_path=Path("nonexistent.md")` call sites)
- **Severity**: warning
- **Issue**: Tests pass `l4_path=Path("nonexistent.md")` — a bare relative filename — to isolate D2’s emission contract from L4 file content. This works only as long as no file named `nonexistent.md` exists in the repo root (the test runner’s `cwd`). If such a file is ever created, all D2 tests will silently pick up real L4 ops from that file instead of `L4Document.empty()`, potentially masking regressions or causing spurious failures.
- **Evidence**: The test runner sets `cwd=str(TESTS_DIR.parent)` (repo root) in `run_tests.py` line 113. `Path("nonexistent.md")` resolves relative to that cwd. In `emit_v2_linked` (line 98), `Path(l4_path).is_file()` would return `True` and real L4 ops would be parsed, changing the composed output under test in an uncontrolled way.
- **Suggested fix**: Use an absolute path that is guaranteed not to exist, e.g. `Path(tmp_path) / "nonexistent.md"` in fixture-based tests, or a module-level sentinel like `_NO_L4 = Path("/dev/null/nonexistent.md")` (or a Windows-safe equivalent such as `Path("NUL")` / a path with a GUID component). This removes the ambient-dependency on the repo-root directory listing.