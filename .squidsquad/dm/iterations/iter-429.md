# DM Iteration 429 — 2026-06-14 02:4x (22:45 local)

**Wake mode**: LOOP (harness UP on :7373, PM loop-pin active). pending-ship had 1 item after several quiet cycles.

## Shipped 1 item (local-merge, with counter reconciliation)
- **#11511** (role:skill) — PR #12223. Real-conflict detection (git_ops check_real_conflict, merge-tree both-directions) + pre-commit guard unstaging state files on feature branches — fixes transient-state CONFLICTING flap. PM-committed unstick (skill was deadlocked on bg-gate-across-reboots #12142; root cause later found = Claude usage-limit exit 1, #12244). Verifier PASS. Counter 13→14.

## Counter-regression reconcile (verifier-flagged, DM-handled)
- Branch squidsquad/task/11511 carried stale `Shipped Since Last Bump=12` (rode in via pre-guard Part-1 commit 82e8d4ba6). origin/main was 13 (#11745). config.md is `_is_state_file=True` but NOT in `.gitattributes merge=ours` (only working-state/current-state/cycle-*.json/backlog-cache/BRIEFING are) → plain merge takes branch's stale 12 → REGRESSION 13→12.
- **Fix**: `git merge --no-ff --no-commit` → confirmed raw merge gave 12 → `git checkout HEAD -- config.md` (restore main's 13) → edit to **14** (13 + this ship) → add → commit. Verified counter=14 on merge commit before push. No regression.
- **@pm flagged**: consider adding `.squidsquad/config.md merge=ours` to .gitattributes (belt-and-suspenders; the Part-2 guard already covers going-forward). Skill/PM-owned config, not a DM action.

## Context (not DM-actionable)
- PM cycles 2353–2357: diagnosed + broke #11511 deadlock; root-caused skill reboot churn = Claude session/usage-limit (exit 1), filed #12244 harness-backoff; #12142 = durable WIP-across-reboots fix. skill currently STOPPED (quota recovery, operator-directed).

## State
- Ship counter **14/10**. Bump HELD ([[feedback_bump_requires_pm_signal]]). pending-ship now EMPTY.
- Harness untouched (operator decision c421); loop-pin intact.

## Carried
- #10540 OPEN (DM-domain, PM routing). config.md .gitattributes gap (@pm). #11723 Parts 1&3 + #11745 macOS/Linux (PM follow-ups). #11600 clone-reg half. pending DM approvals #8702/#7447/#9933.
