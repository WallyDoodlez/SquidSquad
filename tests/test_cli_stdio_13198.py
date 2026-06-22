"""#13198 — shared CLI stdio hardening (`cli_stdio.harden_stdio`) + fleet wiring.

Follow-up to #13185: that fix added a local `_harden_stdio` to tracker.py; a
sweep found the same latent cp1252-crash class in the other agent-facing CLI
scripts. #13198 consolidates the logic into `cli_stdio.harden_stdio` and wires it
into every CLI `main()`.
"""

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cli_stdio  # noqa: E402


def _cp1252_stream():
    """A strict cp1252 text stream — mimics the Windows console that crashed."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")


class TestHardenStdio:
    def test_baseline_cp1252_arrow_raises(self):
        """The crash being fixed: U+2192 on a strict cp1252 stream raises."""
        s = _cp1252_stream()
        with pytest.raises(UnicodeEncodeError):
            s.write("done → ok")

    def test_harden_sets_backslashreplace_and_no_raise(self):
        out, err = _cp1252_stream(), _cp1252_stream()
        with patch.object(cli_stdio.sys, "stdout", out), \
             patch.object(cli_stdio.sys, "stderr", err):
            cli_stdio.harden_stdio()
            assert cli_stdio.sys.stdout.errors == "backslashreplace"
            assert cli_stdio.sys.stderr.errors == "backslashreplace"
            # The previously-crashing write now succeeds (escaped, not raised).
            cli_stdio.sys.stdout.write("done → ok")
            cli_stdio.sys.stdout.flush()

    def test_safe_when_stream_not_reconfigurable(self):
        """Best-effort: a stream without reconfigure() is left as-is, no raise."""
        class _NoReconfigure:
            pass
        with patch.object(cli_stdio.sys, "stdout", _NoReconfigure()), \
             patch.object(cli_stdio.sys, "stderr", _NoReconfigure()):
            cli_stdio.harden_stdio()  # must not raise

    def test_idempotent(self):
        out, err = _cp1252_stream(), _cp1252_stream()
        with patch.object(cli_stdio.sys, "stdout", out), \
             patch.object(cli_stdio.sys, "stderr", err):
            cli_stdio.harden_stdio()
            cli_stdio.harden_stdio()  # second call is a no-op, no raise
            assert cli_stdio.sys.stdout.errors == "backslashreplace"


class TestFleetWiring13198:
    """Every agent-facing CLI script must invoke the hardening at its entry so
    no script can reintroduce the cp1252 crash. tracker.py routes through its
    `_harden_stdio` delegate (which calls the shared helper); the other 8 call
    `harden_stdio()` directly in main(). cycle.py is intentionally excluded — it
    already force-reconfigures stdout to UTF-8 (a different but equally
    crash-safe approach; aligning it is an optional cosmetic follow-on)."""

    WIRED = [
        "config", "subloop_driver", "model_router", "scan_index", "compose",
        "boot_remote", "add_role", "migrate_state_branch", "tracker",
    ]

    @pytest.mark.parametrize("mod", WIRED)
    def test_cli_invokes_harden_stdio(self, mod):
        src = (SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")
        assert "harden_stdio()" in src, (
            f"{mod}.py must invoke harden_stdio() at its CLI entry (#13198) — "
            f"the cp1252 crash-proofing was dropped"
        )

    def test_tracker_delegates_to_shared_helper(self):
        """tracker.py's #13185 local helper now delegates to the shared one."""
        src = (SCRIPTS / "tracker.py").read_text(encoding="utf-8")
        assert "from cli_stdio import harden_stdio" in src

    def test_shared_helper_module_exists(self):
        assert (SCRIPTS / "cli_stdio.py").exists()
