"""#13857 -- engine-boundary grep-audit (P1 T4, S1.2 / AC3).

VAULT-ARCH section 8.5: search, telemetry-write, and impressions-report live
in the packaged engine; no SquidSquad script reimplements them. Section 6.2:
sub-skills must reach the vault through the engine, never raw grep (a grep
that finds the right note leaves no impression/used trail, so the note reads
as dead to the maintenance signal).

P1 enforcement shape (deliberate): the v1 sub-skills still carry grep-based
vault search snippets -- their engine-backed rewrite is explicitly P4 scope
(PRD-VAULT-V2 S4.5). This audit therefore RATCHETS instead of banning
outright: today's sites are frozen as an allowlist that may only shrink.
Any NEW raw vault-grep introduced into agent instructions fails here, and
the Python-side boundary (no telemetry writers, no ranking reimplementation)
is a hard zero from day one. When P4 rewrites a file, its allowlist entry is
deleted -- the ratchet tightens until the list is empty.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
ENGINE = REPO / "references" / "skills" / "vault-search"

# Audit scope: EVERY agent-reachable text surface under references/ --
# *.md instruction/doc files plus *.j2 prompt templates (rendered into real
# prompts by model_router). The verifier's #13857 AC3 rejection proved that
# scanning only sub-skills/ + roles/ misses live teaching surfaces
# (references/docs/vault-reference.md is linked FROM an allowlisted
# sub-skill; references/prompts/research.md.j2 renders into research
# prompts). references/skills/ (the engine package itself) is excluded: its
# SKILL.md teaches the BAN, and the ban-prose filter already handles it.
AUDIT_ROOT = REPO / "references"
AUDIT_EXCLUDE = REPO / "references" / "skills"


def _audit_files():
    for pattern in ("*.md", "*.j2"):
        for f in AUDIT_ROOT.rglob(pattern):
            if AUDIT_EXCLUDE in f.parents:
                continue
            yield f

# A grep/rg invocation aimed at the vault tree. Matches command snippets in
# instruction sources, not prose ABOUT the ban (those lines name the ban or
# negate the command).
VAULT_GREP = re.compile(r"\b(?:grep|rg)\b[^\n]*(?:\.squidsquad/vault|vault/galaxy|vault/ --include)")
BAN_PROSE = re.compile(r"raw-grep|grep ban|never (?:raw-)?grep|not grep|instead of grep", re.IGNORECASE)

# Frozen v1 allowlist: file (relative to repo root) -> max allowed matching
# lines. These are the pre-engine search/link snippets whose engine-backed
# rewrite is P4 (PRD-VAULT-V2 S4.5). SHRINK ONLY -- never add an entry, never
# raise a count. Delete entries as P4 rewrites land.
V1_ALLOWLIST = {
    "references/sub-skills/common/vault-protocol.md": 2,
    "references/sub-skills/roles/pm/improvement-scan.md": 1,
    "references/sub-skills/roles/pm/task-intake-phases.md": 1,
    "references/sub-skills/roles/verifier/verification-issue-flow.md": 1,
    "references/sub-skills/roles/worker/implement-tasks.md": 1,
    # Verifier-found in the #13857 AC3 rejection (outside the original scan
    # roots): the v1 grep-mode reference doc (linked from vault-protocol's
    # allowlisted entry; retires with vault-protocol's P4 rewrite) and the
    # research-prompt template's vault-consult step (P4/S4.1-S4.2 rewires
    # research context injection through the engine).
    "references/docs/vault-reference.md": 6,
    "references/prompts/research.md.j2": 1,
}


def vault_grep_lines(path: Path):
    lines = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if VAULT_GREP.search(line) and not BAN_PROSE.search(line):
            lines.append(line.strip())
    return lines


class TestRawGrepRatchet:
    def test_no_new_vault_grep_sites_in_instructions(self):
        violations = {}
        for f in _audit_files():
            rel = f.relative_to(REPO).as_posix()
            hits = vault_grep_lines(f)
            allowed = V1_ALLOWLIST.get(rel, 0)
            if len(hits) > allowed:
                violations[rel] = hits
        assert not violations, (
            "New raw vault-grep in agent-reachable references/ surface "
            "(engine boundary, VAULT-ARCH 6.2/8.5 -- route through the "
            f"engine skill): {violations}"
        )

    def test_allowlist_entries_still_exist(self):
        """A rewritten/removed site must also be removed from the allowlist,
        keeping the ratchet honest (stale entries would mask new sites)."""
        for rel, allowed in V1_ALLOWLIST.items():
            path = REPO / rel
            assert path.is_file(), f"allowlist entry vanished -- delete it: {rel}"
            hits = vault_grep_lines(path)
            assert len(hits) == allowed, (
                f"{rel}: allowlist says {allowed} site(s), found {len(hits)} -- "
                "shrink the allowlist to match (ratchet only tightens)"
            )


class TestPythonBoundary:
    def test_no_script_writes_telemetry_shards(self):
        """Only the engine appends telemetry events. wizard.py is the single
        sanctioned .telemetry reference (the section 8.5 installer duty:
        seeding the dir + merge=union .gitattributes -- never events)."""
        offenders = []
        for py in SCRIPTS.glob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            if ".telemetry" in text and py.name != "wizard.py":
                offenders.append(py.name)
        assert offenders == [], f"scripts referencing telemetry shards: {offenders}"

    def test_wizard_telemetry_ref_is_seed_only(self):
        text = (SCRIPTS / "wizard.py").read_text(encoding="utf-8", errors="replace")
        assert "merge=union" in text  # the sanctioned seed
        assert ".jsonl\" " not in text and "jsonl'" not in text.replace("*.jsonl", "")  # no shard writes

    def test_no_script_reimplements_ranking(self):
        """The ranking brain (tie-break scoring, tier ordering, traversal
        budget) lives behind the engine boundary -- section 8: SquidSquad
        scripts never reimplement ranking."""
        markers = ["tieBreakScore", "tie_break_score", "traversalBudget", "traversal_budget"]
        offenders = []
        for py in SCRIPTS.glob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            if any(m in text for m in markers):
                offenders.append(py.name)
        assert offenders == [], f"ranking logic outside the engine: {offenders}"


class TestEnginePresence:
    def test_engine_package_carries_the_ops(self):
        """The section 8.5 operations the boundary depends on exist in the
        committed package: search (vault-query) + record (record-consumption).
        The report op is P3 scope (PRD S3.3) and lands with its consumer."""
        assert (ENGINE / "SKILL.md").is_file()
        assert (ENGINE / "scripts" / "vault-query.mjs").is_file()
        assert (ENGINE / "scripts" / "record-consumption.mjs").is_file()
        assert (ENGINE / "scripts" / "lib" / "consumption.mjs").is_file()

    def test_skill_md_teaches_the_ban_and_identity(self):
        text = (ENGINE / "SKILL.md").read_text(encoding="utf-8")
        assert "--instance-id" in text and "--alias" in text
        assert "raw-grep ban" in text or "Never grep" in text
        assert "--no-write" in text
