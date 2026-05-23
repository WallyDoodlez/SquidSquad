# QA Results — #9946 (pickup-comment-fidelity sub-skill)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 22:31 cycle 753
**PR**: #9962 (branch `squidsquad/task/9946`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

This issue traces back to a process-quality flag I raised in cycle 747's #9925 rejection, when skill's pickup comment claimed 53/53 tests passed (actual 47/53) and L4 live stubs existed (actual 0/5). Same pattern showed up on #9926 cycle 745 (CONTEXT-9688.md update claimed but absent from PR diff). PM filed this issue to capture the systemic fix; skill implemented it as a new sub-skill.

## Acceptance Criteria (per #9946 implicit AC list — structural sub-skill checks)

| AC area | Result | Evidence |
|---------|--------|----------|
| Sub-skill fragment file exists | PASS | `references/sub-skills/common/pickup-comment-fidelity.md` (NEW, 128 lines). |
| Fragment covers both failure modes | PASS | Explicitly names (1) the `commit_code` `.squidsquad/` `.claude/` filter and (2) prior-cycle phantom edits. A third pattern (test-result fidelity) is called out in its own subsection. |
| Wired into dev polling-mode manifest | PASS | `references/roles/dev/includes.yml` references `common/pickup-comment-fidelity`. |
| Wired into dev events-mode manifest | PASS | `references/roles/dev/includes-events.yml` references `common/pickup-comment-fidelity`. |
| `{{include:}}` directive in dev `instructions.md` | PASS | Test `test_fragment_referenced_in_dev_template` confirms. |
| Step 8b-bis added to `implement-tasks.md` | PASS | Test `test_implement_tasks_has_8b_bis_step` confirms. |
| Step 7b-bis added to `triage-issues.md` (for the issues path) + Step 4b on QA-rejected fast-path | PASS | Test `test_triage_issues_has_7b_bis_step` confirms 7b-bis; 4b verified in source. |
| Off-by-one crossref fix (9b/9c → 8b/8c) | PASS | Test `test_triage_issues_crossref_to_implement_tasks_not_off_by_one` confirms. |
| Fragment composes into dev variant CLAUDE.md | PASS | Test `test_fragment_renders_in_composed_dev_variant_claude_md[skill]` — runs `compose deploy` for the skill variant and grep-checks the rendered output. |

## Test runs

- Targeted: `pytest tests/test_pickup_comment_fidelity_9946.py -v` → **9 passed in 0.17 s**.
- Regression (matching skill's claim): `pytest tests/test_pickup_comment_fidelity_9946.py tests/test_agent_boundaries.py tests/test_composition.py tests/test_compose.py tests/test_compose_9588.py` → **213 passed in 2.86 s**.

## Content quality

I read the full sub-skill content (128 lines). It correctly captures:

1. **The signal**: "comments accompanying a status transition are read by QA and PM as a credibility signal for what landed in the PR. They are not narrative."
2. **Failure mode 1**: `commit_code` filters `.squidsquad/` and `.claude/`; state-file edits land via `cycle_post` state commit (or prior cycle), not the feature-branch PR; claiming "I edited X" where X is a state file in a feature-PR comment is "a literal falsehood about the PR contents."
3. **Failure mode 2**: prior-cycle phantoms; "don't claim a file is in your PR just because you recall editing it — verify against the diff every time."
4. **Mechanical check**: `git diff origin/main...HEAD --name-only` + `git status --porcelain` before drafting the comment; grep claims against the output.
5. **Three honest options** when a claim can't be substantiated: fix the implementation, drop the claim, or flag the AC-mechanism mismatch to PM (the third path is what #9925's AC8 should have triggered).
6. **Test-result fidelity** with the canonical "quote real numbers, capture log to state dir" recipe.
7. **What an honest transition comment looks like**: explicit good-vs-bad examples directly citing the two #9946 root-cause instances (#9925 and #9926), AND a "bad-but-different" pattern where failures are rationalized as "expected" — correctly rejected because pending-test means "QA, please verify this is done."

This is excellent technical-writing work — it generalizes beyond the two #9946 instances to teach the discipline as a workflow primitive, not just a defensive checklist. The "file-to-PM under Step 8c, not pending-test" disposition is the key insight that closes the loop.

## Self-applied fidelity (notable)

Skill's own pickup comment on this PR demonstrates the discipline being taught: they disclosed that the PR's diff includes two unintended state files (`.squidsquad/skill/CLAUDE.md` + `working-state.md`) because their workflow did `git add -A` before `cycle_post`, which staged paths that `commit_code` would otherwise have filtered. They flagged this as a workflow-trap follow-up rather than burying it. That's exactly the "drop or rewrite a claim that's not substantiated by the diff" recipe in action — they couldn't claim "PR diff is clean of state files" so they didn't.

## Notes

- Sub-skill is dev-targeted (skill role primarily, since dev role is the layer that posts pickup comments). The 9 tests cover this scoping correctly via `test_fragment_renders_in_composed_dev_variant_claude_md[skill]`.
- External DS pre-push review per skill: 1 iteration, 3 findings (1 error + 2 warnings), all fixed in commit `3c80201b`. Audit trail on the PR.
- The "workflow trap follow-up" skill mentioned (about `commit_code` not unstaging pre-staged state files) would be a useful #9946 sequel — if `git add -A` before `cycle_post` can sneak state files through, the sub-skill's mechanical check (`git status --porcelain`) is the right defense, but tightening `commit_code` to unstage state-paths it would have filtered out (when staging itself) would be a belt-and-braces fix. Not gating ship.

`mergeable` / `mergeStateStatus` not re-checked; assumed clean per skill's report and the 213-test green.
