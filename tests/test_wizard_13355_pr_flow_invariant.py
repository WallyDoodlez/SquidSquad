"""#13355 — retire the PR-flow on/off prompt; PR flow is always-on.

INSTALLER-RUNTIME.md §3 makes PR flow an invariant (every change lands
through a reviewable pull request; direct commits are never offered) and
the harness has treated branch+PR as the only mode since #9478 D2 — yet
wizard.py still shipped `pr_flow_prompt()` defaulting to OFF (direct
commits), and `build_config_md` rendered the flag as a generic
`- **Pr Flow**:` line under `## Flags` that `config.py`'s FIELD_MAP
(`("PR Flow", "Enabled")`) never reads — so fresh installs had NO
`## PR Flow` section at all and the runtime read pr-flow as absent.
Same gap for the merge gate: the manual's §9 says to record the Auto
Merge answer in config, but nothing emitted an `## Auto Merge` section,
and `config.py get auto-merge` (the verifier/DM merge-gate read)
sys.exit(1)s on a missing field with no registered default.

This suite locks the retirement and the wiring:
- the prompt trio (function, cmd wrapper, CLI dispatch) is gone;
- config.md always ships `## PR Flow / Enabled: yes` (invariant — a
  legacy spec's `pr_flow: False` is ignored, never rendered);
- the merge gate renders as `## Auto Merge / Enabled` from
  `flags.auto_merge` (default yes);
- runtime graceful defaults: pr-flow → yes (the only mode), auto-merge →
  no (conservative human gate) for configs missing the sections.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import config  # noqa: E402
import wizard  # noqa: E402

WIZARD_PY = REPO_ROOT / "references" / "scripts" / "wizard.py"


def _spec(flags):
    return {
        "project": {"name": "t", "repo": "o/r"},
        "preset": "software-dev",
        "agents": [
            {"id": "pm", "alias": "pm", "role": "pm"},
        ],
        "tools": {},
        "loop": {"interval_minutes": 30, "context_threshold": 70},
        "flags": flags,
    }


class TestPromptRetired(unittest.TestCase):
    def test_prompt_functions_gone(self):
        self.assertFalse(hasattr(wizard, "pr_flow_prompt"))
        self.assertFalse(hasattr(wizard, "cmd_pr_flow_prompt"))

    def test_cli_command_gone(self):
        proc = subprocess.run(
            [sys.executable, str(WIZARD_PY), "pr-flow-prompt"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False,
            cwd=str(REPO_ROOT),
        )
        self.assertNotEqual(
            proc.returncode, 0,
            "pr-flow-prompt must no longer be a wizard.py subcommand",
        )


class TestPrFlowSectionInvariant(unittest.TestCase):
    def test_always_enabled_yes(self):
        text = wizard.build_config_md(_spec({"improvement_scan": True}))
        self.assertIn("## PR Flow\n\n- **Enabled**: yes", text)

    def test_legacy_pr_flow_false_is_ignored(self):
        """A pre-#13355 spec still carrying pr_flow: False cannot turn the
        invariant off — and the retired flag never renders anywhere."""
        text = wizard.build_config_md(_spec({"pr_flow": False}))
        self.assertIn("## PR Flow\n\n- **Enabled**: yes", text)
        self.assertNotIn("**Pr Flow**", text)

    def test_runtime_reads_yes_from_rendered_config(self):
        """End-to-end: the section build_config_md emits is the one the
        runtime FIELD_MAP actually reads."""
        text = wizard.build_config_md(_spec({}))
        val = config._parse_field(text, "PR Flow", "Enabled")
        self.assertEqual(val, "yes")


class TestAutoMergeSection(unittest.TestCase):
    def test_defaults_to_yes(self):
        text = wizard.build_config_md(_spec({"improvement_scan": True}))
        self.assertIn("## Auto Merge\n\n- **Enabled**: yes", text)

    def test_spec_no_renders_no(self):
        """The merge gate is the surviving variable — a 'human approves
        each merge' answer flows through to the section."""
        text = wizard.build_config_md(_spec({"auto_merge": False}))
        self.assertIn("## Auto Merge\n\n- **Enabled**: no", text)
        val = config._parse_field(text, "Auto Merge", "Enabled")
        self.assertEqual(val, "no")

    def test_auto_merge_not_duplicated_under_flags(self):
        text = wizard.build_config_md(_spec({"auto_merge": True}))
        flags_block = text.split("## Flags")[1].split("## ")[0]
        self.assertNotIn("Auto Merge", flags_block)

    def test_generate_default_spec_carries_auto_merge_not_pr_flow(self):
        spec = wizard.generate_default_spec()
        self.assertNotIn("pr_flow", spec["flags"])
        self.assertIs(spec["flags"]["auto_merge"], True)


class TestRuntimeGracefulDefaults(unittest.TestCase):
    def test_pr_flow_defaults_yes(self):
        self.assertEqual(config._FIELD_DEFAULTS.get("pr-flow"), "yes")

    def test_auto_merge_defaults_no(self):
        self.assertEqual(config._FIELD_DEFAULTS.get("auto-merge"), "no")


if __name__ == "__main__":
    unittest.main()
