# TEST-PLAN-13369 — boot-drain work vs booting-liveness bound

**Issue**: #13369 (verifier-filed, severity:medium, type:issue — auto-approved lane)
**PR**: #13375 `squidsquad/task/13369`, head 6f85fca37
**Derived from**: my own issue's remediation directions + regression-test direction (I authored the issue; those are the ACs).

ACs:
- **AC-a (contract half)**: event-mode-contract.md Case A orders `bootup-complete` BEFORE tending boot-drain events; rationale present; no other surface still teaches the fatal order.
- **AC-b (harness half)**: `progress_liveness()` booting branch past `BOOT_GRACE_SECONDS` is activity-aware — fresh activity postdating THIS spawn (or a ceiling-bounded active pause) = alive; truly-inert boot past the bound = still `wedged-boot-timeout` (**#13179 preserved**).
- **AC-c (regression direction, verbatim from my issue)**: "booting agent with recent activity heartbeats must NOT be killed at the bound; truly-idle booting agent past the bound must still be killed."
- **AC-d (no collateral)**: zombie-kill keys on the boolean, no consumer string-matches new reason values; post-boot liveness paths unchanged (existing suites green).
- **AC-e (comprehension)**: contract fragment is LLM-consumed → CQ spec (13369_spec.json) verifier-reviewed + fresh-agent run, zero misreads.
- **AC-f (gates)**: full static gate on branch HEAD; landing safety (no deletions, no fleet/state artifacts).

## Test cases

- **TC-1**: read the contract diff — step order booted→drain, Case E deploy-signal parenthetical consistent, diagram (`references/roles/instructions.md`) agrees; grep for any remaining drain-before-booted teaching.
- **TC-2**: read `progress_liveness()` booting branch — signals consulted only PAST grace; heartbeat must postdate spawn (generation gap guarded); pause ceiling bounded; inert path intact.
- **TC-3**: run `tests/test_13369_booting_liveness_activity.py` — must include both regression directions from AC-c + the incident shape.
- **TC-4**: run existing liveness suites (12460/13283/13335 families) — unchanged behavior.
- **TC-5**: grep consumers of liveness reason strings — none match `booting-active`/`booting-<pause>` variants; kill decision boolean-keyed.
- **TC-6**: CQ spec review vs my independently-derived questions; fresh sonnet agent on modified contract fragment only; zero misreads required.
- **TC-7**: full static gate on 6f85fca37.
- **TC-8**: landing safety — deletions, behind-count, fleet/state artifacts.

Every TC: PASS / FAIL / HUMAN-REQUIRED. Zero-gap gate applies.
