# QA-RESULTS-13198 — fleet-wide cp1252 stdout crash class

**Verifier**: qa
**Date**: 2026-06-21 20:30
**Verdict**: FAIL (zero-gap) — AC-4 ASCII sweep incomplete. Status → In Progress (back to skill).
**Change under test**: PR #13214, branch `squidsquad/task/13198`.

## AC walk

| AC | Result |
|----|--------|
| AC-1 shared canonical helper | PASS |
| AC-2 each agent-facing CLI calls it at main() | PASS |
| AC-3 tracker.py refactored to shared helper (no dup) | PASS |
| **AC-4 ASCII sweep of decorative non-ASCII in stdout** | **FAIL** |
| AC-5 new file in installer manifest | PASS |
| AC-6 tests | PASS |

## What's correct (so the fix needs only AC-4 completed)
- **AC-1/TC-1**: `references/scripts/cli_stdio.py` `harden_stdio()` — reconfigure `errors="backslashreplace"`,
  best-effort (guards AttributeError/ValueError/OSError), CLI-only, idempotent. Mirrors #13185.
- **AC-2/AC-3/TC-2**: all 9 agent-facing CLIs (add_role, boot_remote, compose, config, migrate_state_branch,
  model_router, scan_index, subloop_driver) call `harden_stdio()` at `main()` top; tracker.py refactored
  to delegate to the shared helper (no duplicate impl). 15/15 in `test_cli_stdio_13198.py` PASS
  (parametrized fleet-wiring + delegation + module-exists).
- **AC-5/TC-4**: `installer-files.txt` updated (253→254) including `references/scripts/cli_stdio.py`.
- **TC-6 crash-net**: verified on a strict cp1252 stream — after `harden_stdio()`, `print("→ — •")`
  does NOT raise (backslash-escaped). The crash/false-failure/double-emit harm is eliminated.

## The gap (AC-4 / TC-3) — FAIL
The issue Direction explicitly scopes an "ASCII-replacement sweep of decorative non-ASCII (→, —, •, etc.)
in those scripts' stdout so the common output displays cleanly on every console." The sweep is INCOMPLETE
— 9 decorative chars remain in stdout/stderr print lines across 6 of the swept files (with the helper they
no longer crash, but on a cp1252 console they now render as `→` / `—` — the ugly output the sweep
is meant to prevent, including common success lines):

- `add_role.py:295` — `—` (stderr) ; `add_role.py:384` — `→` (stdout, "Fixing origin: ... → ...")
- `boot_remote.py:703` — `—` (stdout, the per-role status line — common output)
- `compose.py:987` — `—` ; `:1151` — `—` ; `:2244` — `—` (stderr)
- `migrate_state_branch.py:116` — `—` (stdout, "(dry run — no files moved)")
- `model_router.py:909` — `—` (stdout)
- `scan_index.py:444` — `→` (stdout, "Recorded decision: ... → ..." — common success line)

Secondary: no regression guard for the sweep — a test that greps the swept scripts for decorative
non-ASCII in stdout would have caught this (and would prevent reintroduction). Consider adding one
alongside the cleanup.

## Verdict
FAIL — back to In Progress. Complete the ASCII sweep (replace the 9 remaining `→`→`->`, `—`→`--`/`-`)
and ideally add a grep-guard test. The helper/wiring/refactor/manifest/tests are all correct and need
no rework.

---

## RE-VERIFICATION — 2026-06-26 22:52 — VERDICT: PASS (zero gaps)

**Change under re-test**: PR #13214 @ commit `8cfa10a9b` ("complete AC-4 ASCII sweep + add regression guard").
Branch `squidsquad/task/13198`, in sync with origin (0/0).

### AC walk (re-verification)
| AC | Result | Evidence |
|----|--------|----------|
| AC-1/2/3/5/6 crash-net (helper + wiring + tracker delegation + manifest + tests) | PASS (unchanged) | Accepted in prior cycle; worker confirms untouched; 24/24 in `test_cli_stdio_13198.py` |
| **AC-4 ASCII sweep of decorative non-ASCII in stdout** | **PASS (was FAIL)** | Independent AST scan (below) — zero decorative chars across all 8 swept CLIs |

### Independent AC-4 verification (NOT the worker's guard)
Wrote and ran my own AST scanner (`_scan_13198_prints.py`, since removed) over every `print()` string
literal in the swept set (`config, model_router, compose, migrate_state_branch, tracker, boot_remote,
add_role, scan_index`), categorising non-ASCII into **decorative punctuation** (→ — – • smart-quotes …,
what AC-4 targets) vs **other** (emoji etc.):
- **Swept-set decorative count = 0** — all 8 files clean. The worker's AST-span replacement (29 chars,
  superset of my sampled 9) is genuinely complete. The specific lines I flagged
  (`scan_index.py:444 "Recorded decision: ... →"`, the compose/add_role/boot_remote/migrate/model_router
  em-dashes) are all now ASCII (`->`, `--`).
- Diff confirmed print-literal-only (9 files: 8 CLIs + test; 77+/29-); comments/docstrings untouched.

### Regression guard (my prior secondary ask) — PASS
`TestNoDecorativeNonAsciiInPrints13198` in `tests/test_cli_stdio_13198.py` — AST-asserts zero non-ASCII in
print() literals, parametrized over the 9-file wired set. 24/24 (15 prior + 9 new). A reintroduced
decorative char fails here. Locks the sweep against regression.

### Other checks
- **Crash-net (TC-6)**: `test_baseline_cp1252_arrow_raises` + `test_harden_sets_backslashreplace_and_no_raise` PASS.
- **No machine-output regression**: no `ensure_ascii=False` in any swept file → JSON stdout stays pure-ASCII.
- **Curated ship gate** `python tests/run_tests.py`: **53/53 PASS**.
- **Full pytest suite**: 5128 passed, 51 skipped, **19 pre-existing failures UNRELATED to #13198**
  (comprehension harness `_get_result` ID-mismatch in `test_comprehension_{9184,2183,2195}.py` — LLM answered
  correctly but lookup returns None; + `test_compose_author_comments_11142::test_10360_cleanup_markers_preserved`
  asserting `#10360-cleanup:` markers in `references/roles/worker/instructions.md`). None touch #13198's
  print-literal / scripts surface; none in the ship gate. Flagged to PM separately as repo-health, not a #13198 block.

### Out-of-scope observation (flagged to PM, NOT a #13198 block)
`harness.py` `main()` does not harden its own stdout (no reconfigure/harden_stdio), and `start.ps1` launches it
via bare `python` with no `PYTHONUTF8` — leaving 4 decorative + 33 emoji prints latently cp1252-vulnerable.
This is outside #13198's locked scope (the 9 agent-facing CLIs; worker explicitly scoped to those). `cycle_pre/post/cycle`
self-protect via their own UTF-8 reconfigure, so their decorative chars are harmless. Raised for PM to triage as a
possible follow-up.

### Verdict
**PASS — zero gaps.** AC-4 gap closed and independently confirmed; crash-net intact; regression-guarded.
Status pending-test → pending-ship. PR #13214 approved + merged.
