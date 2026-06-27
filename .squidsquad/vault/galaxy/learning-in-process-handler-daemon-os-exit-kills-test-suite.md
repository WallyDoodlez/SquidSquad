---
name: learning-in-process-handler-daemon-os-exit-kills-test-suite
description: a pytest test that drives an in-process handler (FastAPI TestClient) whose handler spawns a DAEMON thread that calls os._exit will silently hard-kill the whole test process if the os._exit patch reverts before the thread fires — exit 0, no summary, pytest.main() never returns; the death floats by TIMING (≈the % the suite reached when the delayed thread fired), so it looks position-independent. Join the thread INSIDE the patch context; add a conftest thread-leak guard.
metadata:
  type: learning
type: learning
tags: [learning, testing, pytest, false-green, os-exit, daemon-thread, test-isolation, harness, 12720, 12408, deepseek]
created: 2026-06-17
updated: 2026-06-17
author: skill
owner: skill
status: active
confidence: high
source: observation
---

# Learning: an in-process handler's daemon `os._exit` thread can silently kill the whole test suite

## What happened (#12720)

`pytest tests/` was a **false green**: it hard-exited at ~58% with **exit code 0, no summary, junitxml never written, `pytest.main()` never returned**. Root cause was `test_harness.py::test_post_shutdown_returns_202`: it POSTs `/shutdown` to the in-process `TestClient(app)`. The harness `/shutdown` handler spawns a **daemon thread** named `shutdown` that does `time.sleep(1)` then `os._exit(0)`. The test's `patch("harness.os._exit")` covered only the synchronous POST (which returns 202 immediately); the daemon thread called the **real** `os._exit(0)` ~1s later, after the patch context had already reverted, hard-killing the entire pytest process.

The same masker drove a [[learning-suite-exit-code-not-proof-of-all-pass]] failure in `run_tests.py` (#12408): the static gate runs `pytest` as a subprocess, so `os._exit(0)` killed the subprocess with returncode 0 → the gate reported "passed".

## Why it was hard to diagnose

- **Exit 0 + no traceback** ⇒ not an assertion, not a normal `sys.exit`. A patched `os._exit` "never fires" because the call happens in a daemon thread *after* the patch reverts (the patch and the call are separated in time).
- **"Position/time-based ~58%, stays even when ignoring file X"** is the signature of a **delayed** kill: the death lands on whatever test is running ~1s after the trigger test, not on the trigger test itself — so it floats and looks file-independent. Do not chase the file at the death point; find what armed a delayed thread/`os._exit`/timer earlier.

## The principle

A test that drives an **in-process** handler (TestClient / direct call) whose handler spawns a thread that may call `os._exit` (or any hard exit) MUST **join that thread inside the patch context** so the *mock* fires, not the real exit. Patching `os._exit` is necessary but not sufficient — the patch must outlive the asynchronous call. Corollary: assert thread/mock state **outside** the patch block; a failing assert inside reverts the patch while the thread may still be live → the real `os._exit` fires (the bug re-arms itself). And do not patch the thread's `time.sleep` to "speed it up" — that races the find/join (the thread can finish before you enumerate it); leave the real sleep so the thread is reliably alive when you join it.

## The systemic defense (reusable)

A `tests/conftest.py` thread-leak guard (`wrapper=True` hooks: snapshot threads before the test, check after teardown) that **fails loudly** if a test leaves alive a non-daemon thread (live server/observer) OR a known-dangerous daemon (`shutdown`, the `os._exit` caller). It converts a silent delayed process-kill into a normal per-test failure. The leak check must run **even when teardown raises** (try/except around the `yield`), else a test that fails teardown AND leaks the thread escapes the guard. Sibling to [[learning-in-process-import-resolution-test-contaminates-suite]] — both are "one bad in-process test poisons the whole suite" classes.