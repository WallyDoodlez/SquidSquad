# Code Review — #9398 Phase A Cumulative (PR #9614)

**Reviewer**: Sonnet 4.6 (third-tier fallback, post-DeepSeek/GPT-5 hang)
**Scope**: Six commits, cycles 1189–1196. Full Phase A diff (~1861 lines).
**Prior review (cycle 1191)**: 1 BLOCK + 2 MEDIUM — all applied.

---

## Findings

### LOW — `gh_main.py:108-109` — double file-read in `_serve_read`

```python
sys.stdout.write(fixture.read_text(encoding="utf-8"))
if not fixture.read_text(encoding="utf-8").endswith("\n"):
```

The fixture file is read twice per invocation. This is a TOCTOU window (file could change between reads) and a minor waste for large fixture payloads. More practically, a fixture file that is exactly the wrong size at the OS boundary could emit garbled output. Fix: read once into a local variable.

```python
content = fixture.read_text(encoding="utf-8")
sys.stdout.write(content)
if not content.endswith("\n"):
    sys.stdout.write("\n")
```

**Severity**: LOW — fixture is test-only, file is written once at test setup and never mutated. No data corruption is likely in practice, but the pattern is wrong.

---

### LOW — `event_bus.py:40` — `SQUID_DIR` is module-level; in-process callers see stale value after env-var change

`SQUID_DIR = _resolve_squid_dir()` is evaluated once at import time. All test helpers that need isolation spawn subprocess agents, so this is fine for the production use case. However, the unit tests in `test_9398_squidsquad_dir_env_var.py` must use `_fresh_load` (importlib re-execution) to work around the cache — this is documented and correct. The risk is a future developer importing `event_bus` at module scope in a test and then setting `SQUIDSQUAD_DIR`, expecting the override to take effect. No such pattern exists in the current test suite.

**No code change needed** — the existing `_fresh_load` pattern is the right idiom. A one-line comment in `event_bus.py` near `SQUID_DIR = ...` noting "module-level constant; tests must use subprocess or importlib re-exec to override" would close the trap for future contributors. NIT-level, not blocking.

---

### LOW — `tracker.py` — `_RESOLVED_GH_BIN` global cache is process-wide; parallel pytest workers on the same PATH will share the first resolution

`_RESOLVED_GH_BIN` is a module-level global. If pytest-xdist or any parallel runner forks the test process and multiple test workers share the same interpreter image, the cache is populated by the first `_resolve_gh_bin()` call and all subsequent calls in the same worker image see the same value — which is correct within one worker. However, if a test does `mod._RESOLVED_GH_BIN = None` to force re-resolution (the unit tests don't do this, they use `_fresh_tracker()` instead), a concurrent test in the same worker could see the reset. Current test suite uses `_fresh_tracker()` (isolated module instances) so this is not a problem today. Document as a known limitation.

**Severity**: LOW — current test suite is safe. Not a parallelism bug under existing `run_tests.py`.

---

### LOW — `_run_emit_probe` inline Python string — path injection risk is bounded but non-obvious

```python
f"{str(REPO_ROOT)!r}, 'references', 'scripts'));"
```

`REPO_ROOT` is derived from `Path(__file__).resolve()` at module load, not from user input, so the injection surface is zero for production runs. However, if `REPO_ROOT` contains a single quote (e.g. `/home/user's-machine/SquidSquad`), the `!r` repr escapes will produce a broken Python string literal and the subprocess will fail with a `SyntaxError`, surfacing as `rc=1` from the probe with a confusing error message.

The fix is to pass `REPO_ROOT` via environment variable rather than inline into the `-c` string:

```python
env["_PROBE_REPO_ROOT"] = str(REPO_ROOT)
# Then in -c string:
"import os; sys.path.insert(0, os.path.join(os.environ['_PROBE_REPO_ROOT'], 'references', 'scripts'))"
```

**Severity**: LOW — the repo path is controlled (not user input), and paths with embedded single quotes are vanishingly rare in practice. Worth fixing before Phase B when external CI may run on arbitrary paths.

---

### NIT — `test_9398_real_agent_subprocess.py:171-173` — deferred imports in module body

```python
import os  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
```

These are injected mid-file between test classes to support the work-pickup section. They are already in the standard library; the `# noqa` silencers are correct. This is a style concern only — a future reader adding imports at the top of the file could duplicate them. Moving all imports to the top of the file would be cleaner. Not worth a revision cycle.

---

### NIT — `gh_main.py` — `_emit_empty_for_read("status")` returns `{}` (object), not `[]`

```python
def _emit_empty_for_read(verb: str) -> int:
    if verb == "list":
        sys.stdout.write("[]\n")
    else:
        sys.stdout.write("{}\n")
```

`gh status` outputs a structured object, so `{}` is correct. `gh issue view` also returns `{}`. But `gh pr list` returns an array — it's routed as "list" so it gets `[]`, which is correct. The else-branch correctly handles all current consumers. No bug.

---

## Cross-File Consistency Analysis

**Q1: env_with_gh_shim + real_harness merge order**

`real_harness` builds `env = dict(os.environ)` then sets `SQUIDSQUAD_DIR` and `SQUIDSQUAD_HARNESS_NO_AUTO_START`. `env_with_gh_shim` takes a `base_env` dict and prepends the shim to `PATH`. The degraded-mode tests combine them as:

```python
env = ems.env_with_gh_shim(fixtures_dir=fdir)
env["SQUIDSQUAD_DIR"] = str(squid_dir)
```

This is correct: `env_with_gh_shim` copies `os.environ`, then the test mutates `SQUIDSQUAD_DIR` separately. No conflict. The `real_harness` context yields `squid_dir`; tests that call `boot_agent_subprocess` pass `squid_dir` explicitly. The harness subprocess sees `SQUIDSQUAD_DIR` from its own spawning env (set inside `real_harness`); the agent subprocess inherits the test's env dict. Both agree on `squid_dir`. Clean.

**Q2: tracker.py gh invocations outside `_run_list`**

All `gh` invocations in `tracker.py` go through `_run_list`. The two bare `subprocess.run` calls at lines 314 and 1066 use `sys.executable` (running `diagnostics.py` and `config.py`), not `gh`. No bypass exists.

**Q3: Test isolation / global state bleed**

Each `real_harness()` call creates a fresh `TemporaryDirectory`. The harness subprocess writes its port file to the isolated `squid_dir`. Agent subprocesses inherit `SQUIDSQUAD_DIR` from the test's env dict, which points at that same tmpdir. After the `with real_harness()` block exits, `_terminate_proc` kills the harness and `TemporaryDirectory.__exit__` removes the tmpdir. The next test starts fresh.

The `_RESOLVED_GH_BIN` cache in `tracker.py` is process-wide, but each `_run_tracker` call spawns a new `tracker.py` subprocess — fresh process, fresh module load, fresh cache. No bleed.

The degraded-mode test `test_emit_succeeds_when_harness_comes_up` runs INSIDE `real_harness()`. It uses `_run_emit_probe` which sets `SQUIDSQUAD_DIR` from the fixture's `squid_dir`. This is the same `squid_dir` yielded by the context — correct. Even if this test runs after the work-pickup test (which used `role="skill"` in a different fixture dir), there is no shared global state between the two test runs. The harness's in-memory `AgentState` lives in the subprocess, which is fresh per `real_harness()` context entry.

**Q4: Bootup blocking / 10s timeout**

`boot_agent_subprocess` has `timeout=10.0`. The stub calls `event_bus.bootup_complete(role)` which fires `event_bus.emit`, which uses `_TIMEOUT = 0.5` (urllib with 500ms). If the harness is slow to accept during startup, the `emit` attempt will timeout in 0.5s and return silently (fire-and-forget). The test then calls `_get_agent(port, role, timeout=30.0)` and checks the flag. If the 500ms emit window was missed, `bootup_complete` returns without actually posting, and the flag stays False — the test fails with a clear assertion message. This is correct behavior: `real_harness()` already waits for `/status` 200 before yielding, so the harness IS accepting connections by the time `boot_agent_subprocess` runs. The startup race is closed.

**Q5: Coverage gaps — bootup test doesn't assert gh-shim writes**

The bootup test (`TestBootupCompleteAcrossRealSubprocesses`) doesn't assert on `_writes.log` — that's correct and intentional: the stub emits `bootup-complete`, which is an HTTP POST to `/events`, not a `gh` call. The work-pickup test correctly asserts on `_writes.log` for the `tracker.transition` path. The split is appropriate.

Error paths in the shim (invalid fixture JSON, unreadable `_writes.log`) are not tested. A malformed `default.json` would cause `json.loads` to fail in tracker.py (the parse happens in tracker, not the shim), which would surface as a non-zero tracker exit code and a clear assertion failure. The shim itself silently returns `[]` on read and `0` on write regardless of fixture state — so "corrupt fixture" doesn't crash the shim, it just feeds bad data upstream. Acceptable for a test fixture; the failure mode is detectable.

---

## Summary Table

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | LOW | `gh_main.py:108-109` | Double file-read in `_serve_read` |
| 2 | LOW | `event_bus.py:40` | Module-level constant trap (doc-only fix) |
| 3 | LOW | `tracker.py:319` | `_RESOLVED_GH_BIN` cache in parallel-test context |
| 4 | LOW | `test_9398_real_agent_subprocess.py:381-389` | Path-with-apostrophe injection in emit probe |
| 5 | NIT | `test_9398_real_agent_subprocess.py:171-173` | Mid-file deferred imports |
| 6 | NIT | `gh_main.py:54-61` | `status` verb mapping (correct, no bug) |

No BLOCK findings. No MEDIUM findings. Prior review's 1 BLOCK and 2 MEDIUM are confirmed resolved.

---

## Verdict

**STATUS: REVIEWED — recommend SHIP-AS-IS**

The four LOW findings are all in test/fixture code, not production paths. The double-read in `gh_main.py` is the most embarrassing but causes no data corruption under realistic test conditions. The path-injection concern is theoretical (repo paths with embedded single quotes). All cross-file composition is correct. Test isolation is solid across parallel runs at the `subprocess.run` boundary. The `_resolve_gh_bin` / `_run_list` patch closes the Windows `.cmd` shim gap correctly and completely — all `gh` calls in tracker.py route through it with no bypass.

Phase A infrastructure is ready for Phase B layering.
