# Iteration 467 — 2026-06-13 14:59

**Mode**: POLLING (/loop cron 71281ae5, 30m).

## Summary
Checked prior-cycle handoffs (4 PRs progressing: #11723/#11641 → pending-ship, #11640/#11587 → pending-test; none rejected). Deterministic work-queue pickup: #11505 still blocked, #10690/#10686 gated/operator-manual → first actionable open bug = **#11745** (orphan terminal windows on agent kill, role:skill). Investigated; surfaced a design fork for operator/PM rather than blind-implement.

## Work — #11745 root-cause investigation
Per-platform analysis of `boot_remote.py` `_spawn_windows/_spawn_macos/_spawn_linux`:
- **Windows wt.exe (active/thin)**: agent launched as a command directly in Terminal → tab close governed by profile `closeOnExit`, default `automatic`=`graceful` → closes only on exit 0; killed/non-zero agent leaves an orphan tab. Verified: no `wt.exe` CLI flag exists (microsoft/terminal#15747); `closeOnExit:always` is settings.json-only (MS docs).
- **Windows legacy ps1**: `pwsh -NoExit` pins shell open forever — latent guaranteed orphan.
- **macOS**: `Terminal.app do script` leaves window open post-command unless profile configured.
- **Linux**: `tmux new-session -d` detached; lingering session on stop (kill-session only at spawn).

## Outcome — design fork posted on #11745 (in-progress, blocked on operator/PM)
- **Option A (recommended)**: self-closing separate windows via `cmd /c start` — zero provisioning, OS closes window on any exit code, never accumulates.
- **Option B**: keep wt tabs + provision a `closeOnExit:always` WT profile (`-p squidsquad`) — preserves tabbed UX, needs installer + upgrade settings.json provisioning.
Held for ratification (mirrors #11505 STOP-before-execute / pattern-stale-ac-vs-canonical-arch fork-surfacing). On decision: implement chosen option + drop legacy `-NoExit` + macOS window-close + Linux stop-time kill-session + unit tests on spawn-cmd construction. Live spawn→kill→terminal-gone = verifier/operator manual (AC permits).

## Next
- Await operator/PM A-vs-B decision on #11745.
- Next deterministic actionable if #11745 stays blocked: #11511 (PR mergeability flaps from transient-state commits) — relevant to last cycle's stale-CONFLICTING observation.
- Monitor 4 PRs → DM ships.
