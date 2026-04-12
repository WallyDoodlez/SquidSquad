"""E2E Test: Feature through full status flow.

Creates a fake feature issue, transitions it through every status,
verifies labels at each step, then tears down.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import (
    create_test_issue, edit_test_issue, get_issue_labels,
    get_issue_state, cleanup_all, verify_clean, _run,
)


class TestFeatureStatusFlow(unittest.TestCase):
    """E2E: fake feature through pending → planning → approved → in-progress
    → pending-test → pending-ship → shipped (closed)."""

    issue_number = None

    @classmethod
    def setUpClass(cls):
        """Create the test feature issue."""
        cls.issue_number = create_test_issue(
            title="E2E status flow test feature",
            labels="type:task,priority:low,role:skill,status:pending",
            body="Auto-created by E2E test. Will be cleaned up.",
        )
        assert cls.issue_number > 0, "Failed to create test issue"

    @classmethod
    def tearDownClass(cls):
        """Clean up all test artifacts."""
        cleanup_all()
        problems = verify_clean()
        if problems:
            print(f"WARNING: Cleanup incomplete: {problems}", file=sys.stderr)

    def _assert_has_label(self, label: str):
        labels = get_issue_labels(self.issue_number)
        self.assertIn(label, labels, f"Expected label '{label}' on issue #{self.issue_number}, got: {labels}")

    def _assert_no_label(self, label: str):
        labels = get_issue_labels(self.issue_number)
        self.assertNotIn(label, labels, f"Label '{label}' should not be on issue #{self.issue_number}")

    def test_01_initial_state(self):
        """Issue starts with status:pending."""
        self._assert_has_label("status:pending")
        self._assert_has_label("type:task")
        self.assertEqual(get_issue_state(self.issue_number), "OPEN")

    def test_02_pending_to_planning(self):
        """Transition: pending → planning."""
        edit_test_issue(self.issue_number,
                        remove_label="status:pending",
                        add_label="status:planning")
        self._assert_has_label("status:planning")
        self._assert_no_label("status:pending")

    def test_03_planning_to_approved(self):
        """Transition: planning → approved."""
        edit_test_issue(self.issue_number,
                        remove_label="status:planning",
                        add_label="status:approved")
        self._assert_has_label("status:approved")
        self._assert_no_label("status:planning")

    def test_04_approved_to_in_progress(self):
        """Transition: approved → in-progress."""
        edit_test_issue(self.issue_number,
                        remove_label="status:approved",
                        add_label="status:in-progress")
        self._assert_has_label("status:in-progress")
        self._assert_no_label("status:approved")

    def test_05_in_progress_to_pending_test(self):
        """Transition: in-progress → pending-test."""
        edit_test_issue(self.issue_number,
                        remove_label="status:in-progress",
                        add_label="status:pending-test")
        self._assert_has_label("status:pending-test")
        self._assert_no_label("status:in-progress")

    def test_06_pending_test_to_pending_ship(self):
        """Transition: pending-test → pending-ship."""
        edit_test_issue(self.issue_number,
                        remove_label="status:pending-test",
                        add_label="status:pending-ship")
        self._assert_has_label("status:pending-ship")
        self._assert_no_label("status:pending-test")

    def test_07_pending_ship_to_shipped_and_closed(self):
        """Transition: pending-ship → shipped + close."""
        edit_test_issue(self.issue_number,
                        remove_label="status:pending-ship",
                        add_label="status:shipped")
        _run(f"gh issue close {self.issue_number}")
        self._assert_has_label("status:shipped")
        self._assert_no_label("status:pending-ship")
        self.assertEqual(get_issue_state(self.issue_number), "CLOSED")

    def test_08_no_stale_labels(self):
        """Final state should only have shipped + type + priority + role + test labels."""
        labels = get_issue_labels(self.issue_number)
        status_labels = [l for l in labels if l.startswith("status:")]
        self.assertEqual(status_labels, ["status:shipped"],
                         f"Expected only status:shipped, got: {status_labels}")


class TestBugStatusFlow(unittest.TestCase):
    """E2E: fake bug through open → pending-test → pending-ship → shipped."""

    issue_number = None

    @classmethod
    def setUpClass(cls):
        cls.issue_number = create_test_issue(
            title="E2E bug status flow test",
            labels="type:issue,priority:low,role:skill,status:open",
            body="Auto-created by E2E test.",
        )
        assert cls.issue_number > 0

    @classmethod
    def tearDownClass(cls):
        cleanup_all()

    def test_01_initial_state(self):
        self._assert_has_label("status:open")

    def _assert_has_label(self, label):
        labels = get_issue_labels(self.issue_number)
        self.assertIn(label, labels)

    def _assert_no_label(self, label):
        labels = get_issue_labels(self.issue_number)
        self.assertNotIn(label, labels)

    def test_02_open_to_pending_test(self):
        edit_test_issue(self.issue_number,
                        remove_label="status:open",
                        add_label="status:pending-test")
        self._assert_has_label("status:pending-test")
        self._assert_no_label("status:open")

    def test_03_pending_test_to_pending_ship(self):
        edit_test_issue(self.issue_number,
                        remove_label="status:pending-test",
                        add_label="status:pending-ship")
        self._assert_has_label("status:pending-ship")
        self._assert_no_label("status:pending-test")

    def test_04_shipped_and_closed(self):
        edit_test_issue(self.issue_number,
                        remove_label="status:pending-ship",
                        add_label="status:shipped")
        _run(f"gh issue close {self.issue_number}")
        self._assert_has_label("status:shipped")
        self.assertEqual(get_issue_state(self.issue_number), "CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
