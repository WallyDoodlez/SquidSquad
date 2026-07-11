# QA-RESULTS-13355 — installer PR-flow invariant

**Issue**: #13355 (type:task, priority:medium)
**PR**: #13386 `squidsquad/task/13355`, head d646ade25 (5 files: config.py +10, wizard.py +75, test_wizard.py, new test_wizard_13355_pr_flow_invariant.py +124, test_wizard_runbook.py)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13355.md`
**Verdict**: **PASS — 5/5 ACs. -> pending-ship.**

## AC walk
- **AC1 PASS (TC-1)** — `pr_flow_prompt` + `cmd_pr_flow_prompt` tombstoned (wizard.py:3464/3937); no `pr-flow-prompt` dispatch command; grep found NO surviving pr-flow on/off toggle, direct-commit text, or `branch_workflow`.
- **AC2 PASS (TC-2)** — `## PR Flow / Enabled: yes` hardcoded (wizard.py:1642-1644), never spec-driven. **Independent E2E** via `generate_default_spec()`: default flags carry NO pr_flow (auto_merge=True); injected legacy `flags.pr_flow=False` -> still renders `Enabled: yes` (invariant ignores it); pr_flow excluded from `## Flags` (1653-1654).
- **AC3 PASS (TC-3)** — `## Auto Merge / Enabled` from `flags.auto_merge` default True (1638-1640). E2E: auto_merge=False -> renders `no`. Merge gate is the one surviving PR variable.
- **AC4 PASS (TC-4)** — new `test_wizard_13355_pr_flow_invariant.py` + retargeted `test_wizard.py` / `test_wizard_runbook.py`: **310 passed**.
- **AC5 PASS (TC-1)** — no toggle/branch_workflow anywhere; branch+PR is the only mode (#9478 D2).
- **Wiring PASS (TC-5)** — config.py FIELD_MAP `pr-flow->(PR Flow,Enabled)`, `auto-merge->(Auto Merge,Enabled)` + fail-safe `_FIELD_DEFAULTS` (pr-flow=yes / auto-merge=no for a legacy config.md missing the section). Live `config.py get pr-flow` => yes, `get auto-merge` => yes. Confirms the latent `- Pr Flow`-under-`## Flags` read-mismatch fix.
- **TC-6 PASS** — full static gate on d646ade25: **5294/0/0** (5266 passed + subtests; #13337 flake did not recur).
- **TC-7 PASS** — landing safety: branch behind current origin/main (missing #13369 merge) but touches a DISJOINT file set. Confirmed `git diff merge-base..HEAD -- <#13369 files>` = EMPTY (branch modifies no #13369 file) -> squash-merge cannot revert #13369. mergeStateStatus CLEAN.

## Actions
- PR #13386 squash-merged to main. Post-merge verified #13369 PRESERVED on origin/main (test present + instructions.md:191 announce-before-drain intact). #13355 pending-test -> pending-ship (DM owns version/counter/tag).

No CQ spec required (deterministic code + prompt removal; INSTALLER-RUNTIME.md unchanged since #13336, which carried its own CQ).
