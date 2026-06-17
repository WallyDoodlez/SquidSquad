"""Shared fixtures for SquidSquad static analysis tests."""

import threading
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
REFERENCES_DIR = REPO_ROOT / "references"
VAULT_DIR = SQUIDSQUAD_DIR / "vault"
SUB_SKILLS_DIR = REFERENCES_DIR / "sub-skills"


@pytest.fixture(scope="session", autouse=True)
def _snapshot_restore_live_config_md():
    """#11044: session-scoped defense against tests that shell out to
    `references/scripts/config.py set ...` (or otherwise write to
    `.squidsquad/config.md` without isolating to tmp_path).

    Subprocess-side writes are not subject to in-process monkeypatches —
    `config.py`'s module-level `CONFIG_PATH` resolves from `__file__`
    at import time, not from the test process's patched `REPO_ROOT`.
    The leak surfaced via `_do_version_bump` shelling out to
    `config.py set version <X>` and silently bumping the live config
    during full-suite runs.

    Belt-and-braces: even after every individual leak is patched, this
    fixture snapshots the live config.md before the suite and restores
    it after. If a future test re-introduces the pattern, the next
    full-suite run still leaves the file at its pre-suite contents.
    """
    config_path = SQUIDSQUAD_DIR / "config.md"
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    try:
        yield
    finally:
        if original is None:
            if config_path.exists():
                config_path.unlink()
        else:
            current = config_path.read_text(encoding="utf-8") if config_path.exists() else None
            if current != original:
                config_path.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# #12720: thread-leak guard — fail LOUDLY when a test leaves a live thread.
#
# Root cause of #12720: tests/test_harness.py::test_post_shutdown_returns_202
# POSTed /shutdown to the in-process app. The handler spawns a `shutdown`
# DAEMON thread that sleeps 1s then calls os._exit(0). The test's os._exit
# patch reverted the instant the POST returned 202 — so ~1s later the REAL
# os._exit(0) fired from the daemon thread and hard-killed the entire pytest
# process (exit 0, NO summary, pytest.main() never returns). In a full
# `pytest tests/` run this masked ~40% of the suite as a false green at ~58%.
#
# This guard would have caught it: a test that leaves the `shutdown` thread
# (or any non-daemon thread / live server) alive after teardown fails loudly
# instead of silently arming a delayed process kill. Sibling to the #11394 /
# #12408 false-green-gate work.
# ---------------------------------------------------------------------------

# Threads that legitimately outlive an individual test — spawned by a class/
# session fixture and torn down by THAT fixture, not by the test body.
_GUARD_ALLOWED_THREAD_NAMES = frozenset({
    # Per-CLASS HTTP stub in tests/integration/test_event_mode_e2e.py:
    # started in setUpClass, joined in tearDownClass.
    "test-event-stream-http",
})

# Thread names that are ALWAYS a leak if alive after a test, even as a daemon:
# the harness `shutdown` thread calls os._exit(0) and WILL kill the process.
_GUARD_DANGEROUS_THREAD_NAMES = frozenset({"shutdown"})


def _guard_leaked_threads(baseline_idents):
    """Live threads that appeared during this test and should not survive it.

    A thread is a leak if it is alive, was not present before the test, is not
    on the fixture allowlist, AND is either non-daemon (a live server/observer
    — the #12720 AC class) or a known-dangerous harness thread (the daemon
    os._exit caller). Benign library daemon threads are tolerated."""
    leaked = []
    current = threading.current_thread()
    for t in threading.enumerate():
        if t is current or not t.is_alive():
            continue
        if t.ident in baseline_idents or t.name in _GUARD_ALLOWED_THREAD_NAMES:
            continue
        if (not t.daemon) or (t.name in _GUARD_DANGEROUS_THREAD_NAMES):
            leaked.append(t)
    return leaked


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    # Baseline captured before setup, so class/session-fixture threads born in
    # setUpClass are attributed correctly (and filtered by the allowlist).
    item._sq_thread_baseline = {t.ident for t in threading.enumerate()}
    return (yield)


def _assert_no_leaked_threads(item):
    baseline = getattr(item, "_sq_thread_baseline", None)
    if baseline is None:
        return
    leaked = _guard_leaked_threads(baseline)
    if leaked:
        desc = ", ".join(f"{t.name!r}(daemon={t.daemon})" for t in leaked)
        pytest.fail(
            f"#12720 thread-leak guard: {item.nodeid} left live thread(s) "
            f"alive after teardown: {desc}. A leaked thread — especially the "
            f"harness `shutdown` thread, which calls os._exit(0) — can hard-"
            f"kill the pytest process mid-run (silent false-green truncation). "
            f"Tear the thread down in the test/fixture; if it calls os._exit, "
            f"join it INSIDE the os._exit patch context.",
            pytrace=False,
        )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    # The leak check MUST run even when the real teardown raises — a test that
    # fails teardown AND leaks a `shutdown` thread must not escape the guard
    # (DS-c1 F5). On the exception path the original teardown error is re-raised
    # only if there is no leak; a leak supersedes it (it is the safety-critical
    # signal — it would otherwise hard-kill the process).
    try:
        res = yield
    except BaseException:
        _assert_no_leaked_threads(item)
        raise
    _assert_no_leaked_threads(item)
    return res


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def squidsquad_dir():
    return SQUIDSQUAD_DIR


@pytest.fixture
def references_dir():
    return REFERENCES_DIR


@pytest.fixture
def vault_dir():
    return VAULT_DIR


@pytest.fixture
def sub_skills_dir():
    return SUB_SKILLS_DIR


@pytest.fixture
def config_text():
    return (SQUIDSQUAD_DIR / "config.md").read_text(encoding="utf-8")


@pytest.fixture
def skill_claude_md():
    return (SQUIDSQUAD_DIR / "skill" / "CLAUDE.md").read_text(encoding="utf-8")
