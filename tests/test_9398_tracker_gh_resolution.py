"""Unit tests for the #9398 ``tracker._resolve_gh_bin`` patch.

Background: on Windows, ``subprocess.run([\"gh\", ...])`` uses
``CreateProcessW`` for executable lookup, which only directly
executes ``.exe`` and ``.com`` files. ``.cmd`` and ``.bat`` files
in PATH get skipped. The #9398 Phase A PATH-shim ships ``gh.cmd``;
without the patch, the real ``gh.exe`` always wins.

The patch (``references/scripts/tracker.py``):
- ``_resolve_gh_bin()`` calls ``shutil.which(\"gh\")`` once and
  caches the result. ``shutil.which`` IS PATHEXT-aware on Windows,
  so it finds ``gh.cmd`` when it's first in PATH.
- ``_run_list(cmd_list)`` substitutes ``\"gh\"`` (the literal first
  element) with the resolved path before invoking subprocess.

This is the same fix-shape as ``run_comprehension_test._find_claude``
shipped via #9574 for the ``claude`` CLI under the same root cause.

Tests pin:
1. ``_resolve_gh_bin`` returns a string.
2. With a custom PATH that prepends a directory containing ``gh.cmd``
   AND no ``gh.exe``, the resolved path points at the .cmd.
3. ``_run_list([\"gh\", ...])`` does the substitution; non-``gh``
   commands pass through unchanged.
4. The cache is sticky within a process (subsequent calls return the
   first resolution).
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKER_PATH = REPO_ROOT / "references" / "scripts" / "tracker.py"


def _fresh_tracker(env: dict | None = None):
    """Load a fresh copy of tracker.py with a controlled os.environ.

    Each test gets its own module instance so the
    ``_RESOLVED_GH_BIN`` module-level cache doesn't leak across
    tests. We patch ``os.environ`` BEFORE the import so any
    module-level reads happen in the controlled env."""
    with mock.patch.dict(os.environ, env or {}, clear=False):
        spec = importlib.util.spec_from_file_location(
            f"_tracker_{id(env)}", TRACKER_PATH
        )
        if not (spec and spec.loader):
            raise ImportError(f"cannot load {TRACKER_PATH}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


class TestResolveGhBin(unittest.TestCase):
    def test_returns_string(self):
        mod = _fresh_tracker()
        got = mod._resolve_gh_bin()
        self.assertIsInstance(got, str)
        self.assertTrue(got, msg="_resolve_gh_bin must not return empty")

    def test_picks_up_path_prepended_cmd_on_windows(self):
        """On Windows, prepend a dir containing only ``gh.cmd`` to
        PATH; resolution must find it via PATHEXT instead of any
        real ``gh.exe`` deeper in the PATH chain. This is the load-
        bearing assertion — without it, the #9398 PATH-shim never
        gets hit by tracker.py invocations."""
        if sys.platform != "win32":
            self.skipTest("PATHEXT precedence is Windows-specific")
        with tempfile.TemporaryDirectory(prefix="ghshim-") as tmp:
            shim_dir = Path(tmp)
            # Create a no-op gh.cmd in the shim dir.
            (shim_dir / "gh.cmd").write_text(
                "@echo gh-cmd-shim\n", encoding="utf-8"
            )
            # Keep the patched env in scope for the _resolve_gh_bin
            # call too — shutil.which reads os.environ['PATH'] at
            # call time, NOT at module load.
            patched_path = (
                str(shim_dir) + os.pathsep + os.environ.get("PATH", "")
            )
            with mock.patch.dict(os.environ, {"PATH": patched_path}):
                mod = _fresh_tracker()
                got = mod._resolve_gh_bin()
            self.assertEqual(
                Path(got).resolve(), (shim_dir / "gh.cmd").resolve(),
                msg=(
                    f"_resolve_gh_bin must find the shim's gh.cmd "
                    f"when prepended to PATH (#9398). Got: {got!r}"
                ),
            )

    def test_cache_is_sticky_within_process(self):
        """Repeated calls return the same result — a different
        underlying CLI install path showing up mid-process won't
        cause confusing inconsistency between calls."""
        mod = _fresh_tracker()
        first = mod._resolve_gh_bin()
        # Mutate PATH after first resolution.
        with mock.patch.dict(os.environ, {"PATH": ""}, clear=False):
            second = mod._resolve_gh_bin()
        self.assertEqual(first, second)


class TestRunListSubstitutesGh(unittest.TestCase):
    def test_first_arg_gh_substituted_with_resolved_bin(self):
        """``_run_list([\"gh\", ...])`` must replace ``\"gh\"`` with
        the resolved path before invoking subprocess. Without this
        substitution the PATH-shim is bypassed (the #9398 bug)."""
        mod = _fresh_tracker()
        # Pin the resolver to a sentinel so we can detect substitution.
        mod._RESOLVED_GH_BIN = "/sentinel/path/to/gh"

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            class _R:
                stdout = ""
                stderr = ""
                returncode = 0
            return _R()

        with mock.patch.object(mod.subprocess, "run", side_effect=fake_run):
            mod._run_list(["gh", "issue", "list", "--limit", "1"])

        self.assertEqual(captured["cmd"][0], "/sentinel/path/to/gh")
        # Rest of args preserved as-is.
        self.assertEqual(
            captured["cmd"][1:],
            ["issue", "list", "--limit", "1"],
        )

    def test_non_gh_first_arg_passes_through_unchanged(self):
        """Substitution only triggers on the literal ``\"gh\"``
        — other commands (rare in tracker.py but possible) are
        unaffected."""
        mod = _fresh_tracker()
        mod._RESOLVED_GH_BIN = "/sentinel/path/to/gh"
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            class _R:
                stdout = ""; stderr = ""; returncode = 0
            return _R()

        with mock.patch.object(mod.subprocess, "run", side_effect=fake_run):
            mod._run_list(["git", "status"])
        self.assertEqual(captured["cmd"], ["git", "status"])

    def test_empty_cmd_list_does_not_crash(self):
        """Edge: an empty ``cmd_list`` would be a programming error,
        but the substitution check must not IndexError before
        subprocess sees the bad input."""
        mod = _fresh_tracker()
        with mock.patch.object(mod.subprocess, "run") as fake:
            fake.return_value = mock.Mock(stdout="", stderr="", returncode=0)
            try:
                mod._run_list([])
            except IndexError:
                self.fail("_run_list must not IndexError on empty cmd_list")
            except Exception:
                pass  # subprocess may raise something else; that's fine


if __name__ == "__main__":
    unittest.main()
