NO_FINDINGS

---

**Rationale for each review criterion:**

**(a) loop="none" vs startup/shutdown:** `loop="none"` only changes which event loop is created — it has no effect on uvicorn's `Server.run()`, `should_exit`, or the daemon-thread join loop (lines 3205–3215). The `asyncio.run()` inside `server.run()` creates and destroys the loop internally; the `should_exit` flag is a plain boolean checked in uvicorn's serve loop; the main-thread join with `timeout=1.0` is pure threading. None of these mechanisms are loop-type-dependent.

**(b) Platform regression:** `requirements.txt` does not include `uvloop`. On Linux/macOS without uvloop, uvicorn's `loop="auto"` falls back to `asyncio.new_event_loop()` → `SelectorEventLoop` — the same path `loop="none"` takes. No behavioral change.

**(c) Policy ordering:** `asyncio.set_event_loop_policy(...)` executes at line 3118; `_build_uvicorn_config(...)` runs at line 3202; the loop is created later inside `server.run()` on the daemon thread (line 3205–3206). Policy is set first.

**(d) Proactor re-imposition via subprocess paths:** The comment at lines 3115–3116 explicitly states the harness uses only synchronous `subprocess.run`/`Popen`. Uvicorn itself (an ASGI HTTP server) does not spawn asyncio subprocesses. No path re-imposes Proactor.

**(e) loop_factory=None → new_event_loop() → policy:** The test at `tests/test_11587_uvicorn_selector_loop.py` line 75 confirms `Config(loop="none").get_loop_factory() is None` against the installed uvicorn. The end-to-end test at line 106 confirms that `asyncio.new_event_loop()` under `WindowsSelectorEventLoopPolicy` yields a `SelectorEventLoop`. The chain is verified.