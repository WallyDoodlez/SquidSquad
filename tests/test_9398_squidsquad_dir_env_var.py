"""Regression tests for the #9398 Phase A precondition: SQUIDSQUAD_DIR env var.

Background: ``harness.py`` and ``event_bus.py`` previously hard-coded
``SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"`` as a module-level
constant. The §4.1 / §4.5 real-agent-subprocess fixture work needs to
spawn a test harness on a random port WITHOUT clobbering the live
harness's ``.harness-port`` file (which all other SquidSquad processes
use for port discovery). This Phase A precondition adds env-var
override: ``SQUIDSQUAD_DIR=<tmpdir>`` re-points both modules' state
roots at the tmpdir.

Tests pin:

1. ``event_bus.SQUID_DIR`` honors ``SQUIDSQUAD_DIR`` env var.
2. ``harness.SQUIDSQUAD_DIR`` honors ``SQUIDSQUAD_DIR`` env var.
3. With the env var unset, both modules fall back to the previous
   default (``REPO_ROOT / ".squidsquad"``).
4. ``harness.HARNESS_PORT_FILE`` rebases under the env-overridden
   directory — the load-bearing assertion for #9398 fixture
   isolation. If the constant is computed once at module load against
   the old SQUIDSQUAD_DIR, the override is silently broken.
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"


def _fresh_load(module_name: str, file_path: Path, env: dict):
    """Load a module from disk with a controlled os.environ.

    Module-level constants are evaluated at import time, so the env
    var must be set BEFORE the import. We use mock.patch.dict on
    ``os.environ`` around an importlib spec-based load.
    """
    with mock.patch.dict(os.environ, env, clear=False):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not (spec and spec.loader):
            raise ImportError(f"cannot load {file_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


class TestEventBusSquidDirEnvVar(unittest.TestCase):
    def test_event_bus_honors_squidsquad_dir_env_var(self):
        with tempfile.TemporaryDirectory(prefix="sqdir-test-") as tmp:
            mod = _fresh_load(
                "_event_bus_squidsquad_dir_test",
                SCRIPTS / "event_bus.py",
                {"SQUIDSQUAD_DIR": tmp},
            )
            self.assertEqual(
                str(mod.SQUID_DIR), str(Path(tmp)),
                msg=(
                    "event_bus.SQUID_DIR must be the SQUIDSQUAD_DIR env var "
                    "when set (#9398). Without this, a test harness in a "
                    "tmpdir can't be discovered by event_bus.emit() in the "
                    "agent subprocess."
                ),
            )

    def test_event_bus_default_unchanged_when_env_var_unset(self):
        # mock.patch.dict with clear=True ensures the env var is unset
        with mock.patch.dict(os.environ, {}, clear=True):
            mod = _fresh_load(
                "_event_bus_default_test",
                SCRIPTS / "event_bus.py",
                {},
            )
            self.assertEqual(
                str(mod.SQUID_DIR).replace("\\", "/").lower(),
                str(REPO_ROOT / ".squidsquad").replace("\\", "/").lower(),
                msg=(
                    "Without SQUIDSQUAD_DIR set, event_bus.SQUID_DIR must "
                    "fall back to the previous default REPO_ROOT/.squidsquad "
                    "— production callers see zero behavior change."
                ),
            )


class TestHarnessSquidDirEnvVar(unittest.TestCase):
    """The harness side of the #9398 fixture-isolation contract.
    We DO NOT actually start the harness here (uvicorn etc. is heavy
    + has side effects); the test only re-imports the module under
    the env var and verifies the constants resolved correctly."""

    def test_harness_squidsquad_dir_honors_env_var(self):
        with tempfile.TemporaryDirectory(prefix="sqdir-test-") as tmp:
            mod = _fresh_load(
                "_harness_squidsquad_dir_test",
                SCRIPTS / "harness.py",
                {"SQUIDSQUAD_DIR": tmp},
            )
            self.assertEqual(
                str(mod.SQUIDSQUAD_DIR), str(Path(tmp)),
                msg=(
                    "harness.SQUIDSQUAD_DIR must be the SQUIDSQUAD_DIR env "
                    "var when set (#9398). Without this, a test harness on "
                    "a random port would still write .harness-port to the "
                    "live .squidsquad/ directory, breaking the live system."
                ),
            )

    def test_harness_port_file_rebases_under_env_overridden_dir(self):
        """Load-bearing assertion: the derived
        ``HARNESS_PORT_FILE`` constant must live UNDER the
        env-overridden directory, not under the original
        REPO_ROOT/.squidsquad. If it's computed once-at-load against
        the old constant and never re-derived, the override is
        silently broken at the file-write site."""
        with tempfile.TemporaryDirectory(prefix="sqdir-test-") as tmp:
            mod = _fresh_load(
                "_harness_port_file_test",
                SCRIPTS / "harness.py",
                {"SQUIDSQUAD_DIR": tmp},
            )
            self.assertEqual(
                str(mod.HARNESS_PORT_FILE), str(Path(tmp) / ".harness-port"),
                msg=(
                    "harness.HARNESS_PORT_FILE must rebase under the "
                    "env-overridden SQUIDSQUAD_DIR. If this fails, the "
                    "test harness will overwrite the live .squidsquad/"
                    ".harness-port file every time it starts (#9398)."
                ),
            )

    def test_harness_default_unchanged_when_env_var_unset(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            mod = _fresh_load(
                "_harness_default_test",
                SCRIPTS / "harness.py",
                {},
            )
            self.assertEqual(
                str(mod.SQUIDSQUAD_DIR).replace("\\", "/").lower(),
                str(REPO_ROOT / ".squidsquad").replace("\\", "/").lower(),
                msg=(
                    "Without SQUIDSQUAD_DIR set, harness.SQUIDSQUAD_DIR "
                    "must fall back to REPO_ROOT/.squidsquad — production "
                    "callers see zero behavior change."
                ),
            )


class TestSquidsquadDirNullEnvVarHandled(unittest.TestCase):
    """A common foot-gun: the env var is set to an empty string (e.g.,
    by a shell script with ``SQUIDSQUAD_DIR=$something_undefined``).
    The current implementation uses ``or`` to treat empty as unset,
    which is the right behavior — pin it so a future refactor that
    uses ``os.environ.get("SQUIDSQUAD_DIR", default)`` (which returns
    "" rather than the default for empty values) doesn't break this."""

    def test_empty_string_env_var_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"SQUIDSQUAD_DIR": ""}, clear=False):
            mod = _fresh_load(
                "_event_bus_empty_env_test",
                SCRIPTS / "event_bus.py",
                {"SQUIDSQUAD_DIR": ""},
            )
            # Should be the default, NOT the empty string interpreted as cwd.
            self.assertEqual(
                str(mod.SQUID_DIR).replace("\\", "/").lower(),
                str(REPO_ROOT / ".squidsquad").replace("\\", "/").lower(),
                msg=(
                    "An empty SQUIDSQUAD_DIR env var must fall back to "
                    "the default — empty string would otherwise resolve "
                    "to the process cwd, scattering harness state across "
                    "wherever the harness was started from."
                ),
            )


class TestSquidsquadDirEnvVarFootguns(unittest.TestCase):
    """Sonnet code review of PR #9614 flagged three foot-guns:
    trailing whitespace, leading ``~``, and (already pinned above)
    empty string. Pin the first two so a future refactor that drops
    strip/expanduser handling fails loudly."""

    def test_trailing_whitespace_is_stripped(self):
        """A frequent ``export SQUIDSQUAD_DIR=$tmp `` typo — the
        trailing space silently produces a different path that
        doesn't exist; the harness's port write fails as a logged
        WARNING and the harness becomes undiscoverable. Strip it."""
        with tempfile.TemporaryDirectory(prefix="sqdir-ws-") as tmp:
            mod = _fresh_load(
                "_event_bus_ws_test",
                SCRIPTS / "event_bus.py",
                {"SQUIDSQUAD_DIR": f"  {tmp}  "},
            )
            self.assertEqual(
                str(mod.SQUID_DIR), str(Path(tmp)),
                msg=(
                    "SQUIDSQUAD_DIR with surrounding whitespace must "
                    "be stripped (PR #9614 Sonnet code review). "
                    "Without this, '  /tmp/x  ' resolves to a literal "
                    "path with spaces in it — the directory the user "
                    "wanted does NOT get used."
                ),
            )

    def test_tilde_is_expanded(self):
        """``~/sq-test`` should resolve to the user's home, not a
        literal tilde-prefixed directory under the cwd."""
        mod = _fresh_load(
            "_event_bus_tilde_test",
            SCRIPTS / "event_bus.py",
            {"SQUIDSQUAD_DIR": "~/__sq_tilde_probe__"},
        )
        # Path.expanduser turns ``~`` into ``Path.home()``.
        expected = Path.home() / "__sq_tilde_probe__"
        self.assertEqual(
            str(mod.SQUID_DIR), str(expected),
            msg=(
                "SQUIDSQUAD_DIR='~/foo' must be expanduser'd to the "
                "user's home (PR #9614 Sonnet code review). Without "
                "this, the tilde is treated literally and Path('~/"
                "foo') points at a relative './~' subdirectory."
            ),
        )

    def test_harness_strip_expanduser_same_contract(self):
        """The two modules' resolution functions must apply the
        same foot-gun handling. A regression in only one module
        would be worse than both broken — agents and the harness
        would disagree on where the port file lives."""
        with tempfile.TemporaryDirectory(prefix="sqdir-h-") as tmp:
            mod = _fresh_load(
                "_harness_ws_test",
                SCRIPTS / "harness.py",
                {"SQUIDSQUAD_DIR": f"  {tmp}\t"},
            )
            self.assertEqual(str(mod.SQUIDSQUAD_DIR), str(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
