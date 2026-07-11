"""#13329 — scan the target repo for existing agent-facing assets.

The installer should discover a project's existing Claude Code skills / slash
commands / CLAUDE.md conventions, confirm with the user which are used, and
incorporate the confirmed ones as L4 pointers so SquidSquad's agents respect
and leverage them. This suite pins the deterministic detection half
(`wizard.scan_existing_assets` + the `scan-existing-assets` CLI); the confirm
gate and the L4 pointer-writes are the installer agent's job (l4-curation).

Per the confirmed design: pointer + one-line intent that captures the TRIGGER
(WHEN to invoke), MCP out of v1 scope (flagged for awareness only).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402

WIZARD_PY = REPO_ROOT / "references" / "scripts" / "wizard.py"


def _write(root, rel, content=""):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


class TestEmptyRepo(unittest.TestCase):
    def test_no_claude_dir_yields_empty(self):
        with tempfile.TemporaryDirectory() as d:
            r = wizard.scan_existing_assets(d)
            self.assertEqual(r["skills"], [])
            self.assertEqual(r["commands"], [])
            self.assertEqual(r["claude_md_files"], [])
            self.assertFalse(r["mcp_config_present"])


class TestSkillDetection(unittest.TestCase):
    def test_skill_frontmatter_name_and_trigger_intent(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/skills/deploy-helper/SKILL.md",
                   "---\nname: deploy-helper\n"
                   "description: Use when deploying to staging or prod.\n---\n# body\n")
            r = wizard.scan_existing_assets(d)
            self.assertEqual(len(r["skills"]), 1)
            s = r["skills"][0]
            self.assertEqual(s["name"], "deploy-helper")
            self.assertIn("deploying", s["intent"])  # trigger captured
            self.assertEqual(s["path"], ".claude/skills/deploy-helper/SKILL.md")

    def test_skill_without_frontmatter_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/skills/raw/SKILL.md", "# Raw Skill\n\nDoes things.\n")
            r = wizard.scan_existing_assets(d)
            self.assertEqual(r["skills"][0]["name"], "raw")  # dir name
            self.assertEqual(r["skills"][0]["intent"], "Raw Skill")  # first heading

    def test_skill_dir_without_skill_md_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/skills/notaskill/README.md", "x")
            self.assertEqual(wizard.scan_existing_assets(d)["skills"], [])

    def test_skill_crlf_frontmatter_parsed(self):
        """Windows-authored SKILL.md (CRLF) must still yield name + intent."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".claude" / "skills" / "win" / "SKILL.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(
                b"---\r\nname: win\r\n"
                b"description: Use when on Windows.\r\n---\r\n# body\r\n")
            r = wizard.scan_existing_assets(d)
            self.assertEqual(r["skills"][0]["name"], "win")
            self.assertIn("Windows", r["skills"][0]["intent"])


class TestCommandDetection(unittest.TestCase):
    def test_command_name_and_intent(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/commands/ship.md",
                   "---\ndescription: Ship the current branch after review.\n---\n")
            r = wizard.scan_existing_assets(d)
            self.assertEqual(len(r["commands"]), 1)
            self.assertEqual(r["commands"][0]["name"], "ship")  # filename stem
            self.assertIn("Ship", r["commands"][0]["intent"])

    def test_command_first_line_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/commands/audit.md", "# Audit\nRun the audit.\n")
            self.assertEqual(
                wizard.scan_existing_assets(d)["commands"][0]["intent"], "Audit")


class TestClaudeMdAndSkips(unittest.TestCase):
    def test_root_and_nested_claude_md_listed(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "CLAUDE.md", "# root")
            _write(d, "packages/api/CLAUDE.md", "# nested")
            r = wizard.scan_existing_assets(d)
            self.assertIn("CLAUDE.md", r["claude_md_files"])
            self.assertIn("packages/api/CLAUDE.md", r["claude_md_files"])

    def test_squidsquad_and_vendored_claude_md_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".squidsquad/skill/CLAUDE.md", "# composed")
            _write(d, "node_modules/pkg/CLAUDE.md", "# vendored")
            self.assertEqual(wizard.scan_existing_assets(d)["claude_md_files"], [])


class TestMcpAwareness(unittest.TestCase):
    def test_mcp_config_flagged_not_imported(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".mcp.json", "{}")
            r = wizard.scan_existing_assets(d)
            self.assertTrue(r["mcp_config_present"])
            # MCP is out of v1 scope — only flagged, never listed as an asset.
            self.assertEqual(r["skills"], [])
            self.assertEqual(r["commands"], [])


class TestCli(unittest.TestCase):
    def test_cli_ok_envelope(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, ".claude/commands/x.md", "# X")
            proc = subprocess.run(
                [sys.executable, str(WIZARD_PY), "scan-existing-assets", d],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=60, check=False,
            )
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout)
            self.assertTrue(out["ok"])
            self.assertEqual(len(out["commands"]), 1)


if __name__ == "__main__":
    unittest.main()
