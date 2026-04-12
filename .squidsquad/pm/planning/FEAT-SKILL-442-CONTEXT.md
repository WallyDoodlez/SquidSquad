# FEAT-SKILL-442 Context — Rename feature/bug to task/issue

## Scope

Pure vocabulary rename across the entire SquidSquad codebase. ~60 files, ~500 references, 10 file renames, 2 GitHub label renames, ~34 open issue title renames. No lifecycle or architecture changes.

## Locked Decisions (human decided)

- **Vocabulary**: `feature` → `task`, `bug` → `issue` everywhere in SquidSquad-specific context
- **Labels**: `type:feature` → `type:task`, `type:bug` → `type:issue`
- **Commands**: `create-bug` → `create-issue`, `create-feature` → `create-task`, `list-bugs` → `list-issues`, `list-features` → `list-tasks`
- **Title prefixes**: `FEAT:` → `TASK:`, `BUG:` → `ISSUE:`
- **Ordering**: #442 lands BEFORE #401 (capability sub-skills). #401 on hold until #442 ships.
- **`/squidsquad-bug`**: rename to `/squidsquad-issue` for consistency
- **Historical CHANGELOG entries**: leave as-is (historical records)
- **Closed GitHub Issue titles**: leave as-is (historical)
- **`severity:` labels**: keep unchanged — still makes sense for issues
- **Legacy directories** (`.squidsquad/skill/features/`, `.squidsquad/skill/bugs/`): leave as-is, not actively used
- **Default `bug` GitHub label**: remove it (SquidSquad uses `type:issue`)

## Dev Discretion (dev agent can choose)

- Order of file edits within the implementation phases
- Whether to add backward-compat aliases for old tracker.py commands (optional)
- How to structure the migration script (standalone or part of wizard upgrade)

## Side Effect Mitigations (required)

- Stop all agents before deploying (label rename mid-cycle breaks agent queries)
- Update all `{{include:}}` directives when renaming sub-skill files
- Run full test suite after rename
- Recompose all agent CLAUDE.md files after reference updates
- DO NOT rename: generic English usage in manifest.py, git branch convention "feature/test", historical CHANGELOG, closed issue titles, existing planning artifacts (FEAT-SKILL-XXX)

## Upgrade Path (required)

- GitHub label rename via `gh label edit` (in-place, automatic for all existing issues)
- Open issue title rename via script (~34 issues: FEAT: → TASK:, BUG: → ISSUE:)
- Wizard upgrade step: rename labels + recompose agents
- Graceful degradation: non-upgraded installs continue working but find no matching issues if repo labels were renamed

## Out of Scope

- Lifecycle changes (same PM plans → agent executes flow)
- Architecture changes
- Historical data rewriting
- Legacy directory cleanup
