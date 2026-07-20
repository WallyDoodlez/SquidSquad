# Working State

- **Task**: #13957 (9398 gh-shim test broken by #13863 push-doctor), picking up — batch 2/3 of the open-bug sweep (strategy comment on #13944). Fix direction: neutralize the push-doctor inside the shim env WITHOUT weakening the real gate — preferred: shim workspace's origin push URL → local bare repo so the dry-run push succeeds hermetically; fallback: shim-only env skip-knob. Regression: shim test green on a gh-helper clone.

## Batch 1/3 DONE (2026-07-20)
- **#13944 → pending-test, PR #13959.** tc_coverage now parses merged-cell table rows (result search skips the TC cell — #2469 analog) + bold-bullet TEST-PLAN declarations (scope extension found during live verify: plan side was ALSO at 0 TCs). Live: --issue 13863/13865 both 9/9 (100%), was 0/0-skip. 10 regression tests, 56 total; static gate PASS 6016/0; external review NO_FINDINGS first pass.

## Handed off this session (2026-07-20)
- **#13857 vault-v2 P1 (engine foundation) → pending-test, PR #13958** (11 files). Engine forked from reference system into references/skills/vault-search (source of truth; .claude/skills is per-clone deploy — commit_code filters .claude/ BY DESIGN, that's why the source moved under references/). Adaptations: PARAG folders, galaxy budget, JSONL shards (read-aggregate dedup-by-id + append-only, notes NEVER mutated), required --instance-id/--alias, --task attribution, --no-write zero events. wizard install_vault_engine() scaffold step 5b (deploy + soft node preflight + .telemetry/.gitattributes merge=union seed), vault_engine flag + config.py vault-engine row (+graceful default). Boundary ratchet test freezes 6 v1 grep sites (P4/S4.5 shrinks it). 134 targeted tests; static gate PASS 6050/0. External review: 4 rounds, 6 findings (config default, task-0 x2, updated exposure, installer fixture, negative-top uncap), all fixed+pinned, r4 NO_FINDINGS. Deferred BY PRD SCOPE: impressions report P3/S3.3, instance-id mint P5/S5.2 (SKILL.md documents unprovisioned fallback). CQ AC gap flagged to PM on the issue (SKILL.md is new LLM-consumed instruction; body has no CQ AC).
- **#13561 (TUI observability) → pending-human-review, PR #13945** (replaces #13889). RECOVERY: prior session's 6 docs/*-ARCH.md reconciliations were stranded UNCOMMITTED in the worktree AND PR #13889 auto-closed empty (its seed commit daef22565 reached main via the state-file push → GitHub closed as merged-into-base). Committed 219b5b235 + sync-merge 957cafb6d, re-raised PR #13945, transitioned. On operator approval → back to in-progress for Phase 1 (harness display-truth fields: current_task ingestion, in_cycle pairing, work_state derivation fn + matrix, /status additions, RED regression test) → Phase 2 (TUI render) → Phase 3 (context channel). Plan: tracker strategy comment + .squidsquad/pm/planning/GAP-ANALYSIS-TUI-OBSERVABILITY.md.

## Queue snapshot
- #13957 (mine, this pickup). Approved-but-gated: #10690 (E6+E7 gate), #10686 (operator-manual). Prior pending-test batch (#13863/#13865/#13847/#13855/#13846) all confirmed shipped on boot. Verify with list-issues on each wake — work_queue() omits open bugs.

## Session residuals / lessons (2026-07-20 boot session)
- **PR seed-commit dual-landing auto-closes the PR**: a commit present on BOTH a task branch (as PR seed) and local-main (state-file path) closes the PR the moment main pushes. Plan-in-PR seeds must never ride the direct-to-main state lane.
- **commit_code filters .claude/ — deliverables can silently vanish from a PR**: T2's engine "commit" contained only the test file until caught by git show --stat. ALWAYS verify what landed after commit-code when new paths are involved.
- stash@{0} (#13556 post-merge-hook WIP) confirmed SUPERSEDED (hooks + install-hooks landed, #13556 shipped) — safe to drop on a cleanup pass.
- Event stream returned ~2300-evicted gap + stale 07-19 backlog on boot (cursor beecc63 evicted); forge-read confirmed ALL backlog issues already shipped; walked + acked per event. Recovery path worked as documented.
- gh push credentials healthy all session (post-#13863); the 9398 shim failure MIMICS the credential-wedge signature — check `git push --dry-run origin main` outside the shim before diagnosing a live wedge.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 05:52 (clean; 1/3 of burst).

## Quiet Cycle Counter: 0

- **Vault Writes This Cycle**: 2
