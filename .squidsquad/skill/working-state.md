# Working State

- **Task**: none in-flight. All this-cycle work handed off to verifier (pending-test). Next actionable: #12271 (liveness, in-progress, high), then approved #12527/#12492/#10690/#10686 — all warrant fresh context.

## THIS CYCLE (2026-06-27, EVENT-mode continuation)

- **#13275 + #13276 RE-LANDED → pending-test (PR #13280).** Root cause: PR #13274's squash captured a STALE INTERMEDIATE commit (b649dc5b9), silently dropping the 2 newest branch commits — ecf6ffb9a (#13275 TUI infra: requirements-tui.txt / tui/__init__.py / render+drift tests / installer-files 254→258) and 03ab86ef8 (#13276 agent_rows None-guard). Verifier correctly REJECTED both (fixes never reached main). Recovered verbatim from branch tip 03ab86ef8 onto a fresh branch off main. Gate 5076 (TUI subset 30). **This is a distinct squash-loss variant** (partial loss on an AHEAD branch) — the #13271 behind-count guard does NOT catch it; data point posted on #13271; see [[learning-squash-drops-newest-commits-of-ahead-branch]].

- **#12450 S3+S4 SHIPPED → pending-test (PR #13281).** Installer auto-detects + follows the project's test strategy (operator request; PM split L3=behavior / L4-seed=specifics).
  - S3: `format_scan_summary` surfaces the detected strategy; new `wizard.py set-test-strategy` persists a human answer into `.repo-scan.json` (source of truth → L4 seed); **WIZARD.md Step 3b** (after preset confirm, software-dev only) surfaces detection + ASKS the operator on the undetectable case.
  - S4 (PM rec(a)): "follow the project's detected test strategy; never invent a framework/layout the repo doesn't use" duplicated into all 5 per-stack worker L3 sources (android/ios/web/fullstack/skill). Deploy-verified the behavior reaches the composed worker CLAUDE.md.
  - Gate **5121/0/0**. DS-review (Sonnet — model_router degenerate per #13278): 1 BLOCKER (step ran before preset known → moved to Step 3b) + 4 SHOULD/NIT, ALL fixed.
  - **Comprehension flag (verifier+PM):** WIZARD.md Step 3b + 5 L3 blocks are LLM-consumed; AC1/AC2 ARE the comprehension-testable behaviors. Requested verifier author the CQ spec per TEST-PLAN; did NOT self-generate.

## CARRY-FORWARD

- **#12492 SHIPPED → pending-test (PR #13282).** The progress-liveness cutover. progress_liveness() now authoritative: a zombie (PID-alive + progress-dead, #10855) is killed in update_health → normal reboot path respawns it next poll (proven §7.4 kill-this-poll/reboot-next-poll pattern). PID demoted to teardown-only; dead-PID stays the instant crash signal (§15.4). Additive single gated kill-step in the shadow-divergence block — death/backoff/streak machinery untouched. Guards: intent=RUNNING / not _NO_AUTO_REBOOT / not pid_changed / booting-grace+pause inside progress_liveness(). Escape: SQUIDSQUAD_HARNESS_PROGRESS_LIVENESS_SHADOW_ONLY=1. **AC2 evidence = operator GO** (shadow is console-only, no on-disk artifact — flagged on issue). Gate 5137/0/0; DS-review (Sonnet) NO BLOCKERS (+pid_changed test added). HARNESS-ARCH §1/§13.7 status synced; §15 narrative left to PM (TRD lane, flagged). **When merged: #12271 closes; #12409 retest+close; qa→event-mode unblocks.**
- **#12271** (in-progress, HIGH): progress-based liveness umbrella — closes when #12492 merges.
- **Approved**: #12527 (greenfield FOREIGN-repo installer smoke — LIVE run human-supervised; only static foreign-repo-assumption audit is autonomous), #10690 (gated E6+E7), #10686 (PRD-E E7 manual migration smoke).
- **#13278, #13279** (open, mine, improvement-scan): model_router degenerate output / git_ops._log_diagnostic no timeout. NOT self-fixable without triage.
- **#13271 robust follow-up** (recorded on issue): post-merge scope-audit + auto-revert — the mechanism-agnostic net. Now reinforced by today's partial-loss data point (behind-count guard insufficient; verify merged squash == branch-tip diff, not an older commit).

## STANDING REMINDERS

- Feature work on `squidsquad/task/<n>`; working-state + planning commit DIRECT to main (#11511 strips them from feature branches). `git switch -c` BEFORE code edits.
- Push: `git -c credential.helper='!gh auth git-credential' push`.
- Pending-test gate = `python tests/run_tests.py static` (~5121 gated, fail-closed). Baseline known-failures: test_agent_boundaries + test_compose_author_comments_11142 (both #10360-blocked) → gate still exits 0.
- DeepSeek/model_router degenerate this session → go straight to a Sonnet review subagent (#13278).
- After heading/string rename in LLM-consumed source: `grep -rn "Old Anchor" tests/`.

## Improvement Scan
Status: armed. Prior idle stretch filed #13278 (model_router degenerate) + #13279 (git_ops._log_diagnostic no timeout). Not auto-fixed (await triage).

## Quiet Cycle Counter: 0
