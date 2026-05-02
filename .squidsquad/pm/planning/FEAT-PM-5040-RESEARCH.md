Now I have all the information. Let me compile the final research document.

```markdown
# FEAT-PM-5040 Research — Unified Branch Model

## Summary
This research covers changing the hardcoded branch pattern `squidsquad/<role>/<number>` (constructed in `git_ops.py task_begin` line 508) to a configurable `squidsquad/task/<number>` via L4 project instruction override. The branch pattern appears in **4 construction sites** (Python code) and **21+ parsing/search sites** across Python scripts, agent instruction templates, sub-skill templates, project instructions, and tests. The change is straightforward mechanically but has a wide blast radius across templates and tests. The primary risk is stale branch references in agent creative-phase actions (where agents manually construct branch names from instructions rather than calling deterministic scripts) and in already-open PRs/branches during migration.

**Recommendation**: Feasible with caveats. Centralize branch construction into a single factory function in `git_ops.py` that reads a new config field `branch-pattern` (defaulting to `squidsquad/{role}/{number}` for backward compat), then provide per-project override via `.squidsquad/project/` L4 instructions or a `config.md` field. Branch parsing should become pattern-aware using the configured delimiter rather than hardcoding position 2 as the issue number.

## Vault Context
- **BRIEFING.md priorities**: #4709 EPIC Harness Phase 2 (planned, high) — may interact since harness controls agent lifecycle including branch setup. None directly blocking.
- **Related decisions**: [[decision-branch-per-feature-workflow]] — The foundational decision that established `squidsquad/<type>-<role>-<issue>` (later simplified to `squidsquad/<role>/<number>`). This is the decision we're amending. The dual-lane approach (code on branches, state on main) is unchanged — only the branch naming convention changes.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — Branch name construction should stay in scripts, not in agent prose instructions. The current split (hardcoded in `git_ops.py` but also repeated verbatim in agent instructions) violates this pattern. This change is an opportunity to fix that.
- **Human preferences**: Prefers direct/mechanical checks over indirect state files. Prefers working code over documentation. Primary platform: Windows 11. Branch naming change should be a config flag, not a documentation change.
- **Related learnings**: [[learning-qa-branch-merge-workaround]] — QA branch discovery failures (#3361). Any branch pattern change must ensure QA can still find branches across clones. The new pattern is actually friendlier to QA since `squidsquad/task/*` is a single glob.

## Impact Analysis
- **Files touched**:
  - **Scripts (7)**: `references/scripts/git_ops.py` (construction + parsing), `references/scripts/cycle_pre.py` (construction ×2 + search), `references/scripts/cycle_post.py` (indirect — passes branch from cycle-output), `references/scripts/tracker.py` (parsing ×5), `references/scripts/config.py` (new field)
  - **Templates/instructions (7)**: `references/agent-instructions.md` (4 references), `references/sub-skills/roles/dev/implement-tasks.md`, `references/sub-skills/roles/dev/triage-issues.md`, `references/sub-skills/roles/dm/delivery-packaging.md`, `references/sub-skills/roles/pm/task-intake.md`, `references/sub-skills/roles/qa/verification.md`
  - **Live project instructions (1)**: `.squidsquad/project/dev-instructions.md` line 15
  - **Tests (5)**: `tests/test_git_ops.py`, `tests/test_cycle_post.py`, `tests/test_cycle_pre.py`, `tests/test_feat_3296_task_boundary.py`, `tests/test_feat_1074_auto_merge.py`
- **Behavior changes**:
  1. `task-begin <role> <number>` currently derives `squidsquad/<role>/<number>` — must become config-driven
  2. `commit-code <role> <branch> <msg>` — agents pass the branch explicitly; the change only affects how agents *construct* the branch argument before calling commit-code
  3. `pr_create` — no branch construction internally; agents pass branch via current checkout
  4. `cycle_post.py` — reads `code_commit.branch` from cycle-output.json (agent-constructed); does not construct branch names itself
  5. QA branch resolution (`cycle_pre.py` lines 609/632) — constructs `squidsquad/{query_role}/{num}` directly
  6. PR/branch discovery (`tracker.py`, `verification.md`) — uses `squidsquad/*/{number}` wildcard, which is role-agnostic and should continue working with `squidsquad/task/{number}`
- **Dependencies**: `config.py` `get_field`/`set_field` for the new `branch-pattern` field. L4 project instruction override via `.squidsquad/project/` files (compose.py already loads these). No new package dependencies.

## Side Effects
- **Risk 1**: Agents manually constructing branch names from instructions (rather than calling `task-begin`) will use the old pattern until templates are recomposed. Severity: **M** — Mitigation: All branch name construction must go through `git_ops.py`; templates should reference `task-begin`/`task-end` only, not the raw pattern. The `agent-instructions.md` lines 699, 703, 760, 773, 775, 793 all embed the raw pattern and need updating.
- **Risk 2**: Parsing code that assumes `parts[2]` is the issue number (e.g., `git_ops.py` line 304 `parts[2].isdigit()`, `tracker.py` line 712 `parts[2] == str(number)`) breaks if the pattern changes from 3 segments to 3 segments with different semantics. Severity: **H** — Mitigation: Make parsing pattern-aware: extract the issue number by looking for a numeric segment at a configurable position, or use a regex `squidsquad/\w+/(\d+)`.
- **Risk 3**: Already-open PRs and branches using the old `squidsquad/<role>/<number>` pattern will not match new searches. Severity: **M** — Mitigation: Both old and new patterns must be recognized during a migration window. `pr-merge` line 304 already checks `parts[0] == "squidsquad"` and `parts[2].isdigit()` — this would still match if we changed the middle segment. The PR search patterns (`squidsquad/*/NUMBER`) are already role-agnostic and will match both old and new.
- **Risk 4**: The `commit-code` function takes an explicit branch argument — if an agent constructs the branch using old instructions while `task-begin` uses the new pattern, the branch created by `task-begin` and the branch committed to by `commit-code` could differ. Severity: **H** — Mitigation: `task-begin` should export the branch name it created (e.g., write to stdout or a state file). Cycle-output's `code_commit.branch` should be populated by the agent reading the branch name from `task-begin` output, not from template instructions.

## Edge Cases
- **Multi-role branches**: Currently, each role gets its own branch for the same issue number (`squidsquad/skill/100` vs `squidsquad/qa/100`). With `squidsquad/task/<number>`, all roles share one branch. This means `task-begin` for QA on issue #100 would checkout the same branch that skill created. This is the *intended behavior* (unified branch) but requires that agents don't step on each other's commits. The `commit-code` function already isolates code from state, so this is safe — but QA should not commit code to the branch during verification, only read it.
- **Branch already exists**: `task_begin` (line 529) creates the branch if missing — with shared branches, a second agent calling `task-begin` would find the existing branch and check it out, which is correct.
- **Branch deletion after merge**: `pr-merge` deletes branches (`--delete-branch`). With shared branches, deletion after merge is correct — the branch served its purpose.
- **Cross-clone branch discovery**: QA's clone must find the branch. With `squidsquad/task/<number>`, the branch name no longer encodes the creating role — QA just needs to know the issue number (which it already has). This actually simplifies QA's lookup.
- **`cycle_pre.py` QA input**: Currently derives `branch` for each pending-test item as `squidsquad/{query_role}/{num}`. With unified branches, this should be `squidsquad/task/{num}` (or whatever the pattern is). The `source_role` field is already separate from the branch name.

## Integration Risks
- **Cycle-post PR creation**: `cycle_post.py` line 298-317 creates PRs on the feature branch. It checks out the branch from `code_commit.branch`. If the branch name in cycle-output is stale (agent used old pattern), the PR creation will fail. The agent constructs `code_commit.branch` in its creative phase — it must use the config-driven branch name.
- **Tracker unmerged-branch check**: `tracker.py` `_check_unmerged_branch` (line 668) uses `git branch -a --list "*squidsquad/*/{number}"` — this wildcard matches both old and new patterns. Safe. Same for `_check_unmerged_pr` (line 708) and `_convert_draft_pr_to_ready` (line 747).
- **PR conflict rebase**: `agent-instructions.md` line 773-793 has agents search `squidsquad/[ROLE]/` for their own PRs. With unified branches, agents would search for `squidsquad/task/` — but multiple agents' PRs could match. The "only rebase own branches" guard at line 793 becomes trickier. Mitigation: the PR's author metadata distinguishes ownership; branch name no longer encodes it.
- **Forge adapter PR search**: `tracker.py` line 708 and 747 search with `f"squidsquad/ {number}"`. This is role-agnostic and will continue to work.

## Upgrade & Migration
- **New config values**: 
  - `branch-pattern` under `## Git Branches` section: `- **Branch Pattern**: squidsquad/{role}/{number}` (default, backward-compatible). Projects override to `squidsquad/task/{number}`.
  - `FIELD_MAP` entry in `config.py`: `"branch-pattern": ("Git Branches", "Branch Pattern")`
- **New files**: None required for the config approach. If L4 project override: `.squidsquad/project/branch-workflow.md` (or inline in existing `dev-instructions.md`)
- **Template changes**: `agent-instructions.md` lines 699, 703, 760, 773, 775, 793 must replace `squidsquad/[ROLE]/[NUMBER]` with a reference to the config-driven pattern. Alternatively, instruct agents to call `git_ops.py task-begin` and capture the branch name from its output, then use that variable everywhere.
- **Upgrade steps**:
  1. Add `branch-pattern` to `config.py` FIELD_MAP with default `squidsquad/{role}/{number}`
  2. Add `## Git Branches > Branch Pattern` to `config.md`
  3. Add `_get_branch_name(role, number)` factory function to `git_ops.py` that reads `branch-pattern` config and substitutes `{role}` and `{number}`
  4. Replace all 4 construction sites with calls to `_get_branch_name()`
  5. Make parsing sites pattern-aware: extract issue number by finding the numeric segment after the last `/` (works for both old and new patterns since the number is always the terminal segment)
  6. Update `agent-instructions.md` and sub-skill templates to use `task-begin` output rather than hardcoding the pattern
  7. Update all tests
  8. For existing projects: the default `squidsquad/{role}/{number}` preserves backward compatibility. New projects set `squidsquad/task/{number}` at setup time.
- **Graceful degradation**: If `branch-pattern` is missing from config (old config.md), `_get_branch_name()` falls back to `squidsquad/{role}/{number}`. Parsing code that uses `parts[-1]` (last segment) for the issue number works for both old and new patterns. Parsing code that checks `parts[0] == "squidsquad"` and `len(parts) >= 3` continues to work.

## Open Questions
- **Q1**: Should the branch pattern be per-project config (`.squidsquad/config.md`) or L4 instruction override (`.squidsquad/project/dev-instructions.md`)? — **Why**: Config is machine-readable by `config.py` and accessible to all scripts. L4 instructions are human/agent-readable prose. A config field is more reliable for deterministic scripts; L4 override is better for agent behavior guidance. Recommendation: config field for machine consumption, L4 instructions reference the config (don't hardcode).
- **Q2**: Should `task-begin` output the branch name on stdout so agents can capture it? — **Why**: Currently `task-begin` is silent on success. If agents capture the branch name from `task-begin` output and use that variable everywhere, the pattern can change without updating agent instructions. This aligns with [[pattern-deterministic-scripts-over-prose]].
- **Q3**: Migration window — how long should both old and new branch patterns be recognized? — **Why**: Open PRs on old-pattern branches will exist. Parsing code that extracts the issue number from the last segment works for both. PR search `squidsquad/ <number>` also works for both. The migration may not need a window — the parsing is already position-tolerant.

## Recommendation
**Feasible with caveats.** The change is straightforward: centralize branch construction into one function, add one config field, update ~4 construction sites and ~21 reference sites. The main caveat is the wide blast radius in agent-facing instructions — agents currently construct branch names from hardcoded patterns in prose. This change should also make `task-begin` print the branch name to stdout so agents can capture it programmatically, eliminating the need to hardcode the pattern in instructions. Parsing sites are already mostly pattern-tolerant (they look for `squidsquad/*/NUMBER` or extract `parts[2]` which would still be the issue number in `squidsquad/task/NUMBER`).

## Vault Candidates
- **Type**: learning — **Branch name pattern coupled across 25+ sites** — **Why**: This research documents every site where the branch pattern is constructed or parsed. Future changes to branch naming will need this map. The key insight is that construction sites (4) are few but parsing/reference sites (21+) are many — centralizing construction is the lever.
- **Type**: pattern — **Deterministic script output capture pattern** — **Why**: Having `task-begin` print the branch name to stdout so agents can capture it (rather than hardcoding the pattern in prose) is a general pattern for keeping agent instructions decoupled from implementation details. Aligns with [[pattern-deterministic-scripts-over-prose]].
- **Type**: decision — **Branch parsing should use the terminal path segment for issue number** — **Why**: All current parsing uses `parts[2]` (3-segment assumption). Switching to `parts[-1]` makes parsing invariant to prefix changes. This should be the standard for any future branch pattern changes.
```