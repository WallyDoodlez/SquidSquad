"""Validate tests/comprehension/10678_spec.json (#10678, PRD-D D7).

Spec-file integrity checks. The actual fresh-agent comprehension run
via ``run_comprehension_test.py`` happens later when QA executes it
against a live model; these tests just confirm the spec is well-formed
and covers the AC-mandated scenarios.

Mirrors the tests/test_comprehension_10659.py pattern: schema check +
required-topic coverage check + file-path sanity.
"""

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "tests" / "comprehension" / "10678_spec.json"


@pytest.fixture(scope="module")
def spec():
    assert SPEC_PATH.exists(), f"missing spec: {SPEC_PATH}"
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema — top-level shape mirrors the existing comprehension spec contract.
# ---------------------------------------------------------------------------


class TestSpecSchema:
    def test_spec_is_valid_json(self):
        json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    def test_required_top_level_keys(self, spec):
        assert set(spec.keys()) >= {"issue", "title", "files", "questions"}

    def test_issue_number_matches_d7(self, spec):
        assert spec["issue"] == 10678

    def test_every_question_has_required_fields(self, spec):
        for q in spec["questions"]:
            assert "id" in q
            assert "question" in q
            assert "expected" in q
            assert q["id"]
            assert q["question"].strip()
            assert q["expected"].strip()

    def test_question_ids_unique(self, spec):
        ids = [q["id"] for q in spec["questions"]]
        assert len(ids) == len(set(ids)), f"duplicate question ids: {ids}"


# ---------------------------------------------------------------------------
# Required topic coverage — every AC3 scenario must have a question that
# covers it in BOTH question prose and expected answer.
# ---------------------------------------------------------------------------


class TestRequiredCoverage:
    """AC3 scenarios — every one must surface in at least one question.

    The match is two-sided: the regex must appear in the question prose
    AND in the expected answer. A question that asks about a scenario
    but ships with an expected answer that ignores it would slip through
    a one-sided check (and be a meaningless test).
    """

    AC3_SCENARIOS = [
        # DS-D7 F2: tightened so this regex doesn't spuriously match
        # question 2's "Read docs/sub-skill-catalog.md" prose. Require
        # an actual resolution VERB ("consult" / "resolve" / "look up")
        # OR an explicit "catalog row/entry/lookup" noun phrase — not
        # just the word "catalog" appearing as a filename component.
        # AND require a downstream action that isn't just the word
        # "Read" as a sentence opener (require "source path" or an
        # explicit "read THAT/THE file" form).
        (
            "resolvable-reference-execute",
            r"(consult|resolve|look[- ]?up|"
            r"catalog\s+(row|entry|lookup|table\s+row)).*"
            r"(source\s+path|read\s+(that|the)\s+file|"
            r"execute|fetch)",
        ),
        # DS-D7 F1: widened so "no matching row" (the phantom question's
        # actual phrasing) + "forbidden" (its actual error word) match.
        # Without this widening the regex spuriously matched the
        # "report-all-not-just-first" question instead, leaving this
        # AC3 scenario unguarded if the phantom question were deleted.
        (
            "unresolved-name-error",
            r"(no\s+(matching\s+)?(catalog\s+)?(row|entry)|unresolved|"
            r"not\s+indexed|silently\s+skipping).*"
            r"(error|abort|surface|reject|fail|forbidden)",
        ),
        (
            "missing-source-file-error",
            r"(source\s*path|source\s*file|file).*"
            r"(missing|does\s+not\s+exist|gone).*"
            r"(error|abort|surface|reject|fail)",
        ),
        (
            "multiple-refs-in-order",
            r"(multiple|several|three).*(order|sequence|top\s+to\s+bottom)",
        ),
    ]

    @pytest.mark.parametrize("label,regex", AC3_SCENARIOS)
    def test_scenario_covered(self, spec, label, regex):
        pat = re.compile(regex, re.IGNORECASE | re.DOTALL)
        for q in spec["questions"]:
            # DS-D7 F3: match against question PROSE only, not the ID.
            # Including the ID would let an ID containing "resolve" +
            # "execute" satisfy the resolvable-reference-execute regex
            # even if the prose was rewritten to a different topic.
            question_blob = q["question"]
            if pat.search(question_blob) and pat.search(q["expected"]):
                return
        pytest.fail(
            f"No question covers required AC3 scenario {label!r} in BOTH "
            f"question prose AND expected answer (regex /{regex}/). "
            f"Have ids: {[q['id'] for q in spec['questions']]}"
        )

    def test_at_least_five_questions(self, spec):
        """AC4 pass-rate target ≥9/10 implies ≥5 distinct scenarios for
        meaningful coverage; we ship more to harden against single-
        question stochasticity."""
        assert len(spec["questions"]) >= 5, (
            f"spec must have ≥5 questions; has {len(spec['questions'])}"
        )


# ---------------------------------------------------------------------------
# Expected-answer load-bearing content — each "expected" answer should
# reference the COMPOSE-ARCHITECTURE §4.5 prose enough to fail when the
# prose stops teaching the behavior. We don't grade the model's free-form
# response here; we just guard against a spec that ships with empty /
# placeholder expected answers.
# ---------------------------------------------------------------------------


class TestExpectedAnswersSubstantive:
    MIN_EXPECTED_CHARS = 100

    def test_expected_answers_have_substantive_length(self, spec):
        too_short = [
            q["id"] for q in spec["questions"]
            if len(q["expected"]) < self.MIN_EXPECTED_CHARS
        ]
        assert not too_short, (
            f"expected answer too short (< {self.MIN_EXPECTED_CHARS} chars) "
            f"for question ids: {too_short}"
        )

    def test_no_placeholder_expected_answers(self, spec):
        placeholders = ("TBD", "TODO", "FIXME", "<expected>", "...placeholder")
        for q in spec["questions"]:
            for placeholder in placeholders:
                assert placeholder not in q["expected"], (
                    f"question {q['id']!r} has placeholder {placeholder!r} "
                    f"in expected answer"
                )


# ---------------------------------------------------------------------------
# Files list sanity — spec must reference COMPOSE-ARCHITECTURE.md (the
# §4.5 prose under test) AND the catalog the agent looks names up in.
# Every listed file must exist on disk.
# ---------------------------------------------------------------------------


class TestFilesListSanity:
    def test_every_listed_file_exists(self, spec):
        for entry in spec["files"]:
            path = REPO_ROOT / entry
            assert path.exists(), f"spec lists nonexistent file: {entry}"

    def test_includes_compose_architecture(self, spec):
        # §4.5 lives here -- the load-bearing prose for the resolution
        # contract under test.
        assert any(
            entry.endswith("COMPOSE-ARCHITECTURE.md")
            for entry in spec["files"]
        ), (
            "spec must include docs/COMPOSE-ARCHITECTURE.md — the §4.5 "
            "prose whose comprehension is being tested"
        )

    def test_includes_sub_skill_catalog(self, spec):
        # The agent under test must have access to the catalog because
        # AC2 names it as the lookup source.
        assert any(
            entry.endswith("sub-skill-catalog.md")
            for entry in spec["files"]
        ), (
            "spec must include docs/sub-skill-catalog.md — the lookup "
            "the agent performs against per AC2"
        )

    def test_no_state_file_or_composed_output_references(self, spec):
        """The spec tests the SOURCE prose, not composed CLAUDE.md or
        .squidsquad/ runtime state. Composed output drifts with every
        deploy; the source is the contract."""
        banned = (".squidsquad/", "CLAUDE.md", "/installer-files.txt")
        for entry in spec["files"]:
            for b in banned:
                assert b not in entry, (
                    f"spec must not reference {b!r} — test the source "
                    f"docs, not composed/state files. Got: {entry!r}"
                )
