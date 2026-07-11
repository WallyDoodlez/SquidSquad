"""#13328 — retire the loop-interval prompt; interval is a silent fallback default.

Operator feedback (live greenfield install): the setup wizard shouldn't ask the
user for a loop/iteration duration. Event mode is the always-on default and the
loop is only an automatic boot-time fallback when the harness is unreachable
(INSTALLER-RUNTIME.md §5), so prompting the user to tune a fallback's cadence is
stale and the "how often should each agent run its cycle?" framing is misleading.

This suite locks the retirement and the config wiring:
- the prompt trio (validate_interval, cmd_validate_interval, the validate-interval
  CLI command) is gone;
- build_config_md writes the interval under the section config.py actually reads
  (## Iteration Interval / Minutes), with a silent 30-minute default — NOT the
  dead ## Loop heading the FIELD_MAP never read (the #13328 latent bug, same
  drift class as #13355's PR Flow);
- context-threshold likewise renders under its read section (## Context Pressure);
- config.py carries a graceful interval default so a config.md missing the
  section reads 30 rather than sys.exit(1)ing.
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


def _spec(loop):
    return {
        "project": {"name": "t", "repo": "o/r"},
        "preset": "software-dev",
        "agents": [{"id": "pm", "alias": "pm", "role": "pm"}],
        "tools": {},
        "loop": loop,
        "flags": {"improvement_scan": True},
    }


class TestPromptRetired(unittest.TestCase):
    def test_prompt_functions_gone(self):
        self.assertFalse(hasattr(wizard, "validate_interval"))
        self.assertFalse(hasattr(wizard, "cmd_validate_interval"))

    def test_cli_command_gone(self):
        proc = subprocess.run(
            [sys.executable, str(WIZARD_PY), "validate-interval", "10"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False, cwd=str(REPO_ROOT),
        )
        self.assertNotEqual(
            proc.returncode, 0,
            "validate-interval must no longer be a wizard.py subcommand")


class TestIntervalSection(unittest.TestCase):
    def test_no_dead_loop_section(self):
        text = wizard.build_config_md(_spec({}))
        self.assertNotIn("## Loop", text)

    def test_silent_default_30(self):
        text = wizard.build_config_md(_spec({}))
        self.assertIn("## Iteration Interval\n\n- **Minutes**: 30", text)

    def test_spec_value_renders(self):
        text = wizard.build_config_md(_spec({"interval_minutes": 15}))
        self.assertIn("## Iteration Interval\n\n- **Minutes**: 15", text)

    def test_context_pressure_section_default(self):
        text = wizard.build_config_md(_spec({}))
        self.assertIn("## Context Pressure\n\n- **Threshold**: 70", text)

    def test_interval_reads_back_from_rendered_config(self):
        """End-to-end: the section build_config_md emits is the one config.py's
        FIELD_MAP actually reads (the #13328 fix)."""
        text = wizard.build_config_md(_spec({}))
        self.assertEqual(config._parse_field(text, "Iteration Interval", "Minutes"), "30")

    def test_threshold_reads_back_from_rendered_config(self):
        text = wizard.build_config_md(_spec({"context_threshold": 80}))
        self.assertEqual(config._parse_field(text, "Context Pressure", "Threshold"), "80")


class TestRuntimeGracefulDefault(unittest.TestCase):
    def test_interval_defaults_to_30(self):
        self.assertEqual(config._FIELD_DEFAULTS.get("interval"), "30")


class TestGeneratedSpec(unittest.TestCase):
    def test_generate_default_spec_interval_is_30(self):
        spec = wizard.generate_default_spec()
        self.assertEqual(spec["loop"]["interval_minutes"], 30)


if __name__ == "__main__":
    unittest.main()
