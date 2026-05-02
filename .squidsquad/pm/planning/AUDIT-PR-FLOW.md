Now I have complete data for the audit. Let me compile the final document.

```markdown
# AUDIT-PR-FLOW Research — End-to-End PR Lifecycle Gap Analysis

## Summary

Audited the complete PR lifecycle across 7 files (~2,400 lines of executable code, ~2,100 lines of agent instruction templates). The PR workflow spans five agents (dev/skill, QA, PM, DM) and three mechanical scripts (git_ops.py, tracker.py, cycle_post.py). The architecture has three layers: agent instructions (what agents are told to do), mechanical scripts (what actually runs deterministically), and the pipeline sentinel (what PM monitors). Gaps arise when these layers disagree or when responsibilities are fragmented across agents without clear ownership.

**Primary finding**: The draft→ready auto-conversion in `tracker.py` (lines 970–972) and the QA verification sub-skill's explicit `gh pr ready` calls create redundant, confusing double-conversion. More critically, `_convert_draft_pr_to_ready()` at `tracker.py:752–755` contains a **dead code path** — it finds draft PRs on Forgejo backends but does nothing (`pass`) instead of calling `adapter.pr_ready()`, meaning draft PRs are **never converted to ready on non-GitHub forges**. The PM pipeline sentinel (#1228) was designed to fix QA-skip gaps but shipped without auto-merge capability — it detects conflicts and syncs status but never merges. DM's delivery-packaging has a PR merge gate, but it only triggers when branch-workflow is on AND it finds an open non-draft PR, creating a narrow window where PRs could be shipped without merge.

**Recommendation**: Feasible with caveats. Seven distinct gaps found; four are code bugs (Forgejo dead path, double conversion, missing `pr-ready` in git_ops.py, no auto-merge in sentinel) and three are process gaps (ordering dependency, vague push-back, reactive orphan detection). Fix the code bugs first, then tighten the process.

## Vault Context
- **BRIEFING.md priorities**: #4084 Draft PR workflow for dev agents (shipped) — this is the feature being audited. #1228 Pipeline sentinel (shipped) — structurally relevant; it was the fix for the QA-skip gap but didn't include auto-merge.
- **Related decisions**: [[decision-branch-per-feature-workflow]] — all PR logic is gated on `branch-workflow: yes`; code on branches, state on main
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — tracker.py auto-convert is the mechanical layer; agent instructions are prose that may not match
- **Human preferences**: "Never ship with failed TCs", "Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap" — directly applicable to orphaned PRs and stuck drafts
- **Related learnings**: [[learning-qa-branch-merge-workaround]] — QA clone isolation causes branch discovery failures; this means QA may verify on wrong branch if task-begin fails silently

## Impact Analysis
- **Files touched**:
  - `references/scripts/tracker.py` (line 752–755: dead `pass` in `_convert_draft_pr_to_ready`)
  - `references/scripts/git_ops.py` (missing `pr-ready` subcommand)
  - `references/sub-skills/roles/qa/verification.md` (double draft→ready conversion, QA Step 4/5)
  - `references/sub-skills/roles/pm/pipeline-sentinel.md` (no auto-merge logic)
  - `references/sub-skills/roles/dm/delivery-packaging.md` (PR merge gate only on branch-workflow)
  - `references/scripts/forge_adapter.py` (has `pr_ready()` but tracker.py doesn't call it)
  - `tests/test_tracker_authority.py` (DraftPRConversion tests don't cover Forgejo path)
- **Behavior changes**:
  - Forgejo draft PRs would actually convert to ready (currently dead)
  - `git_ops.py` would get a `pr-ready` subcommand for agent use
  - PM pipeline sentinel would auto-merge eligible PRs (currently only detects)
  - QA would stop double-converting (tracker.py already handles it)
  - DM's merge gate would be clarified or removed (QA already merges)
- **Dependencies**: `forge_adapter.py` (pr_ready exists, lines 260–261 and 458–462), `gh` CLI (pr ready, pr merge), `tracker.py` transition authority

## Side Effects
- **Risk 1**: Fixing the Forgejo dead path could cause unexpected PR state changes on existing installs — Severity: M — Mitigation: The fix is idempotent (ready→ready is a no-op). Only draft PRs that accumulated while the path was dead would suddenly become ready. This is actually the desired behavior.
- **Risk 2**: Adding auto-merge to pipeline sentinel creates double-merge risk with QA's existing auto-merge — Severity: M — Mitigation: QA's auto-merge runs during verification (pending-test→pending-ship). Pipeline sentinel should only auto-merge tasks already at pending-ship that QA didn't merge (e.g., human-merged PRs detected by status sync). Gate on `status:pending-ship` AND `open PR exists`.
- **Risk 3**: Adding `pr-ready` to git_ops.py may encourage agents to use it at wrong times — Severity: L — Mitigation: The dev instructions already say "A PR must NEVER be in ready state while the agent is actively pushing commits to it." The command docstring should reinforce this.
- **Risk 4**: Removing QA's explicit `gh pr ready` could break the "PR Flow no" path where QA merges directly — Severity: L — Mitigation: QA's merge path already calls `gh pr ready` before `pr-merge`; tracker.py auto-convert already handled it. The explicit call is redundant but harmless. Keep it as belt-and-suspenders.

## Edge Cases
- **Dev transitions to pending-test before creating PR**: tracker.py `_convert_draft_pr_to_ready` searches for PRs matching the issue number. If no PR exists yet, it's a silent no-op. When the PR is later created, it stays draft forever unless QA explicitly converts it. Handle: QA verification Step 4 already includes `gh pr ready` as a fallback. Pipeline sentinel could detect "pending-test with draft PR for >N minutes" as a stall condition.
- **QA task-begin fails (branch not on origin)**: QA instructions say "push back to the submitting agent" but don't specify mechanical action. Currently QA likely transitions back to in-progress. If QA verifies on main instead (learning-qa-branch-merge-workaround), the verification may pass but the PR branch was never tested. Handle: task-begin failure should ALWAYS transition back to in-progress with explicit comment; never fall through to main.
- **DM finds a draft PR at pending-ship**: DM delivery-packaging line 45 says "STOP — this PR has not been verified by QA." But the item is at pending-ship, meaning QA DID verify. The draft state means tracker.py's auto-convert failed (possibly the Forgejo bug) or QA skipped the explicit `gh pr ready`. DM should convert to ready and merge, not stop. Handle: DM should call `gh pr ready` then merge, rather than stopping.
- **Auto-merge ON but PR Flow OFF**: Current QA verification merges PRs even when PR Flow is off (verification.md lines 586–625). But the config check for auto-merge only happens in the "PR Flow yes" branch (line 564). So when PR Flow is off, QA always merges regardless of auto-merge setting. This is intentional (the "merge PR" section at line 586 runs unconditionally) but the config flag `auto-merge` becomes meaningless when PR Flow is off.
- **Multiple agents transition same item simultaneously**: tracker.py transition is not atomic across the GitHub API — two agents could both transition the same item. The current authority table (tracker.py lines 190–200) defines who can make which transitions, but there's no locking. Handle: Low probability in practice (agents run on different cycles), but pipeline sentinel's status sync (section 3) could race with QA's verify-and-transition.

## Integration Risks
- **Pipeline sentinel (PM) + QA verification race**: PM sentinel runs every cycle and syncs PR status (merged → pending-ship). QA also runs every cycle and transitions verified items to pending-ship. If QA verifies item #42 and transitions to pending-ship, then PM sentinel detects the PR was already merged and also tries to transition to pending-ship, the second transition is rejected by tracker.py authority (QA can transition pending-test→pending-ship; PM can transition pending-ship→in-progress but NOT pending-test→pending-ship). This is safe but noisy. Handle: Sentinel should check current status before transitioning.
- **DM delivery + QA auto-merge overlap**: QA auto-merges during verification (pending-test→pending-ship). DM tries to merge again during delivery (pending-ship→shipped). git_ops.py `pr_merge` handles "already merged" gracefully (lines 280–282: returns success). Safe but wasteful. Handle: DM should check PR state before attempting merge — if already merged, skip.
- **cycle_post.py PR creation (skill only) vs manual PR creation (all devs)**: `cycle_post.py` lines 298–317 mechanically creates PRs only for the `skill` role. Other dev roles (fullstack, web, ios, android) must create PRs manually during their creative phase. If a non-skill dev forgets to create a PR but transitions to pending-test, the tracker auto-convert has nothing to convert, and QA has no branch to check out. Handle: Pipeline sentinel should detect "pending-test without open PR" as a stall condition.

## Upgrade & Migration
- **New config values**: None required. Existing `auto-merge`, `branch-workflow`, and `pr-flow` suffice.
- **New files**: Potentially a `pr-ready` entry in `git_ops.py` main dispatch (line 591+). No new standalone files.
- **Template changes**: 
  - `references/sub-skills/roles/qa/verification.md` — clarify that draft→ready is automatic via tracker.py; keep explicit call as belt-and-suspenders
  - `references/sub-skills/roles/pm/pipeline-sentinel.md` — add auto-merge section for pending-ship items with open PRs
  - `references/sub-skills/roles/dm/delivery-packaging.md` — change "STOP if draft" to "convert to ready and merge if draft"
  - `references/sub-skills/common/git-commit.md` — add `git_ops.py pr-ready` as an available command
- **Upgrade steps**: 
  1. Fix tracker.py line 752–755 (Forgejo dead path)
  2. Add `pr-ready` subcommand to git_ops.py
  3. Add auto-merge to pipeline-sentinel.md
  4. `compose.py deploy-all` to propagate template changes
  5. No data migration needed
- **Graceful degradation**: If user doesn't upgrade, Forgejo draft PRs remain stuck as draft, pipeline sentinel continues without auto-merge, and DM may stop on draft PRs at pending-ship. No crash or data loss — just gaps persist.

## Open Questions
- **Q1**: Should pipeline sentinel auto-merge, or should that stay in QA's verification? — **Why**: Moving auto-merge to sentinel means PM merges PRs independently of QA verification. This could create a situation where PM merges a PR that QA was about to reject. But the status gate (pending-ship) should prevent this — QA transitions to pending-ship only after verification passes.
- **Q2**: Should `pr-ready` in git_ops.py use the forge adapter's `pr_ready()` or just wrap `gh pr ready`? — **Why**: git_ops.py `pr-create` and `pr-merge` both have forge adapter paths (lines 209–223 and 247–268). `pr-ready` should follow the same pattern for consistency. The forge adapter already has the method (lines 260–261 for GitHub, 458–462 for Forgejo).
- **Q3**: Should DM's PR merge gate be removed entirely since QA already handles merging? — **Why**: DM merging PRs during delivery creates a second merge path that could conflict with QA's merge. If QA's auto-merge is reliable, DM's gate is unnecessary. But if QA's auto-merge fails silently (e.g., merge conflict that QA routes back to in-progress but the item somehow reaches pending-ship), DM's gate catches it. This is a "belt and suspenders" question.

## Recommendation

**Feasible with caveats.** Seven gaps found; four are code bugs that should be fixed, three are process refinements. The order of operations:

1. **Fix `tracker.py:752–755`** — replace `pass` with `adapter.pr_ready(pr["number"])` (critical, dead code on Forgejo)
2. **Add `pr-ready` to `git_ops.py`** — follow existing forge adapter pattern from `pr-create`/`pr-merge`
3. **Add auto-merge to pipeline sentinel** — gate on `status:pending-ship` + open PR + `auto-merge: yes` + no `review:human-required` label
4. **Clarify DM's PR merge gate** — convert draft to ready and merge instead of stopping; or remove if QA merge is reliable
5. **Add stall detection for "pending-test with no open PR"** — catches the ordering gap where dev transitions before creating PR
6. **Add test coverage** for Forgejo `_convert_draft_pr_to_ready` path (currently untested)

## Vault Candidates
- **Type**: learning — Forgejo adapter `pr_ready()` exists but tracker.py dead path never calls it — **Why**: Classic "adapter method exists but integration code doesn't use it" pattern. Worth recording because the same pattern could exist in other adapter methods. Check all `ForgeAdapter` abstract methods against their callers.
- **Type**: decision — Auto-merge responsibility is fragmented across 3 agents (QA, PM, DM) — **Why**: Architectural smell. A single mechanical script should own PR merging, not spread across agent instructions. Consider consolidating into `cycle_post.py` or a new `pr_ops.py`.
- **Type**: pattern — Double-conversion (agent instructions + mechanical scripts both doing the same thing) is a recurring SquidSquad pattern — **Why**: tracker.py auto-converts draft→ready AND QA instructions tell QA to convert draft→ready. Same pattern as git-commit where agents commit manually AND cycle_post.py commits mechanically. The pattern is intentional (belt-and-suspenders) but should be documented as such rather than accidental.
- **Type**: learning — Pipeline sentinel (#1228) shipped with conflict detection and status sync but without auto-merge, despite the research doc explicitly identifying auto-merge as a pipeline-critical function — **Why**: The feature shipped incomplete because the research correctly identified the gap but the implementation (pipeline-sentinel.md) didn't include the auto-merge section. Gap between research and implementation is worth tracking as a process risk.
- **Type**: decision — `pr-flow` and `auto-merge` config flags interact unintuitively: when PR Flow is off, QA merges PRs regardless of auto-merge setting — **Why**: The auto-merge config flag only gates behavior inside the "PR Flow yes" branch (verification.md line 564). When PR Flow is off, the "merge PR" section (line 586) runs unconditionally. This means `auto-merge: no` has no effect when `pr-flow: no`. Either the flags should be independent or the documentation should clarify the interaction.
```