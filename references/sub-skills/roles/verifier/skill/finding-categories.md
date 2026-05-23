### Finding Categories (Software Development)

When classifying findings during verification, use these domain-specific categories to determine the responsible role:

| Category | Description | Route to |
|---|---|---|
| **Implementation defect** | Code bug, wrong behavior, crash, missing error handling | Dev role that built it (check `role:*` label on the issue) |
| **Specification/AC gap** | Acceptance criteria ambiguous, missing, contradictory, or incomplete | PM (PM owns specs and acceptance criteria) |
| **Design defect** | UI/UX issue, visual mismatch, interaction problem, accessibility gap | Designer if present (check config.md Dev Agents), otherwise PM |
| **Test infrastructure** | Test environment broken, missing dependency, flaky test unrelated to code | Role that owns the test infrastructure, or flag as `blocked:human-action` |

These categories are specific to software development teams. Other domains (e.g., accounting, journalism) would have their own finding categories at this layer.

**When category is ambiguous**: If a finding could be either a spec gap or an implementation defect (e.g., code does something reasonable but spec didn't cover the case), route to PM first — PM decides whether the spec needs updating or the implementation is wrong.
