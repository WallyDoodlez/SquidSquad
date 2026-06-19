"""#12408 regression: the static gate must fail closed on an incomplete run.

Background. `tests/run_tests.py` is the static gate every agent's verification
relies on. Before #12408 `run_static_tests()` returned `subprocess.returncode
== 0` and nothing else. A gated test that hard-exited the pytest process
mid-run (`os._exit(0)`, `sys.exit(0)`, `pytest.exit(..., returncode=0)`) forced
returncode 0 while skipping pytest's session teardown — so no junit was
written, the failure aggregation never ran, and the truncated run reported
false-green. That is how the #12380 regression reached pending-test.

#12720 fixed the *specific* culprit (a /shutdown daemon-thread `os._exit`
race). #12408 hardens the *gate itself* so this whole class of bug can never
silently pass again: the gate now requires positive proof the pytest session
finished — a parseable junit recording >0 tests with 0 failures/errors — and
fails closed on anything else.

These tests lock both halves:
  - the pure verdict helper (`_static_gate_verdict`), and
  - the `run_static_tests()` wiring that feeds it a junit path.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
sys.path.insert(0, str(TESTS_DIR))

import run_tests  # noqa: E402
from run_tests import _static_gate_verdict  # noqa: E402


def _write_junit(path, tests, failures=0, errors=0, skipped=0, root="testsuites"):
    """Write a minimal but structurally-real pytest junit report."""
    inner = (
        f'<testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}" time="1.0"></testsuite>'
    )
    xml = f"<testsuites>{inner}</testsuites>" if root == "testsuites" else inner
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + xml, encoding="utf-8")


# ---------------------------------------------------------------------------
# _static_gate_verdict — pure verdict logic (deterministic, fast)
# ---------------------------------------------------------------------------

def test_verdict_passes_on_complete_clean_junit(tmp_path):
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=170, failures=0, errors=0, skipped=15)
    passed, reason = _static_gate_verdict(0, junit)
    assert passed is True, reason
    assert "170" in reason


def test_verdict_fails_on_recorded_failures(tmp_path):
    """AC1: a recorded failure fails the gate even if returncode were 0."""
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=170, failures=1)
    passed, reason = _static_gate_verdict(1, junit)
    assert passed is False
    assert "failure" in reason.lower()


def test_verdict_fails_on_recorded_errors(tmp_path):
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=170, errors=2)
    passed, reason = _static_gate_verdict(1, junit)
    assert passed is False
    assert "error" in reason.lower()


def test_verdict_fails_on_missing_junit_even_with_returncode_zero(tmp_path):
    """THE #12408 bug: hard-exit forces returncode 0 and writes no junit.

    A returncode of 0 with no junit is the canonical mid-run-hard-exit
    signature (the session-finish hook never fired). The gate must fail closed,
    NOT trust the false-green returncode.
    """
    junit = tmp_path / "never_written.xml"
    assert not junit.exists()
    passed, reason = _static_gate_verdict(0, junit)
    assert passed is False
    assert "INCOMPLETE RUN" in reason


def test_verdict_fails_on_zero_tests(tmp_path):
    """A junit that recorded 0 tests means nothing ran — fail closed."""
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=0)
    passed, reason = _static_gate_verdict(0, junit)
    assert passed is False
    assert "0 tests" in reason


def test_verdict_fails_on_malformed_junit(tmp_path):
    junit = tmp_path / "j.xml"
    junit.write_text("<testsuites><testsuite tests='5'", encoding="utf-8")  # truncated
    passed, reason = _static_gate_verdict(0, junit)
    assert passed is False
    assert "INCOMPLETE RUN" in reason


def test_verdict_fails_on_nonzero_returncode_with_clean_junit(tmp_path):
    """Defense in depth: even a clean junit can't override a non-zero rc."""
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=170, failures=0)
    passed, reason = _static_gate_verdict(2, junit)
    assert passed is False
    assert "non-zero" in reason


def test_verdict_handles_bare_testsuite_root(tmp_path):
    """xunit1 / older pytest emits a bare <testsuite> root, not <testsuites>."""
    junit = tmp_path / "j.xml"
    _write_junit(junit, tests=42, failures=0, root="testsuite")
    passed, reason = _static_gate_verdict(0, junit)
    assert passed is True, reason
    assert "42" in reason


# ---------------------------------------------------------------------------
# run_static_tests() — wiring: it must request junit and route through verdict
# ---------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, returncode):
        self.returncode = returncode


def _fake_pytest(write_kwargs, returncode, record):
    """Build a subprocess.run replacement that simulates a pytest invocation:
    it optionally writes a junit at the `--junit-xml` path, then returns a
    CompletedProcess-like object with the given returncode. `write_kwargs=None`
    simulates a mid-run hard-exit (no junit written)."""
    def _run(cmd, **kwargs):
        record["cmd"] = cmd
        if "--junit-xml" in cmd:
            jpath = Path(cmd[cmd.index("--junit-xml") + 1])
            if write_kwargs is not None:
                _write_junit(jpath, **write_kwargs)
        return _FakeCompleted(returncode)
    return _run


def test_gate_requests_junit_from_pytest(monkeypatch):
    """run_static_tests must pass --junit-xml so completeness is checkable."""
    record = {}
    monkeypatch.setattr(
        run_tests.subprocess, "run",
        _fake_pytest({"tests": 170}, 0, record),
    )
    run_tests.run_static_tests()
    assert "--junit-xml" in record["cmd"], record.get("cmd")


def test_gate_fails_when_pytest_hard_exits_false_green(monkeypatch):
    """End-to-end #12408: pytest returns 0 but writes no junit (hard-exit).
    The old gate returned True here; the hardened gate must return False."""
    record = {}
    monkeypatch.setattr(
        run_tests.subprocess, "run",
        _fake_pytest(None, 0, record),  # rc 0, NO junit -> false-green
    )
    assert run_tests.run_static_tests() is False


def test_gate_passes_on_clean_complete_run(monkeypatch):
    record = {}
    monkeypatch.setattr(
        run_tests.subprocess, "run",
        _fake_pytest({"tests": 170, "failures": 0, "errors": 0}, 0, record),
    )
    assert run_tests.run_static_tests() is True


def test_gate_fails_on_real_failure(monkeypatch):
    """AC1: a deliberate gated failure makes run_static_tests() return False."""
    record = {}
    monkeypatch.setattr(
        run_tests.subprocess, "run",
        _fake_pytest({"tests": 170, "failures": 1}, 1, record),
    )
    assert run_tests.run_static_tests() is False


def test_gate_cleans_up_its_junit_temp_file(monkeypatch):
    """The gate must not leak its temp junit into the system temp dir."""
    record = {}
    monkeypatch.setattr(
        run_tests.subprocess, "run",
        _fake_pytest({"tests": 170}, 0, record),
    )
    run_tests.run_static_tests()
    jpath = Path(record["cmd"][record["cmd"].index("--junit-xml") + 1])
    assert not jpath.exists(), "static gate leaked its junit temp file"
