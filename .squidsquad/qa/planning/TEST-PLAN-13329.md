# TEST-PLAN-13329 — scan repo for existing Claude assets -> confirm -> L4

**Issue**: #13329 (type:task, priority:medium) — largest greenfield item.
**PR**: #13441 `squidsquad/task/13329`, head 63275b39e.

## ACs
- AC1: wizard scans .claude/skills/ + .claude/commands/ + CLAUDE.md, lists detected assets.
- AC2: confirmation gates incorporation; declined/unused NOT imported.
- AC3: confirmed items -> L4 (.squidsquad/project/) AND surface in composed CLAUDE.md (CONSUMPTION PATH required).
- AC4 (comprehension): freshly-composed agent sees incorporated skill/command references.
- AC5: no regression to existing auto-detect.

## Test cases
- TC-1 (AC1): read scan_existing_assets; live E2E on temp repo with skill/command/CLAUDE.md/mcp + empty-repo no-op.
- TC-2 (AC2): INSTALLER-RUNTIME §9 Step-4 confirm-gate prose.
- TC-3 (AC3): verify L4->compose consumption path is real — project/<role-class>.md content surfaces verbatim in composed CLAUDE.md (checked pm.md); pointer-not-copy; narrowest-role.
- TC-4 (AC4 CQ): 13329_spec; fresh Sonnet on §4-step4 + §9-Step4; zero misreads (scan/gate/pointer-narrowest/MCP-awareness).
- TC-5 (AC5): diff scope — scan-summary/set-test-strategy untouched.
- TC-6 (gate+landing): combined-state static gate (branch behind main, shares wizard.py/INSTALLER-RUNTIME.md/runbook with #13327/#13328/#13339); local merge + gate; all sibling doc edits coexist.

CQ REQUIRED — INSTALLER-RUNTIME.md + the L4 consumption path are LLM-consumed (AC3/AC4).
