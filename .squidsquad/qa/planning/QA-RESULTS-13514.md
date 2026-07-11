# QA-RESULTS #13514 — setup-yes surfaces per-role compose failure

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13523 — MERGED (squash 9de7e3ed1, 2026-07-11T17:02Z)
**Branch verified on**: squidsquad/task/13514; promoted test re-verified on main @9de7e3ed1

## AC walk (independent)

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | non-zero exit on any per-role compose failure | live E2E `cmd_setup_yes` → `EXIT: 1` (all-fail + partial) | **PASS** |
| AC2 | distinct FAILED summary line | `Created 0 agent(s) (2 FAILED to compose)` + `ERROR: 2 role(s) failed to compose a CLAUDE.md: pm, skill` | **PASS** |
| AC3 | "Created N" counts only composed agents | `Created 0` (all-fail) / `Created 1` (partial) vs pre-fix `Created 2` | **PASS** |
| AC4 | regression test: stubbed failing deploy → non-zero | worker's 3 tests + my 5 independent tests, all green | **PASS** |

## Independent verification — the seam the worker's tests skipped

Worker's `tests/test_13514_setup_yes_surfaces_compose_failure.py` STUBS
`scaffold_install` and hardcodes `claude_md == "FAILED"`. It proves the fix reacts
to the sentinel but not that the real code emits it. I drove the **real**
`scaffold_install` (wizard.py:2089-2099) with `compose.deploy_role_v2` patched to
raise:

- **TC-S** — real `scaffold_install` records `claude_md == "FAILED"` on a genuine
  deploy exception. Seam confirmed live.
- **TC-S2** — negative control: a successful deploy records a real path string
  (`str(claude_path)`), which can never equal the bare `"FAILED"` sentinel → the
  fix's `== "FAILED"` check cannot false-positive.
- **TC-1/2/3** — full end-to-end `cmd_setup_yes` (no stub): all-fail (rc1, Created 0,
  banner suppressed), partial (rc1, Created counts composed, ERROR names pm),
  all-compose (rc0, no FAILED).

## Live output (real cmd_setup_yes, all roles' deploy fails)

```
Scaffolding...
  Created 0 agent(s) (2 FAILED to compose)
Creating GitHub labels...
  All labels exist
[stderr]
  WARNING: Failed to deploy pm: simulated compose blocker
  WARNING: Failed to deploy skill: simulated compose blocker
ERROR: 2 role(s) failed to compose a CLAUDE.md: pm, skill. The install is NOT
bootable for those agents — see the WARNING(s) above for the cause.
=== EXIT: 1 ===
```

Pre-fix (from issue evidence): `Created 2 agent(s)` / `EXIT: 0` (CLAUDE.md produced: NONE).

## Test runs

- Worker regression: `tests/test_13514_setup_yes_surfaces_compose_failure.py` — 3 passed
- Independent QA plan: `TEST-13514-tests.py` — 5 passed
- Promoted regression test: `tests/test_feat_13514_setup_yes_compose_failure_qa.py` — 5 passed on main @9de7e3ed1
- Full static gate: **5384 gated tests, 0 failures** (186.58s, exit 0)

## Notes

- `type:issue` (bug) — auto-approved, no human gate.
- Not LLM-consumed instructions (pure Python) → no comprehension spec required.
- Coupled to #13513 (shipped): together, greenfield compose failures are now self-evident.
