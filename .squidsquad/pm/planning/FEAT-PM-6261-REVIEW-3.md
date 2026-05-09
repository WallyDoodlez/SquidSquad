# FEAT-PM-6261 Focus Area 3 Review — DM Skips QA + DM Merge Conflict Handling

## Current DM Flow (exact code references)

### tracker.py — LEGAL_TRANSITIONS (lines 117–151)

```python
LEGAL_TRANSITIONS = {
    ...
    "status:in-progress": {
        "status:pending-test",
        "status:approved",
        "status:planning",
        "status:pending-human-review",
        "status:pending-human-setup",
    },
    "status:pending-test": {"status:in-progress", "status:pending-ship", "status:pending-human-review"},
    "status:pending-ship": {"status:shipped", "status:in-progress"},
    ...
}
```

`in-progress → pending-ship` does NOT exist in LEGAL_TRANSITIONS. DM cannot skip pending-test from the tracker's perspective — the state machine does not have this edge.

### tracker.py — ROLE_AUTHORITY (lines 167–216)

```python
ROLE_AUTHORITY = {
    ...
    # QA/PM owns verification
    ("status:pending-test", "status:in-progress"): {"qa", "pm"},
    ("status:pending-test", "status:pending-ship"): {"qa", "pm"},
    ("status:pending-test", "status:pending-human-review"): {"qa", "pm"},
    ...
    # DM owns delivery / shipping
    ("status:pending-ship", "status:shipped"): {"dm"},
    # Backward: pending-ship→in-progress for merge conflicts (#1727)
    ("status:pending-ship", "status:in-progress"): {"pm", "qa"},
    ...
}
```

Key observations:
- `dm` does NOT appear in any `pending-test` transition authority.
- `dm` is only authorized for `pending-ship → shipped`.
- Merge conflict rollback (`pending-ship → in-progress`) is authorized only for `pm` and `qa` — **NOT `dm`**.

### delivery-packaging.md — Step 0b isDraft gate (lines 40–50)

```
0b. PR merge gate: If Branch Workflow is enabled ... check for an associated PR ...
    Find the PR matching this issue number. If found:
    - If isDraft is true: STOP — this PR has not been verified by QA. Comment... Skipping.
    - If isDraft is false: merge the PR before shipping:
        python references/scripts/git_ops.py pr-merge [PR_NUMBER]
        If merge fails, comment on the issue and skip this item.
```

The plan correctly identifies removing the `isDraft` condition from Step 0b. The merge-fail path (`If merge fails, comment on the issue and skip this item`) already exists but has no tracker transition — it just skips. This is the merge conflict handling path.

### common/task-pickup.md — pending-test transition (lines 22–28)

```
9. Transition to pending-test:
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
   ...
```

This sub-skill is included by DM via `includes.yml` (line 10: `common/task-pickup`). DM uses it for bugs fixed via issue-triage, which go `open → pending-test` (not via task-pickup). Task-pickup (`approved → in-progress → pending-test`) is for approved task work. DM picks up items at `pending-ship` directly — DM does NOT use task-pickup for delivery items.

### dm/instructions.md — no pending-test references

DM's instructions.md has no explicit pending-test references. DM's cycle: pick up `pending-ship` items in delivery-packaging, fix `open` bugs in issue-triage (which goes `open → pending-test`). Neither path uses `in-progress → pending-ship`.

---

## Changes Needed

- [Remove `isDraft` check from delivery-packaging.md Step 0b] — **COVERED** (research line 25, behavior change #3)
- [Update tracker.py docstring lines 22-23 to remove "PM/QA combined identity" language] — **COVERED** (research line 47)
- [Update ROLE_AUTHORITY comment lines 182-186 to change framing] — **COVERED** (research line 47)
- [Merge conflict path in delivery-packaging.md: add explicit tracker transition] — **GAP** (see below)
- [Add `in-progress → pending-ship` to LEGAL_TRANSITIONS for dm-lead] — **NOT IN PLAN — and NOT NEEDED** (DM never goes in-progress → pending-ship; the plan's framing about "DM skipping QA" refers only to the isDraft gate, not a new transition path)
- [Update ROLE_AUTHORITY: `pending-ship → in-progress` to include `dm`] — **GAP** (see below)
- [tests/test_tracker_authority.py: comment text references "PM/QA combined identity"] — **COVERED** (research addresses docstring/comment language)

---

## Event/Script Side Effects of Skipping pending-test

**Clarification**: DM does NOT skip pending-test in the state-machine sense. Items still go through `pending-test → pending-ship` (via QA). "DM skips QA" means DM's delivery-packaging no longer gatekeeps on `isDraft` status. The tracker state machine path for items is unchanged: `in-progress → pending-test → pending-ship → shipped`.

- **No event emission gap**: `pending-test → pending-ship` still fires `status-transition` events (tracker.py line 994–1003). No change.
- **TC coverage gate still runs**: The hard gate at tracker.py lines 904–939 (TC coverage check for `pending-test → pending-ship`) is not affected — it still fires when QA calls this transition. DM never calls this transition.
- **`_GUARDED_TRANSITIONS`** set includes `("status:pending-test", "status:pending-ship")` — the unread-feedback guard. DM does not call this transition, so no impact.
- **cycle_pre.py `_get_verifiable_roles()`** (lines 430–450): always includes `dm` and `pm` in the pending-test query — this is for QA to find DM-owned items that need verification. Unchanged by this task.
- **cycle_pre.py `_build_dm_input`** queries `pending-ship` items (line 875). This is what DM actually consumes — unchanged.
- **Auto-draft-PR-conversion** in tracker.py (lines 981–982): fires on `pending-test` and `pending-ship` transitions. Not affected.

---

## Gaps Found

### GAP-1: Merge conflict path in delivery-packaging has no tracker transition (UNHANDLED)

**Current state**: delivery-packaging.md Step 0b says "If merge fails, comment on the issue and skip this item." No transition is specified. The item remains at `pending-ship` with a comment but no status change.

**Problem**: With the `isDraft` gate removed, DM will now always attempt `gh pr merge`. If the merge fails (conflict), the item stays stuck at `pending-ship` indefinitely. The existing comment-and-skip behavior was acceptable when DM could skip for other reasons (isDraft), but after removing that gate, the only reason DM skips is a merge failure — which needs an active rollback to route it back to the dev agent.

**What's needed**: When `pr-merge` fails, DM should transition `pending-ship → in-progress` and comment explaining the conflict. But ROLE_AUTHORITY currently does NOT authorize `dm` for `pending-ship → in-progress` (only `pm` and `qa` are authorized). DM cannot perform this rollback.

**Research mentions this (Open Question Q3)**: "What should DM do if a PR exists but can't be merged (conflict)? Currently there's no merge conflict handling... DM should handle conflicts by commenting on the issue and skipping." But the research does NOT identify that `dm` is blocked by ROLE_AUTHORITY from performing `pending-ship → in-progress`.

**Fix required**: Either:
- Add `dm` to `ROLE_AUTHORITY[("status:pending-ship", "status:in-progress")]` (currently `{"pm", "qa"}`), OR
- Document that DM comments and PM/QA must perform the rollback transition manually

The plan does not specify either option. This is an unresolved gap.

### GAP-2: LEGAL_TRANSITIONS and ROLE_AUTHORITY need no DM-specific changes for the isDraft removal — but the plan implies otherwise

**Research line 47**: "lines 182-186 (ROLE_AUTHORITY comment): rewrite to say 'PM is authorized alongside QA for pending-test transitions as a coordination backstop.'"

This is purely a comment/docstring change. Confirmed: the actual ROLE_AUTHORITY entries are unchanged (PM retains `pending-test → in-progress` and `pending-test → pending-ship` authority). No code change needed to the authority table for the DM isDraft removal — only the comment framing changes. The plan correctly describes this as documentation only.

### GAP-3: test_tracker_authority.py test comment references "PM/QA combined identity" framing (MINOR)

**File**: `tests/test_tracker_authority.py` line 156:
```python
# Both QA and PM are authorized. PM is always authorized because the PM
# agent carries the combined "PM/QA" identity in deployments without a
# dedicated QA agent.
```

The plan covers updating tracker.py's own comment (line 182-186 of tracker.py) but does NOT mention updating the corresponding test file comment. After #6261, this test comment will be stale — it still describes the old "combined PM/QA identity" framing. This is a minor documentation gap but will cause confusion if someone reads the tests to understand the authority model.

### GAP-4: DM's merge conflict path has no rollback instructions in delivery-packaging.md (BEHAVIOR GAP)

**Current delivery-packaging.md Step 0b**:
```
If merge fails, comment on the issue and skip this item.
```

After removing the `isDraft` gate, this is the only early-exit path. "Skip" means the item stays at `pending-ship` with a conflict-explanation comment. No one is instructed to roll it back. With PM's pipeline sentinel (Step 6f), PM will eventually detect `pending-ship` stall and nudge — but it will nudge DM again (since the item is at `pending-ship`), not route it back to the dev agent.

**What's needed in delivery-packaging.md**: Explicit instruction for the merge-fail path. Something like: "Comment explaining the conflict, then notify PM to route back via `pending-ship → in-progress`." The plan does not address what the updated delivery-packaging.md should say for the merge-fail path.

### GAP-5: `common/task-pickup.md` L2 sub-skill changes are NOT needed for DM (confirm no scope creep)

The research notes that L2 `task-pickup` sub-skill (which transitions `in-progress → pending-test`) is included by DM via `includes.yml`. DM uses this sub-skill only for bug fixes picked up via issue-triage (`open → in-progress → pending-test`). The plan for "DM skips QA" applies only to delivery items at `pending-ship` — NOT to DM's own bug fix flow, which still correctly goes through `pending-test`. The plan correctly does NOT change `task-pickup.md` for DM.

**Risk**: If a developer reads the plan and thinks "DM skips QA" means DM's own bugs also skip QA, they will incorrectly modify task-pickup.md or issue-triage.md. The plan should explicitly state the scope: the QA skip applies only to delivery items picked up from `pending-ship`, not to DM-owned bugs.

### GAP-6: cycle_pre.py `_build_dm_input` still queries `pending-ship` only — no change needed, but plan doesn't confirm this

cycle_pre.py line 875 builds DM's work queue from `status:pending-ship`. Nothing changes here. The plan does not explicitly confirm this, which could cause uncertainty. Minor documentation gap only.

---

## Summary Table

| Gap | Severity | Covered in Plan? |
|-----|----------|-----------------|
| GAP-1: DM blocked from `pending-ship → in-progress` by ROLE_AUTHORITY | HIGH | NO — Q3 is raised but not resolved |
| GAP-2: LEGAL_TRANSITIONS/ROLE_AUTHORITY need no code change (confirmed) | — | YES (correctly) |
| GAP-3: test_tracker_authority.py comment stale after framing change | LOW | NO |
| GAP-4: delivery-packaging.md merge-fail path has no rollback instruction | MEDIUM | NO |
| GAP-5: task-pickup.md not changed — scope correctly limited | — | YES (implicitly) |
| GAP-6: cycle_pre.py DM input builder unchanged | LOW | NO (but benign) |

**Critical gap**: GAP-1 and GAP-4 are coupled. DM cannot self-heal on merge conflict because tracker.py blocks `dm` from transitioning `pending-ship → in-progress`. The plan raises this as an open question (Q3) but does not answer it. Without resolution, merged-PR-conflict items will silently stall at `pending-ship` after the `isDraft` gate is removed.
