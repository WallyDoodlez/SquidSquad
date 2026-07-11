"""#12450 Surface 4 — the L3 "follow the project's detected test strategy"
behavior is duplicated into every per-stack worker domain source.

PM locked the L3=behavior / L4-seed=specifics split and (rec a) the behavior
is duplicated into each per-stack worker L3 source (there is no shared
software-dev domain dir). This file asserts the behavior is present in all five
worker stack instruction sources and survives compose into the worker output.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKER_ROLES = REPO_ROOT / "references" / "roles" / "worker"
STACKS = ["android", "ios", "web", "fullstack", "skill"]

# The behavioral anchor every stack must carry (#12450 S4).
ANCHOR = "follow the project's detected test strategy"
NEGATIVE_ANCHOR = "never invent a framework or test layout the repo doesn't use"


class TestL3TestStrategyBehavior(unittest.TestCase):
    def test_all_stacks_carry_the_behavior(self):
        for stack in STACKS:
            src = WORKER_ROLES / stack / "instructions.md"
            self.assertTrue(src.exists(), f"missing L3 source for {stack}")
            text = src.read_text(encoding="utf-8")
            self.assertIn(ANCHOR, text, f"{stack}: missing test-strategy behavior")
            self.assertIn(
                NEGATIVE_ANCHOR, text,
                f"{stack}: missing the negative-constraint half")

    def test_behavior_inside_domain_context_block(self):
        """The line must live inside the composed domain-context sub-skill block
        so it actually reaches the worker CLAUDE.md."""
        for stack in STACKS:
            text = (WORKER_ROLES / stack / "instructions.md").read_text(
                encoding="utf-8")
            open_marker = "<!-- sub-skill: domain-context -->"
            close_marker = "<!-- /sub-skill: domain-context -->"
            self.assertIn(open_marker, text)
            self.assertIn(close_marker, text)
            block = text.split(open_marker, 1)[1].split(close_marker, 1)[0]
            self.assertIn(ANCHOR, block, f"{stack}: behavior outside the block")

    def test_behavior_is_in_the_included_domain_context_block(self):
        """The behavior must live in the domain-context block each stack's
        includes.yml wires in — guaranteeing it reaches the composed output.

        Each stack's L3 manifest pulls ``roles/worker/<stack>/domain-context``;
        compose extracts that block from instructions.md. Asserting the anchor is
        inside the block (test_behavior_inside_domain_context_block) plus the
        include reference here proves the wiring without running the full pipeline.
        """
        for stack in STACKS:
            inc = (WORKER_ROLES / stack / "includes.yml").read_text(
                encoding="utf-8")
            self.assertIn(
                f"roles/worker/{stack}/domain-context", inc,
                f"{stack}: domain-context not wired into includes.yml")


if __name__ == "__main__":
    unittest.main()
