## Feature Approval Gate

Features start as `Pending` — **a human must explicitly approve them** before any agent picks them up.

Status values: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Pending Ship` → `Shipped`

- `Pending`: Filed, awaiting human approval to begin planning.
- `Planning`: Human approved. PM is running the Feature Intake Process (Phases 1-3: Research → Discussion → Planning).
- `Approved`: Planning complete. Dev agent can pick this up.
- `Rejected`: PM recommends against the feature based on research. Human can override.

To approve a feature:
1. Present it to the human during the check-in step.
2. Get explicit confirmation ("yes", "approved", "go ahead", etc.).
3. Update status to `Planning` (NOT `Approved`) and begin the Feature Intake Process.
4. After all planning phases complete (RESEARCH.md, CONTEXT.md, TEST-PLAN.md created), update status to `Approved`.

Light mode (trivial features): PM can fast-track through planning with abbreviated research, but status still transitions through `Planning` → `Approved`.

Do not set status to `Approved` without completing the planning phases. Do not approve features yourself without human confirmation.
