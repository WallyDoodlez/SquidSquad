# QA-RESULTS-13329 — installer: scan repo for existing Claude assets -> confirm -> L4

**Issue**: #13329 (type:task, priority:medium, PM-specced — largest greenfield item)
**PR**: #13441 `squidsquad/task/13329`, head 63275b39e (5 files: wizard.py +129, INSTALLER-RUNTIME.md +10, new 13329_spec.json +30, new test_wizard_13329_scan_assets.py +144, test_wizard_runbook.py +2)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13329.md`
**Verdict**: **PASS -> pending-ship.**

## AC walk
- **AC1 PASS (scan)** — `scan_existing_assets` detects `.claude/skills/*/SKILL.md` + `.claude/commands/*.md` (name+path+intent) + CLAUDE.md files + `mcp_config_present`. **Independent live E2E** on a temp repo: skill 'myskill' (intent), command 'deploy' (intent), 1 CLAUDE.md, mcp=True; empty repo -> no-op (0/0, mcp False).
- **AC2 PASS (confirm gate)** — INSTALLER-RUNTIME.md §9 Step-4: per-asset confirm; declined/stale NOT imported. Prose + CQ2.
- **AC3 PASS (L4 write + CONSUMPTION PATH — the load-bearing AC)** — incorporation is an L4 POINTER (name+path+intent, NOT a body copy) written to `.squidsquad/project/<role-class>.md` via l4-curation. **Consumption path VERIFIED real, not hand-waved**: 19/20 non-trivial lines of the existing `.squidsquad/project/pm.md` appear VERBATIM in composed `.squidsquad/pm/CLAUDE.md` → a pointer written to project/<role-class>.md surfaces in that role's composed instructions at recompose. compose.py `check_alias_staged_l4` + `l4_parser` confirm project/<role-class>.md is the L4 link-stage input.
- **AC4 PASS (CQ)** — INSTALLER-RUNTIME.md §4-step4 + §9-Step4. 13329_spec 4 Qs verifier-reviewed; fresh Sonnet agent on named sections only → **4/4 zero misreads**: scan envelope; per-asset confirm-gate; frontend skill → L4 pointer into narrowest role only, body not copied; MCP awareness-only, NOT incorporated.
- **AC5 PASS (no regression)** — diff scope: scan_existing_assets is additive; scan-summary/set-test-strategy untouched.
- **Tests** — 11 scan-assets tests pass.
- **Landing** — branch 2 behind main + shares wizard.py/INSTALLER-RUNTIME.md/test_wizard_runbook.py with #13327/#13328/#13339 (on main). COMBINED state (local merge origin/main, no push): 3-way CLEAN; combined INSTALLER-RUNTIME.md carries #13329 §4-Step4 + #13327 §7 + #13339 detect-maturity; combined static gate **5320/0/0**.

## Actions
- PR #13441 squash-merged to main. #13329 pending-test -> pending-ship (DM ships). Closes the greenfield-feedback trio (#13327/#13328/#13329).
