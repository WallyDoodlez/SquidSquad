"""#14147 -- the verifier's pending-test scans are role-agnostic.

verification.md Step 5 and verification-issue-flow.md scanned
`list-tasks skill` / `list-issues skill`, hardcoding the `skill` alias. A
pending-test item owned by pm, dm or another worker alias was never picked up
by the documented scan. Both now use `list-by-labels
type:<kind>,status:pending-test`, with no `role:*` filter.
"""

import re
import sys
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
VERIFIER = REPO / "references" / "sub-skills" / "roles" / "verifier"
sys.path.insert(0, str(REPO / "references" / "scripts"))

import tracker  # noqa: E402

TASK_SCAN = "python references/scripts/tracker.py list-by-labels type:task,status:pending-test"
ISSUE_SCAN = "python references/scripts/tracker.py list-by-labels type:issue,status:pending-test"


def test_task_scan_is_role_agnostic():
    text = (VERIFIER / "verification.md").read_text(encoding="utf-8")
    assert TASK_SCAN in text


def test_issue_scan_is_role_agnostic():
    text = (VERIFIER / "verification-issue-flow.md").read_text(encoding="utf-8")
    assert ISSUE_SCAN in text


def test_no_verifier_scan_hardcodes_an_alias():
    for md in VERIFIER.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        hits = re.findall(r"tracker\.py list-(?:tasks|issues) \w+ --status pending-test", text)
        assert not hits, f"{md}: {hits}"


def test_list_by_labels_ands_both_labels_without_role():
    """The scan passes exactly the type + status labels to the forge, so
    items of every role:* match."""
    adapter = mock.Mock()
    adapter.list_issues.return_value = [
        {"number": 1, "labels": [{"name": "role:pm"}]},
        {"number": 2, "labels": [{"name": "role:dm"}]},
    ]
    with mock.patch("tracker._get_forge_adapter", return_value=adapter), \
         mock.patch("builtins.print"):
        got = tracker.list_by_labels("type:task,status:pending-test")
    labels = adapter.list_issues.call_args.kwargs["labels"]
    assert labels == ["type:task", "status:pending-test"]
    assert not any(label.startswith("role:") for label in labels)
    assert [i["number"] for i in got] == [1, 2]
