# FEAT-PM-329 Context — Consistent Per-Cycle Reporting

## Scope

Standardize iteration log format across all agent roles (PM, QA, Skill/Dev, DM, Designer) and ensure every cycle — including quiet ones — writes a log entry. Centralize log writing in cycle.py to enforce consistency programmatically. Fix vault_remember.py is_quiet() to avoid regression.

## Locked Decisions (human decided)

- **Architecture**: All roles write iteration logs through `cycle.py log-iteration` — the script owns the format. Agents pass structured data (cycle number, type, work summary bullets, notes), script writes the file. Format changes happen in one place only.
- **Field set**: Minimal common fields — Date, Cycle Number, Type (active/quiet), Work Summary (free-form bullets), Notes. No role-specific fields. Role details go naturally in work summary bullets.
- **Quiet-cycle format**: 2-3 line condensed entry — Date, Type: quiet, one-line note explaining why (e.g., "No approved tasks available", "No issues found"). Proves liveness without noise.
- **vault_remember.py fix**: is_quiet() must be updated to check iter file content (Type: quiet vs active) instead of mtime, since quiet cycles now write files too.
- **Audience**: Human reading iteration logs. Not for tooling or parsing.
- **Tight scope**: No commit message changes, no cross-agent rollups, no dashboards, no new fields beyond consistency.

## Dev Discretion (dev agent can choose)

- Exact cycle.py CLI interface (args, flags) for log-iteration command
- How work summary bullets are passed to the script (JSON array, multi-arg, etc.)
- Whether to add a `--quiet` flag or detect from empty work summary
- Exact wording of quiet-cycle notes per role

## Side Effect Mitigations (required)

- vault_remember.py is_quiet() MUST be fixed as part of this task — not a follow-up
- Existing iter file cleanup logic (delete oldest when >20 files) must still work
- compose.py deploy-all must be run after template changes
- No scripts currently parse iter file content — but the new format should still be human-readable markdown

## Upgrade Path (required)

- Template changes: sub-skill files in references/sub-skills/ updated, compose.py deploy-all regenerates CLAUDE.md files
- Script changes: cycle.py gains log-iteration command, vault_remember.py is_quiet() updated
- Existing iter files in old format remain — no migration needed, they're historical
- Graceful degradation: old templates still work, just produce inconsistent format

## Out of Scope

- Combined cross-agent rollup reports
- Daily/weekly summaries
- Status bar or dashboard changes
- Commit message format standardization
- Parsing tooling or web views
- Any new fields not required for consistency
