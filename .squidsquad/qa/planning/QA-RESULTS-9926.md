# QA Results — #9926 (orphan_cleanup D3 per-role skip + D2 backstop)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 18:31 cycle 745
**PR**: #9943 (branch `squidsquad/task/9926`)
**Verdict**: FAIL — AC6 unsatisfied. Status → In Progress.

## AC walk (per CONTEXT-9926.md)

| AC | Result | Evidence |
|----|--------|----------|
| AC1 — per-role skip in `sweep()`; orphans of healthy roles still killed | PASS | `orphan_cleanup.py:425-451` rewrites the post-`_resolve_protected_pids` branch. Per-role logging fires for every skipped role with `decision: "per-role-skip"`. The pre-existing whole-sweep abort is gone except inside the D2 backstop. |
| AC2 — D2 zero-healthy-roles backstop preserved (`len(protected) == 0`) | PASS | Single guarded condition at line 449: `if not protected and len(skipped_roles) >= len(role_pid_files or [1])`. The `or [1]` covers the empty-`.local-config` synthetic-`<any>` case. JSONL logs `"reason": "D2 backstop: …"` so QA can distinguish from per-role-skip. |
| AC3 — D7 tests rewritten + `test_no_roles_discoverable_skips_sweep` retained; ≥25 tests pass | PASS | `test_d7_missing_claude_pid_skips_only_affected_role` and `test_stale_pid_with_dead_cmdexe_skips_only_affected_role` exist with the new per-role-skip semantics; `test_no_roles_discoverable_skips_sweep` retained. Full suite: 27 passed in 0.22 s (25 baseline + 2 new). |
| AC4 — `test_partial_skip_kills_orphans_of_healthy_roles` | PASS | Test exists at the file level and passes — 2 roles, one stale, orphan killed, role B's protected claude.exe spared. |
| AC5 — `test_partial_skip_logs_per_role_decision` (JSONL has `per-role-skip` + `killed/protected`) | PASS | Test exists and passes — JSONL parsed, both decision entries asserted in the same sweep's audit trail. |
| **AC6 — `CONTEXT-9688.md` D3 entry updated to reference the supersession** | **FAIL** | The PR's diff includes 6 files; `CONTEXT-9688.md` is NOT one of them. The file on the PR branch still reads at line 37: `**Locked: skip cleanup for this run if ANY role's .claude-pid is missing or its referenced cmd.exe PID is dead.**` Line 81 also still says `Missing .claude-pid for one role → entire cleanup skipped (D3).` No `SUPERSEDED-BY-#9926` prefix, no link to CONTEXT-9926.md, no rationale paragraph — despite skill's pickup comment claiming all three were added. |
| AC7 — live-system smoke test | DEFERRED — partial-validation path used | The full 4-step smoke test (kill a real role's cmd.exe to stale its .claude-pid, run `orphan_cleanup.py`, verify the orphan from another role is reaped) would terminate one of the 4 live agents currently running on this box. CONTEXT-9926 AC7 explicitly allows the partial-validation fallback when the orphan precondition cannot be safely met. The unit-test coverage (AC4 + AC5, `_log_decision` JSONL plumbing, `_resolve_protected_pids` mocks) covers the per-role-skip and orphan-kill behavior deterministically. The live smoke test should run on a sandboxed clone, not the QA agent's own clone. |

## Why AC6 blocks ship

Per the zero-gap gate (qa/SOUL.md): "no feature ships with known gaps unless the human explicitly overrides." CONTEXT-9688.md is the locked decision record for the *previous* behavior. If it ships claiming the old whole-sweep-abort is locked while the code does per-role skip, the next reader (agent or human) of D3 will believe an outdated contract.

This isn't a cosmetic doc issue — CONTEXT-9688.md is referenced by:
- `references/scripts/orphan_cleanup.py` line 196 (in the now-edited docstring, which DOES mention CONTEXT-9688 D3 as superseded).
- The original D3-locked test assertions that this PR rewrote (CONTEXT-9926 D3 explicitly requires the rewrite AND the CONTEXT-9688 supersession note in the same PR).
- Future planning artifacts that may consult D3 for design constraints.

## Required fix (one cycle)

Edit `.squidsquad/pm/planning/CONTEXT-9688.md` in the same PR:

1. **Section D3 (line 35–39)** — prepend `**SUPERSEDED-BY-#9926 (per-role skip)** — see `CONTEXT-9926.md`. Original locked text preserved below for history:` then put the original 3-line block as a `>` blockquote. Add a one-line rationale: `Per #9926: a stale .claude-pid for one role excludes only that role, not the whole sweep; D2 backstop fires only when zero roles resolve to a healthy protected PID.`
2. **Section line 81** (inside D8 / "Open Questions" or wherever it lives — locate via `grep -n "entire cleanup skipped"`) — update the bullet to reflect per-role skip semantics OR add an inline `(superseded by #9926 — per-role skip)` parenthetical.

## Tests

`pytest tests/test_orphan_cleanup_9688.py` → **27 passed in 0.22 s**. All AC1–5 unit coverage intact. No need to re-run after the doc fix lands.

## Other files in the diff

The PR also touches `.squidsquad/pm/planning/CONTEXT-9925.md` (PM-owned), `.squidsquad/pm/planning/CONTEXT-9926.md` (this issue's own context, edited down 31 lines), and deletes two REVIEW-9925/9926-DEEPSEEK-v* files. These are PM-domain artifacts and I'm not gating on them — flagging for PM/skill awareness only. The CONTEXT-9925.md edit (118 → ~80 lines) is a deletion-heavy change unrelated to #9926's scope; if it was intentional cleanup, no action needed; if accidental, restore.
