"""QA independent verification for #13169 — _normalize_result_id must preserve
the hyphenated-slug ids that real comprehension specs use.

Independent angle vs skill's TestResultIdNormalization13169 (which covers Q-1,
q-2, Q-Q-1): real specs key questions on hyphen-bearing slugs like
'1-grammar-scope' and 'detection-durable-vs-oneoff' (and bare 'CQ1'). The fix
must strip ONLY the single leading 'Q-' and preserve every internal hyphen —
over-stripping would corrupt the id and reintroduce the lookup-miss #13169 fixes.
Authored by verifier (qa, comprehension-spec owner); preserved permanently.
"""
import importlib.util
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "references", "scripts")
_spec = importlib.util.spec_from_file_location(
    "rct_13169", os.path.join(SCRIPTS, "run_comprehension_test.py"))
_rct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rct)


class TestNormalizeIdRealSpecSlugs13169(unittest.TestCase):
    def setUp(self):
        self.n = _rct._normalize_result_id

    def test_judge_echo_preserves_hyphenated_slugs(self):
        # judge-echoed "Q-<slug>" -> bare slug, internal hyphens intact
        self.assertEqual(self.n("Q-CQ1"), "CQ1")
        self.assertEqual(self.n("Q-1-grammar-scope"), "1-grammar-scope")
        self.assertEqual(self.n("Q-detection-durable-vs-oneoff"),
                         "detection-durable-vs-oneoff")
        self.assertEqual(self.n("Q-3-step-heading-anchor-levels"),
                         "3-step-heading-anchor-levels")

    def test_bare_slug_ids_pass_through_untouched(self):
        for sid in ("CQ1", "1-grammar-scope", "detection-durable-vs-oneoff"):
            self.assertEqual(self.n(sid), sid)

    def test_case_and_whitespace(self):
        self.assertEqual(self.n("q-CQ2"), "CQ2")
        self.assertEqual(self.n("  Q-CQ3  "), "CQ3")


if __name__ == "__main__":
    unittest.main()
