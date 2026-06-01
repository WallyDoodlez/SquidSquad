"""Validate tests/comprehension/10659_spec.json (#10659, PRD-C C10).

Spec-file integrity checks. The actual fresh-agent comprehension run via
``run_comprehension_test.py`` happens later when QA executes it against a
live model — these tests just confirm the spec is well-formed and covers
the AC-mandated scenarios.

Mirrors the tests/test_comprehension_8694.py pattern: schema check +
required-topic coverage check + file-path sanity.
"""

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "tests" / "comprehension" / "10659_spec.json"


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

    def test_issue_is_int_and_matches(self, spec):
        assert isinstance(spec["issue"], int)
        assert spec["issue"] == 10659

    def test_title_is_string(self, spec):
        assert isinstance(spec["title"], str)
        assert spec["title"].strip(), "title must be non-empty"

    def test_files_is_nonempty_list_of_strings(self, spec):
        assert isinstance(spec["files"], list)
        assert spec["files"], "files must be non-empty"
        for entry in spec["files"]:
            assert isinstance(entry, str) and entry.strip()

    def test_questions_is_list_of_objects(self, spec):
        assert isinstance(spec["questions"], list)
        for q in spec["questions"]:
            assert isinstance(q, dict)
            assert {"id", "question", "expected"} <= set(q.keys())
            for k in ("id", "question", "expected"):
                assert isinstance(q[k], str) and q[k].strip()

    def test_question_ids_are_unique(self, spec):
        ids = [q["id"] for q in spec["questions"]]
        assert len(ids) == len(set(ids)), f"duplicate question ids: {ids}"


# ---------------------------------------------------------------------------
# Required topic coverage — every AC2 category must surface in at least one
# question. The regex matches the id OR the question prose; if neither hits
# for a topic the spec is missing that scenario.
# ---------------------------------------------------------------------------


class TestRequiredScenarioCoverage:
    REQUIRED_TOPICS = [
        # AC2 categories
        ("detection (durable vs one-off)",
         r"durable|one.?off|from now on|going forward|just this once|for this (?:task|pr)"),
        ("scope (role-class vs alias)",
         r"role.?class|alias|fan.?out|every role.?class|single file"),
        ("decision tree (insert-before vs append)",
         r"insert.?before|append|step:cycle/|targeted op|whole.?slot"),
        ("forbidden slots (vault refusal)",
         r"vault|forbidden|refuse|L1.?exclusive|framework.?owned"),
        ("removal (counter-entry / undo)",
         r"counter.?entry|removal|undo|forget|prune|delete"),
    ]

    @pytest.mark.parametrize("label,regex", REQUIRED_TOPICS)
    def test_topic_covered_by_at_least_one_question(self, spec, label, regex):
        pat = re.compile(regex, re.IGNORECASE)
        for q in spec["questions"]:
            blob = f"{q['id']} {q['question']}"
            if pat.search(blob):
                return
        pytest.fail(
            f"No question covers required scenario {label!r} "
            f"(regex /{regex}/). Have ids: {[q['id'] for q in spec['questions']]}"
        )

    def test_at_least_five_questions(self, spec):
        """AC2 mandates ≥5 scenarios. We ship more for richer coverage."""
        assert len(spec["questions"]) >= 5, (
            f"spec must have ≥5 questions; has {len(spec['questions'])}"
        )


# ---------------------------------------------------------------------------
# Expected-answer load-bearing content — each "expected" answer should
# reference the sub-skill prose enough to fail when the prose stops teaching
# the behavior. We don't grade the model's free-form response here; we just
# guard against a spec that ships with empty / placeholder expected answers.
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
        placeholders = ("TBD", "TODO", "FIXME", "<expected>", "...")
        for q in spec["questions"]:
            for placeholder in placeholders:
                assert placeholder not in q["expected"], (
                    f"question {q['id']!r} has placeholder {placeholder!r} "
                    f"in expected answer"
                )


# ---------------------------------------------------------------------------
# Files list sanity — spec should reference the l4-curation sub-skill prose
# under references/sub-skills/common/, and each path must exist on disk.
# ---------------------------------------------------------------------------


class TestFilesListSanity:
    def test_every_listed_file_exists(self, spec):
        for entry in spec["files"]:
            path = REPO_ROOT / entry
            assert path.exists(), f"spec lists nonexistent file: {entry}"

    def test_includes_l4_curation_sub_skill(self, spec):
        assert any(
            entry.endswith("common/l4-curation.md")
            for entry in spec["files"]
        ), (
            "spec must include references/sub-skills/common/l4-curation.md "
            "— the sub-skill prose whose comprehension is being tested"
        )

    def test_no_state_file_or_composed_output_references(self, spec):
        """The spec should test the SOURCE prose, not composed CLAUDE.md
        or .squidsquad/ runtime state. Composed output drifts with every
        deploy; the source is the contract.
        """
        banned = (".squidsquad/", "CLAUDE.md", "/installer-files.txt")
        for entry in spec["files"]:
            for b in banned:
                assert b not in entry, (
                    f"spec must not reference {b!r} — test the source "
                    f"sub-skill, not composed/state files. Got: {entry!r}"
                )
