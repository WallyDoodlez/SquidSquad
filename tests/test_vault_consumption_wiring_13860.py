"""#13860 P4 -- the consumption pipeline is WIRED into the agent instructions.

Production-caller check (the "shipped unwired" audit pattern): each pipeline
step's instruction surface must invoke the real vault_consume.py subcommands,
never raw-grep the vault, and the example receipt blocks the instructions show
agents must themselves pass the gate those agents will be held to.
"""

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SUB = REPO / "references" / "sub-skills"
sys.path.insert(0, str(REPO / "references" / "scripts"))

import vault_consume as vc  # noqa: E402

RAW_VAULT_GREP = re.compile(r"grep[^\n`]*\.squidsquad/vault")


def read(rel):
    return (SUB / rel).read_text(encoding="utf-8")


def fenced_blocks(text):
    """Fenced code blocks, fence-pairing by line (opening fences may carry a
    language tag, so a regex over the raw text mis-pairs them)."""
    blocks, cur = [], None
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if cur is None:
                cur = []
            else:
                blocks.append("\n".join(cur))
                cur = None
        elif cur is not None:
            cur.append(line)
    return blocks


def dedent_block(block):
    return "\n".join(line.strip() for line in block.splitlines())


class TestWorkerPickup:
    TEXT = read("roles/worker/implement-tasks.md")

    @pytest.mark.parametrize("needle", [
        "vault_consume.py lineage-path [NUMBER]",
        "vault_consume.py init-fix-plan [NUMBER] --role [ROLE]",
        "vault_consume.py search --alias [ROLE] --task [NUMBER]",
        "--types rule",
        "vault_consume.py cite --alias [ROLE] --task [NUMBER]",
        "vault_consume.py check-receipts [NUMBER]",
        "check-receipts [NUMBER] --diff-base origin/main",
        "git add <lineage path>",
    ])
    def test_step_invokes_pipeline(self, needle):
        assert needle in self.TEXT

    def test_no_raw_vault_grep(self):
        assert not RAW_VAULT_GREP.search(self.TEXT)

    def test_example_receipts_pass_the_gate(self):
        blocks = [dedent_block(b) for b in fenced_blocks(self.TEXT)]
        ctx = [b for b in blocks if b.startswith(vc.CONTEXT_SECTION)]
        rules = [b for b in blocks if b.startswith(vc.RULES_SECTION)]
        assert ctx and rules
        assert vc.check_section(ctx[0], vc.CONTEXT_SECTION)[0] == "cited"
        assert vc.check_section(rules[0], vc.RULES_SECTION)[0] == "cited"

    @pytest.mark.parametrize("line,heading,status", [
        ("- None relevant (searched: <keywords>)", vc.CONTEXT_SECTION, "none"),
        ("- None matched (searched rules lane: <keywords>)", vc.RULES_SECTION, "none"),
        ("- Engine unavailable: <reason>", vc.RULES_SECTION, "unavailable"),
    ])
    def test_documented_none_and_unavailable_lines_pass(self, line, heading, status):
        assert line.split(" (")[0].split(":")[0].lstrip("- ") in self.TEXT
        assert vc.check_section(f"{heading}\n{line}\n", heading)[0] == status


class TestBugFlow:
    TEXT = read("roles/worker/triage-issues.md")

    def test_pickup_creates_fix_plan(self):
        assert "vault_consume.py init-fix-plan [NUMBER] --role [ROLE]" in self.TEXT
        for section in ("Root cause", "Intended direction", "Impact"):
            assert section in self.TEXT

    def test_gate_before_pending_test(self):
        assert "check-receipts [NUMBER] --diff-base origin/main" in self.TEXT

    def test_no_raw_vault_grep(self):
        assert not RAW_VAULT_GREP.search(self.TEXT)


class TestPmIntake:
    TEXT = read("roles/pm/task-intake-phases.md")

    def test_research_search_through_engine(self):
        assert "vault_consume.py search --alias [PM_ALIAS]" in self.TEXT

    def test_filing_injects_context(self):
        assert "vault_consume.py inject-context [NUMBER] --alias [PM_ALIAS]" in self.TEXT
        # injection happens in Phase 3 (after create-task), before 3B seeds the plan body
        assert self.TEXT.index("inject-context") < self.TEXT.index("### Phase 3B")
        assert self.TEXT.index("### Phase 3 ") < self.TEXT.index("inject-context")

    def test_dispatch_table_names_injection(self):
        assert "inject-context" in read("roles/pm/task-intake.md")

    def test_no_raw_vault_grep(self):
        assert not RAW_VAULT_GREP.search(self.TEXT)

    def test_worker_reads_injected_section(self):
        assert "issue body's `## Vault context` section" in read("roles/worker/implement-tasks.md")


@pytest.mark.parametrize("rel", ["roles/verifier/verification-issue-flow.md",
                                 "roles/verifier/verification.md"])
class TestVerifierGate:
    def test_runs_receipt_gate_against_pr_diff(self, rel):
        assert "vault_consume.py check-receipts [NUMBER] --diff-base origin/main" in read(rel)

    def test_rule_compliance_and_degradation(self, rel):
        text = read(rel)
        assert "## Applicable rules" in text and "rule compliance" in text
        assert "pass-with-note" in text

    def test_gate_precedes_verdict(self, rel):
        text = read(rel)
        verdict = "6. If verified" if "issue-flow" in rel else "2d. **AC walk"
        assert text.index("check-receipts") < text.index(verdict)

    def test_no_raw_vault_grep(self, rel):
        assert not RAW_VAULT_GREP.search(read(rel))


class TestSubSkillRewrites:
    """S4.5: the four vault sub-skills are engine-backed v2 (no v1 grep modes,
    no retired fields, no time decay, no pattern-posture-*)."""

    PROTOCOL = read("common/vault-protocol.md")
    OPTIMIZE = read("common/vault-optimize.md")
    SYNTHESIS = read("roles/pm/vault-synthesis.md")

    @pytest.mark.parametrize("rel", ["common/vault-protocol.md", "common/vault-optimize.md",
                                     "roles/pm/vault-synthesis.md", "roles/pm/improvement-scan.md"])
    def test_no_raw_vault_grep(self, rel):
        assert not RAW_VAULT_GREP.search(read(rel))

    def test_protocol_engine_read_contract(self):
        assert "vault_consume.py search --alias [ROLE]" in self.PROTOCOL
        assert "vault_consume.py cite --alias [ROLE]" in self.PROTOCOL
        assert "Engine unavailable" in self.PROTOCOL

    def test_protocol_names_all_consumption_steps(self):
        for needle in ("inject-context", "lineage-path", "check-receipts",
                       "## Vault context consumed", "## Applicable rules"):
            assert needle in self.PROTOCOL

    def test_protocol_v2_frontmatter_and_rule_lane(self):
        assert "vault_entity.py create <type> <slug>" in self.PROTOCOL
        assert "Do not add `confidence`, `source`, `links`" in self.PROTOCOL
        assert "rule-" in self.PROTOCOL and "## Scope" in self.PROTOCOL

    def test_protocol_receipt_lines_match_gate(self):
        """The receipt line forms the protocol teaches are the ones the gate accepts."""
        assert "- None relevant (searched: …)" in self.PROTOCOL
        assert vc.check_section(f"{vc.CONTEXT_SECTION}\n- None relevant (searched: x)\n",
                                vc.CONTEXT_SECTION)[0] == "none"
        assert vc.check_section(f"{vc.RULES_SECTION}\n- [[rule-a]] -- b\n", vc.RULES_SECTION)[0] == "cited"

    def test_optimize_is_propose_only(self):
        assert "vault_optimize.py propose-prunes" in self.OPTIMIZE
        assert "vault_optimize.py compact-telemetry --alias [ROLE]" in self.OPTIMIZE
        # the v1 auto-archive / time-decay path is never invoked
        for cmd in ("vault_optimize.py run\n", "```bash\npython references/scripts/vault_optimize.py run"):
            assert cmd not in self.OPTIMIZE
        assert "Do NOT run `vault_optimize.py run`" in self.OPTIMIZE

    def test_synthesis_v2_output_target(self):
        assert "systems/" in self.SYNTHESIS
        assert "Never create `pattern-posture-*` notes" in self.SYNTHESIS
        assert "vault_consume.py cite --alias [ROLE] --task" in self.SYNTHESIS

    def test_l1_vault_slot_names_engine_and_receipts(self):
        text = (REPO / "references" / "roles" / "vault.md").read_text(encoding="utf-8")
        assert "vault_consume.py search" in text and "## Applicable rules" in text
        assert "`rule-*`" in text and "`style-*`" not in text

    def test_research_prompt_does_not_grep_vault(self):
        text = (REPO / "references" / "prompts" / "research.md.j2").read_text(encoding="utf-8")
        assert not RAW_VAULT_GREP.search(text)
