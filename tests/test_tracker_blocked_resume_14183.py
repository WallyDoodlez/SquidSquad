"""#14183 -- parked (status:blocked) work has a deterministic resume trigger.

The blocker of a park is usually a DIFFERENT item (a dependency PR, a human
ticket), so its merge/close emits no event naming the parked item, and
work_queue() used to drop blocked items entirely. Resuming depended on the
parking agent's conversation context, which a respawn wipes. Now:

- a park must name its blocker (``--blocked-on``), recorded as a marker comment;
- work_queue() lists a parked item again (``resumable``) once every recorded
  blocker is closed/merged/shipped, or when the park recorded none;
- ``blocked-resumable --min-age`` backs PM pipeline-sentinel's 4h check.

All forge access is faked -- no real gh runs here.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker  # noqa: E402


class _R:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


class FakeForge:
    """Minimal GitHub stand-in: issues with labels/comments/state, driven
    through tracker's own gh wrappers."""

    def __init__(self):
        self.issues = {}

    def add(self, n, labels, state="open", title=None):
        self.issues[n] = {"number": n, "title": title or f"item {n}",
                          "labels": list(labels), "comments": [],
                          "state": state, "closed_at": None}

    def close(self, n, when="2026-09-26T10:00:00Z"):
        self.issues[n]["state"] = "closed"
        self.issues[n]["closed_at"] = when

    def _lbl(self, n):
        return [{"name": l} for l in self.issues[n]["labels"]]

    def run_list(self, cmd, check=True, **kw):
        cmd = [str(c) for c in cmd]
        if cmd[1:3] == ["issue", "list"]:
            want = [cmd[i + 1] for i, c in enumerate(cmd) if c == "--label"]
            rows = [i for i in self.issues.values() if i["state"] == "open"
                    and all(w in i["labels"] for w in want)]
            return _R(json.dumps([{"number": i["number"], "title": i["title"],
                                   "labels": self._lbl(i["number"]),
                                   "comments": [{"body": b} for b in i["comments"]]}
                                  for i in rows]))
        if cmd[1:3] == ["issue", "edit"]:
            n = int(cmd[3])
            for i, c in enumerate(cmd):
                if c == "--remove-label":
                    for l in cmd[i + 1].split(","):
                        if l in self.issues[n]["labels"]:
                            self.issues[n]["labels"].remove(l)
                if c == "--add-label":
                    self.issues[n]["labels"] += cmd[i + 1].split(",")
            return _R()
        return _R()

    def run_timeout(self, cmd, timeout, check=False):
        cmd = [str(c) for c in cmd]
        if cmd[1] == "api" and "/issues/" in cmd[2]:
            n = int(cmd[2].rsplit("/", 1)[1])
            if n not in self.issues:
                return _R("", 1, "Not Found")
            i = self.issues[n]
            return _R(json.dumps({"state": i["state"], "closed_at": i["closed_at"],
                                  "labels": self._lbl(n)}))
        return _R()

    def comment_body(self, cmd, body, check=True):
        self.issues[int(cmd[3])]["comments"].append(body)
        return _R()


@pytest.fixture
def forge(monkeypatch):
    f = FakeForge()
    monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
    monkeypatch.setattr(tracker, "_run_list", f.run_list)
    monkeypatch.setattr(tracker, "_run_list_timeout", f.run_timeout)
    monkeypatch.setattr(tracker, "_run_gh_with_body", f.comment_body)
    monkeypatch.setattr(tracker, "_get_issue_role_labels", lambda n: {"skill"})
    monkeypatch.setattr(tracker, "_check_unread_feedback", lambda n, r: [])
    monkeypatch.setattr(tracker, "_expand_issue_refs", lambda t: t)
    return f


def _queue(capsys):
    q = tracker.work_queue("skill")
    capsys.readouterr()
    return {i["number"]: i for i in q}


# ---- AC1: the park records its blocker -------------------------------------

def test_park_without_blocked_on_is_refused_before_any_write(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("no forge write before the --blocked-on check")
    monkeypatch.setattr(tracker, "_run_list", boom)
    with pytest.raises(SystemExit) as e:
        tracker.transition(1, "in-progress", "blocked", role="skill-lead")
    assert e.value.code == 2
    assert "--blocked-on" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["PR-14182", "", "14182,abc", True])
def test_malformed_blocked_on_is_refused(monkeypatch, bad):
    monkeypatch.setattr(tracker, "_run_list", lambda *a, **k: pytest.fail("write"))
    with pytest.raises(SystemExit) as e:
        tracker.transition(1, "in-progress", "blocked", role="skill-lead",
                           blocked_on=bad)
    assert e.value.code == 2


def test_blocked_on_arg_forms():
    assert tracker._parse_blocked_on_arg("14182") == [14182]
    assert tracker._parse_blocked_on_arg("#14182, #14190") == [14182, 14190]
    assert tracker._parse_blocked_on_arg(None) is None


def test_park_posts_machine_readable_marker(forge):
    forge.add(10, ["role:skill", "status:in-progress", "type:issue"])
    tracker.transition(10, "in-progress", "blocked", role="skill-lead",
                       blocked_on="#20,21")
    assert "status:blocked" in forge.issues[10]["labels"]
    assert tracker._latest_blocked_on(forge.issues[10]["comments"]) == [20, 21]


def test_quoted_marker_is_ignored():
    # Review F4: a quote-reply keeps the marker text behind "> ".
    assert tracker._latest_blocked_on([
        "**skill-lead**: Parked\n<!-- squidsquad:blocked-on 5 -->",
        "> **skill-lead**: Parked\n> <!-- squidsquad:blocked-on 99 -->\nok"]) == [5]


def test_marker_post_failure_exits_loudly_not_traceback(forge, capsys):
    # Review F2: the label already moved; a failed marker post must be a clean
    # non-zero exit that says how to recover, never an unhandled traceback.
    import subprocess as sp
    forge.add(11, ["role:skill", "status:in-progress", "type:issue"])

    def fail(cmd, body, check=True):
        raise sp.CalledProcessError(1, cmd, stderr="rate limited")

    tracker._run_gh_with_body = fail  # restored by the forge fixture's monkeypatch
    with pytest.raises(SystemExit) as e:
        tracker.transition(11, "in-progress", "blocked", role="skill-lead",
                           blocked_on="20")
    assert e.value.code == 1
    assert "marker was not posted" in capsys.readouterr().err
    assert "status:blocked" in forge.issues[11]["labels"]


def test_at_query_cap_blocked_items_are_still_checked(forge, capsys, monkeypatch):
    # Review F5: a blocked item outside the first 100 open items still surfaces.
    for n in range(1000, 1100):
        forge.add(n, ["role:skill", "status:approved", "type:task"])
    forge.add(5000, ["role:skill", "status:blocked", "type:issue"])
    real = forge.run_list

    def capped(cmd, check=True, **kw):
        res = real(cmd, check=check, **kw)
        if "status:blocked" not in [str(c) for c in cmd]:
            rows = [r for r in json.loads(res.stdout) if r["number"] != 5000][:100]
            return _R(json.dumps(rows))
        return res

    monkeypatch.setattr(tracker, "_run_list", capped)
    assert _queue(capsys)[5000]["resumable"] is True


def test_latest_marker_wins_and_absent_is_none():
    assert tracker._latest_blocked_on(["plain text"]) is None
    assert tracker._latest_blocked_on([
        "<!-- squidsquad:blocked-on 5 -->", "x",
        "<!-- squidsquad:blocked-on 6,7 -->"]) == [6, 7]


# ---- AC2: a resolved blocker resurfaces the parked item ---------------------

def test_park_resolve_respawn_sees_item_actionable(forge, capsys):
    """Park A on B; resolve B; a fresh work_queue() (all a respawned agent
    has -- no conversation memory) lists A as resumable."""
    forge.add(100, ["role:skill", "status:in-progress", "type:issue"])  # A
    forge.add(200, ["role:dm", "status:pending-ship", "type:issue"])    # B
    tracker.transition(100, "in-progress", "blocked", role="skill-lead",
                       blocked_on="200")
    assert 100 not in _queue(capsys)          # B still open -> stays parked
    forge.close(200)                           # B merges/ships
    q = _queue(capsys)                         # simulated respawn
    assert q[100]["status"] == "blocked" and q[100]["resumable"] is True
    assert q[100]["blocked_on"] == [200]
    # and resuming is the ordinary assignee transition
    tracker.transition(100, "blocked", "in-progress", role="skill-lead")
    assert "status:in-progress" in forge.issues[100]["labels"]


def test_resumable_ranks_after_in_progress_before_new_work(forge, capsys):
    forge.add(1, ["role:skill", "status:approved", "type:issue", "severity:high"])
    forge.add(2, ["role:skill", "status:in-progress", "type:issue"])
    forge.add(3, ["role:skill", "status:blocked", "type:issue"])
    forge.issues[3]["comments"].append("<!-- squidsquad:blocked-on 9 -->")
    forge.add(9, [], state="closed")
    order = [i["number"] for i in tracker.work_queue("skill")]
    capsys.readouterr()
    assert order == [2, 3, 1]


def test_all_blockers_must_resolve(forge, capsys):
    forge.add(3, ["role:skill", "status:blocked", "type:issue"])
    forge.issues[3]["comments"].append("<!-- squidsquad:blocked-on 8,9 -->")
    forge.add(8, [], state="closed")
    forge.add(9, ["status:pending-test"])
    assert 3 not in _queue(capsys)
    forge.issues[9]["labels"] = ["status:shipped"]   # shipped counts too
    assert _queue(capsys)[3]["resumable"] is True


def test_unrecorded_park_resurfaces_rather_than_strands(forge, capsys):
    forge.add(4, ["role:skill", "status:blocked", "type:issue"])
    q = _queue(capsys)
    assert q[4]["resumable"] is True and q[4]["blocker_unrecorded"] is True


def test_blocker_lookup_failure_keeps_item_parked(forge, capsys):
    forge.add(5, ["role:skill", "status:blocked", "type:issue"])
    forge.issues[5]["comments"].append("<!-- squidsquad:blocked-on 404 -->")
    assert 5 not in _queue(capsys)


# ---- AC3: pipeline-sentinel's stranded-park view -----------------------------

def test_blocked_resumable_min_age(forge, capsys):
    now = datetime.now(timezone.utc)
    old = (now - timedelta(minutes=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for n, blocker, when in ((6, 60, old), (7, 70, new)):
        forge.add(n, ["role:skill", "status:blocked", "type:issue"])
        forge.issues[n]["comments"].append(f"<!-- squidsquad:blocked-on {blocker} -->")
        forge.add(blocker, [])
        forge.close(blocker, when)
    forge.add(8, ["role:qa", "status:blocked", "type:task"])   # unrecorded, other role
    hits = tracker.blocked_resumable(min_age_minutes=90)
    capsys.readouterr()
    assert {h["number"] for h in hits} == {6, 8}
    assert {h["role"] for h in hits} == {"skill", "qa"}


def test_cli_flags_registered():
    assert "blocked-on" in tracker.KNOWN_FLAGS["transition"]
    assert tracker.KNOWN_FLAGS["blocked-resumable"] == {"role", "min-age"}


# ---- AC4: docs match the mechanism -------------------------------------------

def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_soul_names_the_real_resume_mechanism():
    soul = _read("references/roles/SOUL.md")
    assert "a forge event surfaces the change" not in soul
    assert "--blocked-on" in soul and "resumable" in soul


def test_case_d_park_step_requires_blocked_on():
    emc = _read("references/sub-skills/common-events/event-mode-contract.md")
    case_d = emc[emc.index("### Case D"):emc.index("### Case E")]
    assert "--blocked-on" in case_d


def test_sentinel_checks_stranded_parks():
    s = _read("references/sub-skills/roles/pm/pipeline-sentinel.md")
    assert "tracker.py blocked-resumable --min-age 90" in s
    assert "work-assign" in s[s.index("**4h."):]
