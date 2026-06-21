"""Tests for the SquidSquad Harness TUI app (#12801 Story 1.3).

The TUI stack (textual + pytest-asyncio) is a SEPARATE-process dependency, not a
harness-runtime one — so the whole module skips cleanly where it isn't installed
(rather than ERRORing). Render fidelity is verified by the operator inline; these
tests cover the structure + data binding that CAN be asserted headlessly.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("textual")  # TUI-process dep — skip if absent
pytest.importorskip("pytest_asyncio")  # async run_test dep — skip if absent

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "tui"))

import app  # noqa: E402
import harness_client as hc  # noqa: E402


# --- pure title / project helpers (sync) -----------------------------------

class TestTitleAndProject:
    def test_title_text_format(self):
        assert app.title_text("demo-proj") == "🦑 SquidSquad · demo-proj"

    def test_project_name_is_nonempty_str(self):
        name = app.project_name()
        assert isinstance(name, str) and name

    def test_project_name_is_repo_dir(self):
        # references/tui/app.py → parents[2] is the repo root dir.
        assert app.project_name() == REPO_ROOT.name


# --- compose() structure (sync — no event loop) ----------------------------

class TestCompose:
    def test_yields_titlebar_then_agents_panel(self):
        widgets = list(app.HarnessTUI(project="demo").compose())
        ids = [w.id for w in widgets]
        assert ids == ["titlebar", "agents-panel"]

    def test_titlebar_carries_branded_text(self):
        titlebar = list(app.HarnessTUI(project="demo").compose())[0]
        assert "🦑 SquidSquad · demo" in str(titlebar.render())

    def test_stores_base_url_and_project(self):
        a = app.HarnessTUI(base_url="http://x:1", project="p")
        assert a._base_url == "http://x:1"
        assert a._project == "p"


# --- mount + repaint (async run_test; threaded refresh stubbed) -------------

@pytest.mark.asyncio
async def test_mount_and_repaint(monkeypatch):
    # Stub the threaded auto-refresh so the test drives _repaint deterministically.
    monkeypatch.setattr(app.HarnessTUI, "refresh_agents", lambda self: None)
    a = app.HarnessTUI(project="demo")
    async with a.run_test() as pilot:
        await pilot.pause()
        table = a.query_one("#agents", app.DataTable)
        # on_mount added the 5 columns and the panel border title.
        assert len(table.columns) == len(app._AGENT_COLUMNS)
        assert "demo" in str(a.query_one("#titlebar").render())

        # reachable: rows render.
        cells = hc.agent_table_rows(
            {"agents": [{"role": "skill", "status": "running",
                         "intent": "running", "current_cycle": "#1",
                         "last_activity_at": 0, "lag": 0}]},
            1000,
        )
        a._repaint(cells, True)
        await pilot.pause()
        assert table.row_count == 1

        # unreachable: a single placeholder row, not a crash.
        a._repaint([], False)
        await pilot.pause()
        assert table.row_count == 1
