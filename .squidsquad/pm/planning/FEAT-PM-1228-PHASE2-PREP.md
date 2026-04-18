# FEAT-PM-1228 Phase 2 Prep — PM Pipeline Sentinel

## Optimal Question Order

Questions should be addressed in this order based on dependencies:

1. **Q1** (architecture) — All other questions depend on whether this is a new sub-skill or a restructuring. Must be decided first.
2. **Q2** (behavior) — Defines what the sentinel actually does. Depends on Q1 (determines where the logic lives).
3. **Q4** (behavior/compatibility) — Defines boundaries when DM is present. Depends on Q1 (determines scope of new sub-skill).
4. **Q3** (scope) — Whether to run during planning suppression. Least dependent, least controversial, can be decided last.

---

## Q1: Should the pipeline sentinel be a new sub-skill or a restructuring of existing sub-skills?

**Category**: Architecture / Scope

### Option A: New sub-skill (`pipeline-sentinel.md`) -- RECOMMENDED

Extract pipeline logic into a dedicated `pipeline-sentinel.md` sub-skill. Existing sub-skills (pr-flow, delivery-fallback, post-merge-recompose) are slimmed down; pipeline-sentinel consolidates the always-run portions.

| Pros | Cons |
|------|------|
| Clean separation of concerns: "verification" vs "pipeline management" are clearly distinct | Creates a new file that partially overlaps with existing sub-skills |
| Easy to test in isolation — one sub-skill, one responsibility | Developers must understand the split (which logic lives where) |
| QA-skip gate stays simple ("skip verification") — no complex re-gating | Slight increase in total template size from the new include |
| Matches the research recommendation | Migration: must slim existing sub-skills to avoid duplication |

### Option B: Renumber steps (move 6b/6d/6e outside the skip block)

Keep all logic in existing sub-skills. Renumber Steps 6b/6d/6e to 7a/7b/7c so they fall after the QA-skip block ends.

| Pros | Cons |
|------|------|
| No new files — minimal structural change | Awkward numbering (7a/7b/7c inserted before current Step 7) |
| No logic duplication at all | Template becomes harder to read — pipeline steps scattered |
| Smaller diff | QA-skip gate wording must be very precise ("skip Steps 3-6 but not 6b/6d/6e" is confusing) |
| | Doesn't solve the conceptual problem — verification and pipeline are still interleaved |

### Option C: Re-gate the QA-skip to be more granular

Keep the current structure but modify the QA-skip gate to enumerate exactly which sub-steps are skipped (3, 4, 5, 6, 6c) and which are not (6b, 6d, 6e).

| Pros | Cons |
|------|------|
| No new files, no renumbering | Fragile — every future step addition must update the gate enumeration |
| Minimal template change | Easy to accidentally skip a pipeline step when adding new verification sub-steps |
| Preserves current numbering | The gate becomes a maintenance liability |
| | Doesn't address the conceptual coupling between verification and pipeline |

**Recommendation**: Option A. The new sub-skill creates a clear architectural boundary. The "duplication" is actually a move, not a copy — existing sub-skills get slimmer. This is the cleanest long-term solution and matches the research findings.

---

## Q2: Should PR conflict detection run when PR Flow is off?

**Category**: Behavior / Compatibility

### Option A: Yes, run conflict detection whenever Branch Workflow is on -- RECOMMENDED

Gate conflict detection on `Branch Workflow: yes` (PRs exist), not on `PR Flow: yes` (the full review workflow). This matches the auto-merge behavior which already "runs regardless of PR Flow setting."

| Pros | Cons |
|------|------|
| Catches merge conflicts in the current project config (`PR Flow: no`, `Branch Workflow: yes`) | Slightly more work per cycle (one `gh pr list` call) |
| Consistent with auto-merge gating (both ignore PR Flow) | Users who intentionally disabled PR Flow may not expect PM to touch PRs at all |
| Fixes the primary failure case identified in the research | Minor: may surface conflicts the team was intentionally ignoring |
| Simple mental model: "if PRs exist, PM watches them" | |

### Option B: Only run conflict detection when PR Flow is on

Keep the current gating — conflict detection requires `PR Flow: yes`.

| Pros | Cons |
|------|------|
| Respects the user's explicit decision to disable PR Flow | Leaves the primary bug unfixed for `PR Flow: no` configs |
| No behavior change for existing installs | Conflicts go undetected — tasks stall silently |
| | Contradicts auto-merge behavior (which already ignores PR Flow) |
| | Defeats the purpose of this task |

### Option C: New config flag (`PR Conflict Detection: yes/no`)

Add a dedicated config field for conflict detection, independent of both PR Flow and Branch Workflow.

| Pros | Cons |
|------|------|
| Maximum user control | Yet another config field to maintain |
| Users can enable conflict detection without enabling full PR Flow | Adds complexity for a niche use case |
| | Default must be chosen carefully — `yes` changes behavior, `no` keeps the bug |
| | Over-engineering for what is essentially a bug fix |

**Recommendation**: Option A. Conflict detection is a safety net, not a workflow feature. If PRs exist (`Branch Workflow: yes`), conflicts should be detected regardless of whether the full PR review flow is enabled. This aligns with auto-merge's existing gating and fixes the core bug.

---

## Q3: Should the pipeline sentinel also run during planning phase suppression?

**Category**: Scope / Performance

### Option A: Skip during suppression (accept the gap) -- RECOMMENDED

Planning suppression only runs pull + health check. Pipeline sentinel is skipped, same as all other steps. Accept that stalled tasks won't be detected during the ~30-minute planning window.

| Pros | Cons |
|------|------|
| Keeps suppression simple — fewer moving parts during planning | 30-minute blind spot for stalled tasks |
| No risk of pipeline actions interfering with planning focus | A merge conflict that appears during planning won't be caught until planning ends |
| Matches existing suppression behavior (only pull + health) | |
| Research explicitly recommends this approach | |

### Option B: Run pipeline sentinel during suppression

Add pipeline-sentinel to the suppression's allowed steps (alongside pull + health check).

| Pros | Cons |
|------|------|
| No blind spot — conflicts and stalls detected continuously | Adds complexity to the suppression path |
| Could auto-merge a PR that unblocks another agent during planning | Risk of side effects during planning (auto-merge triggers recompose, which changes templates mid-planning) |
| | If recompose runs during planning, it could invalidate the planning artifacts being created |
| | More things that can go wrong during a sensitive phase |

### Option C: Run a lightweight subset during suppression (conflict detection only, no auto-merge)

Allow conflict detection during suppression but not auto-merge or delivery. Read-only monitoring.

| Pros | Cons |
|------|------|
| Detects problems without causing side effects | Partial solution — adds complexity for limited benefit |
| No risk of template changes during planning | Must clearly separate "detection" from "action" in the sub-skill |
| Reasonable middle ground | Over-engineering for a 30-minute window |
| | If a conflict is detected but not acted on, it just waits — same as Option A |

**Recommendation**: Option A. The 30-minute gap is acceptable. Planning phases are short, and any stalled task or conflict will be caught on the very next normal cycle. Adding pipeline logic to suppression risks template changes mid-planning, which could invalidate the artifacts being created. Keep it simple.

---

## Q4: What is the interaction with DM when DM is present?

**Category**: Behavior / Compatibility

### Option A: PM merges PR, DM handles delivery (clear boundary) -- RECOMMENDED

PM's pipeline sentinel handles auto-merge and conflict detection. DM handles `pending-ship -> shipped` transition and all delivery packaging (docs, changelog, version bumps). PM never attempts shipping when DM is present.

| Pros | Cons |
|------|------|
| Clear ownership: PM = merge + monitor, DM = ship + deliver | Requires DM to check for already-merged PRs (PM may have merged before DM picks up) |
| Matches the existing pr-flow design intent ("auto-merge for pending-ship tasks when DM is present") | Two agents touching the same PR lifecycle (PM merges, DM ships) |
| DM doesn't need merge logic — it just does delivery | If PM merge fails, DM may not know to wait |
| No risk of PM doing delivery work that conflicts with DM's output | |

### Option B: DM handles both merge and delivery when present

When DM is present, pipeline sentinel skips auto-merge entirely. DM merges and ships as a single atomic operation.

| Pros | Cons |
|------|------|
| Single agent owns the full ship path — simpler mental model | DM must duplicate merge logic (conflict detection, error handling) |
| No coordination needed between PM and DM for merging | Conflict detection only happens when DM picks up the task — could be delayed |
| Atomic merge+ship reduces risk of partial state | DM may not run as frequently as PM — stalls go undetected longer |
| | Contradicts the existing pr-flow design which already has PM auto-merging when DM is present |

### Option C: PM handles everything, DM only does version bumps

Expand PM's pipeline sentinel to include delivery packaging. DM is reduced to version bump and release management only.

| Pros | Cons |
|------|------|
| PM already has all the context from verification | Violates the DM role's purpose (delivery management) |
| Fewer handoffs | PM becomes overloaded — coordination + verification + delivery |
| | DM becomes nearly useless — just a version bump bot |
| | Breaks the role separation that SquidSquad is designed around |

**Recommendation**: Option A. This preserves the existing role boundaries and matches the current pr-flow design intent. PM handles the mechanical parts (merge, conflict detection, monitoring) while DM handles the judgment parts (delivery packaging, docs, changelog, version bumps). The boundary is clean: PM ensures the code is merged and ready; DM ensures the delivery is complete and correct.
