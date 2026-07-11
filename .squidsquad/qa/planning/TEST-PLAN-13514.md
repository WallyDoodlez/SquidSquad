# TEST-PLAN #13514 — setup-yes must surface per-role compose failure

**Derived independently from the issue body "Fix direction" ACs — not from the worker's diff.**

Bug: `wizard.py setup-yes` reported `Created N agent(s)` and exited 0 even when
every role's compose failed and no CLAUDE.md was produced — a non-bootable install
masquerading as success. Coupled to #13513 (the compose blocker this masked).

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `cmd_setup_yes` returns **non-zero** when any role fails to compose |
| AC2 | A **FAILED summary line** distinct from "Created N agent(s)" is printed |
| AC3 | "Created N" counts only agents that produced a **valid CLAUDE.md**, not scaffolded dirs |
| AC4 | Regression test: a stubbed failing deploy makes `cmd_setup_yes` return non-zero |

## Independent verification strategy

The worker's tests stub `scaffold_install` and hardcode `claude_md == "FAILED"`.
That proves the fix's *reaction* but not that the real `scaffold_install` *emits*
the sentinel — the seam the fix relies on. This plan drives the **real**
`scaffold_install` and the **real** `cmd_setup_yes` with `compose.deploy_role_v2`
patched to raise, against a throwaway temp target (non-destructive).

## Test cases (`TEST-13514-tests.py`)

| TC | AC | What it proves | Result |
|----|----|----|--------|
| TC-S  | seam | real `scaffold_install` records `claude_md=='FAILED'` when deploy raises | PASS |
| TC-S2 | seam | negative control: successful deploy records a real path, never `'FAILED'` | PASS |
| TC-1  | AC1/2/3 | full E2E, all roles fail → rc!=0, "Created 0", FAILED text, banner suppressed | PASS |
| TC-2  | AC1/3 | full E2E, only pm fails → rc!=0, Created counts composed only, ERROR names pm | PASS |
| TC-3  | control | full E2E, all compose → rc==0, no FAILED text | PASS |

Plus worker's `tests/test_13514_setup_yes_surfaces_compose_failure.py` (3 cases) — re-run green.

## Live evidence (real cmd_setup_yes, all roles fail)

```
  Created 0 agent(s) (2 FAILED to compose)
  WARNING: Failed to deploy pm: simulated compose blocker
  WARNING: Failed to deploy skill: simulated compose blocker
ERROR: 2 role(s) failed to compose a CLAUDE.md: pm, skill. The install is NOT bootable ...
=== EXIT: 1 ===
```

Contrast with the pre-fix issue evidence: `Created 2 agent(s)` / `EXIT: 0`.
