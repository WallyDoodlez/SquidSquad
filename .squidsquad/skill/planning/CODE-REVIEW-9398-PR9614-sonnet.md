# Code Review — #9398 Phase A (PR #9614)

**Reviewer**: Claude Sonnet 4.6 (third-tier fallback after DeepSeek hang + GPT-5.2 quota)
**Date**: 2026-05-20
**Files reviewed**: `references/scripts/harness.py`, `references/scripts/event_bus.py`,
`tests/integration/fixtures/event_mode_subprocess.py`,
`tests/integration/fixtures/_boot_agent_stub.py`,
`tests/integration/test_9398_real_agent_subprocess.py`,
`tests/test_9398_squidsquad_dir_env_var.py`, `tests/run_tests.py`

---

## Finding 1 — MEDIUM: Resource leak on Popen failure / TemporaryDirectory cleanup race

**File**: `tests/integration/fixtures/event_mode_subprocess.py`, lines 299–315

`stdout_fh` and `stderr_fh` are opened **before** the `try` block. If
`subprocess.Popen()` raises (e.g., `FileNotFoundError` because Python is not on PATH,
or `PermissionError` on a locked executable), the `finally` block never executes and both
file handles leak until CPython GC collects them. On Windows this matters more than on
POSIX: `tempfile.TemporaryDirectory.__exit__` calls `shutil.rmtree`, which will raise
`PermissionError` if either log file is still open, causing the tmpdir to not be cleaned
up and the test to surface a confusing secondary error instead of the real Popen failure.

The fix is to wrap the file opens and Popen inside a single try, or use `contextlib.ExitStack`:

```python
with contextlib.ExitStack() as stack:
    stdout_fh = stack.enter_context(open(stdout_log, "wb"))
    stderr_fh = stack.enter_context(open(stderr_log, "wb"))
    proc = subprocess.Popen(cmd, **popen_kwargs)
    stack.callback(_terminate_proc, proc)
    try:
        port = _wait_for_port_file(squid_dir, proc, startup_timeout)
        _wait_for_status_ok(port, status_timeout)
        yield port, proc, squid_dir
    finally:
        pass  # ExitStack handles teardown
```

Or minimally, open inside the `try`:

```python
stdout_fh = open(stdout_log, "wb")
stderr_fh = open(stderr_log, "wb")
try:
    proc = subprocess.Popen(cmd, **popen_kwargs)
    ...
finally:
    _terminate_proc(proc)   # only safe if proc was assigned
    stdout_fh.close()
    stderr_fh.close()
```

The second form still risks `NameError` on `proc` if Popen raises before assignment.
`ExitStack` is cleanest. Likelihood this fires in practice: low (Python is always on PATH
in CI), but the correctness gap is real and the Windows tmpdir-cleanup side-effect is
non-obvious.

---

## Finding 2 — MEDIUM: `SQUIDSQUAD_DIR` env var not stripped; tilde not expanded

**File**: `references/scripts/harness.py` line 46, `references/scripts/event_bus.py` line 22

```python
SQUIDSQUAD_DIR = Path(os.environ.get("SQUIDSQUAD_DIR") or (REPO_ROOT / ".squidsquad"))
```

Three edge cases Path() does not handle automatically:

1. **Trailing/leading whitespace** — `SQUIDSQUAD_DIR="  /tmp/test  "` produces a path
   with literal spaces in the name. The harness will try to write `.harness-port` inside
   `"  /tmp/test  /"` which almost certainly does not exist, causing an `OSError` on the
   port file write (caught and logged as a WARNING, so the harness continues but is
   un-discoverable).
2. **Tilde** — `SQUIDSQUAD_DIR=~/projects` is passed literally; `Path("~/projects")`
   does **not** expand the tilde. The path written to `.harness-port` will be the literal
   string `~/projects/.harness-port` which won't match what `event_bus` resolves after
   `expanduser()` (if the consumer ever expands it).
3. **Relative path** — `SQUIDSQUAD_DIR=relative/path` is resolved relative to the
   harness's `cwd`, which is `REPO_ROOT` (set in Popen). This works by accident because
   `real_harness` sets `cwd=str(REPO_ROOT)` and both the harness and the agent stub also
   use `REPO_ROOT`. If cwd ever differs between processes the paths diverge silently.

Recommended fix for both files:
```python
_sqdir_raw = os.environ.get("SQUIDSQUAD_DIR", "").strip()
SQUIDSQUAD_DIR = (
    Path(_sqdir_raw).expanduser().resolve()
    if _sqdir_raw
    else REPO_ROOT / ".squidsquad"
)
```

`.resolve()` also handles the relative path case (anchors it to cwd at import time).
Severity is MEDIUM rather than BLOCK because: (a) the fixture always passes a clean
absolute tmpdir path, (b) the whitespace/tilde cases require operator error, and (c) all
4 unit tests in `test_9398_squidsquad_dir_env_var.py` pass clean paths and would not
catch this.

---

## Finding 3 — LOW: `_validate_role` reads LIVE `config.md` regardless of `SQUIDSQUAD_DIR`

**File**: `references/scripts/harness.py` line 1109; `references/scripts/boot_remote.py` lines 38–40

`_validate_role` calls `boot_remote._get_all_roles()`, which reads
`SQUIDSQUAD_DIR / "config.md"` — but `boot_remote` hard-codes its own `SQUIDSQUAD_DIR`
from `REPO_ROOT / ".squidsquad"` and does **not** honor the env var. In the test
harness, this means: the harness process runs with `SQUIDSQUAD_DIR=<tmpdir>` but the
role allowlist is still read from the live `config.md`. The PR already documents this
as a known out-of-scope limitation (role allowlist is sourced from live config) and
relies on `"skill"` being in every real config. This is correct and safe.

However there is a subtle secondary effect: the "fall open" path at lines 1470–1476 of
harness.py (when `_get_all_roles()` raises `Exception`) means that if the live
`config.md` is missing (clean checkout, fresh CI box with no `.squidsquad/`), the
allowlist becomes `None` and ALL role names are accepted. The test then passes for a
different reason than intended. Not a correctness risk for the shipped system, but
worth noting for CI reproducibility.

**Recommendation**: No action required for this PR (out-of-scope). File a follow-up
task to make `boot_remote` honor `SQUIDSQUAD_DIR` for Phase B.

---

## Finding 4 — LOW: `WindowsError` coverage in `_terminate_proc` is correct (no action needed)

**File**: `tests/integration/fixtures/event_mode_subprocess.py` line 176

The review brief asked whether `(OSError, ValueError)` is sufficient on Windows where
`CTRL_BREAK_EVENT` might raise `WindowsError`. Confirmed: `WindowsError` is an alias
for `OSError` on Windows (same class, `issubclass(WindowsError, OSError)` is `True`).
The catch is correct and sufficient. The race where the harness was already killed by
another test is also handled: `proc.poll() is not None` short-circuits the signal send
at line 169. No action required.

---

## Finding 5 — LOW: 30s `tasklist` timeout has no fallback assertion path

**File**: `tests/integration/test_9398_real_agent_subprocess.py` lines 405–423

The 30s timeout on `GET /agents/{role}` was added to accommodate the post-#9481
`update_health` → `tasklist` path on Windows cold cache. This is documented and
reasonable. However: if `tasklist` truly hangs (seen once in #9242), the entire
`urlopen` call blocks for 30s and then raises `socket.timeout`, causing the test to fail
with a confusing `[Errno 10060] Connection timed out` rather than a clear assertion
error. A stuck tasklist is not a test infrastructure bug — it's a real system pathology
— but the error message will mislead a CI operator into thinking the harness is down.

The PR notes `GET /status` does NOT trigger `update_health` (post-#9481 fix). A
defensive option: add a `GET /status` probe before `GET /agents/{role}` to confirm the
harness itself is alive, separating harness-down from tasklist-hang in failure output.
This is optional polish; the test remains valid without it.

---

## Finding 6 — LOW: Cross-test isolation via `"skill"` role — confirmed safe

**File**: `tests/integration/test_9398_real_agent_subprocess.py` lines 436, 470

Every test that calls `real_harness()` gets a fresh `tempfile.TemporaryDirectory` with a
new `SQUIDSQUAD_DIR`. The harness subprocess reads `.harness-state.json` from
`SQUIDSQUAD_DIR` (confirmed in harness.py lines 421–424). Agent state (`AgentState` map)
is in-memory and initialized fresh per harness process. There is no shared mutable state
between tests. The live harness (if running) is on a different port and a different
`SQUIDSQUAD_DIR` — the role allowlist check reads from live `config.md` but does not
write to live state. Isolation is sound.

---

## Finding 7 — NIT: `_boot_agent_stub.py` only runs under `if __name__ == "__main__"`

**File**: `tests/integration/fixtures/_boot_agent_stub.py` lines 83–100

The entire executable body is under the `if __name__ == "__main__"` guard, which is
correct for a script invoked via `python _boot_agent_stub.py <role>`. If someone
accidentally imports it (e.g., pytest discovery in non-package mode), it silently does
nothing. The `__init__.py` in `fixtures/` makes this an explicit package so accidental
import is unlikely. Acceptable as-is.

---

## Finding 8 — NIT: CI flakiness vectors

The new tests are inherently time-dependent (subprocess spawn, uvicorn cold start,
`tasklist`). Known risks on a busy CI runner:

1. **Port collision**: No `port_hint` is passed; the harness auto-selects a port. If
   two test workers (parallel pytest) race to start harnesses at the same time, one may
   bind a port the other expected to be free. `real_harness` reads the actual port from
   the port file so there is no explicit port assumption — this is already handled
   correctly.
2. **Startup timeout (15s)**: Generous for most machines; may be tight on a slow
   Windows CI node with cold Python import cache (uvicorn + fastapi + 20+ local modules).
   No action needed unless flakiness is observed.
3. **`test_live_port_file_not_touched`** skips when `.squidsquad/.harness-port` is
   absent. On a clean CI checkout this skip is silent. The test that actually matters
   (`test_port_file_lives_under_isolated_squid_dir`) does not skip. The skip is correct
   behavior.

---

## Summary

| # | Severity | Issue | Action |
|---|----------|-------|--------|
| 1 | MEDIUM | File handles leak if `Popen` raises; Windows tmpdir cleanup may fail | Fix with `ExitStack` |
| 2 | MEDIUM | `SQUIDSQUAD_DIR` not stripped/expanduser'd; whitespace/tilde/relative edge cases | Fix both files with `strip().expanduser().resolve()` |
| 3 | LOW | `boot_remote` reads live config.md (out of scope, documented) | File follow-up task |
| 4 | LOW | `WindowsError` ⊂ `OSError` confirmed — no action | None |
| 5 | LOW | 30s timeout has no harness-alive fallback on tasklist hang | Optional polish |
| 6 | LOW | Cross-test isolation via `"skill"` — confirmed sound | None |
| 7 | NIT | Stub guard pattern | Acceptable |
| 8 | NIT | CI flakiness vectors | Monitor |

The two MEDIUM findings (#1, #2) are correctness gaps, but neither causes test failures
under the expected execution path (Popen always succeeds, fixture always passes clean
absolute paths). The PR is otherwise well-structured with appropriate documentation of
known limitations. The three-gotcha mitigations are correctly implemented.

**STATUS: REVIEWED — recommend SHIP-WITH-CHANGES**

Fix findings #1 and #2 before merge. #3 warrants a follow-up task but should not block
this PR given it is explicitly scoped out. All other findings are informational.
