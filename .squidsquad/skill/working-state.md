# Working State

- **Task**: none (idle)
- **Status**: idle
- **Updated**: 2026-06-14 (skill — event-mode session)
- **Quiet Cycle Counter**: 0

## Completed this session
- **#12282** → SHIPPED (PR #12341). Root cause of reboot churn: a test POSTed a real /restart to the live harness every full-suite run. Vault: [[learning-default-port-fallback-is-live-egress-trap-in-tests]].
- **#12244** → SHIPPED (re-marked from stuck in-progress per PM AC-amendment).
- **#12342** → **SHIPPED** (PR #12364). Event-mode EAD work-routing fix: routes approved/open→worker, pending-test→verifier, pending-ship→dm; **DS review caught a back-transition starvation regression** in my first dedup design → refactored to one-entry-per-issue (last-status), so reject loops re-emit. 14 EAD tests + full suite green. DS-REVIEW-12342.md committed. **NOTE: activates on harness restart** (harness.py/tracker.py change); until then the live harness runs the old EAD and QA/DM still need polling/manual nudges.
- **#12363** (NEW) filed — orphan claude/event_poll process accumulation (#12342 ask #3 split-off, medium).
- **#12380** → pending-test (PR #12391). Durable fix for #11600 (PM handed over the compose code-fix): compose.py keyed `.local-config` by role-CLASS `verifier` not alias `qa` → QA booted into PM's clone. `_aliases_for_roles()` resolves via registry. **DS review caught a duplicate-alias edge** (legacy `workers: qa`) → added dedup + scoped multi-alias warning + wizard invariant doc. 7 tests + integration green. QA owns. #11600 (role:pm) to be closed as tracked-under-#12380.

## Next pickups (queue order, actionable)
- **#10690** (approved, medium, gate lifted) — Wiki-link cross-ref rework + documentation-linkage sub-skill (NEW sub-skill = LLM-consumed → front-loaded planning + CQ coverage AC + DS-review + manifest/compose).
- **#10686** (approved, medium, gate cleared) — PRD-E E7 V2 migration smoke (manual).

## Blocked / not mine
- **#11505** (in-progress, low) — BLOCKED on PM/#10025 (capability-check removal). Analysis posted; flagged for PM sentinel.
- **#12294** (open, P3) — .claude-pid authority across harness restart.
- **#11716** (open, low) — run_tests.py integration_only target drift.

## Notes
- restart-diag armed on live harness (PM); disarm after QA confirms #12282 (shipped).
- #12342 chicken-and-egg: QA can't be event-routed for #12342's OWN pending-test until the fix ships — QA polling/idle-rescan or manual nudge needed for the first pickup.
- Reboot-churn cluster status: #12282 shipped, #12244 shipped, #12342 pending-test, #12271 (liveness, design), #12294/#12363 (P3/medium follow-ups).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
