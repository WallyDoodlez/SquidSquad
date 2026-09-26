"""#14124 / #14125 -- every `tracker.py transition` an agent instruction tells an
agent to run must be one the tracker accepts.

Both issues were the same defect: a sub-skill prescribed a transition that
tracker.py rejects (#14124: DM `pending-ship -> pending-test`, not a legal
edge; #14125: PM `in-progress -> approved`, an assignee-only edge), so the
documented recovery path could never execute. This gate scans the instruction
sources under `references/` for literal transition commands and checks each
against LEGAL_TRANSITIONS and ROLE_AUTHORITY.

Limit: `_assignee` authority depends on the issue's role:* label, which a
static scan cannot know, so a literal role on an `_assignee` edge passes.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import tracker  # noqa: E402

CMD = re.compile(
    r"tracker\.py transition \S+ (?P<frm>[a-z-]+) (?P<to>[a-z-]+) --role (?P<role>[^\s`\"']+)")
PLACEHOLDER = re.compile(r"[\[<]")


def _documented_transitions():
    found = []
    for path in sorted((REPO / "references").rglob("*.md")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in CMD.finditer(line):
                found.append((f"{path.relative_to(REPO).as_posix()}:{n}",
                              m["frm"], m["to"], m["role"]))
    return found


DOCUMENTED = _documented_transitions()


def test_scan_finds_the_known_commands():
    # Guards the regex: a silent zero-match scan would pass everything.
    assert len(DOCUMENTED) >= 20
    assert any(loc.startswith("references/sub-skills/roles/dm/delivery-packaging.md")
               for loc, *_ in DOCUMENTED)


@pytest.mark.parametrize("loc,frm,to,role", DOCUMENTED, ids=[d[0] for d in DOCUMENTED])
def test_documented_transition_is_executable(loc, frm, to, role):
    src, dst = f"status:{frm}", f"status:{to}"
    assert dst in tracker.LEGAL_TRANSITIONS.get(src, set()), (
        f"{loc}: {frm} -> {to} is not a legal transition")
    auth = tracker.ROLE_AUTHORITY.get((src, dst))
    assert auth, f"{loc}: {frm} -> {to} has no authority mapping"
    if PLACEHOLDER.search(role) or "_assignee" in auth:
        return
    canon = tracker._canonicalize_role(role)
    assert canon in auth, (
        f"{loc}: --role {role} ({canon}) may not perform {frm} -> {to} "
        f"(allowed: {sorted(auth)})")


def test_14124_dm_citation_route_back_uses_legal_edge():
    text = (REPO / "references/sub-skills/roles/dm/delivery-packaging.md").read_text(encoding="utf-8")
    assert "transition [NUMBER] pending-ship pending-test" not in text
    assert "transition [NUMBER] pending-ship in-progress --role dm-lead" in text
    # The route-back wakes the worker, so its comment must address the worker...
    cite = [l for l in text.splitlines() if "PR does not cite the planning contract" in l]
    assert len(cite) == 1 and "worker: cite the planning artifacts" in cite[0]
    assert "verifier: confirm AC walk" not in text
    # ...and the stacked-PR route-back (same transition) keeps its own remedy.
    stacked = [l for l in text.splitlines() if "is stacked on" in l and "--message" in l]
    assert len(stacked) == 1 and "retarget the PR base" in stacked[0]


def test_14125_pm_may_return_stalled_task_to_approved(monkeypatch):
    # The task belongs to the stalled agent's role, not PM; never query the forge.
    monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda number: {"skill"})
    ok, reason = tracker._check_authority(1, "status:in-progress", "status:approved", "pm-lead")
    assert ok, reason
    # the assignee keeps the edge too (its own re-plan path)
    assert "_assignee" in tracker.ROLE_AUTHORITY[("status:in-progress", "status:approved")]
