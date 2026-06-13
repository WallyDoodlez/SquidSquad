# Iteration 465 — #11723 root fix attempt #2; backed out (404 deeper than expected)

**Mode**: loop (sticky). Manual ops.

## What happened
- Gates still closed (#11683 unmerged). Attempted #11723 follow-up (1) properly: (a) boot_remote._resolve_squidsquad_dir env-honor + (b) real_harness fixture writes isolated .local-config (roles -> '.' so _deferred_init skips all → zero distribution).
- Verified the surface first: only the real_harness SUBPROCESS fixture runs _deferred_init; test_event_mode_e2e intentionally avoids the app lifespan. So (a)+(b) SHOULD be the complete fix.
- Result: **404 PERSISTS.** test_9398 TestBootupCompleteAcrossRealSubprocesses (2 tests) still 404 on GET /agents/skill with (a)+(b); they PASS on clean branch (confirmed via stash). So (a)+(b) insufficient.
- Diagnosed deeper: harness is healthy under isolated config (/status 200, clean stderr — not a crash), but the agent's bootup-complete flow doesn't create the 'skill' role record. So the interaction is in the bootup-complete path under isolated SQUIDSQUAD_DIR, NOT in _deferred_init as first assumed.
- **Backed out (a)+(b)** — keeping PR #11729 (Part 2, DS-clean) as the shippable deliverable. Documented the precise debugging lead on #11723 (investigate boot_agent_subprocess stub + bootup-complete role resolution under (a); capture the STUB's stdout/stderr).

## Lesson / judgment
Two cycles (464, 465) confirm the #11723 root fix is a genuinely careful multi-component change that doesn't converge in deep context. The disciplined move each time was to back out rather than half-ship a high-blast-radius change. Part 2 (#11729) already protects the symptom, and the team's pin-keeper scaffolding mitigates — so the root fix is NON-urgent. Should be deprioritized: keep deferring to fresh context or until it operationally matters. Stop re-attempting it in this session.

## Next cycle
- Priority: #11683 ship → land the 4 gated PRs.
- Do NOT re-attempt #11723 root fix this session (diminishing returns; lead documented for fresh context).
