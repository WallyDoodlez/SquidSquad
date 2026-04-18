# FEAT-PM-1228 Research — PM Pipeline Sentinel

## Summary

The PM Ralph Loop has a structural flaw: Steps 3-6 (Testing & Verification) are skipped wholesale when a QA agent is present, but pipeline-critical logic (PR monitoring, auto-merge, conflict detection, delivery fallback, post-merge recompose) is nested inside that skipped block. This means when QA is installed (the common case), PM never runs:

- **Step 6b** (pr-flow): PR conflict detection (`mergeable: CONFLICTING`), merged/closed PR status sync, auto-merge for pending-ship tasks when DM is present
- **Step 6d** (delivery-fallback): Auto-merge + delivery packaging + ship transition when DM is absent
- **Step 6e** (post-merge-recompose): Template recomposition after branch merges

QA has its own Step 5b (Monitor PRs) but it only covers a subset: merged/closed status sync and PR comments. QA does NOT check for merge conflicts (`mergeable` field not queried) and does NOT auto-merge. QA's PR monitoring is gated on `PR Flow: yes` in config, which is currently `no` in this project's config.md.

The fix requires extracting pipeline management from the QA-skipped block into an always-run step.

## Impact Analysis

### Files touched
- `references/sub-skills/pm-specific/pr-flow.md` — extract pipeline-sentinel logic or restructure
- `references/sub-skills/pm-specific/testing-and-verification.md` — narrow the QA-skip gate
- `references/sub-skills/pm-specific/delivery-fallback.md` — may need to be callable from outside Steps 3-6
- `references/sub-skills/pm-specific/post-merge-recompose.md` — move outside QA-skip block
- `references/roles/pm/CLAUDE.md` — restructure step ordering in the template
- `references/roles/pm/includes.yml` — potentially add new sub-skill entry
- `.squidsquad/pm/CLAUDE.md` — recomposed output

### Behavior changes
- PR conflict detection runs every cycle regardless of QA presence
- Auto-merge runs every cycle for pending-ship tasks regardless of QA presence
- Post-merge recompose runs every cycle regardless of QA presence
- Delivery fallback (when DM absent) runs every cycle regardless of QA presence
- Stall detection for pending-ship tasks becomes a new capability
- No change to verification behavior — QA still owns testing when present

### Dependencies
- `references/scripts/git_ops.py` — `pr_merge()` function (no changes needed)
- `references/scripts/config.py` — config reading (no changes needed)
- `references/scripts/tracker.py` — status transitions (no changes needed)
- `references/scripts/compose.py` — recomposition (no changes needed to script, but must be run after template changes)

## Current Ralph Loop Structure

### Step-by-step map

| Step | Sub-skill | Skipped when QA present? | Pipeline-critical? |
|------|-----------|--------------------------|-------------------|
| 1 | pull-latest | No | No |
| 1b | context-pressure | No | No |
| 1c | resume-working-state | No | No |
| 2 | checkin | No | No |
| 3 | testing-and-verification (E2E tests) | **YES** | No (QA runs its own) |
| 4 | testing-and-verification (investigate failures) | **YES** | No (QA handles) |
| 5 | testing-and-verification (verify fixed issues) | **YES** | No (QA handles) |
| 6 | testing-and-verification (verify pending-test tasks) | **YES** | No (QA handles) |
| 6b | pr-flow (PR monitoring + auto-merge) | **YES** | **YES** |
| 6c | testing-and-verification (ship counter) | **YES** | Partially (counter increment) |
| 6d | delivery-fallback | **YES** | **YES** |
| 6e | post-merge-recompose | **YES** | **YES** |
| 7 | health-check | No | No |
| 7b | github-issues (triage) | No | No |
| boot | boot-remote-agents | No | No |
| scan | improvement-scan | No | No |
| 8 | iteration-log | No | No |
| 4b | vault-remember | No | No |
| vault | vault-optimize | No | No |
| 9 | git-commit | No | No |
| 10 | self-restart | No | No |

### The QA-skip gate (testing-and-verification.md, line 1-3)

The gate is at the very top of the `testing-and-verification` sub-skill:
```
QA presence check: If .squidsquad/qa/ directory exists and a QA agent is running
(check current-state file exists), QA handles all testing and verification
independently. Skip Steps 3-6 entirely.
```

The problem: Steps 6b, 6c, 6d, and 6e are numbered as sub-steps of 6, so they fall inside the "Skip Steps 3-6" blanket. But they are actually separate sub-skills (pr-flow, delivery-fallback, post-merge-recompose) included independently in `includes.yml`.

### Why the numbering is misleading

In `references/roles/pm/CLAUDE.md` (the template), the includes are:
```
{{include: pm-specific/testing-and-verification}}   ← Steps 3-6
{{include: pm-specific/pr-flow}}                     ← Step 6b
Step 6c (inline)                                     ← counter
{{include: pm-specific/delivery-fallback}}           ← Step 6d
{{include: pm-specific/post-merge-recompose}}        ← Step 6e
```

These are separate includes, but the testing-and-verification sub-skill's QA gate says "Skip Steps 3-6 entirely." When PM reads the composed output, it sees the gate first, then all subsequent steps numbered 6b/6c/6d/6e appear to be within scope of the skip.

## Auto-Merge Flow Analysis

### Current triggers
Auto-merge appears in TWO places:

1. **pr-flow.md (Step 6b)**: "Auto-merge for pending-ship tasks (runs regardless of PR Flow setting)" — triggers when a task transitions to `Pending Ship` AND DM is present. This is the DM-present path.

2. **delivery-fallback.md (Step 6d, sub-step 0)**: Auto-merge as first step of PM delivery when DM is absent. This is the DM-absent path.

### Conditions for auto-merge
All must be true:
- `Auto Merge: yes` in config.md
- `Branch Workflow: yes` in config.md
- Item is `type:task` (not `type:issue`)
- Item does NOT have `merge:manual` label

### What happens on success/failure
- **Success**: Discussion comment logged, proceed to delivery
- **Merge conflict**: Route back to dev agent (status -> In Progress), skip delivery
- **Unexpected failure**: Log error, fall back to manual merge, leave as pending-ship

### Why it doesn't run when QA is present
Both auto-merge paths live inside the Steps 3-6 block that gets skipped when QA is present. The pr-flow sub-skill's auto-merge section explicitly says "runs regardless of PR Flow setting" but this is moot because the entire step is skipped by the QA gate.

## QA's Partial Coverage

QA has its own PR monitoring (Step 5b in `qa-specific/verification.md`) but it:
- Does NOT check `mergeable` field (no conflict detection)
- Does NOT auto-merge PRs
- Does NOT run delivery-fallback
- Does NOT run post-merge-recompose
- Is gated on `PR Flow: yes` (currently `no` in this project)

QA transitions tasks to `pending-ship` (or `pending-review` when PR Flow is on), but nobody picks up the pending-ship items for merge+delivery because PM skips those steps.

## Side Effects

### Risk 1: Race condition between QA verification and PM auto-merge — Severity: M
If PM auto-merges a PR for a task that QA is currently verifying, QA may be verifying stale code.
**Mitigation**: Auto-merge only triggers for tasks already at `pending-ship` status. QA transitions tasks to `pending-ship` only after verification passes. So by the time PM tries to auto-merge, QA has already approved. No race.

### Risk 2: Delivery-fallback running while QA is mid-verification — Severity: L
If delivery-fallback runs on a task that QA hasn't finished verifying, it could ship prematurely.
**Mitigation**: Delivery-fallback only processes tasks at `pending-ship` status. QA must transition the task to `pending-ship` first. Status is the gate, not the step ordering.

### Risk 3: Step ordering change breaks planning phase suppression — Severity: L
Planning phase suppression (Step 1c) skips "all other steps." The new pipeline sentinel step must also be skippable during planning suppression, same as the current behavior.
**Mitigation**: Planning suppression explicitly lists what it runs (pull + health check). The new step is not in that list, so it will be suppressed by default. This is acceptable — pipeline monitoring can wait 30 minutes during planning.

### Risk 4: Post-merge recompose running more frequently — Severity: L
Currently only runs when PM does the full QA fallback path. Moving it outside the QA skip means it runs every cycle.
**Mitigation**: The sub-skill already has an early exit ("If no merged branches touched references/, skip silently"). Cost is one `git log` check per cycle — negligible.

### Risk 5: Double PR monitoring (PM + QA both checking PRs) — Severity: M
If PM's pipeline sentinel checks PRs AND QA's Step 5b checks PRs, they may try to transition the same task.
**Mitigation**: PM's pipeline sentinel should focus on merge-conflict detection and auto-merge only. Status sync for merged/closed PRs can be deduplicated — either PM or QA does it, not both. Since QA already has Step 5b, PM's sentinel should skip the "merged/closed PR status sync" portion when QA is present and PR Flow is on.

## Edge Cases

### QA rejects a task that PM already auto-merged the PR for
This cannot happen under the current status flow. Auto-merge triggers on `pending-ship`, which is AFTER QA has verified. If QA later rejects (which would require a re-test), the PR is already merged. The dev agent would need to fix on a new branch. This is the correct behavior — the merge was valid at the time.

### Multiple pending-ship tasks have PRs that conflict with each other
PM processes pending-ship tasks sequentially within a cycle. The first PR merges successfully. The second PR will report `merge conflict` from `git_ops.py pr_merge()`. PM routes the second task back to `in-progress` with a "merge conflicts" comment. The dev agent rebases and resubmits. This is handled correctly by existing logic.

### Tasks without PRs (direct-to-main workflow)
When `Branch Workflow: no`, no PRs exist. Auto-merge silently skips ("otherwise no PR exists — silent no-op"). Delivery-fallback proceeds directly to delivery packaging. This is handled correctly.

### Stalled pending-ship tasks
Currently invisible. A task can sit at `pending-ship` indefinitely if no agent processes it. With the pipeline sentinel, PM would detect tasks at `pending-ship` for longer than a configurable threshold and take action (auto-merge if eligible, or flag for human attention).

### PR Flow off but Branch Workflow on
This is the current project config (`PR Flow: no`, `Branch Workflow: yes`). PRs exist but PM skips the PR monitoring step. Auto-merge still triggers (it "runs regardless of PR Flow setting") but only when PM actually reaches Step 6b — which it doesn't when QA is present. This is the primary failure case this task fixes.

## Integration Risks

### Interaction with TASK#1074 (auto-merge PRs)
TASK#1074 added auto-merge logic to pr-flow and delivery-fallback. The QA results show it failed verification (config.md section missing, composition not deployed). This task (#1228) depends on #1074 being complete — the auto-merge sub-skill content must be finalized before we can restructure where it runs in the loop.

### Interaction with QA's Step 5b
QA's PR monitoring (Step 5b) covers merged/closed status sync when PR Flow is on. If PM also runs PR monitoring, need to avoid duplicate transitions. Recommend: PM's pipeline sentinel handles conflict detection and auto-merge only; status sync is deduplicated by checking current status before transitioning.

## Upgrade & Migration

### New config values
- None required. Existing `Auto Merge`, `Branch Workflow`, and `PR Flow` configs suffice.
- Optional: `Stall Detection Threshold` (minutes) — but could default to `2 * Iteration Interval` to avoid a new config field.

### New files
- `references/sub-skills/pm-specific/pipeline-sentinel.md` — new sub-skill
- Or restructure existing sub-skills (see Recommendation)

### Template changes
- `references/roles/pm/CLAUDE.md` — restructure step ordering
- `references/roles/pm/includes.yml` — add new sub-skill if created

### Upgrade steps
- `compose.py deploy pm` recomposes PM's CLAUDE.md with the new step ordering
- No data migration needed
- No config migration needed (uses existing config fields)

### Graceful degradation
- If user doesn't upgrade: current behavior (pipeline steps skipped when QA present). No breakage, just the existing gap continues.
- If user partially upgrades (sub-skill updated but not recomposed): PM continues with old template. `compose.py deploy pm` must be run.

## Capability Gaps

No new capabilities are needed. All required operations (PR listing, merging, status transitions, git log for recompose) already exist in the scripts and sub-skills. The change is purely structural — moving existing logic to a different position in the loop.

## Stall Detection Design

### Data source
- Query GitHub Issues for tasks at `pending-ship` status: `python references/scripts/tracker.py list-tasks [ROLE] --status pending-ship`
- Check how long each task has been at `pending-ship` by reading the last Discussion comment that set the status. Parse the timestamp from the comment.

### Threshold
- Default: 2x Iteration Interval (60 minutes with 30-minute cycles)
- Could be configurable via config.md but likely not worth a new field initially

### Corrective actions (safe to automate)
- **Auto-merge eligible tasks**: attempt merge, report result
- **Non-mergeable tasks**: comment on the issue flagging the stall, route to human attention
- **Conflicting PRs**: route back to dev agent for rebase

### Storage
- No persistent storage needed. Stall detection is stateless — each cycle queries current pending-ship tasks and checks their timestamps from Discussion comments. This avoids needing a new state file.

## Open Questions

### Q1: Should the pipeline sentinel be a new sub-skill or a restructuring of existing sub-skills?
**Why**: A new sub-skill (`pipeline-sentinel.md`) is cleaner architecturally but duplicates some logic from pr-flow and delivery-fallback. Restructuring existing sub-skills avoids duplication but requires careful refactoring of the QA-skip gate.

### Q2: Should PR conflict detection run when PR Flow is off?
**Why**: Currently pr-flow monitoring is gated on `PR Flow: yes`. But conflict detection is useful regardless — if Branch Workflow is on, PRs exist and can conflict even if PR Flow (the full review workflow) is off. The auto-merge section already says "runs regardless of PR Flow setting." Conflict detection should probably follow the same pattern.

### Q3: Should the pipeline sentinel also run during planning phase suppression?
**Why**: Currently suppression only runs pull + health check. Pipeline monitoring could catch stalled tasks during long planning phases. But adding complexity to the suppression path risks bugs. Recommend: skip during suppression, accept the 30-minute gap.

### Q4: What is the interaction with DM when DM is present?
**Why**: When DM exists, `pending-ship -> shipped` is DM's transition. PM auto-merges the PR (in pr-flow) but does not ship. The pipeline sentinel must not attempt shipping when DM is present — only merge and conflict detection.

## Recommendation

**Feasible with caveats.** The fix is structurally straightforward but requires careful refactoring.

### Recommended approach: Extract and restructure

1. **Create `pipeline-sentinel.md`** as a new PM-specific sub-skill containing:
   - PR conflict detection (extracted from pr-flow, runs when Branch Workflow is on, regardless of PR Flow setting)
   - Auto-merge for pending-ship tasks (extracted from pr-flow and delivery-fallback)
   - Post-merge recompose (moved from Step 6e)
   - Delivery fallback (for DM-absent case, moved from Step 6d)
   - Stall detection for pending-ship tasks (new logic)

2. **Narrow the QA-skip gate** in `testing-and-verification.md`:
   - Change "Skip Steps 3-6 entirely" to "Skip Steps 3-6 (testing and verification only)"
   - Make it clear that pipeline management (Steps 6b-6e) is NOT included in the skip

3. **Restructure the PM template** (`references/roles/pm/CLAUDE.md`):
   - Steps 3-6: Testing & Verification (QA fallback) — still skipped when QA present
   - New Step 6.5 (or Step 6p): Pipeline Sentinel — always runs
   - Step 7+: unchanged

4. **Update `includes.yml`**: Add `pm-specific/pipeline-sentinel` after `pm-specific/testing-and-verification`

5. **Slim down existing sub-skills**: pr-flow and delivery-fallback become thinner (the pipeline portions extracted), retaining only the verification-coupled logic.

### Alternative approach: Renumber and re-gate

Instead of a new sub-skill, renumber Steps 6b/6d/6e to Step 7a/7b/7c (after the QA-skip block). This avoids code duplication but makes the numbering awkward and the template harder to read.

### Recommended: Option 1 (new sub-skill). Cleaner separation of concerns, easier to test, and the duplication is minimal since the logic is being moved, not copied.
