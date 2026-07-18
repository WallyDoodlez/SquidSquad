"""Regression test for #13356 — the boot 'Check harness reachability' step
resolved the harness port from .squidsquad/.harness-port and probed ONLY
that port; any probe failure fell through straight to POLLING mode for the
whole session. A stale-but-valid-looking leaked port file (e.g. 8251 while
the harness is actually live on the default 7373) would silently downgrade
a healthy session to polling with no way to notice short of manually
diffing the running port.

The fix adds a fallback retry against the harness default port 7373 when
the port-file-resolved port fails and differs from 7373, before declaring
the harness unreachable.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTIONS_FILE = REPO_ROOT / "references" / "roles" / "instructions.md"


@pytest.fixture
def instructions_text():
    assert INSTRUCTIONS_FILE.exists(), f"instructions.md missing: {INSTRUCTIONS_FILE}"
    return INSTRUCTIONS_FILE.read_text(encoding="utf-8")


def _reachability_section(text):
    idx = text.index("#### Check harness reachability")
    end = text.index("#### EVENT mode", idx)
    return text[idx:end]


class TestHarnessProbeFallback13356:
    def test_fallback_retry_against_default_port_present(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "7373" in section
        assert "retry" in section.lower()

    def test_fallback_only_when_resolved_port_differs(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "skip this retry" in section.lower() or "already `7373`" in section

    def test_either_probe_succeeding_confirms_event_mode(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "either probe succeeds" in section.lower()

    def test_both_probes_failing_falls_through_to_polling(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "both probes fail" in section.lower()

    def test_stale_port_mismatch_surfaced_as_diagnostic(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "diagnostic" in section.lower()
        assert "mismatch" in section.lower()

    def test_references_issue_13356(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert "13356" in section

    def test_original_port_file_default_logic_unchanged(self, instructions_text):
        section = _reachability_section(instructions_text)
        assert (
            "default port to `7373` (the harness default — see "
            "`cycle_post.py:_discover_harness_port`)"
        ) in section
