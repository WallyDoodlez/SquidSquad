# Working State

- **Task**: #11503 (high, in-progress, role:skill) — post-cutover test-debt: 23 static tests red since v0.44.0 cutover
- **Status**: 17/23 done & committed (Group C ×3 + event-mode ×2 prior; Group A/B ×12 this session). 6 Group A tail remain.
- **Also this session**: #11657 (event_poll stale integration test) filed + fixed (removed as superseded by #11601). Rides bundle branch.
- **Commits this session** (bundle branch, LOCAL — not pushed; push to origin/post-cutover-cleanup explicitly when PR-ready): 85d6eb430 #11503 Group A/B (12 tests); 2ad42181f #11657 event_poll stale-test removal. (Prior-session ancestors: 7f6c5258b, e8896df59, 6968c3217.) push.default=simple → bare push safely refuses (branch≠upstream main).
- **Branch**: squidsquad/skill/post-cutover-cleanup (bundle branch per operator decision c-2026-06-12; even with origin/main). NOTE: upstream is misconfigured to origin/main — push must target origin/post-cutover-cleanup explicitly, NEVER main.
- **Mode**: POLLING (harness probe failed — port file said 59999, connection refused). /loop scheduled (cron ea6e7da1, 30m). NOTE: a process answers on default 7373 (event_poll exit 1 in repro) — port file (59999) looks stale vs the actual harness on 7373; possible #11586-class boot-probe mismatch worth a look later. Did NOT re-probe (mode sticky per boot contract).
- **Updated**: 2026-06-13 02:52

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible — defer until #11503 ships)

## #11503 — plan (front-loaded)
23 static tests quarantined in KNOWN_FAILURES (tests/run_tests.py) when the gate went dead at v0.44.0 cutover (#11394). Fix each, remove its KNOWN_FAILURES entry, gate re-includes it.
- **Group A** — stale tests asserting pre-v2/pre-rename/pre-cutover structure → update test to v2 reality.
- **Group B** — fixture drift: test_config_functions (SAMPLE_CONFIG FIELD_MAP). DONE.
- **Group C** — possibly-real masked regressions (triage first). DONE.

## #11503 — Group A/B DONE this session (commit 85d6eb430)
Un-quarantined 12: test_references, test_state_bus, test_comms_sub_skills, test_4792_fragment_hygiene,
test_deterministic_qa_framework, test_dm_verify_before_block, test_pickup_comment_fidelity_9946,
test_stale_tracker_files_ref (pre-rename/pre-cutover); test_compose_a2f_10492, test_atomic_emit_b7,
test_a3_golden_link_stage (compose golden drift — regenerated fixtures); test_config_functions (Group B).

## #11503 — Group A REMAINING (6 in KNOWN_FAILURES)
test_cycle_pre (#6274 alias rename partial), test_own_domain_autofix (removed v1 {{include:}} syntax),
test_vault_synthesis ('create-task' in restructured pm source), test_terminology_dual_aware_6274
(pre-rename dev/skill → worker/skill), test_compose_author_comments_11142 (boot-bootstrap wrapper marker),
test_agent_boundaries (removed responsibility.md + phrase).

## #11657 — DONE this session (commit 2ad42181f)
Stale integration test test_event_poll_exits_cleanly_when_harness_unreachable asserted pre-#11601
contract (missing port → exit 2). #11601 made _discover_port default to 7373 (fixes #11586). Removed as
superseded — #11601 contract covered in tests/test_event_poll.py (44 pass); harness-down no-crash covered
by event_bus silent-noop tests + test_9398. Deviation (rebind→remove) noted on #11657. Suite green 53/2.

## Tree cruft (NOT #11503, leave untracked)
- .claude/scheduled_tasks.lock.stale-bak — relates to #11641 (stale lock crash); separate issue
- .squidsquad/skill/planning/CODE-REVIEW-11601.md — #11601 leftover (shipped); harmless
- .squidsquad/.harness-port — restored to 59999 during #11657 triage (gitignored)

## Standing items (post-#11503)
- #11641 (high, open) — stale scheduled_tasks.lock crashes claude → reboot loop
- #11640 (high, open) — boot_remote._get_clone_path REPO_ROOT fallback must fail-closed
- #11586 (high, open) — agents don't reach event mode on reboot (cf. port-file/7373 mismatch noted above)
- #11587 (medium), #11511 (medium), #11505 (capabilities teardown)
