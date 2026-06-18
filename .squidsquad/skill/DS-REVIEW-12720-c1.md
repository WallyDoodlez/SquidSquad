I have reviewed all three changed files thoroughly. Here are my findings:

---

### Finding 1

- **File**: tests/test_12720_thread_leak_guard.py
- **Line**: 18
- **Severity**: error
- **Issue**: `import conftest` will raise `ModuleNotFoundError` when the test runs standalone (e.g., `pytest tests/test_12720_thread_leak_guard.py`) because `tests/` is not on `sys.path` by default. The test relies on a fragile side-effect — another test file (like `test_11394_static_discovery.py` line 19 or `test_references.py` line 94) having already added `tests/` to `sys.path` via `sys.path.insert`. This is an import-order dependency that the file itself does not enforce.
- **Evidence**: The project convention for intra-test-directory imports is explicitly demonstrated by `test_11394_static_discovery.py` lines 17–19 (`TESTS_DIR = REPO_ROOT / "tests"` / `sys.path.insert(0, str(TESTS_DIR))`) and `test_references.py` lines 93–94 (same pattern). The new file omits this preamble entirely. When pytest collects this file, only the repo root is on `sys.path`; `tests/` is a subdirectory and not automatically added. Without the `sys.path.insert`, `import conftest` resolves to nothing on the path.
- **Suggested fix**: Add the same `sys.path.insert` preamble other test files use:

  ```python
  import sys
  from pathlib import Path
  TESTS_DIR = Path(__file__).resolve().parent
  sys.path.insert(0, str(TESTS_DIR))
  import conftest
  ```

---

### Finding 2

- **File**: tests/test_12720_thread_leak_guard.py
- **Line**: 18 (via interaction with tests/conftest.py lines 95–96, 103–104)
- **Severity**: warning
- **Issue**: When `import conftest` succeeds (i.e., after `tests/` is added to `sys.path`), it loads `tests/conftest.py` as a NEW module named `conftest`. Pytest already loaded the same file as `tests.conftest` during collection. These are distinct entries in `sys.modules`, so the module body executes twice. The `@pytest.hookimpl(wrapper=True)` decorators at lines 95 and 103 of `tests/conftest.py` mark the hook functions — and those marks are processed when each module instance is registered as a pytest plugin. This means `pytest_runtest_protocol` and `pytest_runtest_teardown` would each be registered twice as wrapper hooks, causing nested double-wrapping of the test lifecycle (two baselines captured, two leak checks run per test).
- **Evidence**: Python's import system keys `sys.modules` by module name, not by file path. `sys.modules['tests.conftest']` (pytest's load) and `sys.modules['conftest']` (the test's `import`) are separate entries, so the file executes twice. The `@pytest.hookimpl(wrapper=True)` line is module-level code that mutates function attributes; when the module is registered as a plugin, those attributes are read and hooks are installed. Two module objects = two registrations.
- **Suggested fix**: After adding `sys.path.insert` (see Finding 1), reference the guard functions through `sys.modules` to avoid re-importing:

  ```python
  import sys
  from pathlib import Path
  TESTS_DIR = Path(__file__).resolve().parent
  sys.path.insert(0, str(TESTS_DIR))
  
  # Use the already-registered conftest module if pytest loaded it first;
  # otherwise import fresh (standalone invocation).
  conftest = sys.modules.get('tests.conftest')
  if conftest is None:
      import conftest as _conftest
      conftest = _conftest
  ```

  Alternatively, and more simply, import just the specific private functions/constants without triggering the module-level hookimpl decorations:

  ```python
  from conftest import _guard_leaked_threads, _GUARD_ALLOWED_THREAD_NAMES
  ```

  This still re-executes the module body (so the hookimpl decorations run again), but it cleanly documents what is actually used. The double-registration risk remains but is noted. The truly clean fix is to move the guard logic and its tests out of conftest.py into a separate helper module that can be imported without side effects.

---

### Finding 3

- **File**: tests/test_12720_thread_leak_guard.py
- **Line**: 76
- **Severity**: warning
- **Issue**: `name = next(iter(conftest._GUARD_ALLOWED_THREAD_NAMES))` will raise `StopIteration` (not a test assertion failure) if the `_GUARD_ALLOWED_THREAD_NAMES` frozenset ever becomes empty. Since this test's stated purpose is to "lock the guard's classification logic so a future edit can't silently neuter it" (docstring line 11–12), a crash-on-empty-set would be a confusing failure mode that doesn't clearly communicate that the allowlist was emptied — defeating the test's own regression-detection goal.
- **Evidence**: `iter()` on an empty frozenset produces an iterator that raises `StopIteration` on the first `next()` call. The resulting traceback would show `StopIteration` at line 76, not a clean `AssertionError` with a descriptive message about the empty allowlist.
- **Suggested fix**: Guard against empty allowlist:

  ```python
  assert conftest._GUARD_ALLOWED_THREAD_NAMES, (
      "_GUARD_ALLOWED_THREAD_NAMES is empty — cannot verify allowlist logic")
  name = next(iter(conftest._GUARD_ALLOWED_THREAD_NAMES))
  ```

---

### Finding 4

- **File**: tests/test_harness.py
- **Line**: 1731
- **Severity**: warning
- **Issue**: `self.assertFalse(t.is_alive(), ...)` sits inside the `with patch(...)` block. If the assertion fails (thread still alive after 10s join timeout), the `AssertionError` propagates, causes the `with` context manager to exit, and reverts ALL patches — including `patch("harness.os._exit")`. The still-alive daemon thread would then call the real `os._exit(0)` and hard-kill the pytest process. Although unlikely in practice (the `time.sleep` mock makes the thread exit almost instantly), this is a latent correctness hazard: a test failure mode that amplifies itself into a process kill.
- **Evidence**: The `_do_shutdown` function at `harness.py:3394` calls `os._exit(0)`. With `harness.time.sleep` mocked, the thread executes in microseconds rather than 1+ seconds. However, if any code path in `_do_shutdown` hangs (e.g., `state.save_state()` blocks on a locked file, or `boot_remote._needs_boot` raises an unexpected exception that is not `CloneResolutionError`), the `t.join(timeout=10)` could expire, `assertFalse` fires, patches revert, and the daemon thread then calls the real `os._exit(0)`. The 10-second timeout window is wide enough to make this plausible under edge-case disk I/O stalls.
- **Suggested fix**: Perform the `assertFalse` / `mock_exit` assertions AFTER the `with` block exits, but only after verifying the thread is dead. Join the thread inside the `with` block, save the result, then assert outside:

  ```python
  with patch(...) as mock_exit:
      resp = self.client.post("/shutdown")
      for t in threading.enumerate():
          if t.name == "shutdown":
              t.join(timeout=10)
              thread_was_alive = t.is_alive()
              break
      else:
          thread_was_alive = None  # thread not found
      mock_called = mock_exit.called
      mock_call_args = mock_exit.call_args
  self.assertIsNotNone(thread_was_alive, "shutdown thread was never spawned")
  self.assertFalse(thread_was_alive, "shutdown thread did not finish...")
  self.assertTrue(mock_called, "os._exit was never called")
  # ...assert call args...
  ```

  This ensures no patch is reverted before the assertions are evaluated.

---

### Finding 5

- **File**: tests/conftest.py
- **Line**: 103–121
- **Severity**: warning
- **Issue**: The `pytest_runtest_teardown` wrapper silently skips the leak check if the teardown phase raises an exception. Because `res = yield` receives the result of the inner chain but the `yield` itself raises if teardown propagates an exception, lines 106–121 never execute. In this scenario, a test that fails during teardown AND leaks a dangerous `shutdown` thread would pass the guard undetected. The leaked thread's `os._exit(0)` (once the real `os._exit` is no longer patched) would still hard-kill pytest.
- **Evidence**: In Python generators used as context managers via `@contextmanager` or `wrapper=True`, if the wrapped code raises, the `yield` statement raises that same exception into the generator. The `res = yield` at line 105 would propagate the exception before assigning to `res`, so the guard logic at lines 106–121 is bypassed entirely. If a test's own teardown or a fixture's teardown fails while simultaneously leaving a `shutdown` thread alive, the guard is blind to it.
- **Suggested fix**: Wrap the yield in a try/finally so the leak check always runs:

  ```python
  @pytest.hookimpl(wrapper=True)
  def pytest_runtest_teardown(item, nextitem):
      exc_info = None
      try:
          res = yield
      except BaseException:
          exc_info = sys.exc_info()
          res = None
      finally:
          baseline = getattr(item, "_sq_thread_baseline", None)
          if baseline is not None:
              leaked = _guard_leaked_threads(baseline)
              if leaked:
                  desc = ", ".join(f"{t.name!r}(daemon={t.daemon})" for t in leaked)
                  pytest.fail(
                      f"#12720 thread-leak guard: {item.nodeid} left live thread(s) "
                      f"alive after teardown: {desc}. ...",
                      pytrace=False,
                  )
      if exc_info:
          raise exc_info[1].with_traceback(exc_info[2])
      return res
  ```