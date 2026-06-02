Now I have a thorough understanding of all three files. Let me trace through each review area systematically.

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 1589–1616 (`start_all`), 1674–1710 (`start_agent`)
- **Severity**: error
- **Issue**: HTTP spawn endpoints do not check `state.compose_freshness_failed`, so they bypass the E1 spawn-refusal contract. When `compose_freshness_failed` is `True` (set at line 1388), the auto-start loop in `_deferred_init` correctly short-circuits (line 1397 `return`), but an operator can still spawn agents via `POST /agents/{role}/start` or `POST /agents/all/start` — directly violating AC4's mandate that "the caller MUST refuse to spawn agents until the operator resolves the source issue; no fall-back."
- **Evidence**: 
  - `compose_freshness.py` lines 68–70: AC4 states on `"failed"` "the caller MUST refuse to spawn agents." 
  - `harness.py` line 1388: `state.compose_freshness_failed = True` is set on failure.
  - `harness.py` lines 1674–1710: `start_agent` reads `state.get_agent(role)` for the "already running" check but never reads `state.compose_freshness_failed`. Same for `start_all` at lines 1589–1616.
  - `tests/test_compose_freshness_e1.py` lines 253–255: the test `test_harness_state_carries_failure_flag` explicitly comments: *"The flag must live on HarnessState so spawn paths beyond _deferred_init's auto-start loop can also gate on it."* — yet those spawn paths never gate on it.
- **Suggested fix**: Add a gate at the top of both `start_agent` and `start_all`:
  ```python
  if state.compose_freshness_failed:
      raise HTTPException(
          status_code=503,
          detail="Compose freshness check failed — agents cannot be spawned. "
                 "Fix the source issue and restart the harness."
      )
  ```
  Also: the health-poller's auto-reboot path (lines 425–437) calls `boot_remote.boot_agent(role)` without checking the flag, so on a harness restart where `.harness-state.json` contains agents with `intent=running`, the poller will re-spawn them even after compose freshness failed. That path should also gate on `self.compose_freshness_failed`.

---

### Finding 2

- **File**: `references/scripts/compose_freshness.py`
- **Line**: 41–55 (specifically lines 48 and 54)
- **Severity**: warning
- **Issue**: `references/sub-skills/manifest.md` (line 54) is matched twice: once by the `references/sub-skills/**/*.md` glob on line 48, and once by the explicit literal glob on line 54. Python's `Path.glob('references/sub-skills/**/*.md')` matches zero or more intermediate directories, so `manifest.md` at the root of `sub-skills/` is included. The file is yielded twice by `_iter_compose_input_files` (line 94–110) and hashed twice in `compute_compose_checksum` (lines 113–152). The result is still deterministic, but:
  1. The file's content contributes double weight — non-obvious to anyone reading the glob list.
  2. If a future maintainer removes the explicit `manifest.md` glob (thinking it's redundant), the checksum changes because the file goes from being hashed 2× to 1× — a regression risk.
- **Evidence**: Line 48 `"references/sub-skills/**/*.md"` — the `**` glob component matches zero directories per Python docs. Combined with line 54 `"references/sub-skills/manifest.md"`, the file `references/sub-skills/manifest.md` matches both patterns. `_iter_compose_input_files` (line 107–109) does not deduplicate; `compute_compose_checksum` (lines 135–141) also does not deduplicate.
- **Suggested fix**: Either remove the explicit `"references/sub-skills/manifest.md"` from `COMPOSE_INPUT_GLOBS` (since it's already covered by `**/*.md`) or add deduplication in `_iter_compose_input_files`:
  ```python
  seen = set()
  for path in _iter_compose_input_files(repo_root):
      try:
          rel = path.relative_to(repo_root).as_posix()
      except ValueError:
          continue
      if rel not in seen:
          seen.add(rel)
          rel_paths.append((rel, path))
  ```

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 1466 (thread launch) vs. 1374–1388 (the check itself)
- **Severity**: warning
- **Issue**: The E1 freshness check runs inside `_deferred_init`, which is launched as a daemon thread at line 1466. The lifespan then immediately starts the health poller (line 1467), starts the L4 watcher (line 1472), and `yield`s (line 1474) — making the HTTP server accept connections. This means `POST /agents/{role}/start` is callable **before** `_deferred_init` reaches the E1 check at line 1376 and potentially sets `compose_freshness_failed = True`. On the "drift → compose runs" path, the compose subprocess could take tens of seconds; during that entire window, HTTP spawn requests succeed unchallenged. 

  Even with the fix from Finding 1 (flag check in endpoints), there's still a race: a spawn request arriving before `_deferred_init` sets the flag would not be blocked, because the flag defaults to `False` (line 221).
- **Evidence**: The execution order in `lifespan`:
  1. Line 1466: `threading.Thread(target=_deferred_init, daemon=True).start()` — the E1 check hasn't run yet.
  2. Line 1467–1472: poller and L4 watcher start synchronously (fast).
  3. Line 1474: `yield` — server begins accepting HTTP requests.
  
  Inside `_deferred_init`:
  1. Lines 1344–1357: port file distribution (I/O, fast).
  2. Lines 1361–1365: `load_state()`, `event_lifecycle.load()`, etc. (I/O, fast).
  3. Lines 1374–1379: **E1 check** — if drift is detected, calls `compose.py deploy-all` via subprocess, which can take 10–60+ seconds.
  4. Line 1388: `compose_freshness_failed = True` (only set after compose fails).
  
  Between steps 3 and 4 in lifespan and steps 1–3 in `_deferred_init`, any HTTP spawn request against the already-yielded server will see `compose_freshness_failed == False` and proceed.
- **Suggested fix**: Move the E1 freshness check into the lifespan **synchronously, before the `yield`** — specifically after `load_state()` and before `threading.Thread(target=_deferred_init).start()`. That way the server doesn't accept connections until the gate has decided. The deferred thread would then only handle the auto-start loop (which is already gated). This also resolves the health-poller race because the poller starts after the check completes.

  Concretely, restructure the lifespan as:
  ```python
  # --- E1 freshness gate (synchronous, before server accepts connections) ---
  state.load_state()
  # ... E1 check here ...
  if result.status == "failed":
      state.compose_freshness_failed = True
      _log("ERROR: ...")
      # Still yield so /status works, but flag blocks spawns
  # --- deferred init (auto-start only) ---
  threading.Thread(target=_deferred_init_auto_start, daemon=True).start()
  state.start_poller()
  state.start_l4_watcher()
  yield
  ```

---

### Finding 4

- **File**: `references/scripts/harness.py`
- **Line**: 425–437 (health poller auto-reboot)
- **Severity**: warning
- **Issue**: The health poller's auto-reboot loop (`update_health`, lines 425–437) calls `boot_remote.boot_agent(role)` without checking `self.compose_freshness_failed`. After a harness restart where `.harness-state.json` contains agents with `intent=running` and `status=running` (from the prior boot), `load_state()` (line 1362) restores those agents into `state.agents`. The poller (started at line 1467) will detect them as dead (stale PIDs), classify them as `status="stalled"` with `prev_status="running"`, and auto-reboot them — even if the E1 check subsequently fails. The same issue applies to agents that die naturally after the harness has been running with a failed compose check.
- **Evidence**: 
  - Lines 425–437: `boot_remote.boot_agent(role)` is called with no `compose_freshness_failed` guard.
  - Line 1388: `state.compose_freshness_failed = True` is set, but `update_health` never reads this field.
  - The `_NO_AUTO_REBOOT` escape hatch (line 99) provides a manual workaround, but the default path (`_NO_AUTO_REBOOT=False`) hits the gap.
- **Suggested fix**: At the top of the reboot loop (line 426, inside the `for role in reboot_roles:` block), add:
  ```python
  if self.compose_freshness_failed:
      _log(f"[compose-freshness-failed] {role} died; not respawning per E1 gate")
      continue
  ```
  This is a defense-in-depth complement to Finding 1's HTTP-endpoint fix.