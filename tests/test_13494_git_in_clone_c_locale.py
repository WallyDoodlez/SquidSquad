"""Regression for #13494 — _git_in_clone forces LC_ALL=C so git emits stable
English messages that the deploy-pull helpers branch on ("untracked files from
stash", "already up to date", "would be overwritten by merge"). Without a forced
locale, a non-English LANG/LC_MESSAGES on the operator's machine would silently
break those substring checks in deploy-critical code.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import harness  # noqa: E402


def test_git_in_clone_forces_lc_all_c():
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["env"] = kw.get("env")
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("harness.subprocess.run", side_effect=fake_run):
        harness._git_in_clone("/some/clone", ["status", "--porcelain"])

    assert captured["cmd"] == ["git", "status", "--porcelain"]
    assert captured["env"] is not None, "must pass an explicit env forcing the locale"
    assert captured["env"].get("LC_ALL") == "C"


def test_git_in_clone_preserves_existing_environment():
    marker_key = "SQUIDSQUAD_13494_MARKER"
    captured = {}

    def fake_run(cmd, **kw):
        captured["env"] = kw.get("env")
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch.dict(os.environ, {marker_key: "keepme"}), \
         patch("harness.subprocess.run", side_effect=fake_run):
        harness._git_in_clone("/some/clone", ["rev-parse", "HEAD"])

    # The forced-locale env is a SUPERSET of the process env, not a replacement —
    # git still needs PATH, HOME, credential config, etc.
    assert captured["env"].get(marker_key) == "keepme"
    assert captured["env"].get("LC_ALL") == "C"
