"""Validate tests/comprehension/8694_spec.json (#8915 / TEST-PLAN-8694.md §3.6).

These tests cover the spec-file integrity refinements:

- AC-1 M-1.1 — file exists; parses as JSON; matches the expected schema.
- AC-1 M-1.2 — covers the six CONTEXT.md-mandated scenarios (mid-task event,
  unknown event, empty work_queue, DM end-of-task comments, comment route-back,
  scan-running boot) plus enough additional questions to reach ≥8 total.
- AC-4 M-4.1 — `files` list contains ONLY fragments under
  `references/sub-skills/common-events/` or per-role
  `references/sub-skills/roles/<role>/events/` (no L4, no SOUL, no CONTEXT.md).

M-1.3 (the actual fresh-agent comprehension run via
`run_comprehension_test.py`) is left to QA — it requires a live model call.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "tests" / "comprehension" / "8694_spec.json"


@pytest.fixture(scope="module")
def spec():
    assert SPEC_PATH.exists(), f"missing spec: {SPEC_PATH}"
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# AC-1 M-1.1 — file exists and matches schema
# ---------------------------------------------------------------------------


class TestSpecSchema:
    def test_spec_is_valid_json(self):
        json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    def test_required_top_level_keys(self, spec):
        assert set(spec.keys()) >= {"issue", "title", "files", "questions"}

    def test_issue_is_int(self, spec):
        assert isinstance(spec["issue"], int)
        assert spec["issue"] == 8694

    def test_title_is_string(self, spec):
        assert isinstance(spec["title"], str)
        assert spec["title"].strip(), "title must be non-empty"

    def test_files_is_list_of_strings(self, spec):
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
# AC-1 M-1.2 — covers the six required scenarios + ≥8 questions
# ---------------------------------------------------------------------------


class TestRequiredScenarioCoverage:
    """At least one question must match each CONTEXT-mandated topic."""

    REQUIRED_TOPICS = [
        # (label, regex matched against id + question text, case-insensitive)
        ("mid-task event", r"mid.?task|case d\b"),
        ("unknown event", r"unknown\s+event|unrecogni[sz]ed"),
        ("empty work_queue", r"empty.*work.?queue|work.?queue.*empty"),
        ("DM end-of-task comments",
         r"\bdm\b.*comment|comment.*\bdm\b|pr.?merge.*comment|merge.*wait.*comment"),
        ("comment-driven route-back",
         r"comment.*hand|route.?back|comment.*role|hand.*back|hand.*work"),
        ("scan-running boot",
         r"scan.*running|status:\s*running|status.?running|scan.?running\s+boot"),
    ]

    @pytest.mark.parametrize("label,regex", REQUIRED_TOPICS)
    def test_topic_covered_by_at_least_one_question(self, spec, label, regex):
        for q in spec["questions"]:
            blob = f"{q['id']} {q['question']}"
            if re.search(regex, blob, re.IGNORECASE):
                return
        pytest.fail(
            f"No question covers required scenario {label!r} "
            f"(regex /{regex}/). Have ids: {[q['id'] for q in spec['questions']]}"
        )

    def test_at_least_eight_questions(self, spec):
        assert len(spec["questions"]) >= 8, (
            f"spec must have ≥8 questions; has {len(spec['questions'])}"
        )


# ---------------------------------------------------------------------------
# AC-4 M-4.1 — files reference only event-mode fragments
# ---------------------------------------------------------------------------


class TestFilesOnlyEventFragments:
    ALLOWED_PREFIXES = (
        "references/sub-skills/common-events/",
        "references/sub-skills/roles/",  # per-role events/ subdir
    )

    BANNED_SUBSTRINGS = (
        "CONTEXT.md",
        "/SOUL.md",
        ".squidsquad/",
        "references/sub-skills/common/",
        "references/sub-skills/common-loop/",
    )

    def test_every_path_starts_with_allowed_prefix(self, spec):
        for entry in spec["files"]:
            assert any(entry.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"file {entry!r} must start with one of {self.ALLOWED_PREFIXES}"
            )

    def test_no_banned_substrings_in_files(self, spec):
        for entry in spec["files"]:
            for banned in self.BANNED_SUBSTRINGS:
                assert banned not in entry, (
                    f"file {entry!r} contains banned substring {banned!r}"
                )

    def test_role_paths_use_events_subdir(self, spec):
        # If any file lives under references/sub-skills/roles/<role>/, it MUST
        # be inside an events/ subdir — never a sibling of loop/ fragments.
        for entry in spec["files"]:
            if entry.startswith("references/sub-skills/roles/"):
                assert "/events/" in entry, (
                    f"per-role spec file must be under events/: {entry!r}"
                )

    def test_every_listed_file_exists(self, spec):
        for entry in spec["files"]:
            path = REPO_ROOT / entry
            assert path.exists(), f"spec lists nonexistent file: {entry}"
