"""QA independent verification for #13170 — POST /merge fail-closed body guard.

Independent angle vs skill's TestMergeBodyGuard13170: (a) confirms a FULLY-VALID
dict passes BOTH guards and reaches the merge path (skill only tested a
missing-pr_number object); (b) adds empty-body + whitespace-body malformed cases
skill did not cover. Authored by verifier (qa); preserved permanently per the
verifier preserved-tests rule.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

from fastapi.testclient import TestClient  # noqa: E402
import harness  # noqa: E402
from harness import app  # noqa: E402


class TestMergeBodyGuard13170QA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_valid_dict_passes_both_guards(self):
        """AC3: a fully-valid object passes the malformed + non-object guards and
        reaches the merge path (spawns the merge thread), proving the guard does
        not reject valid input. Merge machinery mocked to avoid a real merge."""
        with patch.object(harness, "_emit_event"), \
             patch.object(harness.threading, "Thread") as T:
            T.return_value.start.return_value = None
            resp = self.client.post(
                "/merge", json={"pr_number": 999, "branch": "x", "role": "skill"})
        self.assertNotEqual(resp.status_code, 400,
                            "a valid object must not be rejected by the body guard")
        self.assertTrue(T.called, "valid object must reach the merge-thread spawn")

    def test_empty_body_400(self):
        resp = self.client.post("/merge", content=b"",
                                headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("malformed JSON body", resp.json()["detail"])

    def test_whitespace_body_400(self):
        resp = self.client.post("/merge", content=b"   ",
                                headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("malformed JSON body", resp.json()["detail"])

    def test_json_string_body_400_non_object(self):
        resp = self.client.post("/merge", content=b'"a string"',
                                headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("must be a JSON object", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
