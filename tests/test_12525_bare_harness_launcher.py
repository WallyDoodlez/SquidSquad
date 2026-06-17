"""Contract tests for the bare-harness launchers (#12525).

`start-harness.sh` / `start-harness.bat` bring up ONLY the harness, with no
clone-sync and no dep-install (unlike the full start.sh / start.ps1). The
visible-window / double-click behaviour (AC1/AC2) is OS-level and not
unit-testable; these tests pin the deterministic contract: the right harness
invocation, the absence of any git/pip step (AC3), manifest membership (AC4),
and that the existing full launchers are untouched (AC5).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SH = REPO_ROOT / "start-harness.sh"
BAT = REPO_ROOT / "start-harness.bat"
MANIFEST = REPO_ROOT / "references" / "installer-files.txt"

# Any git/pip/clone-sync footprint that would betray the "bare" contract.
_HEAVYWEIGHT = re.compile(
    r"\bgit\b|\bpip\b|pip3|--rebase|requirements\.txt|ensurepip|apt\b|brew\b|"
    r"\.local-config|Sync",
    re.IGNORECASE,
)


def _exec_lines(text, comment_prefix):
    """Executable (non-comment, non-blank) lines only. The header prose
    legitimately names git/pip/start.ps1 to explain what the bare launcher
    avoids — the contract checks must look at the COMMANDS, not the comments."""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.upper().startswith(comment_prefix.upper()):
            continue
        out.append(ln)
    return "\n".join(out)


class TestFilesExist:
    def test_sh_present(self):
        assert SH.is_file(), "start-harness.sh must exist at repo root"

    def test_bat_present(self):
        assert BAT.is_file(), "start-harness.bat must exist at repo root"


class TestShContract:
    def text(self):
        return SH.read_text(encoding="utf-8")

    def test_runs_harness_in_foreground(self):
        # exec → foreground (AC2); targets references/scripts/harness.py.
        assert "references/scripts/harness.py" in self.text()
        assert "exec python3" in self.text()

    def test_cds_to_script_dir(self):
        assert 'cd "$(dirname "$0")"' in self.text()

    def test_no_git_or_pip(self):
        # AC3 — no clone-sync, no dep-install (scan commands, not the header).
        hits = _HEAVYWEIGHT.findall(_exec_lines(self.text(), "#"))
        assert not hits, f"start-harness.sh must not git/pip/sync; found {hits}"

    def test_documents_distinction(self):
        # AC4 — header explains bare vs full launcher.
        assert "BARE" in self.text() and "start.sh" in self.text()


class TestBatContract:
    def text(self):
        return BAT.read_text(encoding="utf-8")

    def test_runs_harness(self):
        assert r"references\scripts\harness.py" in self.text()

    def test_window_stays_open(self):
        # AC1 — persistent visible window.
        assert "pause" in self.text()

    def test_cds_to_script_dir(self):
        assert "cd /d \"%~dp0\"" in self.text()

    def test_no_git_or_pip(self):
        # AC3 — scan commands, not the REM header (which names what it avoids).
        hits = _HEAVYWEIGHT.findall(_exec_lines(self.text(), "REM"))
        assert not hits, f"start-harness.bat must not git/pip/sync; found {hits}"

    def test_does_not_delegate_to_ps1(self):
        # The bare launcher runs python directly, not via start.ps1 (the header
        # may MENTION start.ps1 to explain the distinction — check commands only).
        assert "start.ps1" not in _exec_lines(self.text(), "REM")

    def test_documents_distinction(self):
        assert "BARE" in self.text() and "start.ps1" in self.text()


class TestManifest:
    def text(self):
        return MANIFEST.read_text(encoding="utf-8")

    def test_both_listed(self):
        # AC4 — ship with installs. One path per line.
        lines = {ln.strip() for ln in self.text().splitlines()}
        assert "start-harness.sh" in lines
        assert "start-harness.bat" in lines

    def test_count_header_matches_payload(self):
        text = self.text()
        m = re.search(r"# Total:\s*(\d+)\s*files", text)
        assert m, "manifest must carry a `# Total: N files` header"
        declared = int(m.group(1))
        payload = [
            ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        ]
        assert declared == len(payload), (
            f"header says {declared} files but manifest lists {len(payload)}"
        )


class TestFullLaunchersUntouched:
    """AC5 — the existing full-setup launchers keep their sync + dep logic."""

    def test_start_sh_still_full(self):
        text = (REPO_ROOT / "start.sh").read_text(encoding="utf-8")
        assert "requirements.txt" in text  # still installs deps
        assert "git pull --rebase" in text  # still syncs clones

    def test_start_ps1_still_full(self):
        # start.bat delegates to start.ps1, so a stripped start.ps1 would regress
        # the full-setup path undetected — assert its sync+dep logic survives too.
        ps1 = REPO_ROOT / "start.ps1"
        assert ps1.is_file()
        text = ps1.read_text(encoding="utf-8")
        assert "requirements.txt" in text  # still installs deps
        assert "git pull --rebase" in text  # still syncs clones
