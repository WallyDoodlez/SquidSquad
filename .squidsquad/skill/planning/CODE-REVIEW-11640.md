I've completed a thorough analysis of the diff, all changed code paths, and all integration points. Here are my conclusions:

**Covered spawn paths:**
- `boot_agent` — catches `CloneResolutionError` at the `_needs_boot` gate, returns `action="error"` / `success=False`, zero spawn. ✅
- Harness auto-reboot loop — handles `action="error"` from `boot_agent`, marks `agent.status = "error"`. ✅
- `POST /agents/{role}/start` (`start_agent`) — handles `action="error"`, marks agent error. ✅
- `POST /agents/{role}/restart` (`restart_agent`) — resolves clone before intent mutation, refuses on failure. ✅
- `POST /agents/all/stop` (`stop_all`) — skips unresolvable roles. ✅
- `POST /shutdown` — skips unresolvable roles. ✅
- `POST /agents/all/start` (`start_all`) — goes through `boot_agent` which refuses internally. ✅
- CLI paths (`start_team.py` → `squidsquad_cli.py` → harness HTTP API) — all go through protected endpoints. ✅

**Unprotected `_get_clone_path` / `_needs_boot` call sites verified:**
- Health poller (line 291) — pre-existing `except Exception: continue` catches `CloneResolutionError`. ✅
- `shutdown` lines 2502, 2534 — only reached for roles that already passed the `_needs_boot` filter, which internally resolved the clone. ✅
- `stop_all` line 1633 (`_needs_boot`) — only reached after `_get_clone_path` already succeeded for the same role. ✅

**Behavioral spec verified:**
- Unregistered role → `CloneResolutionError` raised. ✅
- Registered-but-missing path → `CloneResolutionError` raised. ✅
- Explicit `pm -> .` → resolves normally (path exists, returns str). ✅
- Refusal produces zero spawn (caught before orphan sweep, boot sentinel, terminal spawn). ✅
- Refusal marks agent error. ✅

No regressions, no swallowed exceptions, no path that resolves to REPO_ROOT, no unintended state mutation before clone-resolution gate.

NO_FINDINGS