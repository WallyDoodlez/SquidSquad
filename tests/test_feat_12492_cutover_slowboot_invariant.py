"""QA independent verification for #12492 — the progress-liveness cutover must not
endanger a legitimately slow-booting agent (AC3).

Independent angle vs skill's TestProgressLivenessCutover12492 (which patches
verdicts directly): asserts the two standing INVARIANTS that keep a real slow-boot
agent (e.g. qa, >60s lifetime, #12409) safe once progress-liveness is authoritative:
  1. the cutover is actually on (_PROGRESS_LIVENESS_AUTHORITATIVE True), and
  2. BOOT_GRACE_SECONDS stays generous enough that a realistic slow boot (minutes)
     is never treated as a zombie — if someone lowered it, slow-boot agents would
     be killed mid-boot, re-introducing the #12409 reboot loop.
Authored by verifier (qa — the live AC3 case). Preserved permanently.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import harness  # noqa: E402


class TestCutoverSlowBootInvariant12492(unittest.TestCase):
    def test_cutover_is_authoritative(self):
        # The shipped default after #12492 — progress-liveness decides the reboot.
        self.assertTrue(getattr(harness, "_PROGRESS_LIVENESS_AUTHORITATIVE", False),
                        "progress-liveness must be authoritative (the #12492 cutover)")

    def test_boot_grace_protects_realistic_slow_boots(self):
        grace = getattr(harness, "BOOT_GRACE_SECONDS", 0)
        # A real slow boot (qa boots well over 60s; the #12271 incident sat ~54m).
        # The grace must comfortably exceed a normal multi-minute boot so a
        # genuinely-progressing booting agent is never a cutover-zombie.
        self.assertGreaterEqual(grace, 120,
                                "BOOT_GRACE_SECONDS too low — slow-boot agents would be "
                                "killed mid-boot once liveness is authoritative (#12409 loop)")

    def test_shadow_only_escape_hatch_exists(self):
        # An operator must be able to revert the cutover without a code change.
        src = open(os.path.join(os.path.dirname(__file__), "..", "references",
                                "scripts", "harness.py"), encoding="utf-8").read()
        self.assertIn("SQUIDSQUAD_HARNESS_PROGRESS_LIVENESS_SHADOW_ONLY", src,
                      "the cutover must keep a shadow-only escape hatch")


if __name__ == "__main__":
    unittest.main()
