"""#13318 — single consolidated launcher per platform.

Pins the consolidation contract that the per-behavior tests (#12525 bare, #12526
no-rebase, #12825 supervised loop) don't cover directly:

- **AC1** — exactly TWO launchers remain, at ``.squidsquad/start.ps1`` +
  ``.squidsquad/start.sh``; the old root launchers are gone.
- **AC3** — the full-mode path bundles the TUI (references/tui/app.py) and is
  singleton-safe (probes /status before launching, attaches instead of
  double-starting).
- **AC7 enabler** — the two launchers are CODE deliverables exempt from the
  ``.squidsquad/`` state-strip (git_ops._is_launcher_script), so they ship through
  the normal feature-branch PR flow.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

START_SH = REPO_ROOT / ".squidsquad" / "start.sh"
START_PS1 = REPO_ROOT / ".squidsquad" / "start.ps1"

_DELETED = [
    "start.bat", "start.sh", "start.ps1",          # old root launchers (moved)
    "start-harness.sh", "start-harness.bat",        # old bare launchers
    "restart-harness.sh", "restart-harness.bat",    # old supervised launchers
]


class TestSingleEntrypoint:
    """AC1 — only the two consolidated launchers remain."""

    def test_consolidated_launchers_exist(self):
        assert START_SH.is_file()
        assert START_PS1.is_file()

    def test_old_root_launchers_removed(self):
        for name in _DELETED:
            assert not (REPO_ROOT / name).exists(), (
                f"{name} must be deleted — repo root has no launcher scripts (#13318)"
            )


class TestFullBringUp:
    """AC2/AC3 — full mode keeps deps+sync and bundles the TUI."""

    def sh(self):
        return START_SH.read_text(encoding="utf-8")

    def ps1(self):
        return START_PS1.read_text(encoding="utf-8")

    def test_sh_bundles_tui(self):
        # AC3 — full mode launches the TUI after the harness is up.
        assert "references/tui/app.py" in self.sh()

    def test_ps1_bundles_tui(self):
        assert "references/tui/app.py" in self.ps1()

    def test_sh_singleton_probe(self):
        # AC3 — probes /status so a second invocation attaches rather than
        # double-starting the harness.
        t = self.sh()
        assert "/status" in t
        assert "harness_up" in t

    def test_ps1_singleton_probe(self):
        t = self.ps1()
        assert "/status" in t
        assert "Test-HarnessUp" in t

    def test_sh_detaches_harness_for_tui_foreground(self):
        # AC4/AC6 — harness+supervisor run detached (nohup) so quitting the
        # foreground TUI leaves the fleet running.
        assert "nohup" in self.sh()

    def test_ps1_detaches_harness_for_tui_foreground(self):
        # PowerShell detaches via Start-Process (independent process).
        assert "Start-Process" in self.ps1()

    def test_both_resolve_repo_root_from_squidsquad(self):
        # Scripts live in .squidsquad/; they must cd up to the project repo root.
        assert 'dirname "$0"' in self.sh()           # then "/.." in bash
        assert "Split-Path -Parent" in self.ps1()    # parent-of-parent in ps1


class TestGitOpsLauncherCarveOut:
    """AC7 enabler — the two launchers are committable CODE (not .squidsquad/ state)."""

    def test_launchers_are_not_state_files(self):
        import git_ops
        assert git_ops._is_state_file(".squidsquad/start.sh") is False
        assert git_ops._is_state_file(".squidsquad/start.ps1") is False

    def test_other_squidsquad_paths_still_state(self):
        # The carve-out must stay narrow — never re-open the #11511 state leak.
        import git_ops
        assert git_ops._is_state_file(".squidsquad/skill/working-state.md") is True
        assert git_ops._is_state_file(".squidsquad/config.md") is True
        assert git_ops._is_state_file(".squidsquad/statusline.sh") is True
        assert git_ops._is_state_file(".squidsquad/start.sh.bak") is True  # not exact match

    def test_launcher_helper_is_exact_match_only(self):
        import git_ops
        assert git_ops._is_launcher_script(".squidsquad/start.sh") is True
        assert git_ops._is_launcher_script(".squidsquad/start.ps1") is True
        # #13577: the launcher's permissions helper is versioned CODE too — its
        # omission silently stripped a bug-fix commit from a feature branch.
        assert git_ops._is_launcher_script(
            ".squidsquad/inject-permissions.ps1") is True
        assert git_ops._is_launcher_script(".squidsquad/sub/start.sh") is False
        assert git_ops._is_launcher_script("start.sh") is False
        assert git_ops._is_launcher_script(
            ".squidsquad/inject-permissions.ps1.bak") is False
