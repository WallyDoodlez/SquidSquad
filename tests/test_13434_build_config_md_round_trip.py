"""#13434 — general round-trip gate: every field build_config_md emits under a
dedicated section must be readable by config.py at the FIELD_MAP-mapped
(section, field).

The dead-section drift class shipped TWICE (#13328 interval/threshold under a
dead '## Loop' heading; #13355 PR Flow under '## Flags') — build_config_md wrote
a value under a heading config.py's FIELD_MAP never reads, so `config get` saw it
as absent and silently fell back to a default. The existing #5366 guard
(test_config_functions.py) checks FIELD_MAP against a HAND-MAINTAINED
SAMPLE_CONFIG fixture, not against build_config_md's actual output, so
emit-side/read-side drift slips through while the fixture stays correct.

This suite closes that gap with a single invariant that would have caught BOTH
prior incidents (and any future sibling): render build_config_md's output and
assert config._parse_field reads back every field build_config_md is responsible
for emitting under a dedicated section. If a field is ever moved back under a
heading FIELD_MAP doesn't read, its parse returns None and the gate fails.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import config  # noqa: E402
import wizard  # noqa: E402


def _full_spec():
    """A fully-populated spec so every ALWAYS-emitted dedicated-section field is
    present and deterministic (independent of scan/repo autodetection)."""
    return {
        "squidsquad_version": "9.9.9",
        "project": {"name": "roundtrip-proj", "repo": "owner/roundtrip-proj"},
        "preset": "software-dev",
        "agents": [
            {"id": "pm", "alias": "pm", "role": "pm"},
            {"id": "skill", "alias": "skill", "role": "dev", "variant": "skill",
             "stack": "Python 3.11 + pytest", "test_command": "pytest tests"},
        ],
        "tools": {},
        "loop": {"interval_minutes": 20, "context_threshold": 65},
        "flags": {"auto_merge": False, "improvement_scan": True,
                  "vault_remember": True, "diagnostics": True},
        "git_branches": {"working": "main", "state": "squid-squad"},
        "forge_backend": {"provider": "github", "endpoint": "https://api.github.com"},
        "model_routing": {"model": "claude", "research_model": "claude"},
    }


# Short-name keys config.FIELD_MAP maps that build_config_md ALWAYS emits under a
# dedicated section/top-of-file. Each MUST round-trip through _parse_field. This
# is a positive allowlist (not the full FIELD_MAP): fields that are agent-derived,
# optional/conditional (forge owner/repo, project description), stored outside
# config.md (the ship counter, #12823), or carry a graceful runtime default and
# are legitimately absent are intentionally excluded — asserting them would be a
# false positive, not a dead-section catch. Add a row here whenever
# build_config_md gains a new dedicated-section field.
ROUND_TRIP_FIELDS = [
    "version", "tracker", "arch-version",
    "project-name", "repo",
    "interval",            # #13328 — was dead under ## Loop
    "context-threshold",   # #13328 — was dead under ## Loop
    "auto-merge",          # #13355 — dedicated ## Auto Merge (not ## Flags)
    "pr-flow",             # #13355 — dedicated ## PR Flow (not ## Flags)
    "improvement-scan-cool-down",
    "idle-scan-burst",
    "verbose-mode",
    "working-branch", "state-branch",
    "forge-provider", "forge-endpoint",
    "default-model", "research-model", "discussion-prep-model", "test-plan-model",
    "qa-execution-model", "comprehension-model", "improvement-scan-model",
    "code-review-model", "fallback-model", "api-timeout-seconds",
]


class TestBuildConfigMdRoundTrip(unittest.TestCase):
    def setUp(self):
        self.text = wizard.build_config_md(_full_spec())

    def test_every_dedicated_section_field_reads_back(self):
        """No field build_config_md emits under a dedicated section is DEAD."""
        dead = []
        for short in ROUND_TRIP_FIELDS:
            section, field_name = config.FIELD_MAP[short]
            val = config._parse_field(self.text, section, field_name)
            if val is None:
                dead.append(f"{short} -> ({section} / {field_name})")
        self.assertEqual(
            dead, [],
            "build_config_md emits these fields under a heading config.py's "
            "FIELD_MAP does not read (dead-section drift, #13328/#13355 class): "
            + ", ".join(dead),
        )

    def test_allowlist_keys_exist_in_field_map(self):
        """Guard the guard: a typo'd short name would silently skip coverage."""
        missing = [s for s in ROUND_TRIP_FIELDS if s not in config.FIELD_MAP]
        self.assertEqual(missing, [], f"unknown FIELD_MAP short names: {missing}")

    def test_historically_dead_pairs_carry_spec_values(self):
        """Belt-and-suspenders exact-value round-trip for the two shipped bugs."""
        self.assertEqual(config._parse_field(self.text, "Iteration Interval", "Minutes"), "20")
        self.assertEqual(config._parse_field(self.text, "Context Pressure", "Threshold"), "65")
        self.assertEqual(config._parse_field(self.text, "Auto Merge", "Enabled"), "no")
        self.assertEqual(config._parse_field(self.text, "PR Flow", "Enabled"), "yes")

    def test_generated_default_install_round_trips(self):
        """The real --yes default install output round-trips too (not just the
        hand-built spec) for the load-bearing runtime reads."""
        spec = wizard.generate_default_spec()
        text = wizard.build_config_md(spec)
        for short in ("interval", "context-threshold", "pr-flow", "auto-merge",
                      "verbose-mode", "improvement-scan-cool-down", "idle-scan-burst"):
            section, field_name = config.FIELD_MAP[short]
            self.assertIsNotNone(
                config._parse_field(text, section, field_name),
                f"default install: {short} ({section}/{field_name}) is DEAD",
            )


if __name__ == "__main__":
    unittest.main()
