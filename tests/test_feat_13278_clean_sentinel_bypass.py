"""QA independent verification for #13278 — model_router's MIN_OUTPUT_LENGTH gate
must BYPASS the sanctioned clean-review sentinel (NO_FINDINGS) but STILL catch
genuine degeneracy (incl. an auth-error string, which is NOT a clean review).

Independent angle vs skill's route() tests: exercises the documented bypass
predicate (CLEAN_RESULT_SENTINELS, case-insensitive startswith) directly across
real-world variants — especially that an 'ERR 402'-style auth failure does NOT
get mistaken for a clean review (it must still fall back). Authored by verifier
(qa); preserved.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import model_router as m  # noqa: E402


def _is_clean_sentinel(out):
    """Mirror of model_router's inline gate predicate (#13278, model_router.py:817):
    a stripped response that startswith (case-insensitive) any CLEAN_RESULT_SENTINEL."""
    s = (out or "").strip()
    return any(s.upper().startswith(sn.upper()) for sn in m.CLEAN_RESULT_SENTINELS)


class TestCleanSentinelBypass13278(unittest.TestCase):
    def test_clean_sentinel_variants_bypass(self):
        for out in ("NO_FINDINGS", "no_findings", "NO_FINDINGS - all clean", "  NO_FINDINGS  "):
            self.assertTrue(_is_clean_sentinel(out), f"{out!r} must be treated as a clean review")

    def test_genuine_degeneracy_not_bypassed(self):
        # Empty / short-garbage / AUTH-ERROR must NOT be mistaken for a clean
        # review — they stay short-and-non-sentinel → still fall back (the gate's job).
        for out in ("", "error", "ERR 402", "402 Payment Required", "null"):
            self.assertFalse(_is_clean_sentinel(out),
                             f"{out!r} is degenerate/auth-error, not a clean review")

    def test_real_finding_not_a_clean_sentinel(self):
        self.assertFalse(_is_clean_sentinel("FINDINGS: bug at line 5"))

    def test_constants_present(self):
        self.assertIn("NO_FINDINGS", m.CLEAN_RESULT_SENTINELS)
        self.assertEqual(m.MIN_OUTPUT_LENGTH, 200)


if __name__ == "__main__":
    unittest.main()
