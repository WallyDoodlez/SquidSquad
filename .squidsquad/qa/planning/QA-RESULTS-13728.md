# QA-RESULTS-13728 (bundled with #13729/#13730, shared branch `squidsquad/task/13728`, PR #13734)

## Summary
FAIL — back to In Progress. #13728/#13730's own narrow ACs are individually correct (harden_stdio wired, em-dashes swept, branch-flip visibility added), and #13729's fix is fully clean. But the bundle as a whole introduces a real regression: `main()`'s new unconditional `harden_stdio()` import breaks `git_ops.py` execution whenever `cli_stdio.py` isn't co-located, silently defeating the #13556 post-merge safety net. Caught by running the FULL static gate (not just the narrower `test_cli_stdio_13198.py` file, which alone shows all-green) — the zero-gap gate exists precisely to catch this class of cross-cutting breakage.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1 (#13728: harden_stdio wired) | PASS | `git_ops.py main()` calls `harden_stdio()`. |
| AC2 (#13728: 4 em-dash prints ASCII-swept) | PASS (live) | Independently re-ran the same AST-based non-ASCII scan the issue's own repro used against the branch — 0 matches. |
| AC3 (#13728: added to WIRED/SWEPT lists) | PASS | `test_cli_stdio_13198.py` — 28/28 PASS with git_ops included. |
| **Cross-cutting regression** | **FAIL** | `main()`'s new unconditional `from cli_stdio import harden_stdio; harden_stdio()` (lines 2642-2643) has no fail-open guard. When `git_ops.py` runs in isolation from its sibling `cli_stdio.py` (a scenario the pre-existing `test_bare_merge_fires_hook_end_to_end` test deliberately constructs to verify the #13556 post-merge hook's fail-safety in isolation), the import raises `ModuleNotFoundError` before any command dispatch runs. Independently reproduced live outside pytest: a real bare `git merge` that silently drops a protected vault note never gets it restored — the post-merge hook's own docstring guarantee ("Fully fail-safe: the guard never raises") is broken. This is a pre-existing test (not part of this PR's diff) that this PR's own change broke — an unambiguous regression, not a flaky/environmental failure. |
| AC4 (#13729: pm filtering) | PASS (independently re-verified live) | `scan_index.suggest_targets("pm", ...)` — no `references/scripts/` or `tests/` paths. `suggest_targets("skill", ...)` unaffected (still returns code files). |
| AC5 (#13729: scope disclosed) | PASS | Confirmed in PR/comment. |
| AC7 (#13730: branch-flip visibility) | PASS (live) | Direct call to `_checkout_and_sync_working('main')` produces the documented "switched back to 'main'" line. (Side effect note: this real call actually checked out main in my own working tree mid-test — reverted, and separately caught+discarded an unintended real scan-history pruning triggered by my own `suggest_targets()` test calls against pm/skill's real state files — neither is production content I should have touched.) |
| AC8 (#13730: git-commit.md documented) | PASS | Doc note present. |
| AC9 (#13730: underlying behavior unchanged) | PASS | `git branch --show-current` after a real `commit_code()`-equivalent call is still `main`. |
| Comprehension staleness (bundled hygiene) | FAIL (minor) | Full static gate additionally flags `13551_spec.json <- git-commit.md` as unreviewed since #13730's edit. Reviewed: content-safe to refresh (13551's CQ questions concern an untouched section), just never swept. |

## Zero-gap check
2 gaps: the harden_stdio regression (real blocker) and the unswept 13551_spec.json baseline (minor, bundled fix). Neither deferred — both route back to In Progress.

## Verdict (Round 1)
FAIL → In Progress. #13728/#13730's own narrow scope + #13729 in full are correct; the regression is scoped to the harden_stdio import's missing fail-open guard. Route: wrap the import/call so a resolution failure doesn't crash `main()` — matches harden_stdio's own defensive purpose (it should never itself become a new, broader crash vector than the narrow one it fixes). Plus `comprehension_staleness.py refresh 13551_spec.json` as a quick add-on.

---

## Round 2 (2026-07-19)

Skill fixed exactly as suggested: wrapped the `harden_stdio()` import/call in `try/except ImportError: pass` — fails open when `cli_stdio.py` isn't co-located. Also refreshed `13551_spec.json`'s baseline.

| Finding | Result | Evidence |
|---------|--------|----------|
| harden_stdio regression | **RESOLVED** | Independently re-ran the exact standalone repro 3x: 3/3 PASS (was 3/3 deterministic FAIL). Full manual E2E reproduction outside pytest, repeated: the post-merge hook now correctly prints the #13556 restore message and the dropped file exists post-merge — no crash. New `tests/test_13728_harden_stdio_fail_open.py`: 2/2 PASS (fail-open path + still-hardens-when-present path). |
| 13551_spec.json staleness | **RESOLVED** | `comprehension_staleness.py check` exits clean on the branch. |
| #13732 (bundled, same root cause) | **RESOLVED** | Same 3x standalone re-run applies — this closes as fixed-by-#13728, not as the "flaky, no action" misdiagnosis from skill's own investigation. |

**Sanity re-run**: full static gate — 5887/5887 PASS, 0 failures, matching skill's own reported number exactly.

## Verdict (Round 2)
PASS -> Pending Ship. PR #13734 merged (commit a0b61ca2). Also closes #13729, #13730, #13732 (same branch/PR).
