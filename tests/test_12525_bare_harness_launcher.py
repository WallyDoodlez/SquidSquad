"""Contract tests for the bare-harness path (#12525, consolidated into #13318).

The bare path used to be standalone files (start-harness.sh / start-harness.bat);
#13318 folded it into a ``--bare`` / ``--no-setup`` flag on the single consolidated
launchers ``.squidsquad/start.sh`` and ``.squidsquad/start.ps1``. In bare mode the
launcher brings up ONLY the harness (under the supervised loop) with no clone-sync,
no dep-install, and no TUI. The visible-window / double-click behaviour is OS-level
and not unit-testable; these tests pin the deterministic contract: bare mode runs
the harness via the supervised loop, the bare execution path carries no git/pip step
(AC3), manifest membership (AC4), and that the full-mode dep+sync logic still lives
in the consolidated scripts (AC5).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
START_SH = REPO_ROOT / ".squidsquad" / "start.sh"
START_PS1 = REPO_ROOT / ".squidsquad" / "start.ps1"
MANIFEST = REPO_ROOT / "references" / "installer-files.txt"


class TestFilesExist:
    def test_consolidated_sh_present(self):
        assert START_SH.is_file(), ".squidsquad/start.sh must exist"

    def test_consolidated_ps1_present(self):
        assert START_PS1.is_file(), ".squidsquad/start.ps1 must exist"


class TestShContract:
    def text(self):
        return START_SH.read_text(encoding="utf-8")

    def test_runs_harness_in_foreground(self):
        # Bare mode runs the supervised loop, which invokes HARNESS_CMD
        # (default: python3 references/scripts/harness.py) in the foreground.
        assert "references/scripts/harness.py" in self.text()
        assert "run_supervised" in self.text()

    def test_resolves_repo_root_from_script_dir(self):
        # Script lives in .squidsquad/; it must resolve repo root from its own dir.
        assert 'dirname "$0"' in self.text()

    def test_bare_block_skips_deps_and_sync(self):
        # AC3 — the --bare branch must not run deps/clone-sync (it only runs the
        # supervised loop). Scan the bare-mode block, not the whole file (the file
        # also contains the full-mode ensure_deps/sync_clones git/pip code).
        m = re.search(
            r'if \[ "\$BARE" -eq 1 \].*?^fi',
            self.text(), re.DOTALL | re.MULTILINE,
        )
        assert m, "bare-mode block not found in start.sh"
        bare_block = m.group(0)
        assert "ensure_deps" not in bare_block
        assert "sync_clones" not in bare_block
        assert "git pull" not in bare_block
        assert "pip" not in bare_block

    def test_documents_distinction(self):
        # Header names the #12525 bare path on the consolidated script.
        assert "bare mode (#12525)" in self.text()


class TestPs1BareContract:
    def text(self):
        return START_PS1.read_text(encoding="utf-8")

    def test_runs_harness(self):
        # Harness path appears in the default HARNESS_CMD value.
        assert "references/scripts/harness.py" in self.text()

    def test_bare_mode_calls_invoke_supervised(self):
        # AC2 — bare mode runs the supervised loop in the foreground.
        assert "Invoke-Supervised" in self.text()

    def test_resolves_repo_root(self):
        # Script is in .squidsquad/; it must navigate up to repo root.
        assert "Split-Path -Parent" in self.text()

    def test_bare_block_skips_deps_and_sync(self):
        # AC3 — the if ($Bare) block must not run deps/clone-sync.
        m = re.search(r'if \(\$Bare\)\s*\{.*?\n\}', self.text(), re.DOTALL)
        assert m, "bare-mode block not found in start.ps1"
        bare_block = m.group(0)
        assert "Initialize-Deps" not in bare_block
        assert "Sync-Clones" not in bare_block
        assert "git pull" not in bare_block
        assert "pip" not in bare_block

    def test_documents_distinction(self):
        assert "bare mode (#12525)" in self.text()


class TestManifest:
    def text(self):
        return MANIFEST.read_text(encoding="utf-8")

    def test_both_listed(self):
        # AC4 — the consolidated launchers ship with installs. One path per line.
        lines = {ln.strip() for ln in self.text().splitlines()}
        assert ".squidsquad/start.sh" in lines
        assert ".squidsquad/start.ps1" in lines

    def test_deleted_launchers_not_listed(self):
        # The consolidated scripts replaced these; the manifest must not ship them.
        lines = {ln.strip() for ln in self.text().splitlines()}
        for gone in ("start.sh", "start.ps1", "start-harness.sh",
                     "start-harness.bat", "restart-harness.sh", "restart-harness.bat"):
            assert gone not in lines, f"deleted launcher still in manifest: {gone}"

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
    """AC5 — the consolidated launchers still carry full-mode deps + sync logic."""

    def test_start_sh_still_full(self):
        text = START_SH.read_text(encoding="utf-8")
        assert "requirements.txt" in text  # still installs deps
        assert "git pull --no-rebase" in text  # still syncs clones (#12526: merge, not rebase)

    def test_start_ps1_still_full(self):
        assert START_PS1.is_file()
        text = START_PS1.read_text(encoding="utf-8")
        assert "requirements.txt" in text  # still installs deps
        assert "git pull --no-rebase" in text  # still syncs clones (#12526: merge, not rebase)
