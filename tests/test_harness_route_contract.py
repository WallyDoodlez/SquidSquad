"""Contract test: every harness HTTP route has a known caller (#11093).

Closes #11093 Gap from #11090. Approach A (FastAPI route introspection).

The harness HTTP surface is hand-coded at every call site with no shared
schema. Renaming a route in `harness.py` without updating callers would
silently 404 until someone notices a downstream effect. This test catches
that at static-analysis time:

- Every harness route must have a manifest entry (orphan route → test fails).
- Every manifest entry's listed callers must grep-hit the route path (orphan
  caller → test fails).
- Routes called only by operators / curl / browser are marked ``_EXTERNAL``.

Why a manifest rather than pure grep-derivation: an operator-only route has
no Python caller, so pure grep would always flag it as "orphan". The
manifest distinguishes "known external" from "should-have-a-Python-caller".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import harness  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402


# Sentinel: route is reachable only via operator/curl/browser/TUI, NOT from
# any Python module under references/scripts/. Listed routes are still
# enumerated and checked, but no caller-grep is performed.
_EXTERNAL = object()


# Manifest: (METHOD, path) → list of caller module basenames in
# references/scripts/ expected to contain a literal grep-hit of the route's
# path, OR the _EXTERNAL sentinel for operator-only routes.
#
# When adding a new route to harness.py, add a corresponding entry here.
# When deleting a route from harness.py, delete the entry here.
EXPECTED_CALLERS = {
    ("GET",  "/"):                              _EXTERNAL,
    ("GET",  "/status"):                        ["cycle_pre", "squidsquad_cli"],
    ("GET",  "/agents"):                        _EXTERNAL,
    ("GET",  "/agents/{role}"):                 ["cycle_post", "statusline_data"],
    ("GET",  "/agents/{role}/health"):          _EXTERNAL,
    ("GET",  "/agents/{role}/config"):          _EXTERNAL,
    ("POST", "/agents/all/start"):              ["squidsquad_cli"],
    ("POST", "/agents/all/stop"):               ["squidsquad_cli"],
    ("POST", "/agents/{role}/start"):           ["squidsquad_cli"],
    ("POST", "/agents/{role}/stop"):            ["squidsquad_cli"],
    ("POST", "/agents/{role}/restart"):         ["cycle_post", "squidsquad_cli"],
    ("POST", "/events"):                        ["event_bus"],
    ("GET",  "/events"):                        ["event_bus_reader", "event_poll"],
    ("GET",  "/events/for/{role}"):             ["event_poll"],
    ("GET",  "/events/cursor/{role}"):          _EXTERNAL,
    ("POST", "/events/{event_id}/complete"):    _EXTERNAL,
    ("GET",  "/events/lifecycle"):              _EXTERNAL,
    ("GET",  "/human/queue"):                   _EXTERNAL,
    ("POST", "/shutdown"):                      ["squidsquad_cli"],
    # #12825 — agent-triggerable harness restart: POSTed by an agent (PM, for
    # recovery) per the harness-restart sub-skill, or by an operator/curl. No
    # in-repo Python module caller in this slice → _EXTERNAL.
    ("POST", "/restart"):                       _EXTERNAL,
    ("POST", "/merge"):                         _EXTERNAL,
    # #12418 — SessionEnd telemetry hook: POSTed only by Claude Code's native
    # type:http hook wired in .claude/settings.json (no in-repo Python caller).
    ("POST", "/hooks/session-end"):             _EXTERNAL,
    # #12443 — activity heartbeat: POSTed by activity_hook.py (the PostToolUse/
    # PostToolUseFailure command-hook entrypoint AND the post_activity() poster
    # that cycle_post imports). activity_hook is the module that literally holds
    # the route path; cycle_post reaches it via post_activity(), not a literal.
    ("POST", "/hooks/activity"):                ["activity_hook"],
    # #12458 — pause-aware liveness hooks (Notification / PreCompact /
    # PostCompact / StopFailure): POSTed only by Claude Code's native type:http
    # hooks in settings.json (no in-repo Python caller).
    ("POST", "/hooks/pause"):                   _EXTERNAL,
}


def _discover_routes():
    """Enumerate every (METHOD, path) pair registered on harness.app."""
    routes = []
    for r in harness.app.routes:
        if not isinstance(r, APIRoute):
            continue
        for method in sorted(r.methods - {"HEAD"}):
            routes.append((method, r.path))
    return sorted(routes)


def _module_text(name: str) -> str:
    path = SCRIPTS / f"{name}.py"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _caller_has_path(caller_name: str, path: str) -> bool:
    """Return True if the caller module's source literally contains the
    FastAPI path pattern. Placeholders like ``{role}`` survive in f-string
    source (the bytes ``{role}`` are present in ``f"...{role}..."``)."""
    return path in _module_text(caller_name)


def test_every_harness_route_has_manifest_entry():
    """A new route added to harness without a manifest update is an orphan
    route — flagging it here forces the developer to declare callers (or
    explicitly mark _EXTERNAL) on the same PR that registers the route."""
    discovered = set(_discover_routes())
    declared = set(EXPECTED_CALLERS.keys())
    orphan_routes = discovered - declared
    assert not orphan_routes, (
        f"Orphan harness route(s) — no manifest entry in "
        f"tests/test_harness_route_contract.py::EXPECTED_CALLERS: "
        f"{sorted(orphan_routes)}. Add each as either a list of caller "
        f"module basenames or _EXTERNAL."
    )


def test_no_stale_manifest_entries():
    """A manifest entry without a matching harness route means the route
    was renamed/deleted but the manifest wasn't updated — that's the
    rename-silent-404 failure mode the contract is meant to prevent."""
    discovered = set(_discover_routes())
    declared = set(EXPECTED_CALLERS.keys())
    stale = declared - discovered
    assert not stale, (
        f"Stale manifest entry(ies) in "
        f"tests/test_harness_route_contract.py::EXPECTED_CALLERS — "
        f"these routes are declared but no longer registered on "
        f"harness.app.routes: {sorted(stale)}. Either restore the route "
        f"in harness.py or delete the manifest entry."
    )


@pytest.mark.parametrize(
    "method,path,callers",
    [
        (m, p, c) for (m, p), c in EXPECTED_CALLERS.items()
        if c is not _EXTERNAL
    ],
)
def test_each_route_has_at_least_one_python_caller(method, path, callers):
    """Every non-external route must be referenced literally in at least
    one of its declared caller modules. If a route is renamed in
    harness.py, this test goes red naming the orphan caller."""
    hits = [c for c in callers if _caller_has_path(c, path)]
    assert hits, (
        f"Route {method} {path} is declared in EXPECTED_CALLERS as called "
        f"by {callers}, but none of those modules under references/scripts/ "
        f"contain the literal path string {path!r}. Either the route was "
        f"renamed in harness.py (update the manifest path), or the caller "
        f"was renamed/removed (update the manifest caller list)."
    )
