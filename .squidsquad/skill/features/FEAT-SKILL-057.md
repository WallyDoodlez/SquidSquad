## FEAT-SKILL-057 — Templatize boot scripts (start-*.ps1 / start-*.sh)

- **Priority**: Medium
- **Status**: Pending
- **Requested By**: human
- **Assigned To**: skill-lead

### Description

Currently each agent's boot script (`start-skill.ps1`, `start-dm.ps1`, `start-pm.ps1`, plus `.sh` variants) is hand-written with the role name swapped in. They're nearly identical — the only differences are the role name, display label, and initial prompt. This causes:

1. **Bug propagation** — fixes (e.g. `--dangerously-skip-permissions`) must be applied to every script in every repo independently.
2. **Drift** — minor inconsistencies creep in (e.g. `start-skill.ps1` lacks the `if (Test-Path .squidsquad)` guard that the others have).
3. **Manual setup** — new projects copy-paste from an existing project and hand-edit.

### Acceptance Criteria

1. A single template (or generator script) that produces boot scripts for any role.
2. Role-specific values (role name, display label, initial prompt) are parameterized.
3. Both `.ps1` and `.sh` variants are generated from the same source of truth.
4. Existing boot scripts in this repo are regenerated from the template and match current behavior.
5. The `if (Test-Path .squidsquad)` guard is consistent across all generated scripts.

### Discussion

> [2026-04-02 00:00] **skill-lead**: Filed after discovering squidsquad-3 had a stale boot script bug that was already fixed in squidsquad-2. Templatizing would prevent this class of issue.
> [2026-04-02 00:30] **skill-lead**: Renumbered from 052 to 057 — PM filed 052-056 concurrently.
