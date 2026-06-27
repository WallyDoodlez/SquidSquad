# TEST-PLAN-12801 — Harness TUI bottom action bar with reboot

**Derived independently** from the 8 ACs in the issue body.

## ACs
- AC1 bottom action bar lists reboot
- AC2 reboot specific agent + all agents
- AC3 busy indicator before reboot
- AC4 graceful (intent→checkpoint→restart) vs force (immediate, override busy)
- AC5 force is distinct + confirmed
- AC6 lifecycle (not raw kill); force not counted toward crash-streak
- AC7 tests for dispatch + busy + graceful-vs-force
- AC8 HARNESS-ARCH updated

## Method
- **Headless render** (Textual `App.run_test()`/Pilot): assert Footer + reboot/all/force bindings (AC1/2/5) — `tests/test_feat_12801_render_contract_qa.py`.
- **Lifecycle**: harness force endpoint + all/restart + operator_force death-classification (skill's harness tests, full test_harness.py).
- **Dispatch/busy/confirm**: skill's `test_feat_12801_reboot_action_bar.py` + tui tests.
- No CQ (deterministic code; HARNESS-ARCH is human-facing).
