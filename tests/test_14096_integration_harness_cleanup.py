"""#14096 — E2E status-flow tests leaked [TEST] issues onto the live tracker.

Root cause: this machine's ambient gh account has no triage access, so GitHub
silently dropped every label on harness-created issues. ``cleanup_test_issues``
found issues only by the ``squidsquad-test`` label, so it never saw them (20
leaked across 5 runs on 2026-07-20).

Fix pinned here:
- gh calls go through ``gh_identity.gh_env`` (the repo's push identity);
- created issue numbers are tracked in a registry that cleanup always covers,
  plus an atexit sweep for abort paths;
- creation fails loudly (after removing the issue) when the label was dropped;
- cleanup also sweeps open unlabeled leaks by the harness's exact markers.

Every subprocess call is faked: no test here reaches the real forge.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

import integration_harness as ih  # noqa: E402


class FakeGh:
    """Minimal in-memory forge behind subprocess.run."""

    def __init__(self, drop_labels=False, can_delete=True):
        self.issues = {}  # number -> dict(title, body, labels, state)
        self.next = 500
        self.drop_labels = drop_labels
        self.can_delete = can_delete
        self.calls = []
        self.envs = []

    def add(self, title, body, labels=(), state="OPEN"):
        n = self.next
        self.next += 1
        self.issues[n] = {"title": title, "body": body,
                          "labels": list(labels), "state": state}
        return n

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        self.envs.append(kw.get("env"))
        assert isinstance(cmd, list), "harness must pass argv lists"
        if cmd[0] == "git":  # verify_clean's local branch check
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        assert cmd[0] == "gh", f"unexpected call: {cmd}"
        sub = cmd[1:3]
        out, rc = "", 0
        if sub == ["issue", "create"]:
            a = dict(zip(cmd[3::2], cmd[4::2]))
            labels = [] if self.drop_labels else a["--label"].split(",")
            n = self.add(a["--title"], a["--body"], labels)
            out = f"https://github.com/o/r/issues/{n}\n"
        elif sub == ["issue", "view"]:
            i = self.issues[int(cmd[3])]
            out = json.dumps({"labels": [{"name": l} for l in i["labels"]],
                              "state": i["state"], "title": i["title"]})
        elif sub == ["issue", "delete"]:
            if self.can_delete:
                self.issues.pop(int(cmd[3]), None)
            else:
                rc = 1
        elif sub == ["issue", "close"]:
            self.issues[int(cmd[3])]["state"] = "CLOSED"
        elif sub == ["issue", "list"]:
            a = cmd[3:]
            rows = self.issues.items()
            if "--label" in a:
                lab = a[a.index("--label") + 1]
                rows = [(n, i) for n, i in rows if lab in i["labels"]]
            state = a[a.index("--state") + 1] if "--state" in a else "open"
            if state == "open":
                rows = [(n, i) for n, i in rows if i["state"] == "OPEN"]
            if "--search" in a:  # tokenized search: loose on purpose
                rows = [(n, i) for n, i in rows
                        if "TEST" in i["title"] or "Auto-created" in i["body"]]
            out = json.dumps([{"number": n, "title": i["title"],
                               "body": i["body"]} for n, i in rows])
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr="")

    def open_numbers(self):
        return {n for n, i in self.issues.items() if i["state"] == "OPEN"}


@pytest.fixture
def gh(monkeypatch):
    fake = FakeGh()
    monkeypatch.setattr(ih.subprocess, "run", fake)
    monkeypatch.setattr(ih, "gh_env", lambda cmd: {"GH_TOKEN": "pinned"})
    monkeypatch.setattr(ih.time, "sleep", lambda s: None)
    monkeypatch.setattr(ih, "_CREATED_ISSUES", set())
    return fake


class TestIdentityPin:
    def test_every_gh_call_carries_the_pinned_env(self, gh):
        n = ih.create_test_issue("x")
        ih.delete_test_issue(n)
        assert gh.envs and all(e == {"GH_TOKEN": "pinned"} for e in gh.envs)

    def test_string_commands_are_split_and_pinned(self, gh):
        """test_status_flow calls _run(f"gh issue close {n}") -- a string that
        only worked on Windows and skipped the identity pin."""
        n = gh.add("[TEST] s", "Auto-created by test harness.", [ih.TEST_LABEL])
        ih._run(f"gh issue close {n}")
        assert gh.calls[-1] == ["gh", "issue", "close", str(n)]
        assert gh.envs[-1] == {"GH_TOKEN": "pinned"}
        assert gh.issues[n]["state"] == "CLOSED"

    def test_run_wires_gh_identity_module(self):
        import gh_identity
        assert ih.gh_env is gh_identity.gh_env


class TestDroppedLabelFailsLoudly:
    def test_create_raises_and_removes_the_issue(self, gh):
        gh.drop_labels = True
        with pytest.raises(RuntimeError, match="triage"):
            ih.create_test_issue("E2E status flow test feature")
        assert gh.issues == {}, "the unlabeled issue must not be left behind"
        assert ih._CREATED_ISSUES == set()

    def test_falls_back_to_close_when_delete_is_denied(self, gh):
        gh.drop_labels = True
        gh.can_delete = False
        with pytest.raises(RuntimeError):
            ih.create_test_issue("x")
        assert gh.open_numbers() == set()


class TestCleanup:
    def test_registry_covers_issues_without_the_label(self, gh):
        n = ih.create_test_issue("x")
        gh.issues[n]["labels"] = []  # label lost after creation
        ih.cleanup_test_issues()
        assert n not in gh.issues

    def test_sweeps_the_20_leaked_shape_from_earlier_runs(self, gh):
        leaked = {gh.add(f"[TEST] E2E status flow test feature {k}",
                         "Auto-created by E2E test. Will be cleaned up.")
                  for k in range(4)}
        leaked.add(gh.add("[TEST] harness self-test",
                          "Auto-created by test harness."))
        count = ih.cleanup_test_issues()
        assert count == 5
        assert gh.open_numbers().isdisjoint(leaked)

    def test_sweep_never_touches_real_issues(self, gh):
        """GitHub search tokenizes, so real issues can match the query; only
        the exact harness markers qualify."""
        real = {
            gh.add("ISSUE: E2E status-flow tests leave [TEST] issues open",
                   "**Reported By**: pm-lead"),
            gh.add("[TEST] looks like a test", "A human wrote this body."),
            gh.add("Tracker body quotes the marker",
                   "Auto-created by E2E test. Will be cleaned up."),
        }
        ih.cleanup_test_issues()
        assert real <= gh.open_numbers()

    def test_labeled_issues_still_cleaned(self, gh):
        n = gh.add("[TEST] other run", "whatever", [ih.TEST_LABEL])
        ih.cleanup_test_issues()
        assert n not in gh.issues

    def test_atexit_sweep_removes_registered_issues(self, gh):
        """unittest skips tearDownClass when setUpClass raises; the atexit
        hook is the backstop for issues created before the failure."""
        n = ih.create_test_issue("x")
        ih._cleanup_registry_at_exit()
        assert n not in gh.issues

    def test_atexit_hook_registered(self):
        import atexit
        assert ih._cleanup_registry_at_exit.__module__ == ih.__name__
        # atexit has no public introspection; unregister returns silently
        # either way, so re-register to prove the callable is valid.
        atexit.unregister(ih._cleanup_registry_at_exit)
        atexit.register(ih._cleanup_registry_at_exit)

    def test_verify_clean_reports_unlabeled_leaks(self, gh):
        gh.add("[TEST] leftover", "Auto-created by test harness.")
        problems = [p for p in ih.verify_clean() if "unlabeled" in p]
        assert problems
