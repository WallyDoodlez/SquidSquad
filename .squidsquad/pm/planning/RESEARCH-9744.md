# RESEARCH-9744 — DM PR-merge-wait label-blind

**Issue**: #9744
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

In event mode, DM holds a `pending-ship` task open while waiting for a feature PR to merge. The wait loop (Monitor-wake periodic forge-read) re-checks the PR's merge/conflict state on each wake but **never re-checks the issue's current labels**. If an operator adds a `pending-human-review` label during the wait — to redirect DM to a human handoff — DM ignores it until the PR reaches a terminal state or the stalled-PR ceiling is hit (which defaults to unbounded). The redirect could be silently delayed for hours or indefinitely.

This is AUDIT-A-events-architecture.md Risk 6 (MEDIUM severity), promoted to Tier 1 pre-event-flip blocker by the 2026-05-21 triage.

---

## 2. Code / Sub-Skill-Grounded Findings

### 2.1 The wait loop definition

**File**: `references/sub-skills/roles/dm/events/pr-merge-wait.md` — entire file (73 lines)

The "How DM Detects The Merge" section (lines 35–47) defines what DM checks on each Monitor wake:

> On each Monitor wake (the persistent `event_poll.py` heartbeat at the role's wait cadence), DM forge-reads the PR exactly once and inspects:
> - PR state == merged → wait ends
> - PR state == closed and not merged → rollback
> - PR state == open but CONFLICTING → rollback
> - PR state == open and (MERGEABLE or UNKNOWN) AND stalled-PR ceiling exceeded → rollback
> - PR state == open and (MERGEABLE or UNKNOWN) and ceiling not exceeded → continue wait

There is no label re-check in this per-wake step. Labels are only read in the End-Of-Task Re-Read (lines 49–62), which runs only after the PR reaches a terminal state (or ceiling exceeded).

### 2.2 The End-Of-Task Re-Read (where label check currently lives)

`pr-merge-wait.md` lines 49–62: the label recheck is step 3 of the post-wait re-read:

> 3. **Re-check the issue's current labels and status** for any operator changes that should redirect DM (e.g. a human flipped the item to `pending-human-review`, or transitioned it back to `planning`).

And outcome (a) (line 57):

> **(a)** A `pending-human-*` label appeared during the wait → leave the item where the operator put it; do NOT transition.

The logic is correct at task-end but **absent mid-wait**.

### 2.3 Labels DM needs to watch

From tracker.py lines 91–98, the `pending-human-*` taxonomy:

| Label | Meaning |
|-------|---------|
| `status:pending-human-review` | Operator hands off to human reviewer |
| `status:pending-human-approval` | Operator gates on human approval |
| `status:pending-human-setup` | Operator needs env/tool setup first |

The issue body and AUDIT-A both specifically call out `pending-human-review` as the motivating case; the broader category is any `pending-human-*` label (all three variants should abort the wait).

Additionally: a direct status transition to a non-`pending-ship` state (e.g., operator transitions to `in-progress` or `planning`) should also abort — this is already handled by outcome (b) in the End-Of-Task Re-Read but has the same "not mid-wait" gap.

### 2.4 Polling mechanism and cadence

`pr-merge-wait.md` line 39: "Monitor wake (the persistent `event_poll.py` heartbeat at the role's wait cadence)."

The cadence is DM's configured Poll Interval (from `.squidsquad/config.md` `Event Driven > Poll Interval`). No hardcoded value appears in `pr-merge-wait.md` — it inherits the role's event poll interval. The Monitor tool exits non-zero if the harness goes down, so the loop is bounded by harness health per `pr-merge-wait.md` line 47: "Event payloads about the PR are hints; the forge is authoritative."

### 2.5 tracker.py `get-labels` capability

`references/scripts/tracker.py` lines 1138–1150: `get_labels(number)` does a single `gh issue view --json` and extracts the label list. This is the same call DM could use to recheck labels mid-wait. It is cheap (one HTTP call to GitHub, same order as a `gh pr view` call).

The per-wake overhead of adding a `tracker.py get-labels` call is therefore equivalent to the existing PR forge-read — no significant cost increase.

### 2.6 "No Sub-Loop During The Wait" constraint

`pr-merge-wait.md` lines 29–33: DM must NOT enter a watch loop or react to comments mid-wait. The label re-check must NOT be implemented as a comment-reactive path — it must be added to the **existing per-wake forge-read step** to preserve the atomicity guarantee. This is not a new loop; it is an additional check in the current loop body.

### 2.7 Delivery-packaging `delivery: skip` check (not affected)

`pr-merge-wait.md` line 60: the `delivery: skip` check runs at End-Of-Task Re-Read outcome (d), unchanged by this fix.

---

## 3. Options

### Option A — Sub-skill instruction change only (pr-merge-wait.md)

Add a label re-check step to the existing per-wake section (lines 35–47) of `pr-merge-wait.md`:

> On each Monitor wake, DM forge-reads the PR **and** re-checks the issue's current labels:
> - If any `pending-human-*` label is present → abort the wait immediately; skip to End-Of-Task Re-Read (outcome a path).
> - If the issue is no longer at `pending-ship` → abort the wait; skip to End-Of-Task Re-Read (outcome b path).
> - Otherwise → proceed with existing PR state checks as before.

The label re-check uses `tracker.py get-labels <number>`, which is already an available tool.

**Scope**: one sub-skill fragment, one logical change.
**Pipeline**: must go through compose pipeline per `feedback_l1_l4_only` — source edit to `references/sub-skills/roles/dm/events/pr-merge-wait.md` then `compose.py deploy dm`.
**Pros**: minimal surface; the existing End-Of-Task Re-Read already has the full abort logic (outcomes a and b) — the mid-wait path just needs to trigger it earlier.
**Cons**: no automated regression coverage without a new test.

### Option B — Sub-skill instruction change + helper script wrapper

Same as Option A but add a small helper (or extend `git_ops.py`/`tracker.py`) that accepts an issue number and returns a binary "should DM abort the wait?" signal — encapsulating the label-check + status-check into one deterministic call.

**Scope**: sub-skill fragment change + one helper function in tracker.py or a new utility.
**Pros**: the abort signal becomes a single deterministic call (easier to test mechanically); aligns with `pattern-deterministic-scripts-over-prose` from vault.
**Cons**: slightly larger change surface; may be over-engineering for what is effectively a one-liner `tracker.py get-labels` call already available.

### Option C — Sub-skill instruction change + comprehension test spec

Same as Option A but the task explicitly includes a comprehension question (CQ) spec as part of the AC — a fresh agent given only the modified `pr-merge-wait.md` must correctly identify the mid-wait label-check step and the abort paths. Regression test is the CQ, not a live-system test.

**Scope**: sub-skill fragment change + CQ spec in the issue body (QA writes the test).
**Pros**: satisfies `feedback_comprehension_tests_required` (task changes agent instructions); ensures future agents trained on the fragment understand the new behavior; no new Python code.
**Cons**: CQ is instruction-coverage only — does not simulate the runtime behavior of a live DM agent in an actual wait.

---

## 4. Recommended Option

**Option C** (sub-skill instruction change + CQ spec AC).

Reasoning:

1. The fix is entirely in the instruction layer — there is no new Python code or new command needed. `tracker.py get-labels` already exists (tracker.py:1138).
2. Option B's helper wrapper adds code for behavior already available; the pattern is appropriate when the call site is multi-step or reusable, but here it's a single `get-labels` call in one context. Option B is not wrong, but it is not necessary.
3. `feedback_comprehension_tests_required` requires a CQ spec for any task that adds or changes LLM-consumed instructions. Option A omits this; Option C makes it explicit. The CQ is the regression coverage for instruction changes (comprehension testing standard).
4. The fix is narrow: add ~3–5 lines to the per-wake section of `pr-merge-wait.md`, then recompose. The End-Of-Task Re-Read logic (outcomes a and b) does not change — the mid-wait path calls the same abort sequence that already exists.

The recommended change to `pr-merge-wait.md` is:

In the "How DM Detects The Merge" per-wake step, add a label + status pre-check **before** the PR state checks:

1. Call `tracker.py get-labels <issue-number>` to retrieve current labels.
2. If any label name starts with `pending-human-` → abort: fall through to End-Of-Task Re-Read (outcome a logic applies).
3. If `tracker.py get-state <issue-number>` returns a status other than `pending-ship` → abort: fall through to End-Of-Task Re-Read (outcome b logic applies).
4. Otherwise: proceed with existing PR state checks (merged / closed / conflicting / ceiling / continue).

---

## 5. Open Questions for PM / Human

1. **Which `pending-human-*` variants should abort the wait?** The issue body cites `pending-human-review` as the motivating case; AUDIT-A says "operator redirections." Is the intent to abort on all three variants (`pending-human-review`, `pending-human-approval`, `pending-human-setup`), or only `pending-human-review`? Recommendation: all three — the wait should not continue if any human-handoff label is present.

2. **Should a non-`pending-ship` status transition also abort mid-wait?** The End-Of-Task Re-Read already handles outcome (b) (issue no longer at `pending-ship`). Adding a status check mid-wait is a slightly wider fix but closes the same gap for direct status transitions. Is this in-scope for this ticket or a separate fix?

3. **Is a CQ spec sufficient as regression coverage, or does the acceptance criteria require a live-system behavioral test** (e.g., QA simulates the wait in a real agent session)? The issue body's AC says "Regression test: simulate operator adding pending-human-review mid-wait; assert DM detects and exits wait within one Monitor wake interval." That reads like a live-system test, not just a CQ — this should be clarified before dev picks up.

4. **Stalled-PR ceiling default is unbounded** per `pr-merge-wait.md` line 44. The label-blind gap is worst-case "indefinitely" precisely because the ceiling is unbounded. Is adjusting the ceiling default a companion fix to include here, or strictly out-of-scope?

---

## 6. Out of Scope

- Changes to `event_poll.py`, `harness.py`, or any Python scripts — the fix lives entirely in the sub-skill instruction layer.
- Changes to the End-Of-Task Re-Read section of `pr-merge-wait.md` — it already handles operator redirections correctly post-wait.
- The stalled-PR ceiling default value — that is a separate configuration policy decision.
- Other AUDIT-A findings (Risk 1–5) — tracked in their own tickets.
- Polling-mode DM behavior — `pr-merge-wait.md` is an event-mode-only fragment; polling-mode DM does not have this wait construct.
- Label taxonomy changes — the `pending-human-*` labels are stable per tracker.py lines 91–98.
