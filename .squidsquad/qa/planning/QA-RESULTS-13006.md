# QA-RESULTS-13006 — delete orphaned legacy L4 seed stubs (pm-/dm-)

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-20 02:37 · **Verifier:** qa · PR #13012 @ 3a9ad2cb7 · branch `squidsquad/task/13006`.

Bug (type:issue/LOW, auto-approved), filed by skill (hygiene). dead-file deletion + guard
test → no CQ. Worktree `D:\Dev\Dev\sq-13006-verify`. Append-only.

## Fix summary
Deletes 6 dead L4 seed stubs — project/{pm,dm}-{instructions,responsibility,soul-directives}.md —
leftovers from before the L4-seed mechanism was scoped to worker/verifier (sub-phase 6274.2).
Adds a guard test so they can't reappear.

## AC walk (derived; all PASS)
- **AC1 (deletion)** PASS — branch `ls references/sub-skills/project/` shows no pm-/dm- stubs remain (all 6 gone).
- **AC2 (guard test)** PASS — test_13006_orphaned_l4_stubs_removed.py: test_orphaned_pm_dm_stubs_absent
  (the 6 named) + test_no_pm_or_dm_per_slot_seed_stubs (broad — any pm-/dm- straggler) → 2 passed. Non-vacuous.
- **AC3 (genuinely dead — INDEPENDENT confirmation)** PASS — required for a deletion:
  - No `.py` loader references any of the 6 stubs (grep across *.py/*.md/*.yml/*.txt: the only hits are
    prose — skill scan-history, a vault note — and static 8697 comprehension fixture snapshots, none
    load-bearing; deleting the stubs doesn't affect them).
  - wizard.py `_copy_l4_seed_stubs` (L1865-66) copies ONLY worker-*/verifier-* ("leave other seeds alone")
    → the pm-/dm- stubs were never seeded into an install.
  - Not in docs/sub-skill-catalog.md (not runtime-loadable); correctly EXCLUDED from installer-files.txt
    by #12915 (verified this session — #12915 added only worker-/verifier- + shared-* + setup-upgrade-gate).
- **No CQ** — dead-file deletion + guard test.

## No-regression
- test_13006_orphaned_l4_stubs_removed.py → 2 passed.
- Full static gate: `run_tests.py static` → **PASS — 4700 gated tests, 0 failures, 0 errors** (exit 0) —
  confirms no test or code depended on the deleted files. Only the 2 allowlisted #10360 known-failures.

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #13012, no review:human-required → merge
deferred to DM. Counter NOT bumped. TEST-PLAN-13006 + QA-RESULTS-13006 on main.
