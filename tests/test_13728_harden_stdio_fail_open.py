"""Regression test for #13728 verifier round-1 finding.

git_ops.py's main() unconditionally did `from cli_stdio import harden_stdio;
harden_stdio()` -- when cli_stdio.py isn't co-located with git_ops.py (e.g. an
isolated copy, as the real end-to-end #13556 post-merge-hook test constructs),
this raised ModuleNotFoundError before command dispatch ever ran, breaking the
hook's documented "never raises" fail-safe guarantee
(TestPostMergeHookWiring13556.test_bare_merge_fires_hook_end_to_end). Fixed by
wrapping the import/call in try/except ImportError (fail open).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


class TestHardenStdioFailsOpen13728:
    def test_missing_cli_stdio_does_not_crash_main(self):
        """Simulate cli_stdio.py being absent (sys.modules[name] = None makes
        `from cli_stdio import harden_stdio` raise ImportError, matching what
        happens when the module truly can't be found on sys.path)."""
        with patch.dict(sys.modules, {"cli_stdio": None}), \
                patch.object(sys, "argv", ["git_ops.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                git_ops.main()
        assert exc_info.value.code == 0

    def test_present_cli_stdio_still_hardens(self):
        """Sanity: when cli_stdio IS importable, main() still calls harden_stdio()
        (no regression to the #13198 crash-proofing itself)."""
        with patch("cli_stdio.harden_stdio") as mock_harden, \
                patch.object(sys, "argv", ["git_ops.py", "--help"]):
            with pytest.raises(SystemExit):
                git_ops.main()
        mock_harden.assert_called_once()
