"""#12526 — start.ps1 / start.sh clone-sync must NOT use `git pull --rebase`.

The standing operator rule is "never rebase, always merge" (rebase rewrites
history and is fragile on Windows-MSYS2). The launchers synced each agent clone
with `git pull --rebase`, contradicting it. This test locks the fix: no launcher
uses --rebase for its clone/primary sync, and the merge form is used instead.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
START_PS1 = REPO_ROOT / ".squidsquad" / "start.ps1"
START_SH = REPO_ROOT / ".squidsquad" / "start.sh"


@pytest.mark.parametrize("script", [START_PS1, START_SH])
def test_launcher_has_no_rebase_pull(script):
    text = script.read_text(encoding="utf-8")
    assert "pull --rebase" not in text, (
        f"{script.name} uses `git pull --rebase` — violates the never-rebase "
        f"rule (#12526); use `git pull --no-rebase`."
    )
    # Belt-and-suspenders: no bare `--rebase` flag anywhere in the launcher.
    assert not re.search(r"--rebase\b", text), \
        f"{script.name} still references --rebase (#12526)"


@pytest.mark.parametrize("script", [START_PS1, START_SH])
def test_launcher_uses_merge_pull(script):
    """Every clone-sync `git pull` is the explicit merge form (--no-rebase),
    so a clone with `pull.rebase=true` configured can't silently rebase."""
    text = script.read_text(encoding="utf-8")
    pulls = re.findall(r"git pull[^\n|&]*", text)
    assert pulls, f"{script.name} has no `git pull` sync line"
    for p in pulls:
        assert "--no-rebase" in p, \
            f"{script.name}: sync pull `{p.strip()}` must use --no-rebase (#12526)"
