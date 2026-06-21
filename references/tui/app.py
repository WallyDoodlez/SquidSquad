"""SquidSquad Harness TUI (#12801, Story 1.3) — minimal launchable app.

A separate Textual process (the #8704 model — NOT in-process in harness.py)
that polls the harness HTTP surface via ``harness_client`` and renders the live
**Agents** panel. Story 1.3 scope: title-bar branding + refresh loop + the
Agents panel from the data layer. Needs-You / Pipeline / Activity panels and the
action bar (Reboot/Force/Wake) land in later stories.

Launch:
    python references/tui/app.py                       # harness at 127.0.0.1:7373
    python references/tui/app.py --url http://HOST:PORT

Contract: .squidsquad/pm/planning/TUI-INTERFACE-DESIGN.md (operator-approved).
"""

import argparse
import sys
import time
from pathlib import Path

# harness_client lives next to this file — importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_client as hc  # noqa: E402

from textual import work  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Container  # noqa: E402
from textual.widgets import DataTable, Static  # noqa: E402

DEFAULT_URL = "http://127.0.0.1:7373"
REFRESH_SECONDS = 2.0
_AGENT_COLUMNS = ("Role", "State", "Task", "Age", "Lag")


def project_name():
    """Best-effort team/project name for the title bar — the repo directory
    name, so an operator running one TUI per team can tell the windows apart
    (contract §Branding). Falls back to ``SquidSquad`` if the path is unusual."""
    try:
        return Path(__file__).resolve().parents[2].name
    except IndexError:
        return "SquidSquad"


def title_text(project):
    """The branded title-bar string (contract: ``🦑 SquidSquad · <project>``)."""
    return f"🦑 SquidSquad · {project}"


class HarnessTUI(App):
    """Operator console — the Agents panel polling the harness over HTTP."""

    CSS = """
    #titlebar { dock: top; height: 1; content-align: left middle; background: $boost; }
    #agents-panel { border: round $primary; height: 1fr; }
    """

    def __init__(self, base_url=DEFAULT_URL, project=None, **kwargs):
        super().__init__(**kwargs)
        self._base_url = base_url
        self._project = project or project_name()

    def compose(self) -> ComposeResult:
        yield Static(title_text(self._project), id="titlebar")
        table = DataTable(id="agents", cursor_type="row", zebra_stripes=True)
        yield Container(table, id="agents-panel")

    def on_mount(self) -> None:
        table = self.query_one("#agents", DataTable)
        table.add_columns(*_AGENT_COLUMNS)
        self.query_one("#agents-panel").border_title = "Agents"
        self.refresh_agents()
        self.set_interval(REFRESH_SECONDS, self.refresh_agents)

    @work(exclusive=True, thread=True)
    def refresh_agents(self) -> None:
        """Poll ``/status`` off the UI thread (blocking ``urllib``), then repaint
        on the main thread. ``exclusive`` drops an in-flight poll if a new tick
        fires, so a slow/unreachable harness never stacks workers."""
        status = hc.fetch_status(self._base_url)
        rows = hc.agent_table_rows(status, time.time())
        self.call_from_thread(self._repaint, rows, status is not None)

    def _repaint(self, rows, reachable) -> None:
        table = self.query_one("#agents", DataTable)
        table.clear()
        if not reachable:
            table.add_row("—", "[red]harness unreachable[/]", "—", "—", "")
            return
        for row in rows:
            table.add_row(*row)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="SquidSquad Harness TUI (#12801)")
    parser.add_argument(
        "--url", default=DEFAULT_URL,
        help=f"harness base URL (default: {DEFAULT_URL})",
    )
    args = parser.parse_args(argv)
    HarnessTUI(base_url=args.url).run()


if __name__ == "__main__":
    main()
