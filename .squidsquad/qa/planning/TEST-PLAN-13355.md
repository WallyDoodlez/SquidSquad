# TEST-PLAN-13355 — installer PR-flow invariant

**Issue**: #13355 (type:task, priority:medium) — retire pr_flow on/off prompt; PR-flow always-on per INSTALLER-RUNTIME.md §3 + #9478.
**PR**: #13386 `squidsquad/task/13355`, head d646ade25.
**Derived from**: the issue body's Scope/ACs (independent of the worker diff).

## ACs
- **AC1**: `pr_flow_prompt` + `cmd_pr_flow_prompt` + `pr-flow-prompt` CLI command retired — no PR-flow on/off question in the installer.
- **AC2**: `build_config_md` always emits `## PR Flow / Enabled: yes` (invariant, never spec-driven); legacy `flags.pr_flow` ignored; config.md always ships it.
- **AC3**: surviving variable = the merge gate — `## Auto Merge` from `flags.auto_merge` (default yes); NOT PR-flow.
- **AC4**: tests asserting the pr-flow prompt updated; new coverage.
- **AC5**: reconcile with #9478 (branch+PR is the only mode — no toggle).

## Test cases
- **TC-1 (AC1/AC5)**: grep wizard.py — pr_flow_prompt/cmd_pr_flow_prompt/pr-flow-prompt gone; no dispatch command; no surviving on/off toggle / direct-commit / branch_workflow text.
- **TC-2 (AC2)**: read build_config_md emission; INDEPENDENT E2E via generate_default_spec — inject legacy pr_flow=False, assert `## PR Flow / Enabled: yes` still renders + pr_flow absent from `## Flags`.
- **TC-3 (AC3)**: E2E — `## Auto Merge / Enabled` renders auto_merge (yes default; False -> no).
- **TC-4 (AC4)**: run test_wizard_13355_pr_flow_invariant.py + retargeted test_wizard.py/test_wizard_runbook.py.
- **TC-5 (wiring)**: config.py FIELD_MAP + _FIELD_DEFAULTS; live `config.py get pr-flow/auto-merge`.
- **TC-6**: full static gate on branch HEAD.
- **TC-7**: landing safety — branch behind main; confirm disjoint from #13369 (no revert); mergeable CLEAN.

No CQ spec — deterministic wizard.py/config.py + prompt REMOVAL; INSTALLER-RUNTIME.md agent-facing surface unchanged since #13336.
