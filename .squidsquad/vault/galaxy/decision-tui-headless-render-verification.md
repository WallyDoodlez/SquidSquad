---
type: decision
tags: [tui, testing, textual, 12801]
created: 2026-06-27
updated: 2026-06-27
owner: skill-lead
status: active
confidence: high
source: operator-approval
links: []
---

# TUI render-verification = Textual's built-in run_test()/Pilot (no new dep); operator-approved

## Decision

The Harness TUI (#12801) render-check — previously a manual, operator-eyeball gate
that parked every UI story — will be **automated** using **Textual's built-in
headless test harness** (`App.run_test()` + the `Pilot` API), NOT a raw
`pyte`/PTY harness.

- **Operator approval (2026-06-27, inline):** operator delegated the call —
  "I'll rely on your autonomy" — after the pyte option was explained. This blesses
  adopting a headless render-verification approach for the TUI.
- **Tool choice:** `textual==8.2.7` (already installed fleet-wide per #12801 S1.4)
  exposes `App.run_test()` and `textual.pilot` — verified available. This drives the
  app in a headless driver and lets tests query widgets / read rendered content with
  **zero new dependency**. `pyte` and raw PTY plumbing are NOT needed (and PTYs are
  finicky on Windows) — the built-in harness supersedes the earlier pyte idea.
- `pytest-textual-snapshot` (optional SVG-snapshot add-on) is NOT installed and is
  NOT required; structural assertions via Pilot are sufficient for the render gate.

## How to apply (next focused cycle — #12801)

1. Switch to `squidsquad/task/12801`, **merge `origin/main` first** (it is ~154
   behind — do this before any work).
2. Add an async test: `async with app.run_test() as pilot:` → mock
   `harness_client` so it doesn't need a live harness → assert the title bar text
   and that the Agents panel renders a row per agent.
3. Wire it into the static gate so the render self-verifies — this removes the
   manual operator render-check gate that blocked Story 3 (action bar), the
   Pipeline/Activity panels, and Story 4 (wake button).

## Why sequenced, not done inline

Settled + de-risked at decision time; the build (154-commit branch merge + new
async test infra on a high-priority task) is careful work deliberately sequenced to
a fresh focused cycle rather than rushed at the tail of a long session
(recursive-awareness). This note is the durable record so the next cycle executes
the decided approach without re-litigating it.
