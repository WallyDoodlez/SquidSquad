# FEAT-PM-329 Research — Consistent Per-Cycle Reporting

## Summary

All four SquidSquad agent roles (PM, QA, Skill/Dev, DM) plus the Designer role write iteration logs (`iter-N.md`), but each uses a different format with role-specific fields. The formats diverge in two dimensions: (1) field names and structure vary per role, and (2) quiet cycles are universally skipped — no log entry is written. The task is to create a single shared format used by all roles, where every cycle writes a log entry, including a compact entry for quiet cycles.

The iteration-log sub-skill is composed into each role via `includes.yml`, with three tiers: `common/iteration-log` (used by dev roles), role-specific overrides (`pm-specific/iteration-log`, `qa-specific/iteration-log`, `dm-specific/iteration-log`, `designer-specific/iteration-log`). The `cycle.py` script provides a `log-iteration` helper used by dev roles, but PM, QA, and DM write their own format directly. The change requires updating 5 sub-skill template files, 1 Python script, and potentially the `vault_remember.py` quiet-cycle detection logic.

The blast radius is moderate but well-contained — all changes are within `references/sub-skills/` and `references/scripts/`, deployed via `compose.py deploy-all`. No application code is affected. The primary risk is that `vault_remember.py` uses iter file mtime to detect quiet cycles, which could break if quiet cycles now produce a log file.

## Current Formats

### PM (`pm-specific/iteration-log`)
```markdown
# PM Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Human Check-in**: [summary of human input, or "no input"]
- **E2E Tests**: [passed/failed — N tests, X failures / skipped]
- **Issues Filed**: [list IDs, or "none"]
- **Issues Verified**: [list IDs, or "none"]
- **Tasks Shipped**: [list IDs, or "none"]
- **Agent Health**: [list each agent: healthy/stalled/unknown]
- **Notes**: [anything notable for the team]
```
**Quiet trigger**: No QA issues found, no issues verified, no tasks shipped, no human input processed, no improvement scan triggered.

### QA (`qa-specific/iteration-log`)
```markdown
# QA Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **E2E Tests**: [passed/failed — N tests, X failures / skipped]
- **Issues Filed**: [list IDs, or "none"]
- **Issues Verified**: [list IDs, or "none"]
- **Tasks Verified**: [list IDs, or "none"]
- **Agent Health**: [list each agent: healthy/stalled/unknown]
- **Notes**: [anything notable]
```
**Quiet trigger**: No QA issues found, no issues verified, no tasks tested, no improvement scan triggered.

### Skill/Dev (`common/iteration-log`)
```markdown
# [ROLE] Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Issues Fixed**: [list or none]
- **Tasks Progressed**: [list or none]
- **Tests**: [passed/failed]
- **Notes**: [anything notable]
```
**Quiet trigger**: No bugs fixed, no features progressed, no improvement scan triggered.

Note: Dev roles use the `cycle.py log-iteration` script which produces a slightly different field set (`Issues Fixed` / `Tasks Progressed` / `Tests` / `Notes`).

### DM (`dm-specific/iteration-log`)
```markdown
# DM Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Features Delivered**: [list issue #numbers, or "none"]
- **Version Bumped**: [X.Y.Z, or "no"]
- **Notes**: [anything notable]
```
**Quiet trigger**: No features delivered, no improvement scan triggered.

### Designer (`designer-specific/iteration-log`)
```markdown
# Designer Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Designs Progressed**: [list issue #numbers, or "none"]
- **Designs Completed**: [list issue #numbers, or "none"]
- **Quiet Cycles**: [consecutive count, or "0"]
- **Notes**: [anything notable]
```
**Quiet trigger**: No design work done, no improvement scan triggered.

## Current Quiet-Cycle Behavior

All roles share identical behavior on quiet cycles:

- **PM**: "Produce no text output — skip silently to Step 10 (Done)."
- **QA**: "Produce no text output — skip silently to Step 9 (Done)."
- **Skill/Dev**: "Produce no text output — skip silently to Step 6 (Done)."
- **DM**: "Produce no text output — skip silently to Step 6 (Done)."
- **Designer**: "Produce no text output — skip silently to Step 5 (Done)."

No iteration log file is created for quiet cycles in any role. The status bar's `current-state` file is still updated (it always writes `idle|` at cycle end), but no `iter-N.md` file is created.

The Designer role is the only one that tracks a `Quiet Cycles` counter in its log format, but this counter is only written when a non-quiet cycle occurs.

## Sub-Skill Structure

The iteration-log sub-skill uses a 3-tier composition:

1. **`common/iteration-log`** — Used by dev roles (via `dev/includes.yml`). Contains generic format with `cycle.py log-iteration` script integration.
2. **Role-specific overrides** — PM, QA, DM, and Designer each have their own `*-specific/iteration-log` in their `includes.yml`. These override the common version with role-tailored fields.

### includes.yml mapping:
| Role | Iteration-log sub-skill used |
|------|------------------------------|
| PM | `pm-specific/iteration-log` |
| QA | `qa-specific/iteration-log` |
| Dev (skill, fe, be, etc.) | `common/iteration-log` |
| DM | `dm-specific/iteration-log` |
| Designer | `designer-specific/iteration-log` |

### Composition pipeline:
`references/sub-skills/[variant]/iteration-log.md` -> included via `references/roles/[role]/includes.yml` -> `compose.py deploy [role]` -> `.squidsquad/[role]/CLAUDE.md`

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/common/iteration-log.md` — update to shared format
  - `references/sub-skills/pm-specific/iteration-log.md` — replace with shared format
  - `references/sub-skills/qa-specific/iteration-log.md` — replace with shared format
  - `references/sub-skills/dm-specific/iteration-log.md` — replace with shared format
  - `references/sub-skills/designer-specific/iteration-log.md` — replace with shared format
  - `references/scripts/cycle.py` — update `log-iteration` function output format
  - `references/scripts/vault_remember.py` — update `is_quiet()` to handle quiet-cycle logs (lines 57-82)
  - All 5 role CLAUDE.md files (regenerated via `compose.py deploy-all`)

- **Behavior changes**:
  - Every cycle now creates an `iter-N.md` file (including quiet cycles)
  - Quiet-cycle files use a compact format (fewer fields or condensed)
  - All roles use the same field set
  - `vault_remember.py is_quiet` must distinguish quiet-cycle logs from active-cycle logs (can no longer rely on "no iter file = quiet")
  - Iteration cleanup still keeps 20 files, but files accumulate faster since quiet cycles now write

## Side Effects

- **Risk 1**: `vault_remember.py is_quiet()` uses iter file mtime to detect quiet cycles. If quiet cycles now write iter files, this function always returns "non-quiet", causing vault-remember to run on every cycle. — Severity: **H** — Mitigation: Update `is_quiet()` to parse iter file content for a quiet-cycle marker (e.g., `**Type**: quiet`) rather than relying on file existence/recency.

- **Risk 2**: Faster iter file accumulation. With quiet cycles writing files, cleanup runs more often. At 30-minute intervals, a quiet agent generates ~48 files/day vs 0 previously. The 20-file retention limit handles this automatically, but more git history is created. — Severity: **L** — Mitigation: None needed; existing cleanup handles it. Could optionally increase retention to 30 or make it configurable.

- **Risk 3**: Larger git diff per cycle for idle agents. Each quiet cycle now commits a new iter file. — Severity: **L** — Mitigation: Quiet cycles already skip the commit-and-push step. The iter file will be committed on the next active cycle, batched naturally. No change needed.

- **Risk 4**: `cycle.py log-iteration` only used by dev roles currently. PM/QA/DM/Designer write logs directly in their CLAUDE.md instructions. Unifying the format could either (a) make all roles use `cycle.py` or (b) update all role-specific templates to use the same inline format. — Severity: **M** — Mitigation: Prefer option (a) — extend `cycle.py log-iteration` to support the unified format with a `--quiet` flag, so all roles can call it consistently.

## Edge Cases

- **Designer role**: Has an extra `Quiet Cycles` counter field not present in other roles. The unified format should either include this for all roles or drop it. Since quiet cycles now always write, the counter is less valuable — the human can count consecutive quiet entries visually. Recommend dropping it.

- **Iter file cleanup with more files**: Cleanup deletes files beyond the most recent 20 based on mtime. With quiet cycles writing, a quiet agent hits the 20-file limit every ~10 hours (at 30-min intervals). This is fine — cleanup is already well-tested.

- **Suppressed cycles (PM planning phase)**: PM has a "planning phase suppression" mode where cycles are suppressed and skip iteration logging. Should suppressed cycles write a log? Recommendation: Yes — write a one-line `**Type**: suppressed` entry so the human can see the agent was alive but suppressed.

- **Mixed old/new iter files**: After upgrade, an iterations directory will contain old-format and new-format files. This is purely cosmetic — nothing parses iter file content for structured data (except `vault_remember.py is_quiet()` which checks mtime, not content). Not a problem.

- **Step number references**: Each role's iteration-log sub-skill references different step numbers ("skip to Step 10/9/6/5"). A unified template needs a placeholder or role-aware reference. Compose.py already supports `[ROLE]` substitution but not step numbers. Could use "skip to the Done step" as a generic phrasing.

## Upgrade & Migration

- **New config values**: None — no new config fields needed.
- **New files**: None — existing iter file pattern continues.
- **Template changes**: All 5 role-specific iteration-log sub-skills change. The common iteration-log changes. `cycle.py` changes.
- **Upgrade steps**: `compose.py deploy-all` regenerates all CLAUDE.md files. Existing agents will pick up the new template on their next self-restart (triggered by CLAUDE.md mtime change detection).
- **Graceful degradation**: Old templates still work fine. Agents using old templates will continue to skip quiet cycles and use old formats. No breakage — just inconsistency until all agents restart with new templates.

## Open Questions

- **Q1**: Should `cycle.py log-iteration` become the single entry point for ALL roles, or should each role continue writing its own format (just unified)? — **Why**: If all roles use cycle.py, format consistency is enforced programmatically. If roles write inline, drift can reoccur.

- **Q2**: What fields should the unified format include? A superset of all roles' fields would be large. A minimal common set might lose role-specific context (e.g., PM's "Human Check-in", DM's "Version Bumped"). — **Why**: Too many fields = noisy for human reading. Too few = loss of useful context per role.

- **Q3**: What should the compact quiet-cycle entry look like? Options: (a) full format with all fields set to "none"/"n/a", (b) a 2-3 line condensed entry with just date + "quiet cycle", (c) a single-line entry. — **Why**: Locked decision #4 says "compact entry", but the exact shape matters for readability.

- **Q4**: Should `vault_remember.py is_quiet()` be updated now (as part of this task) or deferred as a separate issue? — **Why**: If deferred, vault-remember will malfunction after this change ships (false non-quiet detection on every cycle).

## Recommendation

**Straightforward.** The scope is well-defined — 5 sub-skill templates, 1 script, 1 dependent script fix. All changes flow through the compose pipeline. No application code touched. The `vault_remember.py` fix (Q4) should be included in scope to avoid shipping a known regression. The format unification (Q1-Q3) should be resolved in the discussion phase.
