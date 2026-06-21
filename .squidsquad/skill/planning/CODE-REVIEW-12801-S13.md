# Code Review — #12801 Story 1.3 (minimal launchable TUI)

**model_router external model returned a degenerate sub-threshold response →
Claude-sonnet fallback per [[feedback_model_router_auto_fallback]].**

## Verdict: effectively CLEAN — no high-severity findings, no bugs.

Reviewer confirmed correct for Textual 8.2.7:
- `@work(exclusive=True, thread=True)` + `call_from_thread` is the documented
  pattern; blocking `fetch_status` runs off the UI thread; DataTable mutation
  marshalled to the main thread — no race.
- `set_interval` driving the `@work`-decorated refresh is fine; `exclusive`
  drops an in-flight poll so a slow/unreachable harness never stacks workers.
- `table.clear()` (default `columns=False`) preserves the columns added in
  `on_mount`; correct.
- Graceful degradation at both layers: `agent_table_rows(None) → []`, and the
  `_repaint` "harness unreachable" placeholder row.
- Async smoke test is deterministic (threaded `refresh_agents` stubbed to a
  no-op; `_repaint` driven directly).
- Module-level `pytest.importorskip("textual"/"pytest_asyncio")` raises
  `pytest.skip.Exception` → clean module SKIP (not a collection ERROR) where the
  TUI stack is absent — correct skip-vs-error behavior (the #12747 lesson).
- `Static.render()` safe on an unmounted widget; `project_name()` `parents[2]`
  is the repo root with a `SquidSquad` fallback.

## Findings (both observation-level, NOT bugs) — disposition: JUSTIFIED-IGNORE
1. **[obs] idle fixture readability** — `test_idle_no_task` uses `intent=running`
   + `current_cycle=None`; the test is correct (derive_work_state → idle) but a
   reader could misread the fixture. No behavior issue.
2. **[obs] age cell not asserted across all fixtures** — only
   `test_cells_match_contract_shape` checks `age=="2m"` with a real timestamp;
   other fixtures omit `last_activity_at` (→ `"—"`, intentional graceful
   degradation). Coverage of the age cell is adequate.

No code change required. Operator verifies the live render inline (PM's plan).
Full static gate PASS (4911/0/0); 49 tests in the two TUI test files.
