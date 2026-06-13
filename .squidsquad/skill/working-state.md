# Working State

- **Task**: All 4 PRs landed (#11723/#11641 SHIPPED, #11640/#11587 pending-ship). Queue triage-blocked. iter-469: vault hygiene only.
- **Status**: in-progress (#11745, #11511) — both still blocked on operator/direction (no response as of 15:38). No shippable APPROVED code in queue.
- **Updated**: 2026-06-13 15:38
- **Branch**: main (state). Feature branches: task/11587, task/11640, task/11641, task/11723 (all merged/merging).
- **Quiet Cycle Counter**: 1 (iter-469: vault cross-link only; queue blocked)

## ⚠️ QUEUE STATE — every actionable item is triage/operator-blocked (operator: needs unblocking)
- **#11745** (in-progress) — orphan terminals; blocked on operator A-vs-B UX fork (iter-467).
- **#11505** (in-progress) — capabilities deadwood; blocked on PM/operator #11505↔#10025 disambiguation.
- **#11511** (in-progress) — PR mergeability flap; held for direction confirmation (iter-468, below).
- **#10690** (approved) — wiki-link; gated on E7 (#10686).
- **#10686** (approved) — E7 V2 migration smoke; operator-manual.
- **#11716** (open) — improvement-scan finding; can't auto-fix own scan finding without PM/human triage.
Implementable approved work (the 4 PRs) shipped cycle 466. Until operator triages the above, cycles are investigation-only.

## iter-468 (15:15) — #11511 PR-mergeability-flap: disproved both proposed fixes
DECISIVE: GitHub does NOT honor user .gitattributes merge drivers for PR mergeability (merge=union = open GH feature request since 2021, community discussion #9288; merge=ours is doubly local-only — `merge.ours.driver=true` lives in local .git/config, not committed). So the EXISTING .gitattributes strategies are server-side no-ops; candidate 2 (add merge=union) WON'T fix the flap. Candidate 1 (gitignore): current-state/cycle-*.json/.backlog-cache already gitignored (don't flap); remaining = working-state.md, but gitignoring it breaks INTENTIONAL cross-agent visibility (cycle_post splits state→main on purpose; health_check/state_bus/migrate_state_branch read it).
ROOT CAUSE: working-state.md flaps only when it lands on a FEATURE branch (both-sides-changed). cycle_post already routes state→working/main, not feature branch — it leaks onto feature branches only when the wrapper is bypassed (harness-down manual commits) or branch races. RECOMMENDED (held for confirm, high blast radius): (1) treat GH CONFLICTING as advisory — verify with `git merge-tree --write-tree base head` before hand-nudging; merge locally when harness down (zero-risk, stops wasted cycles now); (2) harden state routing so working-state can't land on feature branches even on manual paths; (3) do NOT add .gitattributes entries / do NOT gitignore working-state. Full detail on #11511 comment.

## 4 prior PRs — status as of 15:38 (out of lane, DM shipping)
- #11723 (#11729) **SHIPPED** · #11641 (#11715) **SHIPPED** · #11640 (#11709) pending-ship · #11587 (#11722) pending-ship

## iter-467 (14:59) — #11745 orphan terminals: investigated, surfaced design fork
Root cause (boot_remote _spawn_*): Windows wt.exe path runs agent as a command launched DIRECTLY in Terminal → closeOnExit default `automatic`=`graceful` → tab stays open on non-zero/kill exit (the orphan). NO wt CLI flag to override (microsoft/terminal#15747); `closeOnExit:always` is settings.json-profile-only. Legacy ps1 path `pwsh -NoExit` = guaranteed orphan. macOS Terminal.app `do script` leaves window. Linux tmux detached session lingers (kill-session only at spawn, not stop).
**FORK posted on #11745 (blocked on PM/operator):** A = self-closing separate windows via `cmd /c start` (zero provisioning, OS-guaranteed close — RECOMMENDED, directly kills the accumulation complaint) vs B = keep wt tabs + provision a `closeOnExit:always` WT profile (preserves tabbed UX, needs installer+upgrade settings.json provisioning). Once ratified I implement chosen option + drop legacy -NoExit + macOS/Linux handling + unit tests on spawn-cmd construction; live verify is verifier/operator manual.

## 4 prior PRs — status as of 14:59 (out of skill lane, monitoring only)
- #11723 (PR #11729) → **pending-ship** (verifier passed; DM next)
- #11641 (PR #11715) → **pending-ship**
- #11640 (PR #11709) → pending-test (verifier not yet)
- #11587 (PR #11722) → pending-test

## ⭐ THIS CYCLE (iter-466, 14:50) — gate #11683 MERGED → landed all 4 PRs
#11683 (the blocker) shipped/merged to main at 333c351b2. Merged origin/main into each branch, ran full suite (run_tests.py exit 0 = pytest + static 53 OK), pushed, transitioned → pending-test. All 4 PRs now **MERGEABLE / CLEAN**:

| Issue | Fix | Branch | PR | Suite | Notes |
|---|---|---|---|---|---|
| #11723 | liveness-aware port discovery (#11586 root cause) | task/11723 | #11729 | green | branch already contained main; pushed unpushed merge 1e760e759 |
| #11641 | stale scheduled_tasks.lock reclaim | task/11641 | #11715 | green (4123) | clean merge |
| #11640 | clone-resolution refuse (no REPO_ROOT fallback) | task/11640 | #11709 | green | **+stale feat_1496 test fix** (commit cab96789b) |
| #11587 | uvicorn loop=none (ProactorEventLoop) | task/11587 | #11722 | green | clean merge |

All DS NO_FINDINGS (done pre-gate). Verifier verifies → DM ships 4.

## ⚠️ GOTCHA hit this cycle — config.md ship-counter test-pollution
`run_tests.py` (integration tests touch the real clone) re-stages a DM-owned `.squidsquad/config.md` "Shipped Since Last Bump" change (saw 8→4) into the index. On a feature branch a bare `git add <file> && git commit` sweeps it into the PR. **Restore before committing: `git checkout HEAD -- .squidsquad/config.md`.** Same class as the .local-config/.harness-port test-pollution. Caught + reverted on #11640 commit this cycle. Vault learning written.

## #11640 stale-test detail
Merge surfaced `test_feat_1496_shared_fs_fallback.py::test_get_clone_path_falls_back_to_repo_root` red — it asserted the OLD REPO_ROOT fallback that #11640 deliberately reverses. Updated in-place → asserts `CloneResolutionError` raise (matches file's #3100 in-place-update convention). New-behavior coverage already comprehensive in test_boot_remote.py. NOTE: this fix travels with #11640; the other 3 branches merged OLD main (pre-#11640) so they still carry the old feat_1496 test + old boot_remote — consistent, no conflict. When DM merges #11640, fix+test land together.

## Mode / environment
- POLLING mode (harness probe failed: 59999 connection-refused). /loop cron **71281ae5** (30m), this session. Mode sticky.
- .harness-port=59999 is the intentional/gitignored state (PM/test pin). Leave it.

## Open (next, in priority order)
1. **#11723 follow-ups (open, non-urgent — Part 2 #11729 protects the symptom):**
   - (1) ROOT fix: boot_remote.py hard-codes SQUIDSQUAD_DIR (ignores $SQUIDSQUAD_DIR env) → _deferred_init clone-distribution pollutes real clones from isolated test harness. Fix = 2 coupled parts (env-honoring resolver + test fixtures writing isolated .local-config). Backed out twice (404s: bootup-complete doesn't create role record under isolated SQUIDSQUAD_DIR). Needs dedicated fresh-context debugging. Keep deferring until it matters operationally.
   - (3) boot Step 1 instruction fall-through to default when file-port probe fails (CQ + recompose).
2. **#11512** (severity:high, role:skill) — event-mode DOA: thin_launcher.py:494-503 unconditionally injects /loop spawn prompt so agents never reach boot Step 1 harness probe. Skill owns fix design.
3. **#11394** (severity:high, role:skill, in-progress per briefing) — run_tests.py STATIC_TEST_MODULES gap. (Note: static gate now runs 53 tests + has test_11394_static_discovery.py — may be partially landed; re-check before picking up.)

## Standing
- #11505 (low, in-progress) blocked on PM/operator #11505↔#10025 disambiguation.
- #10690 / #10686 (approved) E6/E7-gated. #11511 not-implementing. #11716 (low improvement-scan) awaiting triage.
- Pre-existing test-debt: test_cycle_pre TestGetVerifiableRoles (#6274, quarantined) — not mine.

## Tree cruft (untracked, leave)
- .claude/scheduled_tasks.lock.stale-bak — #11641 repro backup
- .squidsquad/skill/planning/CODE-REVIEW-11587.md, CODE-REVIEW-11723.md — DS review evidence
