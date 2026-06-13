# Working State

- **Task**: #11503 (high, in-progress, role:skill) — post-cutover test-debt. **21/23 stale tests cleared; remaining 2 are #10360-gated (not stale).**
- **Status**: Group A tail done this cycle (cycle 1644): 4 stale tests rebound + un-quarantined (cycle_pre, terminology_6274, own_domain_autofix, vault_synthesis). Triage finding: last 2 KNOWN_FAILURES (compose_author_comments_11142, agent_boundaries) block on OPEN #10360 (Responsibility compose slot §5.2), NOT cutover-stale. Re-pointed their reasons; did NOT weaken assertions. PM decision requested on #11503 (recommend: close at 21/23, let #10360 carry final 2).
- **Commits (bundle branch, LOCAL — not pushed; push to origin/post-cutover-cleanup explicitly when PR-ready)**:
  - 7357b6cd7 #11503 Group A tail (4 stale cleared + 2 triaged to #10360) [cycle 1644]
  - eb21957ea cycle 1643 state; 2ad42181f #11657 event_poll removal; 85d6eb430 #11503 Group A/B (12 tests) [cycle 1643]
  - (prior-session ancestors: 7f6c5258b, e8896df59, 6968c3217)
  - push.default=simple → bare push safely refuses (branch≠upstream main).
- **Branch**: squidsquad/skill/post-cutover-cleanup (bundle branch per operator decision c-2026-06-12). NOTE: upstream misconfigured to origin/main — push must target origin/post-cutover-cleanup explicitly, NEVER main.
- **Mode**: POLLING (harness probe failed at boot — port file 59999, connection refused). /loop cron ea6e7da1 (30m). NOTE: a process answers on default 7373 — port file looks stale; possible #11586-class boot-probe mismatch. Did NOT re-probe (mode sticky).
- **Updated**: 2026-06-13 03:30

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible — defer until #11503 dispositioned)

## #11503 — DONE (stale debt cleared)
All 21 genuinely-stale post-cutover tests rebound to v2 reality + un-quarantined across cycles:
- cycle 1642(prior): Group C ×3 + event-mode ×2 (5)
- cycle 1643: Group A/B ×12
- cycle 1644: Group A tail ×4 (cycle_pre, terminology_6274, own_domain_autofix, vault_synthesis)

## #11503 — BLOCKED on OPEN #10360 (the final 2 of 23 — NOT stale)
#10360 = "Implement Responsibility compose slot per COMPOSE-ARCHITECTURE §5.2" (OPEN). Both tests fail on genuinely-incomplete §5.2 work:
- **test_compose_author_comments_11142**: stale half FIXED (boot-bootstrap marker moved to references/roles/instructions.md in #11331). test_10360_cleanup_markers_preserved half detects #10360 breadcrumbs dropped by #11331 rewrite — gated on #10360.
- **test_agent_boundaries**: 20 missing L3 variant responsibility.md stubs (§5.2) gate on #10360; 19 other assertions (ac4/ac6/ac11) superseded by agent-boundaries sub-skill retirement — rewrite whole file when #10360 unblocks.
Cross-linked on #10360. KNOWN_FAILURES reasons re-pointed. DO NOT un-quarantine these by weakening assertions; they ride #10360.

## #11657 — DONE (cycle 1643, commit 2ad42181f)
Stale event_poll integration test removed (superseded by #11601). Deviation noted on issue.

## Tree cruft (NOT tracked, leave untracked)
- .claude/scheduled_tasks.lock.stale-bak — #11641 (stale lock crash)
- .squidsquad/skill/planning/CODE-REVIEW-11601.md — #11601 leftover (shipped)
- .squidsquad/.harness-port — restored to 59999 during #11657 triage (gitignored)

## Standing items
- #10360 (high, OPEN) — Responsibility compose slot §5.2; now also gates the final 2 #11503 tests
- #11641 (high) — stale scheduled_tasks.lock crashes claude → reboot loop
- #11640 (high) — boot_remote._get_clone_path REPO_ROOT fallback must fail-closed
- #11586 (high) — agents don't reach event mode on reboot (cf. port-file/7373 mismatch)
- #11587 (medium), #11511 (medium), #11505 (capabilities teardown)
