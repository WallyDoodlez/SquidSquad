"""#13198 — shared CLI stdio hardening (`cli_stdio.harden_stdio`) + fleet wiring.

Follow-up to #13185: that fix added a local `_harden_stdio` to tracker.py; a
sweep found the same latent cp1252-crash class in the other agent-facing CLI
scripts. #13198 consolidates the logic into `cli_stdio.harden_stdio` and wires it
into every CLI `main()`.
"""

import ast
import io
import re
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
    `harden_stdio()` directly in main(). cycle.py, cycle_pre.py, and
    cycle_post.py are intentionally excluded — they already force-reconfigure
    stdout/stderr to UTF-8 at import time (a different but equally crash-safe
    approach; aligning them onto harden_stdio() is an optional cosmetic
    follow-on). See TestUtf8ReconfigureAlternative13846 below, which verifies
    that alternative actually holds rather than just asserting it in this
    docstring (#13846: an improvement-scan pass initially misread the absence
    of the `harden_stdio()` string as "unprotected" for cycle_pre.py/
    cycle_post.py — investigation proved that false; this test class is the
    correction, so the same false alarm doesn't get re-filed)."""

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


class TestUtf8ReconfigureAlternative13846:
    """#13846: cycle.py, cycle_pre.py, and cycle_post.py use a DIFFERENT but
    equally crash-safe strategy than `harden_stdio()` — they force
    stdout/stderr to real UTF-8 via `.reconfigure(encoding="utf-8",
    errors="replace")` at import time, rather than keeping the console's own
    encoding and backstopping with `errors="backslashreplace"`.

    An improvement-scan pass grepped for the literal string `harden_stdio()`
    across every `references/scripts/*.py` with a `__main__` block, found it
    absent from cycle_pre.py/cycle_post.py, and initially filed that as "the
    harness's every-cycle wrapper scripts are unprotected against the cp1252
    crash" (high severity). Investigation disproved the crash claim — see
    `test_reconfigure_actually_prevents_the_crash` below, which reproduces
    the exact failure mode `TestHardenStdio.test_baseline_cp1252_arrow_raises`
    guards against and confirms the alternative guard prevents it too — but
    surfaced a real, much narrower, lower-severity note: this alternative
    runs at IMPORT TIME, which `cli_stdio.py`'s own module docstring flags as
    the wrong place for stdio hardening ("these modules are also imported as
    libraries, and reconfiguring a library consumer's global stdio would be
    wrong") — and cycle_pre.py IS imported as a library, both by
    cycle_post.py itself (`from cycle_pre import WS_RAW_CAP_BYTES`) and by
    at least 9 test files. Tracked separately (not a crash, just an
    architectural inconsistency with the documented contract) rather than
    fixed inline here, to keep this correction narrowly scoped.
    """

    RECONFIGURE_GUARDED = ["cycle", "cycle_pre", "cycle_post"]

    _RECONFIGURE_STDOUT_RE = re.compile(
        r"""sys\.stdout\.reconfigure\(\s*encoding\s*=\s*['"]utf-8['"]"""
    )

    @pytest.mark.parametrize("mod", RECONFIGURE_GUARDED)
    def test_module_has_utf8_reconfigure_guard(self, mod):
        src = (SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")
        assert self._RECONFIGURE_STDOUT_RE.search(src), (
            f"{mod}.py relies on a UTF-8 reconfigure guard instead of "
            f"harden_stdio() (#13198/#13846) — if this guard was "
            f"intentionally removed, add harden_stdio() to main() instead "
            f"and move {mod!r} from TestUtf8ReconfigureAlternative13846."
            f"RECONFIGURE_GUARDED into TestFleetWiring13198.WIRED so the "
            f"cp1252 crash-proofing isn't silently dropped"
        )

    def test_cycle_pre_and_post_also_guard_stderr(self):
        """cycle_pre.py/cycle_post.py reconfigure BOTH streams (unlike
        cycle.py, which only guards stdout — its CLI never prints decorative
        Unicode to stderr, so that gap is a documented non-issue there, not a
        pattern to enforce on all three)."""
        for mod in ("cycle_pre", "cycle_post"):
            src = (SCRIPTS / f"{mod}.py").read_text(encoding="utf-8")
            assert re.search(
                r"""sys\.stderr\.reconfigure\(\s*encoding\s*=\s*['"]utf-8['"]""",
                src,
            ), f"{mod}.py must also guard stderr, not just stdout"

    def test_reconfigure_actually_prevents_the_crash(self):
        """Real reproduction (not a string match): apply the exact guard
        these modules use to a genuinely cp1252-encoded stream — the same
        stream shape `TestHardenStdio.test_baseline_cp1252_arrow_raises`
        proves crashes without protection — and confirm decorative Unicode
        (the arrow AND the squid emoji these modules print on every cycle)
        writes without raising."""
        stream = _cp1252_stream()
        assert stream.encoding.lower() != "utf-8"
        # Mirrors the exact guard: `if sys.stdout.encoding != "utf-8": ...`
        if stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
        stream.write("[\U0001F991 12:00:00] cycle_post → done — ok\n")
        stream.flush()  # must not raise

    # ---- #13847: guard placement, not just presence ----

    @staticmethod
    def _reconfigure_call_scopes(mod):
        """AST walk: for each `sys.stdout/sys.stderr.reconfigure(...)` call,
        yield the name of the enclosing function ('' at module scope)."""
        tree = ast.parse((SCRIPTS / f"{mod}.py").read_text(encoding="utf-8"))
        scopes = []

        def visit(node, func_name):
            for child in ast.iter_child_nodes(node):
                child_func = func_name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    child_func = child.name
                if isinstance(child, ast.Call):
                    f = child.func
                    if (isinstance(f, ast.Attribute)
                            and f.attr == "reconfigure"
                            and isinstance(f.value, ast.Attribute)
                            and f.value.attr in ("stdout", "stderr")
                            and isinstance(f.value.value, ast.Name)
                            and f.value.value.id == "sys"):
                        scopes.append(func_name)
                visit(child, child_func)

        visit(tree, "")
        return scopes

    @pytest.mark.parametrize("mod", RECONFIGURE_GUARDED)
    def test_guard_is_cli_entry_only_not_import_time(self, mod):
        """#13847: the reconfigure guard must live inside main() — never at
        module scope. cycle_pre.py is imported as a library (by cycle_post.py
        and 9+ test files); an import-time reconfigure silently mutates the
        importing process's global stdio, exactly what cli_stdio.py's
        docstring contract forbids. Verified via AST (not string match) so a
        regression that re-hoists the block to module level fails here even
        if the source text otherwise matches."""
        scopes = self._reconfigure_call_scopes(mod)
        assert scopes, f"{mod}.py: no sys.std*.reconfigure guard found at all"
        at_module_scope = [s for s in scopes if s == ""]
        assert not at_module_scope, (
            f"{mod}.py has {len(at_module_scope)} sys.std*.reconfigure "
            f"call(s) at MODULE scope — the guard must run at CLI entry "
            f"(inside main()) only, per cli_stdio.py's documented contract "
            f"(#13847); import-time reconfigure mutates library consumers' "
            f"global stdio"
        )
        assert any(s == "main" for s in scopes), (
            f"{mod}.py: reconfigure guard exists but not inside main() "
            f"(found in: {sorted(set(scopes))}) — keep it at the CLI entry"
        )


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
