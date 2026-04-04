## Feature Approval Gate

Features start as `Pending` — **a human must explicitly approve them** before any agent picks them up.

Status values: `Pending` → `Planning` → `Planned` → `Approved` → `In Progress` → `Pending Test` → `Pending Ship` → `Shipped`

- `Pending`: Filed, awaiting human approval to begin planning.
- `Planning`: Human approved planning. PM is running the Feature Intake Process (Phases 1-3: Research → Discussion → Planning).
- `Planned`: Planning complete (all artifacts done). Awaiting human approval for execution.
- `Approved`: Human explicitly said "go" — dev/designer agent picks this up.
- `Rejected`: PM recommends against the feature based on research. Human can override.

To approve a feature for planning:
1. Present it to the human during the check-in step.
2. Get explicit confirmation to begin planning ("yes", "plan this", "go ahead", etc.).
3. Update status to `Planning` (NOT `Approved`) and begin the Feature Intake Process.
4. After all planning phases complete (RESEARCH.md, CONTEXT.md, TEST-PLAN.md created), update status to `Planned` (NOT `Approved`).
5. Present the completed plan to the human. Wait for explicit execution approval ("approved", "go", "build it", etc.).
6. Only after human explicitly approves execution, update status to `Approved`.

Light mode (trivial features): PM can fast-track through planning with abbreviated research, but status still transitions through `Planning` → `Planned` → `Approved`.

Do not set status to `Approved` without human explicitly approving execution. Do not skip the `Planned` state — it is the human's review gate between planning and execution.
