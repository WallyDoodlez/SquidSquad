# CODE-REVIEW — #12495 `/work/assign` manual wake-injection primitive

**Reviewer:** Claude/Sonnet subagent (DeepSeek model_router unavailable — 402 Insufficient Balance, fleet-wide; per [[feedback_model_router_auto_fallback]]).
**Date:** 2026-06-21
**Scope:** harness.py `POST /work/assign` route + `_emit_event` return; tracker.py `work-assign` CLI; tests/test_12495_work_assign.py; AGENT-RUNTIME §8.3 / HARNESS-ARCH §2/§4.3/§13.5 / COMPOSE-ARCHITECTURE §5.1.1 / INSTALLER-ARCH reconciliation.

## Scope decision audited
Built the **narrow manual wake primitive** (operator decision 2026-06-19, option a) — emit `assigned-to` without a transition, no `role:*` label write. NOT the never-built "universal router" (transitions ride /work/assign + harness label rewrites). Transition routing remains EAD-based off the status label (`_STATUS_ROUTING`).

## Findings & dispositions

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 4.1 | HIGH | COMPOSE-ARCHITECTURE §5.1.1 step 2 still described the universal-router (harness rewrites role:* on /work/assign) | **FIXED** — reframed to transition→EAD + manual primitive, no label write. (Missed in my first grep — was truncated.) |
| 2.2 | MED | AGENT-RUNTIME §5.4 EAD bullet 4 "(with the harness's role:* label write per §8.3)" contradicts §8.3 | **FIXED** — corrected to no-label-write, EAD routes off status. |
| 2.3 | MED | AGENT-RUNTIME rev-14 changelog label-lifecycle bullet repeats superseded "harness-side rewrites via /work/assign" without marker | **FIXED** — appended superseded-by-rev-18/#12495 note. |
| 1.1 | MED | Config-unreadable bypasses alias-existence (falls open) — asymmetric vs fail-closed JSON guard | **ACCEPTED + TESTED** — deliberate (matches POST /events unknown-role posture; broken-config wedge worse than one event through). Docstring documents it; +`test_config_unreadable_falls_open` cements the contract. |
| 5.1 | MED | No test for the fall-open path | **FIXED** — test added. |
| 1.2 | LOW | self-assign (400) checked before alias-existence (404) — undocumented ordering | **FIXED** — docstring documents check order + rationale (terse 400 vs 404 leaking the registry). |
| 5.2 | LOW | No test for payload-merge passthrough + reserved-key-wins | **FIXED** — `test_extra_payload_merges_reserved_keys_win`. |
| 4.3 | LOW | INSTALLER-ARCH §441 "normal /work/assign → PM" misleading ("normal" vs backup) | **FIXED** — "manual … (backup/escalation path)". |
| 3.1 | — | Verified harness writes NO role:* labels anywhere (grep + `test_no_label_rewrite_on_assign`) | Doc claim CONFIRMED accurate. |
| 1.4 | — | `_emit_event` now returns `event`; all 10 existing call sites discard the return | CLEAN — no caller broken. |

## Verdict
Reviewer's initial verdict was BLOCKING (the HIGH COMPOSE-ARCHITECTURE drift). All HIGH + MED findings now addressed in commit "address Sonnet DS-audit findings". Code correct against the narrow-primitive spec. Tests: 15 cases green. Full static gate exit 0.

## Open flag for operator/PM
Rev-18 reverses the aspirational Q12 (harness label-writer) / Q13 (X-Squidsquad-Alias on every transition) closed-decisions in favor of the as-built narrow primitive + EAD reality. If the FULL universal router was intended (all transitions ride /work/assign + harness label-writes), re-open #12495. Flagged in the §8.3 rev-18 changelog and the pickup comment.
