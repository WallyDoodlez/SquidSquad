I've thoroughly reviewed all three changed files — the wizard.py additions, the WIZARD.md runbook updates, and the new test file. Let me trace through the full logic systematically.

## Analysis Summary

### Correctness — probe/restart routing
- `_read_harness_port` reads `.squidsquad/.harness-port` with a safe fallback to 7373 (line 1090-1096). Matches the existing `cycle_post._discover_harness_port` pattern.
- `_harness_reachable` probes `GET /status` on `127.0.0.1:<port>` and considers ANY failure (transport error, timeout, non-2xx) as "unreachable" (lines 1115-1124). This correctly maps to the "falls through to start.sh" AC1 requirement.
- `_install_aliases` reads config.md and delegates to `config.parse_aliases_registry` (line 1142), which handles both bullet-form and table-form configs. Returns `[]` on any parse failure, which the caller correctly surfaces as an error.
- `_restart_one_alias` sends stop then start, short-circuiting on the first failure and NOT attempting start after a failed stop (lines 1152-1158). The test `test_one_alias_stop_http_error_recorded` explicitly verifies that `start` is never called when `stop` fails (line 512).

### Endpoints match HARNESS-ARCH §4.1
- URLs are constructed as `http://127.0.0.1:{port}/agents/{alias}/{action}` (line 1153), producing paths like `/agents/dm/stop` and `/agents/dm/start`. This matches the §4.1 lifecycle routes.

### Reachable/unreachable branch semantics
- **Reachable**: best-effort per-alias stop+start. Failures are recorded but non-fatal — other aliases still restart (lines 1214-1219). This is correct per the spec.
- **Unreachable**: returns `ok: true` (it's a normal branch, not an error), with `cold_start_cmd: "./start.sh"` (lines 1186-1197). The wizard never spawns the harness.
- **Reachable + no aliases**: returns `ok: false` — correctly treated as an error (lines 1198-1211).

### Test coverage
- `TestUnreachable`: covers transport error (ConnectionRefusedError), non-2xx (503), and port resolution — AC5 unreachable path.
- `TestReachable`: covers full restart sequence, custom port, and no-aliases edge case — AC5 reachable path.
- `TestPartialFailure`: covers stop failure (HTTP 500 via status_map) and start failure (transport error via raise_on) — AC5 partial failure.
- `TestCmdExitCodes`: verifies exit 0 for unreachable and clean restart, exit 1 for reachable-with-failures.

### Regression check
- No existing functions are modified. Only new code is added between `migration_walk_plan` and Step 1, plus a dispatch entry in `main()`. Zero regression risk.

### Doc/runbook sync (AC4)
- WIZARD.md Step 7.5c describes the exact JSON envelope and branching logic the code produces.
- Step 7.6's three-way branching (refreshed / cold-start / partial-failure) maps to the three return shapes from `restart_agents`.
- Step 0b.1 forward-ref is updated to point to 7.5c instead of saying "not yet in this runbook."

### Edge cases handled
- Missing `.harness-port` → default 7373
- Whitespace/junk in port file → default 7373
- Missing config.md → empty alias list → surfaced as error
- Malformed `## Aliases` section → `parse_aliases_registry` raises → caught → `[]`
- Per-alias transport failures → recorded, not fatal
- `_http_request` sends `Content-Length: 0` for body-less POSTs (line 1108), avoiding servers that reject body-less POSTs

NO_FINDINGS