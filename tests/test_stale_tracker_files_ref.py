"""Regression test for #7794: prohibitions must not reference stale 'tracker files' concept.

GitHub Issues is the single source of truth. The prohibition 'Never delete entries
from tracker files' is stale — it must name actual artifacts instead.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
# #11503 rebind: per-role prohibitions.md files were retired in #11087
# (content inlined into each role's instructions.md per #11049 Path A D1
# with <!-- sub-skill: prohibitions --> markers).  Point checks at the
# instructions.md files where the content now lives.
INSTRUCTIONS_DIR = REPO_ROOT / "references" / "roles"


class TestNoStaleTrackerFilesRef:
    """Prohibitions content must not reference the obsolete 'tracker files' concept."""

    @pytest.mark.parametrize("role", ["pm", "dm"])
    def test_prohibitions_no_stale_tracker_files(self, role):
        """Prohibition 'Never delete entries from tracker files' must not exist.

        #11503 rebind: prohibitions.md retired; content lives in
        references/roles/<role>/instructions.md.
        """
        path = INSTRUCTIONS_DIR / role / "instructions.md"
        content = path.read_text(encoding="utf-8")
        assert "from tracker files" not in content

    def test_pm_prohibitions_names_actual_files(self):
        """PM prohibitions must name qa-log.md and enhancements.md.

        #11503 rebind: prohibitions.md retired; content lives in
        references/roles/pm/instructions.md.
        """
        path = INSTRUCTIONS_DIR / "pm" / "instructions.md"
        content = path.read_text(encoding="utf-8")
        assert "qa-log.md" in content
        assert "enhancements.md" in content
        assert "GitHub Issue comments" in content

    def test_dm_prohibitions_names_actual_files(self):
        """DM prohibitions must name actual append-only files.

        #11503 rebind: prohibitions.md retired; content lives in
        references/roles/dm/instructions.md.
        """
        path = INSTRUCTIONS_DIR / "dm" / "instructions.md"
        content = path.read_text(encoding="utf-8")
        assert "append-only" in content.lower() or "append only" in content.lower()
        assert "GitHub Issue comments" in content
