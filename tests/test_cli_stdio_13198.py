"""#13198 — shared CLI stdio hardening (`cli_stdio.harden_stdio`) + fleet wiring.

Follow-up to #13185: that fix added a local `_harden_stdio` to tracker.py; a
sweep found the same latent cp1252-crash class in the other agent-facing CLI
scripts. #13198 consolidates the logic into `cli_stdio.harden_stdio` and wires it
into every CLI `main()`.
"""

import ast
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
        "git_ops",  # #13728: most heavily-invoked fleet CLI, was unswept
        "wizard",  # #13760: setup/install CLI, was unswept
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


class TestHarnessWiring13236:
    """#13236 — harness.py was named in #13198's cp1252 crash-class list but
    left unwired (out of #13198's agent-facing-CLI scope). It is the
    long-running server, not a fire-and-exit CLI, so the harm is a crash+respawn
    on its banner rather than a false-failure double-emit — but a strict cp1252
    console still raises UnicodeEncodeError on the box-drawing banner art.
    harness.py main() must invoke harden_stdio(); its banner literals are
    intentional ASCII-art and are deliberately NOT in the #13198 print-sweep
    guard (TestNoDecorativeNonAsciiInPrints13198.SWEPT)."""

    def test_harness_main_invokes_harden_stdio(self):
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        assert "from cli_stdio import harden_stdio" in src
        assert "harden_stdio()" in src, (
            "harness.py main() must invoke harden_stdio() (#13236) — the "
            "cp1252 banner crash-proofing was dropped"
        )

    def test_harness_not_in_ascii_sweep_guard(self):
        """harness.py's banner is intentional box-drawing art — it must stay out
        of the print-literal ASCII sweep (which would flag/destroy the logo).
        harden_stdio() crash-proofs it instead."""
        assert "harness" not in TestNoDecorativeNonAsciiInPrints13198.SWEPT


def _print_string_literals(src):
    """Yield (lineno, text) for every str literal passed to a `print(...)` call.

    AST-based so it inspects ONLY print arguments — comments and docstrings
    (which legitimately contain decorative em-dashes throughout these scripts)
    are not examined. f-string literal parts are covered: the JoinedStr's
    Constant children are walked, the {expr} interpolations are not (those are
    runtime values, not source decoration).
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            args = list(node.args) + [kw.value for kw in node.keywords]
            for arg in args:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        yield sub.lineno, sub.value


class TestNoDecorativeNonAsciiInPrints13198:
    """AC-4 sweep guard: the swept agent-facing CLIs must emit only ASCII from
    their `print()` calls so stdout/stderr renders cleanly on a cp1252 console
    (the helper crash-proofs it; this keeps it from rendering as escaped
    `\\u2014`). Locks the #13198 ASCII sweep against regression — a decorative
    char re-introduced into any print literal fails here. Comments/docstrings
    are out of scope and untouched (they carry many legitimate em-dashes)."""

    # The swept scripts (mirrors TestFleetWiring13198.WIRED). cycle.py is
    # excluded for the same reason it is excluded from the wiring guard.
    SWEPT = TestFleetWiring13198.WIRED

    @pytest.mark.parametrize("mod", SWEPT)
    def test_print_literals_are_ascii(self, mod):
        src = (SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")
        offenders = [
            (ln, txt) for ln, txt in _print_string_literals(src)
            if any(ord(c) > 127 for c in txt)
        ]
        assert not offenders, (
            f"{mod}.py has non-ASCII chars in print() string literals "
            f"(#13198 ASCII sweep) — replace decorative chars (e.g. U+2192 '->', "
            f"U+2014 '--') so cp1252 stdout renders cleanly: "
            + "; ".join(f"L{ln}: {txt!r}" for ln, txt in offenders)
        )
