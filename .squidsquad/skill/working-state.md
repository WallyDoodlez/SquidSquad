# Working State

- **Task**: none — idle between backlog items (**7 shipped + 1 filed this session**). Driver-tick paced: each idle tick picks up the next clean open bug. #12801 awaits operator inline render check (`python references/tui/app.py`). NEXT bug: **#11716** (run_tests.py integration_only 4-tuple drifted to 6 targets — clean single-file) then #12747(broad live-test SKIP), #13066, #12519, then meds #13113/#12495/#10540.
- **THIS SESSION shipped to pending-test:** #12801 **S2** (data layer) + **S1.3** (launchable TUI app.py + Agents panel; gate 4911) — #12801 STAYS in-progress; #13132 gh-CLI fail-closed (→pending-ship); #13134 /quit-instruction reconcile (→pending-ship; **verifier: CQ + reconcile stale 13032_spec.json**); #13133 scan_index double-count; #13052 v2_catalog_gate backtick regex (Part 1; **Part 2 deferred — security-smoke example-marker false-positive, recommend rescope/close**). **Filed #13136** (stop-requested completeness, needs PM triage).
- **NEXT autonomous backlog** (open role:skill bugs — `list-issues skill`): #13066(low vault frontmatter), #12519(low tracked .claude/settings.json), #12747(low live-test ERROR→clean-SKIP, BROAD ~53 tests — design a conftest/pytest_collection_modifyitems hook, NOT 53 edits; better with fresh context), #13113(med harness telemetry — I have RCA-narrowing), #12495(med AGENT-RUNTIME §8.3 work-assign UNIMPLEMENTED — gates #12801 S4 Wake), #10540(med DM batch ship merges fail). [SHIPPED this session: #12846 PR#13141, #13052 PR#13140; **#11716 CLOSED not-a-bug — already fixed by #12903**]
- **#12801 next stories** (after operator render OK): Story 2 panels (Needs-You from human_queue_rows / Pipeline / Activity), Story 3 action bar (Reboot/Force via harness intent) + Options + Bring-PM hotkey, Story 4 Wake (gated #12495).
- **Updated**: 2026-06-21 04:52:01 (skill — event-mode; #11716 closed not-a-bug)
- **Quiet Cycle Counter**: 0

## #13133 DELIVERED (PR #13138, pending-test) — branch squidsquad/task/13133
scan_index.rebuild() nested findings INSERT inside per-file loop → N-file/1-finding entry = N rows (inflated finding_count/finding_density, skewed suggest_targets). Fix: capture per-file scan_id in dict, insert each finding ONCE attributed to entry['files'][0] (mirrors record_scan default). Tightened test: exact 1 row → tracker.py; file_coverage finding_count 1/0 (was 1/1). 42 green; static PASS 4856/0/0; DS NO_FINDINGS. Deterministic: no CQ/manifest.

## #13134 DELIVERED (PR #13137, pending-test) — branch squidsquad/task/13134
Reconciled agent /quit-termination framing to the #13077 harness-reaper model across 4 handlers (deploy-signal + stop-requested in event-mode-contract.md, self-restart.md, roles/instructions.md Step 7). KEY: LLM agent CANNOT self-/quit — only ceases output; harness force-kills (deploy=active+immediate, status=deploying not covered by 60s net; exit-42/stop=60s net, the actual mechanism not a should-never-fire backstop). exit-42 term KEPT (real cycle_post exit code) per PM. Aligned to committed TRD HARNESS-ARCH §7.4 (fce1f3f2a, merged into branch). Static gate PASS 4856/0/0. Compose reach verified. DS: 1 fixed, 2 → #13136. **VERIFIER CQ (#9184): need new comprehension spec AND reconcile/retire stale tests/comprehension/13032_spec.json (asserts the superseded /quit-load-bearing model).** Filed #13136 (stop-requested ack-stop/ack-cursor completeness).

## #13132 DELIVERED (PR #13135, pending-test) — branch squidsquad/task/13132
tracker.py gh-CLI FALLBACK paths skipped the file's fail-closed pattern (qa improvement-scan, low sev). get_labels/get_state: check=False + returncode/empty guard + try/except JSONDecodeError (→[] / "UNKNOWN" via (data or {}).get('state')); drops nameless label objects. _check_unread_feedback: wrap success-path json.loads → same fail-closed sentinel (guard BLOCKS, not traceback-aborts). +11 regression tests (62 in test_tracker.py). Static gate PASS 4867/0/0. DS external degenerate → Claude-sonnet fallback, 1 LOW finding folded (CODE-REVIEW-13132.md). Deterministic code: no CQ, no manifest.

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
