"""Tests for references/scripts/comprehension_staleness.py (#13709, #13710).

#13709: _PATH_RE's extension whitelist omitted `j2`, so a spec naming a
Jinja2 template (e.g. references/prompts/test-plan.md.j2) had that fragment
silently dropped from staleness tracking.

#13710: refresh()'s summary line and exit code both looked like success even
when every requested spec name failed to resolve (e.g. bare issue numbers
instead of the required "<N>_spec.json" filenames).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comprehension_staleness as cs


# ---------------------------------------------------------------------------
# #13709 — .j2 extension tracking
# ---------------------------------------------------------------------------

class TestJ2ExtensionTracking:
    def test_j2_fragment_is_matched_by_path_re(self):
        matches = cs._PATH_RE.findall(
            "references/prompts/test-plan.md.j2 is the template")
        assert "references/prompts/test-plan.md.j2" in matches

    def test_j2_fragment_survives_spec_fragment_paths(self, tmp_path):
        real_file = tmp_path / "references" / "prompts" / "test-plan.md.j2"
        real_file.parent.mkdir(parents=True)
        real_file.write_text("template body\n", encoding="utf-8")

        with patch.object(cs, "REPO_ROOT", tmp_path):
            frags = cs.spec_fragment_paths(
                {"files": ["references/prompts/test-plan.md.j2"]})
        assert frags == ["references/prompts/test-plan.md.j2"]

    def test_non_j2_extensions_still_work(self, tmp_path):
        real_file = tmp_path / "docs" / "ARCH.md"
        real_file.parent.mkdir(parents=True)
        real_file.write_text("doc body\n", encoding="utf-8")

        with patch.object(cs, "REPO_ROOT", tmp_path):
            frags = cs.spec_fragment_paths({"files": ["docs/ARCH.md"]})
        assert frags == ["docs/ARCH.md"]

    def test_1428_spec_now_tracks_test_plan_j2(self):
        """Regression: the real 1428_spec.json lists test-plan.md.j2 among
        its files -- before the fix this fragment was silently dropped."""
        spec = cs.load_specs()["1428_spec.json"]
        frags = cs.spec_fragment_paths(spec)
        assert "references/prompts/test-plan.md.j2" in frags


# ---------------------------------------------------------------------------
# #13710 — refresh() accurate reporting + exit code
# ---------------------------------------------------------------------------

@pytest.fixture
def spec_dir(tmp_path):
    """An isolated tests/comprehension/-shaped dir with two valid specs
    naming real, tracked files in the actual repo (so committed_blob_sha
    resolves against the real git history)."""
    d = tmp_path / "comprehension"
    d.mkdir()
    for name, target in [
        ("aaa_spec.json", "references/scripts/comprehension_staleness.py"),
        ("bbb_spec.json", "references/scripts/tracker.py"),
    ]:
        (d / name).write_text(
            json.dumps({"issue": 1, "title": "t", "files": [target],
                        "questions": []}),
            encoding="utf-8",
        )
    baseline = d / ".staleness-baseline.json"
    baseline.write_text("{}", encoding="utf-8")
    return d, baseline


class TestRefreshReturnValue:
    def test_all_names_valid_returns_empty_failed_list(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline):
            failed = cs.refresh(["aaa_spec.json", "bbb_spec.json"])
        assert failed == []
        written = json.loads(baseline.read_text(encoding="utf-8"))
        assert set(written) == {"aaa_spec.json", "bbb_spec.json"}

    def test_all_names_invalid_returns_all_as_failed(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline):
            failed = cs.refresh(["1428", "13464", "10678"])
        assert failed == ["1428", "13464", "10678"]
        # Nothing should have been added to the baseline for invalid names.
        written = json.loads(baseline.read_text(encoding="utf-8"))
        assert written == {}

    def test_partial_failure_reports_only_failed_names(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline):
            failed = cs.refresh(["aaa_spec.json", "nonexistent_spec.json"])
        assert failed == ["nonexistent_spec.json"]
        written = json.loads(baseline.read_text(encoding="utf-8"))
        assert set(written) == {"aaa_spec.json"}

    def test_summary_message_reports_actual_over_requested_count(self, spec_dir, capsys):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline):
            cs.refresh(["aaa_spec.json", "bogus_spec.json"])
        out = capsys.readouterr().out
        assert "1/2" in out


class TestMainRefreshExitCode:
    def test_main_exits_nonzero_when_all_names_invalid(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline), \
             patch.object(sys, "argv", ["comprehension_staleness.py", "refresh",
                                        "1428", "13464"]):
            with pytest.raises(SystemExit) as exc:
                cs.main()
        assert exc.value.code == 1

    def test_main_exits_zero_when_all_names_valid(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline), \
             patch.object(sys, "argv", ["comprehension_staleness.py", "refresh",
                                        "aaa_spec.json", "bbb_spec.json"]):
            with pytest.raises(SystemExit) as exc:
                cs.main()
        assert exc.value.code == 0

    def test_main_exits_nonzero_on_partial_failure(self, spec_dir):
        d, baseline = spec_dir
        with patch.object(cs, "SPEC_DIR", d), patch.object(cs, "BASELINE", baseline), \
             patch.object(sys, "argv", ["comprehension_staleness.py", "refresh",
                                        "aaa_spec.json", "bogus_spec.json"]):
            with pytest.raises(SystemExit) as exc:
                cs.main()
        assert exc.value.code == 1
