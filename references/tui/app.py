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
from textual.binding import Binding  # noqa: E402
from textual.containers import Container, Horizontal  # noqa: E402
from textual.screen import ModalScreen  # noqa: E402
from textual.widgets import Button, DataTable, Footer, Label, Static  # noqa: E402

DEFAULT_URL = "http://127.0.0.1:7373"
REFRESH_SECONDS = 2.0
_AGENT_COLUMNS = ("Role", "State", "Task", "Age", "Lag")


class ConfirmReboot(ModalScreen):
    """#12801 AC5 — a distinct, confirmed force-reboot dialog. Surfaces the
    target's busy state (AC3) so an operator never force-kills a working agent by
    accident. Returns True (confirm) / False (cancel) via ``dismiss``."""

    CSS = """
    ConfirmReboot { align: center middle; }
    #confirm-box {
        width: 60; height: auto; padding: 1 2;
        border: thick $error; background: $surface;
    }
    #confirm-msg { width: 100%; content-align: left top; margin-bottom: 1; }
    #confirm-buttons { width: 100%; height: auto; align-horizontal: center; }
    #confirm-buttons Button { margin: 0 1; }
    """

    def __init__(self, message, **kwargs):
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Label(self._message, id="confirm-msg")
            with Horizontal(id="confirm-buttons"):
                yield Button("Force reboot", variant="error", id="confirm-yes")
                yield Button("Cancel", variant="primary", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def on_key(self, event) -> None:
        # Esc cancels — a force action must never be a single accidental keypress.
        if event.key == "escape":
            self.dismiss(False)


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
    """Operator console — the Agents panel polling the harness over HTTP, plus
    the bottom action bar (#12801) for reboot (per-agent / all, graceful + force)."""

    CSS = """
    #titlebar { dock: top; height: 1; content-align: left middle; background: $boost; }
    #agents-panel { border: round $primary; height: 1fr; }
    """

    # #12801 AC1/AC2/AC4/AC5 — the bottom action bar. Footer renders these as the
    # visible action list. `r`/`R` = graceful reboot (selected / all); `f` =
    # FORCE reboot the selected agent (distinct + confirmed via ConfirmReboot).
    BINDINGS = [
        Binding("r", "reboot_selected", "Reboot"),
        Binding("R", "reboot_all", "Reboot all"),
        Binding("f", "force_selected", "Force reboot"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, base_url=DEFAULT_URL, project=None, **kwargs):
        super().__init__(**kwargs)
        self._base_url = base_url
        self._project = project or project_name()
        # Per-row metadata (role + work_state) in table render order, so a
        # cursor-row index maps back to which agent + whether it is busy (AC3).
        self._rows_meta = []

    def compose(self) -> ComposeResult:
        yield Static(title_text(self._project), id="titlebar")
        table = DataTable(id="agents", cursor_type="row", zebra_stripes=True)
        yield Container(table, id="agents-panel")
        yield Footer()

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
        now = time.time()
        status = hc.fetch_status(self._base_url)
        rows = hc.agent_table_rows(status, now)
        meta = [
            {"role": r["role"], "work_state": r["work_state"]}
            for r in hc.agent_rows(status, now)
        ] if status else []
        self.call_from_thread(self._repaint, rows, meta, status is not None)

    def _repaint(self, rows, meta, reachable) -> None:
        self._rows_meta = meta
        table = self.query_one("#agents", DataTable)
        table.clear()
        if not reachable:
            table.add_row("—", "[red]harness unreachable[/]", "—", "—", "")
            return
        for row in rows:
            table.add_row(*row)

    # --- action bar dispatch (#12801) ------------------------------------

    def _selected_agent(self):
        """Return the ``{role, work_state}`` for the cursor row, or None when no
        agent is selectable (harness unreachable / empty table)."""
        if not self._rows_meta:
            return None
        table = self.query_one("#agents", DataTable)
        idx = table.cursor_row
        if idx is None or idx < 0 or idx >= len(self._rows_meta):
            return None
        return self._rows_meta[idx]

    def action_reboot_selected(self) -> None:
        agent = self._selected_agent()
        if agent is None:
            self.notify("No agent selected.", severity="warning")
            return
        # Graceful reboot is safe for a busy agent (it checkpoints + exits at the
        # next cycle boundary), so no confirm — just note the busy state (AC3).
        busy = agent["work_state"] == hc.WORK_STATE_WORKING
        note = " (busy → will reboot at next cycle boundary)" if busy else ""
        self.notify(f"Rebooting {agent['role']}{note}…")
        self._dispatch_reboot(role=agent["role"], force=False, scope="agent")

    def action_reboot_all(self) -> None:
        self.notify("Rebooting all agents (graceful)…")
        self._dispatch_reboot(role=None, force=False, scope="all")

    def action_force_selected(self) -> None:
        agent = self._selected_agent()
        if agent is None:
            self.notify("No agent selected.", severity="warning")
            return
        busy = agent["work_state"] == hc.WORK_STATE_WORKING
        state_word = "WORKING (busy)" if busy else agent["work_state"]
        msg = (
            f"Force-reboot {agent['role']}?\n\n"
            f"State: {state_word}\n"
            f"Force kills the process immediately, overriding the busy guard "
            f"(in-flight work is not checkpointed)."
        )

        def _on_confirm(confirmed) -> None:
            if confirmed:
                self.notify(f"Force-rebooting {agent['role']}…", severity="warning")
                self._dispatch_reboot(role=agent["role"], force=True, scope="agent")

        self.push_screen(ConfirmReboot(msg), _on_confirm)

    @work(thread=True)
    def _dispatch_reboot(self, role, force, scope) -> None:
        """POST the reboot off the UI thread, then report the result via notify."""
        if scope == "all":
            ok, payload = hc.restart_all(self._base_url, force=force)
            target = "all agents"
        else:
            ok, payload = hc.restart_agent(self._base_url, role, force=force)
            target = role
        self.call_from_thread(self._report_reboot, ok, payload, target)

    def _report_reboot(self, ok, payload, target) -> None:
        if ok:
            self.notify(f"Reboot requested for {target}.")
        else:
            reason = (payload or {}).get("error", "unknown error")
            self.notify(f"Reboot failed for {target}: {reason}", severity="error")


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
