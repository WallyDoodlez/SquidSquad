# FEAT-SKILL-1074 Research — Auto-merge PRs after QA passes

## Summary

This task adds auto-merge capability so that when QA verifies a task with zero gaps and PM marks it pending-ship, PM automatically squash-merges the associated PR via `gh pr merge --squash`. This eliminates the human bottleneck on task PRs while keeping manual merge as the default for bug fix PRs.

The implementation touches three layers: (1) the PM template's delivery flow to add merge logic, (2) tracker.py's transition authority to let PM trigger `pending-ship → shipped` when DM is absent or for auto-merge specifically, and (3) a new config field and per-task label for opt-out. The change is architecturally straightforward — it slots into the existing Step 6d delivery fallback and Step 6b PR monitoring flows.

Risk is low. The main edge cases are merge conflicts (recoverable via rebase) and race conditions with human-initiated merges (detectable via PR state check). No breaking changes for existing installs — auto-merge defaults to off until enabled in config.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/pm-specific/delivery-fallback.md` — add auto-merge step before marking shipped
  - `references/sub-skills/pm-specific/pr-flow.md` — add auto-merge detection in PR monitoring
  - `references/scripts/tracker.py` — add PM to `pending-ship → shipped` authority (conditional on auto-merge context), or bypass via DM fallback
  - `references/scripts/git_ops.py` — add `pr-merge` command wrapping `gh pr merge --squash`
  - `references/sub-skills/pm-specific/task-intake.md` — add "manual merge" option to Phase 2 discussion
  - `.squidsquad/config.md` — new `Auto Merge` setting
- **Behavior changes**:
  - Tasks: PR auto-merges after QA pass + PM pending-ship (default)
  - Bugs: always manual merge (no change)
  - Per-task opt-out via `merge:manual` label
- **Dependencies**: `gh` CLI (already required), branch workflow enabled

## Side Effects

- **Risk 1**: PM attempts merge but PR has conflicts — Severity: M — Mitigation: Detect merge failure, route back to skill agent to rebase, QA re-verifies, PM retries. Add `merge-conflict` label to track.
- **Risk 2**: Human merges PR before PM auto-merge runs — Severity: L — Mitigation: Check PR state before attempting merge. If already merged, skip and proceed to shipped.
- **Risk 3**: tracker.py authority model — `pending-ship → shipped` is currently DM-only — Severity: M — Mitigation: Either (a) add PM to the authority set with a condition flag, or (b) have PM use the existing DM delivery fallback path which already handles shipping when DM is absent. Option (b) is simpler and already works.

## Edge Cases

- **Merge conflict**: `gh pr merge` fails → detect exit code, comment on issue, route to skill for rebase, re-verify
- **PR already merged by human**: Check PR state first. If merged, just update tracker status. No double-merge risk.
- **PR closed without merge**: Detect closed state, route back to in-progress with discussion note
- **Concurrent PRs**: Each task has its own branch/PR. No conflict between different task auto-merges.
- **Branch protection rules**: If repo has required reviews, `gh pr merge` will fail. Detect and fall back to manual. Note: SquidSquad repos typically don't have branch protection (single-dev projects).
- **`merge:manual` label added mid-flight**: Check label at merge time, not at task creation. If label present, skip auto-merge.
- **No PR exists (direct-to-main workflow)**: If branch workflow is off, no PR to merge. Auto-merge is a no-op — delivery proceeds normally.

## Integration Risks

- **Post-merge recompose (Step 6e)**: Already runs after detecting merged branches. Auto-merge just means PM triggers the merge instead of the human — recompose still fires on the next cycle. No change needed.
- **QA verification**: QA verifies before PM marks pending-ship. Auto-merge happens AFTER verification. No interaction.
- **DM delivery**: When DM is present, DM handles `pending-ship → shipped`. Auto-merge should happen BEFORE DM ships (merge the code, then DM does delivery packaging). When DM is absent, PM does both (merge + delivery fallback). Sequence: merge PR → delivery packaging → mark shipped.
- **PR Flow setting**: Currently `PR Flow: no`. Auto-merge is independent of PR Flow monitoring. PR Flow tracks human comments on PRs; auto-merge is about the final merge action. Both can coexist.

## Upgrade & Migration

- **New config values**: `Auto Merge: yes` (default `no` — opt-in for safety on existing installs)
- **New labels**: `merge:manual` — per-task opt-out
- **New files**: none
- **Template changes**: delivery-fallback.md, pr-flow.md, task-intake.md updated
- **Upgrade steps**: `squidsquad-upgrade` adds `Auto Merge` to config.md, creates `merge:manual` label on repo
- **Graceful degradation**: If not upgraded, no auto-merge — human continues merging manually. Zero breakage.

## Capability Gaps

- `capability_check.py` — no manifest.yaml found for skill role. Not blocking — this task primarily changes PM templates and scripts.

## Open Questions

- **Q1**: Should auto-merge default to `yes` or `no` for NEW installs? — **Why**: If `yes`, new users get auto-merge immediately which may surprise them. If `no`, they must opt in. Recommend `yes` for new installs (the whole point is reducing friction), `no` for upgrades (don't change existing behavior).
- **Q2**: Should PM also handle `pending-ship → shipped` transition directly, or continue routing through DM? — **Why**: Currently only DM can do this transition. If PM auto-merges and DM is present, who ships? Recommend: PM merges the PR, DM still handles delivery packaging and the shipped transition. If DM is absent, PM does both (existing fallback). No tracker.py authority change needed.
- **Q3**: What happens if auto-merge is enabled but branch workflow is off? — **Why**: No branches = no PRs = nothing to merge. Recommend: auto-merge is silently a no-op when branch workflow is off. No error, no warning.
- **Q4**: Should the `merge:manual` override be set during Phase 2 discussion only, or should the human be able to add it at any time? — **Why**: Adding it later (after task is in-progress) should also work. Recommend: check label at merge time, not at creation time. Human can add/remove the label whenever.

## Vault Candidates

- **Pattern**: "PR auto-merge gated behind QA verification" — reusable pattern for any CI/CD pipeline where automated quality gates replace human review bottlenecks

## Recommendation

**Straightforward**. Slots cleanly into existing delivery flow. Main implementation work is in the PM delivery-fallback sub-skill and a small git_ops.py addition. No architectural changes needed.
