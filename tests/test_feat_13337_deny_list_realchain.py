"""QA independent real-chain tests for #13337 (TEST-PLAN-13337 TC-2..TC-7, TC-9).

Verifier-owned, derived from the issue ACs — NOT from the worker's tests.
Deliberately exercises the REAL CLI boundary: every probe runs
`python references/scripts/wizard.py merge-deny-list ...` as a subprocess
against a real temp project dir with a real .claude/settings.json, and
inspects the real file bytes afterwards. (AC7 says the subcommand must be
testable without an LLM — the subprocess IS that contract.)
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIZARD = REPO_ROOT / "references" / "scripts" / "wizard.py"


def run_cli(*args):
    """Run merge-deny-list via the real CLI; return (rc, envelope-or-None, raw)."""
    p = subprocess.run(
        [sys.executable, str(WIZARD), "merge-deny-list", *args],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    try:
        env = json.loads(p.stdout.strip())
    except Exception:
        env = None
    return p.returncode, env, p.stdout + p.stderr


class RealCliDenyList13337(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.proj = Path(self._td.name)
        self.settings = self.proj / ".claude" / "settings.json"

    def tearDown(self):
        self._td.cleanup()

    def _read(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    # TC-2 + TC-5: absent settings -> created in TARGET project; defaults present
    def test_tc2_absent_settings_created_with_defaults(self):
        rc, env, _ = run_cli(str(self.proj))
        self.assertEqual(rc, 0)
        self.assertTrue(env["ok"])
        self.assertTrue(self.settings.exists(), "settings.json created in TARGET project")
        deny = self._read()["permissions"]["deny"]
        joined = "\n".join(deny)
        self.assertIn("rm -rf /", joined.replace("*", "").replace('"', ""),
                      msg=f"posix root force-delete default expected in {deny}")
        self.assertTrue(any("~" in d or "$HOME" in d or "HOME" in d for d in deny),
                        msg=f"home force-delete default expected in {deny}")
        self.assertTrue(any("rd /s" in d or "Remove-Item" in d for d in deny),
                        msg=f"Windows equivalents expected in {deny}")

    # TC-3: merge-not-clobber, dedupe, unrelated keys preserved, idempotent
    def test_tc3_merge_never_clobber_dedupe_idempotent(self):
        self.settings.parent.mkdir(parents=True)
        prior = {
            "model": "opus",
            "hooks": {"PostToolUse": ["x"]},
            "permissions": {"allow": ["Bash(ls:*)"], "deny": ["Read(.env)"]},
        }
        self.settings.write_text(json.dumps(prior), encoding="utf-8")
        rc, env, _ = run_cli("--path", "secrets/**", str(self.proj))
        self.assertEqual(rc, 0)
        self.assertTrue(env["ok"])
        after = self._read()
        self.assertEqual(after["model"], "opus")
        self.assertEqual(after["hooks"], {"PostToolUse": ["x"]})
        self.assertEqual(after["permissions"]["allow"], ["Bash(ls:*)"])
        deny = after["permissions"]["deny"]
        self.assertIn("Read(.env)", deny, "prior deny entry preserved")
        for verb in ("Read", "Edit", "Write"):
            self.assertTrue(any(d.startswith(f"{verb}(") and "secrets/**" in d for d in deny),
                            msg=f"{verb} expansion of --path expected in {deny}")
        self.assertEqual(len(deny), len(set(deny)), "no duplicates after merge")
        # idempotent re-run: nothing new added, file content stable
        before_bytes = self.settings.read_bytes()
        rc2, env2, _ = run_cli("--path", "secrets/**", str(self.proj))
        self.assertEqual(rc2, 0)
        self.assertTrue(env2["ok"])
        self.assertEqual(env2.get("added"), [], "second run adds nothing")
        self.assertEqual(self.settings.read_bytes(), before_bytes, "file unchanged on re-run")

    # TC-4: dry-run previews without writing
    def test_tc4_dry_run_shows_added_writes_nothing(self):
        rc, env, _ = run_cli("--dry-run", "--path", "secrets/**", str(self.proj))
        self.assertEqual(rc, 0)
        self.assertTrue(env["ok"])
        self.assertTrue(env.get("added"), "dry-run reports what would be added")
        self.assertFalse(self.settings.exists(), "dry-run must not write")

    # TC-6: deny only, never ask
    def test_tc6_no_ask_rules_anywhere(self):
        rc, env, _ = run_cli("--path", "secrets/**", str(self.proj))
        self.assertEqual(rc, 0)
        raw = self.settings.read_text(encoding="utf-8")
        self.assertNotIn('"ask"', raw, "no ask key may be written")
        perms = self._read()["permissions"]
        self.assertNotIn("ask", perms)

    # TC-7: --rule verbatim
    def test_tc7_rule_passed_verbatim(self):
        rc, env, _ = run_cli("--rule", "Bash(curl:*)", str(self.proj))
        self.assertEqual(rc, 0)
        self.assertIn("Bash(curl:*)", self._read()["permissions"]["deny"])

    # TC-9: malformed settings -> fail-closed, original bytes untouched
    def test_tc9_malformed_json_failclosed_no_write(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("{ this is not json", encoding="utf-8")
        before = self.settings.read_bytes()
        rc, env, _ = run_cli("--path", "secrets/**", str(self.proj))
        self.assertNotEqual(rc, 0, "non-zero exit on malformed settings")
        self.assertFalse(env["ok"])
        self.assertTrue(env.get("error"), "error surfaced in envelope")
        self.assertEqual(self.settings.read_bytes(), before, "malformed file untouched")

    def test_tc9b_non_object_settings_failclosed(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("[1, 2, 3]", encoding="utf-8")
        before = self.settings.read_bytes()
        rc, env, _ = run_cli(str(self.proj))
        self.assertNotEqual(rc, 0)
        self.assertFalse(env["ok"])
        self.assertEqual(self.settings.read_bytes(), before)

    def test_tc9c_non_list_deny_failclosed(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps({"permissions": {"deny": "nope"}}),
                                 encoding="utf-8")
        before = self.settings.read_bytes()
        rc, env, _ = run_cli(str(self.proj))
        self.assertNotEqual(rc, 0)
        self.assertFalse(env["ok"])
        self.assertEqual(self.settings.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
