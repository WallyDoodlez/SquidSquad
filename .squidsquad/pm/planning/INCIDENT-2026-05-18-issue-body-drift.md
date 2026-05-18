# Incident Post-Mortem — 2026-05-18

**Three Phase 5 task implementations shipped to main contradicting the locked CONTEXT.md scope.**

## Summary

Between 05:09 and 11:02 on 2026-05-18, skill agent shipped three PRs implementing the **original Phase 2 framing** of bundle tasks #8694, #8695, and #8701 — NOT the **locked CONTEXT.md scope** that emerged from Phase 2 deepseek review.

| # | PR | What shipped | What was locked | Violation |
|---|---|---|---|---|
| 8694 | #8790 | `TrackerHandoffDispatcher` in `harness.py` — reads tracker, emits `assigned-to`, per-role queue state | Agent event-mode L1 base + `event_poll.py`; **no harness dispatch logic** | Thin-harness lock |
| 8695 | #8801 | `bootup_complete` flag + gating logic on `GET /events/for/<role>` returning empty event list pre-boot | `bootup_complete` flag **informational only**, no queuing/gating | Thin-harness lock |
| 8701 | #8868 | Task-mode `--task <id>` flag + per-task log file | Plus: Gap 2 (mode-gated `REQUIRED_FIELDS` validator) + Gap 3 (`_advance_event_cursor` removal) | Missing scope expansions |

## Timeline (UTC)

- **05:01** — PM transitioned 7 bundle/4792 tickets `planned → approved`, posted code-review-gate reminder on each
- **05:09** — Skill implemented `TrackerHandoffDispatcher` for #8694 (PR #8790)
- **05:16** — QA verified #8694: "zero gaps, 10 new tests pass"
- **05:19** — DM merged PR #8790 → #8694 shipped (closed)
- **05:53** — Skill implemented bootup-complete gating for #8695 (PR #8801)
- **10:49** — Skill implemented #8701 task-mode work (PR #8868), missing Gap 2 + Gap 3
- **11:02** — QA verified #8701: "180 tests pass, DeepSeek R1/R2/R3 addressed"
- (later) — DM merged PR #8801 + PR #8868

**PM session was running in parallel** during planning Phase 3 for #4792 — did not catch the in-flight contract violations until post-hoc audit.

## Root Cause

The Phase 2 deepseek review of `CONTEXT.md` rewrote scope for #8694 and #8695 (the thin-harness pivot — dropped dispatch logic, dropped gating). The locked artifacts were updated:

- ✅ `CONTEXT.md` updated
- ✅ `TEST-PLAN-8694.md` / `TEST-PLAN-8695.md` updated
- ✅ `DECISIONS-4792.md` updated (Q-locks)
- ❌ **GitHub issue bodies never updated** — still carried the original Phase 2 framing

When `planned → approved` transition fired, skill picked up the tickets and read the **issue body** (the canonical entry point for dev workflow per `references/sub-skills/roles/dev/implement-tasks.md`). The body said "harness dispatches" / "harness gates"; skill implemented that. CONTEXT.md wasn't consulted because the dev workflow doesn't direct skill to read planning artifacts.

For #8701, the original body was less stale, but the **Gap 2 + Gap 3 scope expansions** that were added via DECISIONS-4792.md and TEST-PLAN-8701 §3.2/§5 were not in the body either. Same pattern: skill implemented only what the body said.

## Gates that failed

1. **Skill (implementation)** — read only the issue body; never opened CONTEXT.md or TEST-PLAN.md
2. **Skill's deepseek code-review loop (`implement-tasks.md §9c`)** — the loop checks implementation quality against the diff, not against CONTEXT.md. Found minor issues (R1/R2/R3) but missed the architectural contract violation.
3. **QA verification** — verified the implementation against itself ("180 tests pass"), not against TEST-PLAN.md AC list. Missed the contract violation.
4. **DM merge** — merged based on QA's verdict. Didn't inspect for architectural conformance.

Three gates all keyed off implementation output rather than planning contract → drift went undetected.

## Remediation filed

**Cleanup bugs (revert / fix the shipped violations):**
- `#8914` — remove `TrackerHandoffDispatcher` + events-endpoint gating from `harness.py`
- `#8918` — mode-gate `cycle_post.py` `REQUIRED_FIELDS` + remove `_advance_event_cursor`

**Re-implementation (the work the violating PRs should have done):**
- `#8915` — implement #8694 actual scope (`event_poll.py` + agent event-mode L1 base content)

**Process improvements (prevent recurrence):**
- `#8916` — L2 dev rule: must read CONTEXT.md / TEST-PLAN.md before implementing tasks that have planning artifacts
- `#8917` — PM rule: when planning rewrites scope, update the corresponding issue body in the same step

**Body rewrites (already applied):**
- All 7 bundle ticket bodies (#8694, #8695, #8697, #8700, #8701, #8704, #4792) rewritten on GitHub with AUTHORITATIVE SCOPE banner pointing at the locked planning artifact. #4792 also retitled from "Deprecate sentinel files" to "Harness sole-authority lifecycle (rescoped from sentinel-file cleanup)".

## Lessons

1. **Issue body is the dev's contract surface.** If planning rewrites scope, the body must be updated synchronously. CONTEXT.md alone is insufficient because the dev workflow doesn't read it.
2. **AUTHORITATIVE SCOPE banner** at top of every issue body protects against future drift — points skill explicitly at the planning artifact.
3. **The code-review loop catches code quality, not architectural contract.** Code-review needs explicit input of the locked spec to catch contract violations.
4. **QA verification must check TEST-PLAN AC list** in addition to running tests. Implementations can pass their own tests while violating the spec.
5. **All three downstream gates (skill / QA / DM) keyed off implementation rather than planning artifact.** At least one of those gates needs to check the planning artifact directly — most efficient is the PM-side body sync (#8917).

## Connection to existing memory notes

- `feedback_issue_body_must_match_context.md` — the lesson, durable across sessions
- `feedback_l1_l4_only.md` — agent instructions through compose stack only (related principle)
- `feedback_harness_sole_lifecycle.md` — single source of truth for lifecycle (related principle)
- `feedback_comprehension_tests_required.md` — comprehension tests for any agent-instruction change (would have helped surface the L1-L4 gap if skill had run them)
