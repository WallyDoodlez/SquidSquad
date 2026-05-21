# CONTEXT-9744 — DM PR-merge-wait label-blind

**Issue**: #9744
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21
**Status**: pending → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9744 + this CONTEXT-9744.md combined are the contract for skill at pickup.

---

## Authoritative Scope

Add a per-wake label-check to `pr-merge-wait.md` lines 35–47 so DM immediately detects any `pending-human-*` label added mid-wait and aborts rather than continuing until PR terminal state.

---

## 1. Locked Decisions

### D1. Option C — sub-skill instruction change only

**Locked**: edit `references/sub-skills/roles/dm/events/pr-merge-wait.md` lines 35–47 only. In the per-wake step, prepend a label + status pre-check before the existing PR state checks:

1. Call `tracker.py get-labels <issue-number>`.
2. If any label name starts with `pending-human-` → abort; fall through to End-Of-Task Re-Read outcome (a).
3. If `tracker.py get-state <issue-number>` returns non-`pending-ship` → abort; fall through to outcome (b).
4. Otherwise proceed with existing PR state checks.

No new Python code. `tracker.py get-labels` already exists at `tracker.py:1138`.

### D2. Labels to watch — all pending-human-* variants

**Locked**: abort on ANY label whose name starts with `pending-human-` — covers `pending-human-review`, `pending-human-approval`, `pending-human-setup` (per `tracker.py:91-98`). Do not restrict to `pending-human-review` alone.

### D3. Compose pipeline mandatory

**Locked**: after editing the sub-skill source, skill MUST run:
```
python references/scripts/compose.py deploy dm
```
and include the regenerated `tests/comprehension/8697_fixtures/dm_*_CLAUDE.md` in the same PR. Per `feedback_l1_l4_only`.

### D4. CQ spec required in same PR

**Locked**: per `feedback_comprehension_tests_required`, skill writes a CQ spec alongside the sub-skill edit. QA owns the spec format (`tests/comprehension/<number>_spec.json`) — skill produces the question content as part of this task.

### D5. Live-system QA test also required

**Locked** (human-directed strong test bar): a live-system QA test ships alongside the CQ spec. QA creates the test plan from AC-2 (below): simulate operator adding a `pending-human-*` label mid-wait; assert DM detects and aborts within one wake interval. Both CQ + live-system test must pass before pending-ship.

### D6. End-Of-Task Re-Read unchanged

**Locked**: outcomes (a) and (b) of `pr-merge-wait.md` lines 49–62 are NOT modified. The mid-wait path calls the same abort sequence that already exists there.

---

## 2. Grounded File References

| File | Purpose |
|------|---------|
| `references/sub-skills/roles/dm/events/pr-merge-wait.md` lines 35–47 | Source of the per-wake step — only edit site |
| `references/scripts/tracker.py:1138` | `get_labels(number)` — existing helper, no changes |
| `references/scripts/tracker.py:91-98` | `pending-human-*` label taxonomy |
| `references/scripts/compose.py` | `deploy dm` regenerates composed DM CLAUDE.md |
| `tests/comprehension/8697_fixtures/dm_*_CLAUDE.md` | Fixtures regenerated in same PR |

---

## 3. Acceptance Criteria

**AC-1 (sub-skill + compose)**: `pr-merge-wait.md` per-wake section (lines 35–47) contains an explicit label pre-check step that calls `tracker.py get-labels`, tests for any `pending-human-*` label, and aborts to End-Of-Task Re-Read outcome (a) if found. Compose pipeline has been run (`compose.py deploy dm`); regenerated `tests/comprehension/8697_fixtures/dm_*_CLAUDE.md` are included in the same PR with no diff from fresh recompose.

**AC-2 (comprehension — CQ spec)**: a fresh agent given only the modified `pr-merge-wait.md` can correctly identify (a) that a label check runs on each wake before PR state checks, (b) which label prefix triggers an abort, and (c) which End-Of-Task Re-Read outcome applies. QA produces the CQ spec in `tests/comprehension/9744_spec.json`; the CQ passes before pending-ship.

**AC-3 (live-system QA test)**: QA executes a live-system test against a running DM agent: simulate an operator adding a `pending-human-review` label to a `pending-ship` task while DM is in the PR-merge-wait loop; assert DM detects the label and aborts the wait within one wake interval (does not continue to next PR state check iteration). Test plan documented in `.squidsquad/qa/planning/TEST-PLAN-9744.md` and results in `QA-RESULTS-9744.md`.

**AC-4 (regression — all three variants)**: the label check covers all three `pending-human-*` variants. Either the sub-skill text uses a prefix match (`starts with pending-human-`) or explicitly lists all three labels.

**AC-5 (End-Of-Task Re-Read unchanged)**: `pr-merge-wait.md` lines 49–62 are unmodified. No net change to outcome (a) or (b) logic there.

---

## 4. Out of Scope

- Changes to `event_poll.py`, `harness.py`, or any Python scripts.
- Changes to the End-Of-Task Re-Read section of `pr-merge-wait.md`.
- Adjusting the stalled-PR ceiling default (separate policy decision).
- Other AUDIT-A findings (Risk 1–5) — tracked in their own tickets.
- Polling-mode DM behavior — `pr-merge-wait.md` is event-mode only.
- Label taxonomy changes to `tracker.py`.

---

## 5. Sequencing

**Tier 1** — pre-event-flip blocker. Can ship in parallel with other Tier 1 blockers (#9478, #9725, #9415). No ordering dependency among Tier 1 items.

Post-ship: agent reboot coordinated with fleet reset (same pattern as CONTEXT-9478 D9).

---

## 6. Risk Notes

1. **Compose drift**: sub-skill edit must be followed by `compose.py deploy dm` in the same PR. If fixtures are not regenerated, CI will fail on comprehension tests.
2. **Prefix match vs explicit list**: using a prefix match (`pending-human-`) is forward-compatible if new `pending-human-*` labels are added; explicit list requires updates. Recommend prefix match.
3. **get-state overhead**: adding a second `tracker.py` call per wake (after `get-labels`) doubles GitHub API calls per wake cycle. Per research, cost is equivalent to the existing PR forge-read — acceptable.
4. **Two CQ + live-system gates**: both must pass before QA transitions to pending-ship. QA must not ship with either gap open per `feedback_no_ship_with_gaps`.

---

## 7. Open Questions Resolved

| Q | Locked |
|---|--------|
| Q1 — Which `pending-human-*` variants abort? | ALL three (`pending-human-review`, `pending-human-approval`, `pending-human-setup`) via prefix match |
| Q2 — Non-`pending-ship` status transition also abort mid-wait? | YES — `get-state` check added to same per-wake step (D1 step 3) |
| Q3 — CQ spec sufficient, or also live-system test? | BOTH — CQ spec (AC-2) AND live-system QA test (AC-3) ship together |
| Q4 — Stalled-PR ceiling default? | Out of scope — separate ticket |

---

## 8. Next Step

PM transitions #9744 `status:open` → `status:pending` → `status:planned`. Human reviews CONTEXT-9744.md. On approval, PM transitions `planned` → `approved`. Skill picks up.
