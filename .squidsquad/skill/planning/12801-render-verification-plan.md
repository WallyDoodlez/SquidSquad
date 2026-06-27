[#12801 render-verification — APPROACH SETTLED + OPERATOR-APPROVED, 2026-06-27]

**Operator delegated the call ("I'll rely on your autonomy") after the pyte option was explained.** Decision: automate the TUI render-check with **Textual's built-in `App.run_test()` + Pilot API** — NOT raw pyte/PTY. Verified: textual 8.2.7 (already installed fleet-wide) exposes run_test + textual.pilot → drives the app headless and lets tests assert on rendered content with **ZERO new dependency**. pyte/PTY not needed (and finicky on Windows). [[decision-tui-headless-render-verification]]

**This removes the manual operator render-check gate** that has parked every UI story (Story 3 action bar, Pipeline/Activity panels, Story 4 wake) since 2026-06-21.

**Execution (next focused cycle — front-loaded so it's mechanical):**
1. `git switch squidsquad/task/12801`; **merge origin/main FIRST** (~154 behind — conflict-resolve via merge per always-merge rule; the branch only adds references/tui/* so main's churn shouldn't overlap).
2. Add `tests/test_tui_render_*.py`: `async with app.run_test() as pilot:` with `harness_client` mocked (no live harness) → assert title bar text (`🦑 SquidSquad · <project>`) + Agents panel renders one row per agent + refresh tick doesn't error.
3. Wire into the static gate so render self-verifies; then proceed to the gated stories (S3 action bar, panels, S4 wake) each with its own pilot test.

**Sequenced (not done inline) for cause:** 154-commit stale-branch merge + new async test infra on a high-pri task at the tail of a 9-ship session = the recursive-awareness risk to avoid. Approach is settled + de-risked; build is the next focused cycle's first task.
