"""#12801 — headless RENDER verification for the Harness TUI (app.py).

This is the automated replacement for the manual operator render-check that
parked every TUI story. It uses **Textual's built-in headless test harness**
(`App.run_test()` + Pilot) — no real terminal, no pyte/PTY, no new dependency —
to drive the actual app and assert on what it renders. Operator-approved
approach (2026-06-27); see vault `decision-tui-headless-render-verification`.

`fetch_status` is mocked so the test needs no live harness. The TUI dep
(`textual`, requirements-tui.txt) is optional at runtime, so the whole module
skips when textual is absent — it runs in environments that have it (the dep is
installed fleet-wide per #12801 S1.4).
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("textual", reason="TUI dep (requirements-tui.txt); render test skips without it")

# references/tui is importable; app.py self-bootstraps harness_client onto path.
TUI_DIR = Path(__file__).resolve().parent.parent / "references" / "tui"
sys.path.insert(0, str(TUI_DIR))

import app as tui_app  # noqa: E402


def _status_fixture(now):
    """A minimal but realistic GET /status payload: two healthy agents."""
    return {
        "harness": {"status": "running", "port": 7373},
        "agents": [
            {
                "role": "skill", "status": "running", "intent": "running",
                "bootup_complete": True, "current_cycle": "12801",
                "last_activity_at": now - 5, "lag": 0,
            },
            {
                "role": "pm", "status": "running", "intent": "running",
                "bootup_complete": True, "current_cycle": None,
                "last_activity_at": now - 12, "lag": 0,
            },
        ],
    }


async def _drive(app):
    """Run the app headless, let its threaded refresh worker finish + repaint."""
    async with app.run_test() as pilot:
        # on_mount kicks the @work(thread=True) refresh_agents; wait it out,
        # then pump the message queue so call_from_thread repaint applies.
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import DataTable, Static
        title = app.query_one("#titlebar", Static)
        table = app.query_one("#agents", DataTable)
        # Snapshot what we need BEFORE the context exits (app shuts down on exit).
        title_str = str(title.render())
        col_count = len(table.columns)
        row_count = table.row_count
        # Pull the role cell (col 0) of every row.
        roles = [
            str(table.get_row_at(i)[0]) for i in range(row_count)
        ]
        return title_str, col_count, row_count, roles


@pytest.mark.asyncio
async def test_titlebar_and_agents_panel_render(monkeypatch):
    """The exact render-check a human used to do by eye, now automated:
    the title bar shows the branded string and the Agents panel renders one
    row per agent from a mocked /status."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status",
                        lambda *a, **k: _status_fixture(now))

    app = tui_app.HarnessTUI(base_url="http://test", project="SquidSquad-2")
    title_str, col_count, row_count, roles = await _drive(app)

    # Title bar — branded contract string.
    assert "SquidSquad" in title_str
    assert "SquidSquad-2" in title_str
    # Agents panel — 5 columns (Role/State/Task/Age/Lag), one row per agent.
    assert col_count == 5
    assert row_count == 2
    assert "skill" in roles
    assert "pm" in roles


@pytest.mark.asyncio
async def test_unreachable_harness_renders_sentinel(monkeypatch):
    """When /status is unreachable (fetch_status -> None), the panel renders a
    single 'harness unreachable' sentinel row rather than crashing or going
    blank — the operator must see the down-state, not a frozen/empty table."""
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: None)

    app = tui_app.HarnessTUI(base_url="http://test", project="SquidSquad-2")
    _title, col_count, row_count, _roles = await _drive(app)

    assert col_count == 5
    assert row_count == 1  # the single sentinel row


def test_title_text_contract():
    """Pure-function guard on the branded title string (contract:
    `🦑 SquidSquad · <project>`)."""
    assert tui_app.title_text("SquidSquad-2") == "🦑 SquidSquad · SquidSquad-2"
