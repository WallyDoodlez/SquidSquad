"""QA independent verification for #13255 — self-emitted events excluded from
GET /events/for/{role}.

Authored by verifier (qa) from the issue ACs, independent of skill's unit tests
in test_harness.py. Adds explicit AC3 coverage (harness-emitted reacts-to event
with no target_alias must still be delivered) that skill's tests do not exercise.
Preserved permanently per the verifier preserved-tests rule.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

from fastapi.testclient import TestClient  # noqa: E402
import harness  # noqa: E402
from harness import event_stream, app  # noqa: E402


class TestSelfEmitFilter13255(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _ids_for(self, role, reacts_to):
        with patch("harness._validate_role"), \
             patch("config.get_event_filters_for_role", return_value=reacts_to):
            resp = self.client.get(f"/events/for/{role}")
        self.assertEqual(resp.status_code, 200)
        return [e["id"] for e in resp.json()["events"]]

    def test_self_emit_filter_all_acs(self):
        event_stream.append({"id": "qa_own", "event_type": "git-commit",
                             "role": "skill", "payload": {}})
        event_stream.append({"id": "qa_cross", "event_type": "git-commit",
                             "role": "qa", "payload": {}})
        event_stream.append({"id": "qa_harness", "event_type": "git-commit",
                             "role": "harness", "payload": {}})
        event_stream.append({"id": "qa_selftarget", "event_type": "git-commit",
                             "role": "skill", "payload": {"target_alias": "skill"}})
        event_stream.append({"id": "qa_noemit", "event_type": "git-commit",
                             "payload": {}})

        ids = self._ids_for("skill", ["git-commit"])

        self.assertNotIn("qa_own", ids, "AC1 self-emitted reacts-to must be excluded")
        self.assertIn("qa_cross", ids, "AC2 cross-agent reacts-to must be delivered")
        self.assertIn("qa_harness", ids, "AC3 harness-emitted (no target) must be delivered")
        self.assertIn("qa_selftarget", ids, "AC4 explicit target_alias wins over self-exclusion")
        self.assertIn("qa_noemit", ids, "AC5 missing emitter must be included")


if __name__ == "__main__":
    unittest.main()
