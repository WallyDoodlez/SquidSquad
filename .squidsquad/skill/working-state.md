# Working State

- **Task**: none (idle). Continuation's 11 ships all MERGED+CLOSED (#11140/#12493/#12854/#13101/#12451 etc. confirmed shipped during the ~6h gap; pending-test queue empty). This boot: advanced **#12801** S2 (TUI data-layer pure derivations) — the one cleanly-autonomous pending slice. Now idle.
- **Updated**: 2026-06-21 03:12 (skill — event-mode boot after fleet restart; #12801 S2 increment pushed)
- **Quiet Cycle Counter**: 0

## #12801 IN-PROGRESS (role:skill, HIGH, operator-requested) — branch squidsquad/task/12801
TUI bottom action bar w/ reboot. Decomp: .squidsquad/skill/planning/TUI-12801-DECOMPOSITION.md (contract = pm/planning/TUI-INTERFACE-DESIGN.md, operator-approved). Separate Textual process consuming harness HTTP (#8704 model).
- **DONE (committed/pushed):** S1.1 harness /status per-agent `lag` (EventLifecycleManager.lag_for) + tests. S1.2 references/tui/harness_client.py Textual-free data layer (derive_work_state, lag_to_bar, agent_rows, fetch_*) + tests. **S2 (this boot, 21cd8c459):** format_age + _iso_to_epoch (Z-tolerant) + human_queue_rows (Needs-You shaping) + last_activity_age wired into agent_rows. 37 tests green; static gate exit 0.
- **GATED / NOT autonomous (carry-over blockers):**
  - **S1.3 Textual App skeleton + Story-3 action bar** — need `textual` installed + an INTERACTIVE TERMINAL to verify render. Cannot do autonomously.
  - **S1.4 dep-declaration** — design nuance: textual is a SEPARATE TUI process, not a harness-runtime import → may NOT belong in requirements.txt (test_runtime_requirements.py scopes that file to harness imports). Resolve placement (requirements-tui? requirements-dev? new file) before declaring. Small but needs a call.
  - **Pipeline / Activity panels** — need forge (tracker) / event-source queries, not /status. Separate pure-logic increment possible but lower value until App skeleton exists to consume it.
  - **Story 4 Wake button** — GATED on #12495 (wake-injection primitive).
- **Next autonomous slice (if revisited):** Pipeline-count + Activity-feed pure derivations could be added Textual-free, but they need a forge/event data source decision first. Better sequenced after S1.3/S1.4 land (human-supervised).

## #12450 IN-PROGRESS (role:skill) — branch squidsquad/task/12450 — PM-BLOCKED
Installer test-strategy auto-detection. Surfaces 1+2 DONE (repo_scan.detect_test_strategy + .repo-scan.json → L4 '### Testing Strategy' seed; tests green). **Blocked on TWO PM inputs (posted as comments 20:53 — but bare comments DON'T wake PM per comment-handling; PM may be unaware):**
- **S4 L3-placement** — no software-dev L3 domain dir exists; skill rec=(a) per-stack dup, alt (b) L2-worker / (c) new shared L3 layer (compose change). Needs PM/operator decision.
- **S3 WIZARD.md fallback** — LLM-consumed → needs comprehension AC that PM/verifier authors per #9184/skill-cq (skill doesn't self-author CQ specs).
- ⚠️ Process gap: the block was only commented, never transitioned → PM has no wake. If revisited, consider transitioning to surface it (but L3 design is genuinely PM's call).

## NEXT actionable queue (forge-authoritative — re-run work-queue)
HIGH approved: **#12527** (greenfield FOREIGN-repo installer smoke) — LIVE run is system-affecting (2nd harness :7373 + dep provisioning + interactive wizard) → human-supervised; only a static foreign-repo-assumption audit slice is autonomous. PM posted pre-run notes 2026-06-20 (#13041 = stale INSTALLER-ARCH §4.1, do NOT treat shipped fixes as breakage). **#12492** GATED on #12460 shadow window. **#12271** umbrella, slices 1-3 shipped, cutover gated.
Medium approved: #10690 (gated E6+E7), #10686 (PRD-E E7 manual migration smoke, post-E6).

## Recurring meta-risk
Clone chronically behind origin. `git -c credential.helper='!gh auth git-credential' pull --ff-only` (manager helper wedges silently; -c BEFORE subcommand). Feature work on squidsquad/task/<n>; working-state + planning commit DIRECT to main (#11511 guard strips them from feature branches). `git switch -c squidsquad/task/<n>` BEFORE code edits. Stale feature branch: if main never touched the branch's files, `git merge origin/main` is conflict-free regardless of commits-behind.

## Full static gate reminder ([[feedback_full_static_gate_not_subset]])
pending-test needs `run_tests.py static` (~4899 gated, fail-closed), NOT bare run_tests.py ("Ran 53/OK" = integration subset). Baseline known-failures: test_agent_boundaries + test_compose_author_comments_11142 (both #10360-blocked) → gate still exits 0. After ANY heading/string rename in LLM-consumed source: `grep -rn "Old Anchor" tests/`.

## Improvement Scan
Status: eligible (idle). Last completed: (none this session — productive boot).
