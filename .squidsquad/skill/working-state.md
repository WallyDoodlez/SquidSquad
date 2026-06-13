# Working State

- **Task**: none active — on main (all shipped work in QA/DM hands; #11511 awaiting PM decision)
- **Status**: none (idle)
- **Updated**: 2026-06-12 20:08
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 1

## ⚠️ Session note
Booted PRE-v0.44.0; runs OLD composed CLAUDE.md (reboot pending per DM — do NOT self-reboot). Harness UP (port 7373) but operator drives via /loop — staying loop-mode this session.

## Last cycle (1640, iter-449): #11511 root-cause SHARPENED + recommendation posted
Productive queue empty (#11503/#11505 gated on #11504; #10690/#10686 operator-gated). Dug into #11511 and CORRECTED the root cause: NOT "GitHub staleness" — it's `.gitattributes` (#5469) `merge=ours` on transient files (working-state.md etc.). merge=ours is a CUSTOM driver honored locally (merge.ours.driver=true set) but NOT by GitHub's server-side merge → branch/main divergence on those files = GitHub CONFLICTING while local merge-tree clean. The intended fix EXISTS but is unwired: state_bus.py/migrate_state_branch.py (dedicated state branch + worktree, off main) — no state branch on origin. Posted options to #11511 (A=activate state branch [recommended]; B=stopgap merge=ours→union where safe, NOT config.md; C=status quo). Corrected vault [[learning-pr-conflicting-flag-can-be-cosmetic]]. NOT implementing — high blast radius, awaiting PM/operator bless.

## Shipped this session (in QA/DM hands)
- **#11512 / PR #11518**: pending-ship. DM to ship.
- **#11519 / PR #11530**: pending-test. QA verifies + merges.
- **#11511**: recommendation posted; awaiting PM/operator decision on approach A vs B.

## Watch
- **PR #11504 / #11394**: GitHub flag flaps (merge=ours not honored server-side — see #11511). QA to merge on content. On merge → resume #11503 fixes + #11505.
- #11503 (high) / #11505 (low): gated on #11504.
- #10690 / #10686 (E7): operator-gated.
- #11329 (approved): runtime per-event ack-cursor.

## ⚠️ Recurring conflict note (UPDATED cycle 1640)
PR #11504 CONFLICTING-while-locally-clean = `merge=ours` custom driver not honored by GitHub server-side (NOT staleness). Real fix = state-branch architecture (state_bus, unwired). Stopgap = merge=union where safe. Tracked #11511. Do NOT hand-nudge.
