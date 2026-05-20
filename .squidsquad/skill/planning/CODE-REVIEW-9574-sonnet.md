# Code Review — PR #9587 / Issue #9574
**Reviewer**: Claude Sonnet 4.6 (third-tier fallback)
**Date**: 2026-05-20
**Files reviewed**: `references/scripts/run_comprehension_test.py` (branch), `tests/test_9574_comprehension_runner_write_contract.py` (branch), `9587-diff.txt`

---

## Fix Verification

### Fix 1 — Prompt-shape pivot (Write-tool → chat-output harvesting)
**Works as described.** `_run_agent` now passes `--output-format json`, parses `data["result"]`, and the runner writes both files from Python. The old placeholder-on-failure path is gone and replaced with a hard `sys.exit(1)`. The eval agent receives answers embedded directly in the prompt, eliminating the Read-tool dependency for stage 2. Mechanically correct.

### Fix 2 — CLI flag ordering (`--output-format` before `--allowedTools`)
**Works as described.** The command list is built as `[claude_bin, "-p", prompt, "--output-format", "json"]` and `--allowedTools` is conditionally appended. The variadic-consumption hazard is correctly avoided. The `if allowed_tools:` guard correctly omits the flag for the eval agent (called with `allowed_tools=""`).

### Fix 3 — Windows `claude.cmd` bypass
**Partially works.** The hardcoded `npm_exe` path covers the standard global npm install on this machine (verified: `APPDATA/npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe` exists). However, two residual paths still return `.cmd`:

1. `shutil.which` returns `.CMD` but no sibling `.exe` exists at `APPDATA/npm/claude.exe` (confirmed absent on this machine). The sibling fallback in step 2a is dead in the default install layout.
2. The bottom fallback loop still returns `APPDATA/npm/claude.cmd` as a last resort — the exact pre-fix failure mode.

In practice, the hardcoded `npm_exe` path is hit first and the issue does not reappear on standard installs. But any non-standard npm prefix (e.g., `npm --prefix C:\tools install -g ...`) bypasses path 1, leaves path 2a dead, and hits path 3, re-triggering the original bug.

---

## Test Coverage Assessment

### Tests that are load-bearing (would catch the regression)

| Test | Would catch regression? |
|------|------------------------|
| `test_empty_agent_text_causes_nonzero_exit` | YES — pins exit-1 on empty output |
| `test_no_placeholder_answers_file_on_empty_output` | YES — pins no-placeholder contract |
| `test_valid_agent_output_writes_files_from_python` | YES — proves Python-side write path |
| `test_run_agent_passes_json_output_format` | YES — would fail if reverted to `--output-format text` |
| `test_output_format_precedes_allowed_tools` | YES — would fail if flag order reverted |
| `test_allowed_tools_omitted_when_empty` | YES — would fail if `--allowedTools ""` restored |
| `test_run_agent_returns_empty_on_is_error` | YES — pins is_error branch |
| `test_run_agent_returns_empty_on_malformed_json` | YES — pins JSON parse error path |
| `test_runner_source_does_not_instruct_write_tool` | **NO — see BLOCK finding below** |

### Findings

---

## BLOCK — `TestPromptDoesNotAskForWriteTool` passes on the pre-fix runner

**File**: `tests/test_9574_comprehension_runner_write_contract.py`, line 655–662

**Issue**: The forbidden phrase list (`"invoke the write tool"`, `"use the write tool"`, `"call the write tool"`, `"your final action must be the write"`) does not match the actual pre-fix prompt phrasing. The old `test_prompt` said `"3. Write ALL answers to: {answers_path}"` and the old `eval_prompt` said `"5. Write results as a JSON array to: {results_path}"`. None of these hit the forbidden list. This test would **pass on the pre-fix runner** — it does not detect the regression it claims to detect.

**Fix**: Add `"write all answers to"` and `"write results as a json array to"` to the `forbidden` list (case-insensitive match is already applied). Alternatively, assert that the prompt contains the required output-format instruction: `"runner harvests this text"` or `"--output-format json"` is the positive contract.

---

## MEDIUM — `_find_claude` fallback loop still returns `.cmd` on non-standard installs

**File**: `references/scripts/run_comprehension_test.py`, lines 96–100 (new runner)

**Issue**: The bottom fallback loop (`for candidate in [Path(APPDATA) / "npm" / "claude.cmd", ...]`) still returns `claude.cmd` when reached. If the npm prefix is non-standard (custom `--prefix`, scoop/winget/choco install, or APPDATA override), `npm_exe` won't exist, `shutil.which` returns `.CMD`, the sibling `.exe` check fails (`.exe` is not adjacent to `.cmd` in the npm layout, confirmed on this machine), and the loop returns the `.cmd`. The original bug reappears.

**Fix**: In the fallback loop, apply the same `.exe` preference logic — for each candidate ending in `.cmd`, try the hardcoded `npm_exe` path first (it's already computed above), or apply `with_suffix(".exe")` to the candidate path itself (even if `claude.exe` doesn't exist in npm/, the exe check would just fail and fall through cleanly):
```python
for candidate in [
    Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
    Path(os.environ.get("APPDATA", "")) / "npm" / "claude",
]:
    if candidate.exists():
        if candidate.suffix.lower() == ".cmd":
            exe_alt = candidate.with_suffix(".exe")
            if exe_alt.exists():
                return str(exe_alt)
        return str(candidate)
```
Or more simply, since `npm_exe` is already the canonical path: return `npm_exe` unconditionally at the top of the loop if it exists (it would have already been returned by the win32 block, so reaching here means it doesn't exist — the loop is the true fallback and the `.cmd` issue is a known risk).

---

## MEDIUM — `_find_claude` has zero unit tests

**File**: `tests/test_9574_comprehension_runner_write_contract.py`

**Issue**: The Windows-specific `_find_claude` fix — the primary author-claimed fix for #9574 — has no test coverage whatsoever. All 9 tests mock `_find_claude` away or mock `subprocess.run`. A future refactor could silently remove the `.exe` preference logic and no test would fail.

**Fix**: Add a `TestFindClaudeWindowsPreference` class:
- Mock `sys.platform` to `"win32"`, mock `Path.exists()` for the npm_exe path → assert the returned path ends in `.exe`.
- Mock `sys.platform` to `"linux"` → assert `shutil.which` result is returned as-is.
- Mock `.cmd` from `shutil.which` with sibling `.exe` present → assert sibling is returned.

---

## LOW — `_strip_outer_fences` returns untrimmed body when closing fence is absent

**File**: `references/scripts/run_comprehension_test.py`, `_strip_outer_fences`

**Issue**: If the agent wraps only the opening fence (e.g., ` ```json\n{...}`) but omits the closing, the function returns `body` without stripping. `body` in this case is everything after the first newline. For JSON output this is benign (the JSON parser handles it). For answers markdown it could include trailing whitespace. Not a correctness bug under normal operation.

**No fix required** — the function's docstring explicitly documents this limitation ("we tolerate exactly one outer layer").

---

## LOW — Error diagnostics don't cross-reference the returncode in the empty-content exit path

**File**: `references/scripts/run_comprehension_test.py`, lines ~195–207

**Issue**: When `answers_text.strip()` is empty AND `test_proc.returncode != 0`, the code prints a WARNING about the returncode and separately prints an ERROR about empty content and exits. The two messages are not linked — a human scanning stderr might not immediately connect that the empty content is the consequence of the non-zero exit. Minor UX issue, not a correctness bug.

**Fix** (optional): Include returncode in the empty-content error message: `"ERROR: test agent returned empty content (rc={test_proc.returncode}) — runner exiting 1."`.

---

## NIT — `f"ERROR: test agent returned empty content — runner exiting 1."` uses f-string unnecessarily

**File**: `references/scripts/run_comprehension_test.py`, lines ~200, ~281

**Issue**: f-string with no interpolation. Not a bug, but triggers linter warnings.

**Fix**: Remove the `f` prefix.

---

## NIT — `_make_proc` in tests uses a bare anonymous class instead of `SimpleNamespace`

**File**: `tests/test_9574_comprehension_runner_write_contract.py`, lines 372–379

**Issue**: `class _Proc: pass` works but `types.SimpleNamespace(stdout=..., stderr=..., returncode=...)` is the idiomatic stdlib pattern. Minor readability.

---

## Existing Spec Compatibility

All five reviewed specs (`1428`, `4792`, `8694`, `8697`, `9184`) are structurally identical and survive the pivot without change. The pivot:
- Stage 1: agent now returns answers in chat rather than writing a file. No spec changes needed.
- Stage 2: eval agent receives answers inline in the prompt instead of via a Read tool. No spec changes needed.
- The `--output-format json` change is transparent to spec consumers.

The 8694 spec (12 questions, 5 files) and 8697 spec (8 fixture files) are the largest. The inline-embed of answers into the eval prompt for 12 questions is slightly larger than the old "Read the answers file" pattern, but well within context budget. No risk of spec-shape breakage.

---

## Summary

The core fixes are correct and the primary regression (rc=0 + no files written on Windows) is fixed. Eight of nine tests are load-bearing. The one structural gap is the Write-tool test (BLOCK) — it passes vacuously on pre-fix code because the forbidden phrase list doesn't cover the actual pre-fix phrasing. The `_find_claude` fix covers the standard npm install but has a residual `.cmd` return path for non-standard installs, and has no test coverage.

**Recommended actions before merge:**
1. (Required) Fix the `TestPromptDoesNotAskForWriteTool` forbidden phrase list to actually detect the pre-fix pattern.
2. (Recommended) Add `.exe` preference to the fallback loop in `_find_claude`.
3. (Recommended) Add at least one unit test for `_find_claude` Windows behavior.

---

STATUS: REVIEWED — recommend SHIP-WITH-CHANGES
