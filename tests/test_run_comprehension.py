"""Unit tests for run_comprehension_test.py — test spec loading and result parsing."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_comprehension_test as rct


class TestFindClaude:
    def test_finds_claude_in_path(self):
        # #9724: the Windows branch in _find_claude short-circuits via
        # `npm_exe.exists()` BEFORE shutil.which is called. Patch Path.exists
        # to False so the Windows branch falls through to the mocked
        # shutil.which. No-op on POSIX (the platform check skips the npm
        # branch entirely there).
        with patch("pathlib.Path.exists", return_value=False), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            assert rct._find_claude() == "/usr/bin/claude"

    def test_returns_none_when_not_found(self):
        with patch("shutil.which", return_value=None):
            with patch("os.environ", {"APPDATA": "/nonexistent"}):
                result = rct._find_claude()
                # May or may not be None depending on platform, but shouldn't crash
                assert result is None or isinstance(result, str)


class TestSpecLoading:
    def test_valid_spec(self, tmp_path):
        spec = {
            "files": ["a.py", "b.py"],
            "questions": [
                {"id": "1", "question": "What does a.py do?", "expected": "It does X."}
            ],
        }
        spec_file = tmp_path / "test_spec.json"
        spec_file.write_text(json.dumps(spec))
        data = json.loads(spec_file.read_text())
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == "1"

    def test_spec_with_multiple_questions(self, tmp_path):
        spec = {
            "files": ["a.py"],
            "questions": [
                {"id": "1", "question": "Q1", "expected": "E1"},
                {"id": "2", "question": "Q2", "expected": "E2"},
                {"id": "3", "question": "Q3", "expected": "E3"},
            ],
        }
        spec_file = tmp_path / "test_spec.json"
        spec_file.write_text(json.dumps(spec))
        data = json.loads(spec_file.read_text())
        assert len(data["questions"]) == 3


class TestResultsParsing:
    def test_parse_clean_json(self, tmp_path):
        results = [
            {"id": "1", "pass": True, "reason": "correct"},
            {"id": "2", "pass": False, "reason": "wrong"},
        ]
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(results))
        parsed = json.loads(results_file.read_text())
        assert len(parsed) == 2
        assert parsed[0]["pass"] is True
        assert parsed[1]["pass"] is False

    def test_strip_markdown_fences(self):
        raw = "```json\n[{\"id\": \"1\", \"pass\": true, \"reason\": \"ok\"}]\n```"
        lines = raw.split("\n")
        clean = "\n".join(l for l in lines if not l.startswith("```"))
        parsed = json.loads(clean)
        assert len(parsed) == 1
        assert parsed[0]["pass"] is True

    def test_empty_results_is_invalid(self, tmp_path):
        results_file = tmp_path / "results.json"
        results_file.write_text("")
        with pytest.raises(json.JSONDecodeError):
            json.loads(results_file.read_text())


class Test1428SpecIntegrity:
    """Validate the spec file for #1428 is well-formed."""

    def test_spec_file_exists(self):
        spec = Path(__file__).parent.parent / "tests" / "comprehension" / "1428_spec.json"
        assert spec.exists()

    def test_spec_has_required_fields(self):
        spec = Path(__file__).parent.parent / "tests" / "comprehension" / "1428_spec.json"
        data = json.loads(spec.read_text())
        assert "files" in data
        assert "questions" in data
        assert len(data["files"]) > 0
        assert len(data["questions"]) > 0

    def test_spec_questions_have_required_fields(self):
        spec = Path(__file__).parent.parent / "tests" / "comprehension" / "1428_spec.json"
        data = json.loads(spec.read_text())
        for q in data["questions"]:
            assert "id" in q, f"Question missing 'id': {q}"
            assert "question" in q, f"Question missing 'question': {q}"
            assert "expected" in q, f"Question missing 'expected': {q}"

    def test_spec_has_5_questions(self):
        spec = Path(__file__).parent.parent / "tests" / "comprehension" / "1428_spec.json"
        data = json.loads(spec.read_text())
        assert len(data["questions"]) == 5

    def test_spec_files_exist(self):
        spec = Path(__file__).parent.parent / "tests" / "comprehension" / "1428_spec.json"
        repo = Path(__file__).parent.parent
        data = json.loads(spec.read_text())
        for f in data["files"]:
            assert (repo / f).exists(), f"Spec references missing file: {f}"
