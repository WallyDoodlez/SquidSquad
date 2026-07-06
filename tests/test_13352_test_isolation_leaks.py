"""#13352 — test runs must not leak into live surfaces.

Three leak classes were observed in production (all artifacts from test /
experiment runs landing on LIVE agent surfaces):

1. Fabricated ``status-transition`` events (synthetic issue 87654) on the
   PRODUCTION event bus: ``env_with_gh_shim()`` did not set
   ``SQUIDSQUAD_DIR``, so a shimmed ``tracker.py transition`` subprocess
   discovered the live ``.squidsquad/.harness-port`` and posted its
   synthetic event for real. Fix: ``env_with_gh_shim`` always sets
   ``SQUIDSQUAD_DIR`` to an isolated EMPTY tmpdir (no port file → emit is
   a silent no-op) unless the caller supplies a ``squid_dir``.

2. ``.harness-port`` poisoned in live clones (observed value 8251): the
   harness's lifespan clone-port distribution ran unconditionally, so an
   isolated test harness (``real_harness`` fixture, ephemeral port) wrote
   its port into every live clone listed in ``.local-config`` — stranding
   those agents in polling fallback at their next boot probe. Fix:
   ``harness._distribute_port_to_clones`` distributes ONLY when
   ``SQUIDSQUAD_DIR`` is the repo's live ``.squidsquad``.

3. Scratch artifacts written into agent clones by experiment scripts
   (``wt-env-probe.txt``, ``conpty-spike-raw-output.txt``) via
   cwd-relative ``.squidsquad/`` paths. Fix: experiments write scratch
   output under ``tempfile.mkdtemp`` only; this suite pins the absence of
   the cwd-relative leak shapes at source level.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration" / "fixtures"))

import harness  # noqa: E402
import event_mode_subprocess as ems  # noqa: E402

LIVE_SQUID = (REPO_ROOT / ".squidsquad").resolve()


class TestEnvWithGhShimIsolation(unittest.TestCase):
    """Leak class 1 — the shim env must never route a subprocess's
    event_bus at the live harness."""

    def test_squidsquad_dir_always_set_and_isolated(self):
        env = ems.env_with_gh_shim()
        self.assertIn("SQUIDSQUAD_DIR", env)
        iso = Path(env["SQUIDSQUAD_DIR"])
        self.assertNotEqual(iso.resolve(), LIVE_SQUID)

    def test_isolated_dir_has_no_harness_port_file(self):
        env = ems.env_with_gh_shim()
        port_file = Path(env["SQUIDSQUAD_DIR"]) / ".harness-port"
        self.assertFalse(
            port_file.exists(),
            "the default isolation dir must stay EMPTY — a port file here "
            "would re-route shimmed subprocess emits at a live harness",
        )

    def test_explicit_squid_dir_wins(self):
        with tempfile.TemporaryDirectory(prefix="explicit-squid-") as tmp:
            env = ems.env_with_gh_shim(squid_dir=Path(tmp))
            self.assertEqual(env["SQUIDSQUAD_DIR"], str(Path(tmp)))

    def test_outer_squidsquad_dir_is_overridden(self):
        """A live SQUIDSQUAD_DIR inherited from the parent process env
        must not survive into the shim env — isolation is the default,
        not an accident of the parent environment."""
        base = {"SQUIDSQUAD_DIR": str(LIVE_SQUID), "PATH": ""}
        env = ems.env_with_gh_shim(base_env=base)
        self.assertNotEqual(
            Path(env["SQUIDSQUAD_DIR"]).resolve(), LIVE_SQUID
        )

    def test_subprocess_port_discovery_returns_none(self):
        """End-to-end: an event_bus in a subprocess under the shim env
        discovers NO harness port — so every emit is a silent no-op
        (the exact mechanism that kept fake 87654 events off the bus)."""
        env = ems.env_with_gh_shim()
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; sys.path.insert(0, r'"
                    + str(REPO_ROOT / "references" / "scripts")
                    + "'); import event_bus; "
                    "print(event_bus._discover_port())"
                ),
            ],
            env=env,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr[:500])
        self.assertEqual(proc.stdout.strip(), "None")


class TestHarnessClonePortDistributionGuard(unittest.TestCase):
    """Leak class 2 — an isolated harness must not write its port into
    live clones."""

    def test_isolated_harness_skips_distribution(self):
        with tempfile.TemporaryDirectory(prefix="iso-squid-") as tmp:
            with patch.object(harness, "SQUIDSQUAD_DIR", Path(tmp)), \
                 patch.object(
                     harness.boot_remote, "_parse_local_config",
                     side_effect=AssertionError(
                         "isolated harness must not even READ .local-config"
                     ),
                 ):
                result = harness._distribute_port_to_clones(8251)
        self.assertIsNone(result)

    def test_production_harness_distributes(self):
        with tempfile.TemporaryDirectory(prefix="fake-clone-") as tmp:
            clone_root = Path(tmp) / "clone-qa"
            (clone_root / ".squidsquad").mkdir(parents=True)
            with patch.object(
                     harness, "SQUIDSQUAD_DIR", REPO_ROOT / ".squidsquad"), \
                 patch.object(
                     harness.boot_remote, "_parse_local_config",
                     return_value={"qa": str(clone_root)},
                 ):
                result = harness._distribute_port_to_clones(7373)
            self.assertEqual(result, 1)
            port_file = clone_root / ".squidsquad" / ".harness-port"
            self.assertTrue(port_file.exists())
            self.assertEqual(
                port_file.read_text(encoding="utf-8").strip(), "7373"
            )

    def test_production_harness_never_writes_own_repo_root(self):
        """The pre-existing self-exclusion still holds after the refactor:
        a clone entry pointing at REPO_ROOT itself is skipped."""
        with patch.object(
                 harness, "SQUIDSQUAD_DIR", REPO_ROOT / ".squidsquad"), \
             patch.object(
                 harness.boot_remote, "_parse_local_config",
                 return_value={"skill": str(REPO_ROOT)},
             ), \
             patch.object(Path, "write_text",
                          side_effect=AssertionError(
                              "must not write into own REPO_ROOT"
                          )):
            result = harness._distribute_port_to_clones(7373)
        self.assertEqual(result, 1)


class TestExperimentScratchPathsStayOutOfClones(unittest.TestCase):
    """Leak class 3 — experiment scripts must not write scratch files
    into any repo clone's .squidsquad/ via cwd-relative paths."""

    FORBIDDEN = (
        'Path.cwd() / ".squidsquad"',
        'Path(".squidsquad',
    )

    def test_no_cwd_relative_squidsquad_writes_in_experiments(self):
        experiments = sorted(
            (REPO_ROOT / "references" / "experiments").glob("*.py")
        )
        self.assertTrue(experiments, "experiments dir unexpectedly empty")
        offenders = []
        for py in experiments:
            text = py.read_text(encoding="utf-8", errors="replace")
            for pattern in self.FORBIDDEN:
                if pattern in text:
                    offenders.append(f"{py.name}: {pattern}")
        self.assertEqual(
            offenders, [],
            "cwd-relative .squidsquad/ paths in experiments write scratch "
            "artifacts into whichever LIVE clone the script runs from "
            "(#13352). Use tempfile.mkdtemp for scratch output: "
            + "; ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
