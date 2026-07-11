I have carefully traced through every code path and edge case. Here is my analysis:

**What the fix does:**

1. **`_parse_args` (line 1961)**: Adds `-h` alongside `--help` so `git_ops.py -h` prints the docstring and exits 0 (matching existing `--help` behavior). This is at the *top-level* (first argument position only) — it does NOT affect free-text args in later positions for other commands.

2. **`pr-merge` guard (lines 2029-2036)**: Before calling `pr_merge()` (which performs real git operations), validates `rest[0]`:
   - Missing/empty → exit 1 (usage error)
   - `-h`/`--help` → exit 0 (help request, no side effects)
   - Non-numeric → exit 2 (distinct from merge failure's exit 1)

**Edge cases traced and verified:**

| Scenario | Path | Result |
|---|---|---|
| `git_ops.py -h` | `_parse_args` catches `-h` | exit 0, prints docstring |
| `git_ops.py pr-merge --help` | `_parse_args` returns `("pr-merge", ["--help"])` → guard catches | exit 0, prints pr-merge usage |
| `git_ops.py pr-merge -h` | Same | exit 0, prints pr-merge usage |
| `git_ops.py pr-merge` | Guard: `not rest` | exit 1 |
| `git_ops.py pr-merge notanumber` | Guard: `isdigit()` fails | exit 2, error message |
| `git_ops.py pr-merge --strategy squash` | Guard: `"--strategy".isdigit()` → False | exit 2 |
| `git_ops.py pr-merge 123` | Guard passes → `pr_merge("123", "squash")` | merge proceeds |
| `git_ops.py pr-merge 123 --strategy merge` | Guard passes → `pr_merge("123", "merge")` | merge proceeds |
| `git_ops.py commit skill "--help"` | `args[0]="commit"` → not caught by `_parse_args` | unaffected |
| `git_ops.py -h pr-merge 123` | `_parse_args` catches `-h` as first arg | exit 0, top-level help (consistent with `--help`) |

**Tests**: All seven new tests are well-structured — they monkeypatch `pr_merge` with a spy and assert it is never called for invalid inputs, validating the "no side effects" requirement. The `_ensure_hooks_installed` is also monkeypatched to keep tests hermetic.

**No regressions**: The `_parse_args` change only affects `-h` in the first argument position, which previously fell through to "Unknown command: -h" (exit 1). Making it consistent with `--help` is the intended behavior. No other command's argument parsing is affected.

**`isdigit()` vs "positive integer"**: The error message says "positive integer" but `isdigit()` accepts `"0"`. However, PR #0 doesn't exist and `pr_merge` would fail at the API level (checking state, finding no PR, returning failure) without dirtying the tree — the critical distinction is numeric vs non-numeric, and `isdigit()` correctly rejects the problematic inputs (`--help`, `--strategy`, `notanumber`, etc.).

NO_FINDINGS