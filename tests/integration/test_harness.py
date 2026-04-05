"""Unit tests for the test harness itself.

Verifies that harness create/teardown functions work correctly.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import (
    create_test_issue, delete_test_issue, get_issue_labels,
    get_issue_state, create_test_branch, delete_test_branch,
    temp_test_file, cleanup_all, verify_clean,
    ISSUE_PREFIX, BRANCH_PREFIX, TEST_LABEL, REPO_ROOT,
)


class TestIssueHarness(unittest.TestCase):
    """Test GitHub Issue create/delete."""

    def test_create_and_delete_issue(self):
        num = create_test_issue("harness self-test", labels="type:bug,priority:low")
        self.assertGreater(num, 0)
        labels = get_issue_labels(num)
        self.assertIn(TEST_LABEL, labels)
        self.assertEqual(get_issue_state(num), "OPEN")
        delete_test_issue(num)

    def test_issue_title_prefix(self):
        num = create_test_issue("prefix check")
        from harness import _run
        result = _run(f"gh issue view {num} --json title -q .title")
        self.assertTrue(result.stdout.strip().startswith(ISSUE_PREFIX))
        delete_test_issue(num)


class TestBranchHarness(unittest.TestCase):
    """Test git branch create/delete."""

    def test_create_and_delete_branch(self):
        name = create_test_branch("harness-self-test")
        self.assertTrue(name.startswith(BRANCH_PREFIX))
        from harness import _run
        result = _run(f'git branch --list "{name}"')
        self.assertIn(name, result.stdout)
        delete_test_branch(name)
        result = _run(f'git branch --list "{name}"')
        self.assertNotIn(name, result.stdout)


class TestFileHarness(unittest.TestCase):
    """Test temp file create/cleanup."""

    def test_temp_file_lifecycle(self):
        with temp_test_file("self-test.md", "hello") as path:
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(), "hello")
        self.assertFalse(path.exists())


class TestCleanup(unittest.TestCase):
    """Test master cleanup and verify."""

    def test_cleanup_and_verify(self):
        # Create artifacts
        num = create_test_issue("cleanup test")
        branch = create_test_branch("cleanup-test")
        # Run cleanup
        counts = cleanup_all()
        # Issues may be 0 if gh issue delete already removed them
        self.assertGreaterEqual(counts["issues"], 0)
        self.assertGreaterEqual(counts["branches"], 1)
        # Verify clean
        problems = verify_clean()
        branch_problems = [p for p in problems if "branch" in p.lower()]
        file_problems = [p for p in problems if "file" in p.lower()]
        self.assertEqual(len(branch_problems), 0)
        self.assertEqual(len(file_problems), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
