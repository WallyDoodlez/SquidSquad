"""Regression test for #7794: prohibitions must not reference stale 'tracker files' concept.

GitHub Issues is the single source of truth. The prohibition 'Never delete entries
from tracker files' is stale — it must name actual artifacts instead.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROHIBITIONS_DIR = REPO_ROOT / "references" / "sub-skills" / "roles"


class TestNoStaleTrackerFilesRef:
    """Prohibitions must not reference the obsolete 'tracker files' concept."""

    @pytest.mark.parametrize("role", ["pm", "dm"])
    def test_prohibitions_no_stale_tracker_files(self, role):
        """Prohibition 'Never delete entries from tracker files' must not exist."""
        path = PROHIBITIONS_DIR / role / "prohibitions.md"
        content = path.read_text(encoding="utf-8")
        assert "from tracker files" not in content

    def test_pm_prohibitions_names_actual_files(self):
        """PM prohibitions must name qa-log.md and enhancements.md."""
        path = PROHIBITIONS_DIR / "pm" / "prohibitions.md"
        content = path.read_text(encoding="utf-8")
        assert "qa-log.md" in content
        assert "enhancements.md" in content
        assert "GitHub Issue comments" in content

    def test_dm_prohibitions_names_actual_files(self):
        """DM prohibitions must name actual append-only files."""
        path = PROHIBITIONS_DIR / "dm" / "prohibitions.md"
        content = path.read_text(encoding="utf-8")
        assert "append-only" in content.lower() or "append only" in content.lower()
        assert "GitHub Issue comments" in content
