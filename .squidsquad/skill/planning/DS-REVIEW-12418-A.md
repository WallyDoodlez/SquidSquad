Now I have all the context I need. Let me compile my findings.

---

### Finding 1

- **File**: references/scripts/compose.py
- **Line**: 1804
- **Severity**: warning
- **Issue**: The `_SESSION_END_HOOK_URL` is hardcoded to port `7373`. If the harness is started on a non-default port (via `--port` or `SQUIDSQUAD_HARNESS_PORT`), the SessionEnd hook POSTs to the wrong port, connection is refused, and the hook fails silently (fail-open). The harness never records the session end, so `update_health` treats the exit as a crash — the safe default — but it loses the graceful-exit signal for no good reason when the port is simply non-default.
- **Evidence**: Line 1804: `_SESSION_END_HOOK_URL = "http://127.0.0.1:7373/hooks/session-end"`. The harness supports `--port` / `SQUIDSQUAD_HARNESS_PORT` (harness.py line 67-69: `DEFAULT_PORT = 7373`, config.py line 46: `_DEFAULT_HARNESS_PORT = 7373`). Multiple discovery paths (cycle_pre, cycle_post, event_poll) all resolve the port dynamically from `.harness-port`. The comment at lines 1799-1803 acknowledges the limitation and defers a dynamic-port variant to #12271.
- **Suggested fix**: Defer to #12271 as the comment states — this is a documented limitation. If a fix is needed now, read the port from `.squidsquad/.harness-port` at compose time (but this file is gitignored and not synced across clones, which conflicts with the "one committed settings.json" design). The proper fix is #12271's dynamic-port approach.

---

### Finding 2

- **File**: references/scripts/compose.py
- **Line**: 1849
- **Severity**: warning
- **Issue**: The write uses `json.dumps(data, indent=2)` without `sort_keys=True`, while the idempotency comparison at lines 1841 and 1846 uses `json.dumps(data, sort_keys=True)`. This asymmetry means the on-disk file retains whatever key ordering the Python dict happened to have (original JSON order + appended keys at end), while the comparison normalizes via sorted keys. Idempotency is NOT broken (the comparison correctly detects structural equality regardless of key order), but the file format is inconsistent with the comparison's canonicalization. If another tool later normalizes the file to sorted keys, a future `_ensure_session_end_hook` call still correctly no-ops — so this is cosmetic, not a functional defect.
- **Evidence**: Line 1841: `before = json.dumps(data, sort_keys=True)`. Line 1846: `if json.dumps(data, sort_keys=True) == before:`. Line 1849: `settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")` — no `sort_keys=True`. The existing `.claude/settings.json` on disk does have alphabetically-sorted keys (it was written by a previous version of this function or another tool), so a first write by this function would reorder the keys to dict-insertion order, producing a diff for anyone inspecting the file even though the semantic content is identical.
- **Suggested fix**: Add `sort_keys=True` to line 1849: `json.dumps(data, indent=2, sort_keys=True)` so the written file matches the comparison's canonical form and avoids gratuitous key reordering on the first write.

---

### Finding 3

- **File**: references/scripts/compose.py
- **Line**: 1843-1844
- **Severity**: warning
- **Issue**: When `data["hooks"]` exists but is not a dict (e.g., `"hooks": null`, `"hooks": []`, `"hooks": "string"`), the function replaces it with `{}` and then populates only `SessionEnd`. This silently drops ALL existing hooks data — not just a malformed SessionEnd entry but also any `SessionStart` hooks. The docstring says "A missing/corrupt file is treated as empty and (re)written," but this applies to the *entire file* being corrupt JSON, not to a valid JSON file where the `hooks` key specifically has the wrong type. The test `test_corrupt_file_treated_as_empty` only covers corrupt *file-level* JSON, not this mid-structure type mismatch.
- **Evidence**: Line 1842-1844: `hooks = data.get("hooks")` → if `hooks` is e.g. `None` (JSON null) or `[]` (JSON array), `isinstance(hooks, dict)` is False → `data["hooks"] = {}` replaces whatever was there. The `before` snapshot on line 1841 was taken before this mutation, so the comparison correctly detects a change, but the rewrite drops all previous hooks content. This is a data-loss path for a file that is valid JSON but has a semantically-wrong `hooks` type — Claude Code would already reject such a file, but the function could be more surgical (only normalize the `hooks` key to a dict, preserving any content if possible).
- **Suggested fix**: Consider preserving existing `hooks` content when the type is wrong but recoverable. At minimum, log a warning when the `hooks` key is being replaced due to type mismatch. Alternatively, leave this as-is if the position is "any malformed hooks block is treated as empty" — but the docstring should be updated to clarify this case.

---

### Finding 4

- **File**: references/scripts/compose.py
- **Line**: 2111-2133
- **Severity**: warning
- **Issue**: `_ensure_session_end_hook` is only called after ALL alias deployments in `deploy-all` succeed. If any alias deployment fails (line 2111-2113), the function exits with `sys.exit(1)` BEFORE the SessionEnd hook is deployed. This means a persistent failure in one alias (e.g., R1-R7 validation failure, catalog gate failure) blocks the SessionEnd hook from ever being deployed, even though the hook deployment is independent of alias composition success. On a fresh install that has never had the hook deployed, this could indefinitely delay hook deployment.
- **Evidence**: Lines 2111-2113: `if failed: print(...) ; sys.exit(1)`. Lines 2128-2133: the hook deployment code comes AFTER the failure check. The hook is only reached when the entire `for alias in sorted(registry)` loop completes without any failures.
- **Suggested fix**: Consider deploying the SessionEnd hook BEFORE the alias loop, or in a `finally` block that runs regardless of alias deployment success. The hook is an independent concern (harness wiring), not dependent on successful compose of any particular alias. The comment at line 2114 itself says "Install topology bookkeeping (harness-wiring, not composition)" — the SessionEnd hook is also harness-wiring and should arguably be treated the same way as `.local-config` generation (which ALSO comes after the failure check and has the same ordering issue).

---

### Finding 5

- **File**: references/scripts/compose.py
- **Line**: 1816
- **Severity**: warning
- **Issue**: The `X-Agent-Role` header value is `"${SQUIDSQUAD_ROLE}"` — a Claude Code env-var interpolation. If `SQUIDSQUAD_ROLE` is not set in the agent's environment at spawn time, Claude Code sends the literal string `${SQUIDSQUAD_ROLE}` as the header value. The harness's `hook_session_end` at harness.py line 2081 receives this literal, which passes the empty check (it's non-empty), then fails the allowed-roles check at line 2098 and drops with `"unknown-role"` → 200 OK. This is fail-open (correct), but the absence of the env var means the hook silently degrades for that agent. The `allowedEnvVars` declaration at line 1817 tells Claude Code this env var is allowed, but does not guarantee it is SET — that depends on the spawn mechanism.
- **Evidence**: Line 1816: `"headers": {"X-Agent-Role": "${SQUIDSQUAD_ROLE}"}`. Harness.py line 2081: `role = (request.headers.get("X-Agent-Role") or "").strip()`. The `thin_launcher` and harness spawn paths both set `SQUIDSQUAD_ROLE`, but a direct `claude` invocation or a misconfigured spawn would leave it unset. The fail-open design handles this gracefully (200 OK, dropped), so this is a robustness note rather than a correctness defect.
- **Suggested fix**: No code change needed — this is a documentation/operational concern. The fail-open behavior is correct.

---

NO_FINDINGS (no errors that break correctness; the warnings above are documented limitations or edge cases with graceful degradation).