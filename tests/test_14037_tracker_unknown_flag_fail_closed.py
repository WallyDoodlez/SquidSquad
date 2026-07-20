"""#14037 -- tracker.py CLI fails closed on unknown/typoed flags.

The opts parser collects ANY --key and each command reads only the keys it
knows, so a typoed optional flag was silently swallowed -- exit 0, data
vanished (live: `create-issue --label improvement-scan` instead of
--extra-label filed #14024/#14025 WITHOUT the label). Now: any flag outside
the command's KNOWN_FLAGS entry exits 2 naming the flag and the valid set.
Unknown COMMANDS still route to the dispatcher's own error, and every
documented flag stays accepted (pinned against the dispatcher's actual
opts reads).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TRACKER = REPO / "references" / "scripts" / "tracker.py"
sys.path.insert(0, str(REPO / "references" / "scripts"))

import tracker  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(TRACKER), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )


class TestUnknownFlagFailsClosed:
    def test_bogus_flag_on_list_tasks_exits_2(self):
        """The live re-verification shape from the issue body -- previously
        exit 0 with a normal listing."""
        proc = run_cli("list-tasks", "skill", "--status", "approved",
                       "--bogus-flag", "xyz")
        assert proc.returncode == 2
        assert "--bogus-flag" in proc.stderr
        assert "list-tasks" in proc.stderr
        assert "--status" in proc.stderr  # names the valid set

    def test_the_live_hit_label_on_create_issue_exits_2(self):
        """The flag typo that filed #14024/#14025 unlabeled."""
        proc = run_cli("create-issue", "--title", "t", "--body", "b",
                       "--role", "skill", "--severity", "low",
                       "--label", "improvement-scan")
        assert proc.returncode == 2
        assert "--label" in proc.stderr
        assert "--extra-label" in proc.stderr  # points at the real flag

    def test_flagless_command_says_so(self):
        proc = run_cli("get-state", "123", "--role", "skill")
        assert proc.returncode == 2
        assert "takes no flags" in proc.stderr

    def test_multiple_unknown_flags_all_named(self):
        proc = run_cli("work-queue", "skill", "--foo", "1", "--bar", "2")
        assert proc.returncode == 2
        assert "--foo" in proc.stderr and "--bar" in proc.stderr

    def test_unknown_command_still_dispatcher_error(self):
        """Unknown commands bypass flag validation -- the dispatcher's own
        error (exit 1) owns them, unchanged."""
        proc = run_cli("frobnicate", "--whatever", "x")
        assert proc.returncode == 1
        assert "Unknown command" in proc.stderr


class TestKnownFlagsTableComplete:
    def test_every_dispatched_opts_read_is_in_the_table(self):
        """Pin the table against main()'s actual opts consumption: every
        opts["k"] / opts.get("k") / `"k" in opts` key in the dispatcher must
        appear in that command's KNOWN_FLAGS -- a new flag added to a command
        without a table update would fail closed at the CLI, which this test
        surfaces at commit time instead."""
        src = (REPO / "references" / "scripts" / "tracker.py").read_text(
            encoding="utf-8")
        main_src = src[src.index("def main():"):]
        used = set(re.findall(
            r'opts(?:\[|\.get\()"([a-z-]+)"', main_src))
        used |= set(re.findall(r'"([a-z-]+)" (?:not )?in opts', main_src))
        tabled = set().union(*tracker.KNOWN_FLAGS.values())
        missing = used - tabled
        assert not missing, f"dispatcher reads flags absent from KNOWN_FLAGS: {missing}"

    def test_every_command_in_dispatcher_is_tabled(self):
        src = (REPO / "references" / "scripts" / "tracker.py").read_text(
            encoding="utf-8")
        main_src = src[src.index("def main():"):]
        cmds = set(re.findall(r'cmd == "([a-z-]+)"', main_src))
        for m in re.finditer(r'cmd in \(([^)]+)\)', main_src):
            cmds |= set(re.findall(r'"([a-z-]+)"', m.group(1)))
        missing = cmds - set(tracker.KNOWN_FLAGS)
        assert not missing, f"dispatched commands absent from KNOWN_FLAGS: {missing}"


class TestDocumentedFlagsStillAccepted:
    """Validation must never reject a documented flag -- exercised through
    _validate_flags directly (no live gh calls)."""

    @pytest.mark.parametrize("cmd,opts", [
        ("list-tasks", {"status": "approved"}),
        ("create-issue", {"title": "t", "body": "b", "role": "r",
                          "severity": "low", "reporter": "x",
                          "extra-label": "improvement-scan"}),
        ("create-task", {"title": "t", "body": "b", "role": "r",
                         "priority": "high", "reporter": "x",
                         "extra-label": "y"}),
        ("transition", {"role": "skill-lead", "force": True}),
        ("comment", {"role": "skill", "message": "m"}),
        ("work-assign", {"target-alias": "skill", "caller": "pm",
                         "issue": "1", "event-context": "c", "payload": "{}"}),
        ("list-by-labels", {"state": "all"}),
        ("repair-status-labels", {"apply": True, "include-unshipped": True}),
        ("check-gh", {}),
    ])
    def test_accepted(self, cmd, opts):
        tracker._validate_flags(cmd, opts)  # must not SystemExit

    def test_rejected_raises_systemexit_2(self):
        with pytest.raises(SystemExit) as e:
            tracker._validate_flags("comment", {"role": "r", "mesage": "typo"})
        assert e.value.code == 2
