# QA-RESULTS-12823 — config.md merge=ours silently drops concurrent changes

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-19 23:57 · **Verifier:** qa · PR #12982 @ 825bd28ac · branch `squidsquad/task/12823`.

Bug (type:issue/medium, auto-approved), filed by dm. config/gitattributes infra → no CQ.
Verified in isolated worktree `D:\Dev\Dev\sq-12823-verify`. Append-only.

## Fix summary
Remediation option 1 (split the counter): `.gitattributes` drops `merge=ours` from
`.squidsquad/config.md` and adds `.squidsquad/.ship-counter merge=ours`. config.py
redirects the ship-counter field to `.ship-counter` (get/set), with a config.md legacy
fallback for in-place upgrades. config.md now merges 3-way; the counter keeps ours-wins
protection in its own file.

## AC walk (derived; all PASS)
- **AC1 (no silent drop)** PASS — **independent LIVE 3-way merge** in an isolated temp repo
  using the branch's `.gitattributes`: (a) far-apart concurrent edits (DM Name + skill Flag)
  → auto-merged CLEAN, both preserved, no conflict; (b) adjacent edits → CONFLICT but BOTH
  sides preserved (no silent drop). Either way the concurrent edit survives — under the old
  `merge=ours` one side would vanish with no marker. .gitattributes: config.md `merge=ours`
  removed; `.ship-counter merge=ours` added.
- **AC2 (counter still protected)** PASS — the ship counter lives in `.squidsquad/.ship-counter`
  with `merge=ours`, preserving the regression-protection that was the sole reason config.md
  carried ours-wins (stale sibling push can't regress a bump).
- **AC3 (storage redirect + migration)** PASS — config.py `get_field`/`set_field` redirect the
  counter to `.ship-counter`; `_read_ship_counter` falls back to the legacy config.md
  `Auto Versioning > Shipped Since Last Bump` field for in-place upgrades; default 0 when
  neither present; `_parse_all` overlays the authoritative value; first write migrates.
  test_12823_ship_counter_split.py (read/write/migration/default/gitattributes).
- **AC4 (git_ops staging)** PASS — `.squidsquad/.ship-counter` added to the common role-owned
  commit patterns so the writing role (DM bump/reset, #9772 reconcile) can stage it.
- **AC5 (regression test)** PASS — test_12823_ship_counter_split.py + updated test_config_functions
  + test_git_ops → 246 passed.
- **(Doc)** git_ops KNOWN-LIMITATION (#9474) comment updated to RESOLVED (#12823) — accurate.
- **No CQ** — config.py + .gitattributes infra; no LLM-consumed instruction change.

## No-regression
- test_12823 + test_config_functions + test_git_ops → 246 passed.
- Full static gate: `run_tests.py static` → **PASS — 4683 gated tests, 0 failures, 0 errors** (exit 0). Only the 2 allowlisted #10360 known-failures.

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #12982, no review:human-required → merge
deferred to DM. Counter NOT bumped. NOTE for DM: this changes config.md's merge driver — the next
delivery-time merge of config.md will be 3-way (real conflicts now surface instead of silent ours-wins);
the interim mitigation in [[learning-config-merge-ours-drops-concurrent-changes]] is superseded once shipped.
TEST-PLAN-12823 + QA-RESULTS-12823 on main.
