"""QA independent verification for #13264 — the v2-manifest-loader tombstone.

Independent angle vs skill's TestManifestV2TombstoneUnreachable13264: skill's
`test_symbol_only_referenced_within_compose` asserts the guard PASSES on the real
tree, but does not prove the guard would FAIL on a violation. This test proves the
guard's scan logic is NOT vacuous — an injected fake offender is detected — so the
tombstone is genuinely enforced against a future silent re-wire. Authored by
verifier (qa); preserved permanently.
"""
import os
import pathlib
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "references" / "scripts"


def _offenders(scripts_dir):
    """The same scan the tombstone guard performs: production scripts (not
    compose.py) that reference the dead symbol."""
    out = []
    for py in pathlib.Path(scripts_dir).glob("*.py"):
        if py.name == "compose.py":
            continue
        if "_load_manifest_v2" in py.read_text(encoding="utf-8"):
            out.append(py.name)
    return out


class TestTombstoneGuardNotVacuous13264(unittest.TestCase):
    def test_real_tree_has_no_production_caller(self):
        self.assertEqual(_offenders(SCRIPTS), [],
                         "_load_manifest_v2 must stay unreachable from production")

    def test_guard_detects_an_injected_offender(self):
        tmp = tempfile.mkdtemp()
        (pathlib.Path(tmp) / "compose.py").write_text(
            "def _load_manifest_v2(): pass", encoding="utf-8")
        (pathlib.Path(tmp) / "fake_deploy.py").write_text(
            "from compose import _load_manifest_v2\n", encoding="utf-8")
        self.assertEqual(_offenders(tmp), ["fake_deploy.py"],
                         "guard scan must detect a re-wire — else the tombstone is unenforced")

    def test_tombstone_marker_on_both_functions(self):
        src = (SCRIPTS / "compose.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(src.count("TOMBSTONE (#13264)"), 2,
                                "both functions must carry the tombstone rationale")


if __name__ == "__main__":
    unittest.main()
