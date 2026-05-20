"""Real-agent-subprocess test fixture for #9398 Phase A.

The §4.1 / §4.5 acceptance criteria call for spawning a *real*
event-mode agent against a *real* harness — not a `TestClient`
in-process proxy. The wire halves already live in
`tests/integration/test_event_mode_agent_subprocess.py`; this fixture
provides the spawn-and-wait infrastructure that lets later tests
exercise the AC-3 M-3.2 and AC-2 M-2.* paths end-to-end.

Two building blocks:

- `real_harness(...)`: context manager that spawns ``harness.py`` as a
  subprocess in an isolated ``SQUIDSQUAD_DIR`` tmpdir, waits for the
  port file and a passing ``/status`` probe, and yields
  ``(port, proc, squid_dir)``. Cleans up the subprocess on exit
  (SIGTERM on POSIX, CTRL_BREAK_EVENT on Windows, with a hard-kill
  backstop).

- `boot_agent_subprocess(role, squid_dir)`: spawns a thin Python
  subprocess that imports ``event_bus`` and calls
  ``bootup_complete(role)`` against the harness whose port is on
  disk in ``squid_dir / ".harness-port"``. The subprocess exits
  immediately after emitting — it does NOT run a full agent loop,
  just the bootup signal. Used by the first §4.1 test to assert the
  harness records the flag flip end-to-end across a real process
  boundary.

Both helpers depend on the #9398-precondition refactor (`harness.py`
and `event_bus.py` honor the ``$SQUIDSQUAD_DIR`` env var) — without
that, the test harness would clobber the live ``.harness-port`` file.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
HARNESS_PATH = SCRIPTS / "harness.py"

# Generous defaults — Windows subprocess + uvicorn cold start is slow.
_DEFAULT_STARTUP_TIMEOUT = 15.0
_DEFAULT_STATUS_TIMEOUT = 10.0
_DEFAULT_TEARDOWN_TIMEOUT = 5.0


def _terminate_proc(proc: subprocess.Popen) -> None:
    """Politely-then-firmly stop a child process.

    On Windows we need CTRL_BREAK_EVENT (Popen must have been started
    with CREATE_NEW_PROCESS_GROUP); on POSIX terminate() suffices.
    Hard kill backstop after _DEFAULT_TEARDOWN_TIMEOUT.
    """
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
    except (OSError, ValueError):
        # Process already gone (race), or pipe closed — let kill() finish.
        pass
    try:
        proc.wait(timeout=_DEFAULT_TEARDOWN_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass


def _wait_for_port_file(squid_dir: Path, proc: subprocess.Popen,
                       timeout: float) -> int:
    """Poll ``squid_dir / .harness-port`` until it appears AND the
    harness subprocess is still alive. Returns the port number.

    Raises ``RuntimeError`` if the subprocess exited before writing,
    or ``TimeoutError`` if it hangs.
    """
    port_file = squid_dir / ".harness-port"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_file.exists():
            try:
                raw = port_file.read_text(encoding="utf-8").strip()
                if raw:
                    return int(raw)
            except (OSError, ValueError):
                # Possibly mid-write; loop and retry.
                pass
        if proc.poll() is not None:
            # stderr is redirected to a file (see real_harness), not
            # a PIPE — read the tail from there so the caller can
            # see why the harness died.
            stderr_tail = ""
            try:
                stderr_path = squid_dir / "harness.stderr.log"
                if stderr_path.exists():
                    raw = stderr_path.read_bytes()[-500:]
                    stderr_tail = raw.decode("utf-8", errors="replace")
            except OSError:
                pass
            raise RuntimeError(
                f"harness subprocess exited rc={proc.returncode} before "
                f"writing port file. stderr tail: {stderr_tail!r}"
            )
        time.sleep(0.1)
    raise TimeoutError(
        f"harness did not write port file within {timeout}s"
    )


def _wait_for_status_ok(port: int, timeout: float) -> None:
    """Probe ``GET /status`` until it returns 200 or timeout elapses.

    The port file is written from the lifespan callback, but uvicorn
    is also still completing its bind/listen at that moment; a
    request issued *immediately* after the port file appears can hit
    a TCP RST. This wait closes that gap.
    """
    deadline = time.monotonic() + timeout
    last_err: str | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/status", timeout=1.0
            ) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError, ConnectionResetError) as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(0.1)
    raise TimeoutError(
        f"/status did not return 200 within {timeout}s. "
        f"Last error: {last_err!r}"
    )


@contextmanager
def real_harness(
    *,
    port_hint: int | None = None,
    startup_timeout: float = _DEFAULT_STARTUP_TIMEOUT,
    status_timeout: float = _DEFAULT_STATUS_TIMEOUT,
):
    """Spawn ``harness.py`` as a subprocess in an isolated SQUIDSQUAD_DIR.

    Yields ``(port, proc, squid_dir)``:
    - ``port``: the port the harness is actually listening on (read
      from the isolated ``.harness-port`` file, NOT from any
      module-level default — the harness may have fallen back to a
      free port if the hint was busy).
    - ``proc``: the ``Popen`` object so tests can ``proc.poll()`` or
      read its pipes if needed.
    - ``squid_dir``: the tmpdir path so tests can probe other
      harness-managed files (``.harness-state.json``,
      ``.event-state.json``, ...) and so an agent subprocess
      spawned by the same test inherits the same ``SQUIDSQUAD_DIR``.

    The harness is started with ``SQUIDSQUAD_HARNESS_NO_AUTO_START=1``
    so it does not try to spawn real agents (which would attempt to
    invoke the live ``claude`` CLI and call out to the forge).
    """
    with tempfile.TemporaryDirectory(prefix="sq-harness-") as tmp:
        squid_dir = Path(tmp)
        env = dict(os.environ)
        env["SQUIDSQUAD_DIR"] = str(squid_dir)
        env["SQUIDSQUAD_HARNESS_NO_AUTO_START"] = "1"

        cmd = [sys.executable, str(HARNESS_PATH)]
        if port_hint is not None:
            cmd.extend(["--port", str(port_hint)])

        # Pipe stdout/stderr to files in the tmpdir, NOT to PIPE
        # handles. The harness chats heavily on stdout (lifespan,
        # event traffic, deferred-init); a PIPE handle that no one
        # reads fills its 4KB OS buffer and the harness blocks on
        # write — which looks externally like an HTTP-layer wedge
        # (a fun day to debug). Files don't have the buffer problem.
        #
        # Resources (stdout_fh, stderr_fh, proc) are tracked through
        # an ExitStack so they're guaranteed-closed on every exit
        # path, including a Popen exception between opening the
        # files and entering the try block (Sonnet code review of
        # #9614). Without this, a Popen FileNotFoundError leaks the
        # file handles and Windows TemporaryDirectory cleanup fails
        # with PermissionError, masking the real failure.
        from contextlib import ExitStack
        stdout_log = squid_dir / "harness.stdout.log"
        stderr_log = squid_dir / "harness.stderr.log"
        with ExitStack() as stack:
            stdout_fh = stack.enter_context(open(stdout_log, "wb"))
            stderr_fh = stack.enter_context(open(stderr_log, "wb"))

            # CREATE_NEW_PROCESS_GROUP on Windows lets us deliver
            # CTRL_BREAK_EVENT during teardown without also killing
            # the parent test runner.
            popen_kwargs = {
                "env": env,
                "cwd": str(REPO_ROOT),
                "stdout": stdout_fh,
                "stderr": stderr_fh,
            }
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                )

            proc = subprocess.Popen(cmd, **popen_kwargs)
            # Register Popen teardown on the same stack so a failure
            # during _wait_for_port_file still gets the subprocess
            # killed (ExitStack runs callbacks in reverse order, so
            # we terminate BEFORE the files close — gives the
            # harness a chance to flush its final log lines).
            stack.callback(_terminate_proc, proc)

            port = _wait_for_port_file(squid_dir, proc, startup_timeout)
            _wait_for_status_ok(port, status_timeout)
            yield port, proc, squid_dir


# Path to the agent-stub script that boot_agent_subprocess spawns.
# Kept as a sibling file so it can be invoked with `python <path>`
# from any cwd without import-path gymnastics.
_BOOT_AGENT_STUB = (
    Path(__file__).resolve().parent / "_boot_agent_stub.py"
)


def boot_agent_subprocess(
    role: str,
    squid_dir: Path,
    *,
    timeout: float = 10.0,
) -> subprocess.CompletedProcess:
    """Spawn a minimal "boot agent" subprocess that emits one
    ``bootup-complete`` event against the harness in ``squid_dir``.

    Inherits ``SQUIDSQUAD_DIR=squid_dir`` so the in-subprocess
    ``event_bus`` module discovers the test harness's port file.

    Returns the ``CompletedProcess`` — caller asserts on exit code
    and stderr if needed. Does NOT run a full agent loop; the goal is
    a clean, reproducible exercise of the bootup-complete contract
    end-to-end across a real process boundary.
    """
    env = dict(os.environ)
    env["SQUIDSQUAD_DIR"] = str(squid_dir)

    return subprocess.run(
        [sys.executable, str(_BOOT_AGENT_STUB), role],
        env=env,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
