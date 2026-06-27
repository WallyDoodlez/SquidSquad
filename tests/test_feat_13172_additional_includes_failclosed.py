"""QA independent verification for #13172 — fail-closed on wrong-type
`additional_includes` in compose._load_manifest_v2_from_file.

Independent angle vs skill's TestManifestV2AdditionalIncludesWrongType13172:
asserts the diagnostic names the ROLE (skill checks only the field name +
'expected list') and covers an int type (skill covers str/dict). Authored by
verifier (qa); preserved permanently per the verifier preserved-tests rule.
"""
import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import yaml  # noqa: E402
import compose  # noqa: E402


class TestAdditionalIncludesFailClosed13172(unittest.TestCase):
    def _run(self, additional, role_name):
        tmp = tempfile.mkdtemp()
        p = pathlib.Path(tmp) / "includes.yml"
        p.write_text(yaml.safe_dump({"base_role": "worker",
                                     "additional_includes": additional}),
                     encoding="utf-8")
        err = io.StringIO()
        code = None
        with patch.object(compose, "_load_manifest_v2",
                          return_value=["common/boot-bootstrap"]):
            try:
                with contextlib.redirect_stderr(err):
                    compose._load_manifest_v2_from_file(p, role_name)
            except SystemExit as e:
                code = e.code
        return code, err.getvalue()

    def test_bare_string_fails_closed_and_names_role(self):
        code, err = self._run("common/cycle-runner", "worker-myrole")
        self.assertEqual(code, 1)
        self.assertIn("worker-myrole", err, "diagnostic must name the role")
        self.assertIn("expected list", err)
        self.assertIn("additional_includes", err)

    def test_int_type_fails_closed(self):
        code, _ = self._run(42, "worker-x")
        self.assertEqual(code, 1)

    def test_null_normalizes_to_empty_no_exit(self):
        code, _ = self._run(None, "worker-x")
        self.assertIsNone(code, "explicit null must normalize to [] (no exit)")


if __name__ == "__main__":
    unittest.main()
