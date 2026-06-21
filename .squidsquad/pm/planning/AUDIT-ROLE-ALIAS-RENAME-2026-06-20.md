# AUDIT: Cross-TRD `role` → `alias` Rename
**Date**: 2026-06-20  
**PRD**: #10839 | **Umbrella**: #10358  
**Authored by**: PM scoping pass (pre-implementation inventory)  
**Gating note**: E6 (#10685) shipped; PRD-D (#10781) status must be confirmed before Phase 2+ begin.

---

## §1 Terminology Baseline

SquidSquad has three distinct concepts that history collapsed into one word, `role`:

| Concept | Definition | Current home in code/docs |
|---|---|---|
| **role-class** | Categorical agent type: `pm` / `worker` / `verifier` / `dm` (+ non-agent `human`). Drives L2 instructions, L4 file selection (`pm.md`, `worker.md`, etc.). Max 4 per install. | `config.py:ALIASES_ROLE_CLASSES`, `references/roles/<role-class>/`, `.squidsquad/project/<role-class>.md` |
| **alias** | Install-time agent-instance name: `skill`, `web`, `frontend-1`, `verifier`, `human`, etc. What routing, clones, file paths, cursors, and forge labels key on. | `.squidsquad/<alias>/`, `.squidsquad/.harness-state.json` (keyed by alias), `.squidsquad/config.md ## Aliases` registry |
| **L3 domain** | Specialization within a role-class: `fe`, `be`, `skill`, `ios`, etc. Drives L3 source selection at compose time. | `references/roles/<role-class>/<domain>/`, `## Aliases` registry third column |

### Already-migrated (no action needed)

- `target_role` → `target_alias` in event payloads: **done** (#11331, `harness.py:3332`).
- `config.py` `parse_aliases_registry()` and `get_alias()`: fully alias-aware, returns `{alias: (role_class, l3_domain)}`.
- `compose.py deploy_alias_v2()`: CLI positional param and output paths are alias-keyed.
- On-disk directory layout `.squidsquad/<alias>/`: correctly uses alias throughout.
- `.squidsquad/.harness-state.json` outer key: alias (not role-class).
- `EAD._alias_for_role_class()` and `target_alias` fields in emitted events: correct.
- `/queue/{alias}` endpoint: already uses `{alias}` in the route (unlike lifecycle endpoints).

---

## §2 Drift Inventory

Legend: **file:line** format. "alias-valued" = the variable holds an alias value but is named `role`.

### Category (i) — DOC-ONLY (prose/table rename, zero runtime risk)

These are band-aid notes in docs that acknowledge the mismatch. When Phase 2/3 land the underlying code fixes, these notes become removable. Until then, they are accurate documentation of technical debt.

| Location | What it says | Action at Phase 1 |
|---|---|---|
| `docs/HARNESS-ARCH.md` §9 (Vocabulary note, line ~470) | Band-aid note explaining `{role}` path params hold alias values | Remove band-aid after Phase 3 ships |
| `docs/HARNESS-ARCH.md` §4.1 table (line ~75-88) | Aspirational response-shape note referencing #10358 | Update table to reflect target shape in Phase 3 |
| `docs/HARNESS-ARCH.md` §3 (line ~59) | `boot_agent(role)` — parenthetical "(legacy parameter name; rename tracked in #10358)" | Remove parenthetical in Phase 2 |
| `docs/HARNESS-ARCH.md` §4.2 event-bus table (line ~96-102) | `{role}` in `/events/for/{role}`, `/events/cursor/{role}` — vocabulary note | Update after Phase 3 |
| `docs/AGENT-RUNTIME.md` §5.3 Vocabulary note (line ~394-396) | Full vocabulary note treating `{role}` as synonym for `{alias}` until #10358 | Remove after Phase 3 |
| `docs/AGENT-RUNTIME.md` §5.2 ack-cursor payload note (line ~298) | "`role` field ... preserved under field-name `role` for code-compat" | Remove after Phase 2 (payload field rename) |
| `docs/AGENT-RUNTIME.md` §8.0 (line ~790) | "`--role` flag accepts the alias value ... rename to `--alias` ships with #10358" | Remove after Phase 2 |
| `docs/INSTALLER-ARCH.md` §4.9 note (line ~290) | "CLI positional parameter is named `<role>` ... alias; the rename to `<alias>` is tracked in #10358" | Remove after Phase 2 |
| `docs/INSTALLER-ARCH.md` §10.3 (line ~556) | "URL-template token is named `{role}` in the source code for legacy compatibility" | Remove after Phase 3 |
| `docs/COMPOSE-ARCHITECTURE.md` header note (line ~21-23) | "CLI flag names (`--role`, `SQUIDSQUAD_ROLE`, ...) accept alias values" | Remove after Phase 2 |
| `CLAUDE.md` root (line 3,5) | `SQUIDSQUAD_ROLE=<role>` — uses `role` in env var name | Update in Phase 2 (env var rename) |

**DOC-ONLY count: ~11 locations** (all in docs/ and CLAUDE.md; all editorial after code fixes land)

### Category (ii) — CODE — Internal (no external contract; medium risk)

Variables, function parameters, and Python attribute names where the value is alias-typed but the identifier says `role`. Renaming is a safe refactor: callers are co-located in the same repo.

| File | Location | What needs renaming | Notes |
|---|---|---|---|
| `harness.py:234` | `AgentState.__slots__` | `"role"` slot → `"alias"` | Cascades to all `self.role` references throughout the file (~50+ hits) |
| `harness.py:272` | `AgentState.__init__(self, role: str, ...)` | param `role` → `alias` | |
| `harness.py:476` | `AgentState.to_dict()` | `"role": self.role` key → `"alias": self.alias` | **EXTERNAL CONTRACT** — see Category (iii) |
| `harness.py:557-563` | `HarnessState.get_agent(role)`, `set_agent(role, state)` | params `role` → `alias` | |
| `harness.py:598-1190` | Health poll loop: `for role in all_roles`, `self.agents[role]`, `reboot_roles`, etc. | loop variables `role` → `alias` | Pure internal; ~60 occurrences in the loop |
| `harness.py:2386-2396` | `_validate_role(role)` function | fn name + param: `_validate_alias(alias)` | |
| `harness.py:3266-3289` | `_filter_events(role=None)` | param `role` → `alias` | |
| `harness.py:1734-1824` | `EventLifecycle` class docstring + `get_cursor(role)`, `advance_cursor(role)` | params `role` → `alias`; comments say "per-role cursor" → "per-alias cursor" | |
| `harness.py:3892` | `_emit_event(event_type, role, ...)` | param `role` → `alias` | Emitter-identity field |
| `harness.py:3904` | `_emit_event` builds `{"role": role, ...}` | event body field `"role"` → see §3 (event payload) | **Partially external** — see Category (iii) |
| `boot_remote.py:138-153` | `_get_all_roles()` | fn name → `_get_all_aliases()` | |
| `boot_remote.py:169-195` | `_get_clone_path(role)` | param → `alias` | |
| `boot_remote.py:218-304` | `_has_booting_sentinel(clone_path, role)`, `_write_booting_sentinel`, `_clear_booting_sentinel` | params → `alias` | |
| `boot_remote.py:311-367` | `_needs_boot(role)` | param → `alias` | |
| `boot_remote.py:558` | `boot_agent(role, ...)` | param → `alias` | Called from harness.py; rename cascades |
| `boot_remote.py:673-677` | CLI `--role <name>` flag | flag → `--alias` | |
| `thin_launcher.py:562-675` | `role = sys.argv[1]`, `env["SQUIDSQUAD_ROLE"] = role`, `--name squidsquad-{role}` | Internal variable + env var set (see env var below) | |
| `event_poll.py:169-404` | `def poll(role, ...)`, `p.add_argument("role")`, `--role` argparse flag | positional arg + flag rename → `alias` | |
| `event_bus.py:108-212` | `def emit(event_type, role, ...)`, `def bootup_complete(role)`, `def ack_cursor(event_id, role)`, `def ack_stop(event_id, result, role=None)` | all `role` params → `alias` | Values are alias-typed |
| `event_bus.py:113` | `"role: Agent role (e.g. 'skill', 'pm', 'qa', 'dm')"` docstring | Update docstring to say "alias" | |
| `cycle.py:68-239` | `def status_bar(role, ...)`, `get_counter(role)`, `set_counter(role, ...)`, etc. | all `role` params → `alias` | |
| `cycle.py:126` | `os.environ.get("SQUIDSQUAD_ROLE", "")` | env var read → `SQUIDSQUAD_ALIAS` | Dependent on env var rename |
| `cycle_pre.py:8` | CLI positional `<role>` | doc string | |
| `cycle_pre.py:1406-1416` | `role = _parse_cli_args(...)`, `ROLE_BUILDERS[role]` | `role` variable → `alias`; `ROLE_BUILDERS` key lookup stays (role-class keyed dict, NOT alias keyed) | Only the CLI arg variable renames; the dict key is role-class typed (stays named correctly) |
| `cycle_pre.py:1487` | `cycle_input["role"] = role` | output JSON field — **EXTERNAL CONTRACT** (see iii) | |
| `cycle_post.py:8` | CLI positional `<role>` | |
| `cycle_post.py:57` | `REQUIRED_FIELDS = {"role", ...}` | JSON field check — **EXTERNAL CONTRACT** (see iii) | |
| `cycle_post.py:165-308` | `def _verify_remote_branch(number, role=...)`, `_do_status_transitions(data, role)`, etc. | `role` params → `alias` | |
| `squidsquad_cli.py:143-247` | `cmd_start(role)`, `cmd_stop(role)`, `cmd_restart(role)` | params + CLI positional | |
| `squidsquad_cli.py:284-290` | reads `a.get("role", "?")` from API response | **EXTERNAL CONTRACT** (reads from `to_dict()`) — see iii | |
| `reboot_agent.py:104-134` | `_read_claude_pid(clone_path, role)`, `write_claude_pid(clone_path, role, pid)` | params → `alias` | |
| `compose.py` CLI docs (line ~2124-2133) | `deploy <role>` usage string | rename to `deploy <alias>` | |

**Internal-code count: ~35 locations / ~120+ individual occurrences**

### Category (iii) — CODE — External Contract (HIGH risk; needs coexistence)

These are wire-format fields, HTTP path params, and env vars that agents/operators/scripts depend on. They must NOT be hard-cut; they require a dual-support window.

| Surface | Current form | Target form | Who depends on it | Risk |
|---|---|---|---|---|
| **FastAPI path param** | `/agents/{role}`, `/agents/{role}/start|stop|restart|health|config`, `/events/for/{role}`, `/events/cursor/{role}` | `/agents/{alias}` etc. | Agents calling `GET /agents/{alias}`, `cycle_post.py` reading intent, `squidsquad_cli.py`, `reboot_agent.py`, TUIs | HIGH — any caller using the old path breaks |
| **`AgentState.to_dict()` `"role"` key** | `{"role": <alias-value>, ...}` | `{"alias": <alias-value>, ...}` | `squidsquad_cli.py:290` reads `a.get("role")`, TUIs display role field, `GET /agents` response consumers | HIGH |
| **`cycle-input.json` `"role"` field** | `{"role": <alias>, ...}` | `{"alias": <alias>, ...}` | `cycle_post.py:57` `REQUIRED_FIELDS = {"role", ...}` — hard validation failure if field missing | HIGH |
| **`SQUIDSQUAD_ROLE` env var** | `SQUIDSQUAD_ROLE=skill` set by `thin_launcher.py:596`; read by `cycle.py:126`, `event_bus.py:209`, `activity_hook.py:87`, `compose.py:1833-1834`, `statusline.sh:19`, test fixtures | `SQUIDSQUAD_ALIAS` | Every agent process; Claude Code hook configs in `settings.json`; tests in `tests/test_activity_hook.py`, `tests/test_compose.py`, `tests/test_compose_9588.py` | HIGH — must keep old name as fallback or set both |
| **`event_bus.emit()` body field `"role"`** | `{"role": <alias>, ...}` in every emitted event | `{"alias": <alias>, ...}` | Harness `POST /events` handler reads `body.get("role")` at `harness.py:3047`; `_emit_event` reads `body.get("role")` at `harness.py:2700,2725`; ack-cursor handler reads `role`; agents calling `ack-cursor`/`ack-stop`/`booted` all send `"role"` field | HIGH |
| **`ack-cursor` payload `"role"` field** | `payload={"event_id": ..., "role": role}` in `event_bus.ack_cursor()` | `{"event_id": ..., "alias": alias}` | Harness reads this to advance cursor; must accept both | HIGH |
| **`X-Agent-Role` HTTP header** | `"X-Agent-Role": "${SQUIDSQUAD_ROLE}"` composed into `settings.json` hooks | `X-Agent-Alias` | Harness hook endpoints (`/hooks/session-end`, `/hooks/activity`, `/hooks/pause`) read `X-Agent-Role` header at `harness.py:2783-2798` | HIGH — hook settings.json is composed into every agent's clone |
| **`GET /events/cursor/{role}` response `"role"` field** | `{"cursor": ..., "role": "<role>"}` | `{"cursor": ..., "alias": "<alias>"}` | `event_poll.py` parses cursor response; `squidsquad_cli.py` | MEDIUM (less external than path) |
| **`POST /merge` request body `"role"` field** | `body.get("role", "unknown")` | `body.get("alias", ...)` | Agents/scripts calling `/merge` endpoint | MEDIUM |
| **`role:*` forge labels** | `role:skill`, `role:verifier`, `role:pm`, etc. | **Decision D1 from #10839: STAY AS `role:*`** — label key stays; only the value stays alias-typed (which it already is). No rename. | `tracker.py` throughout; EAD routing; all agents | N/A — explicitly out of scope per D1 |
| **`compose.py deploy <role>` CLI positional** | `python compose.py deploy skill` | `python compose.py deploy skill` (value unchanged — just positional arg name in code) | Installer Phase 6, deploy scripts | LOW (rename is just param name in source; value unchanged) |

**External-contract count: ~9 surfaces** (5 HIGH, 2 MEDIUM, 1 N/A, 1 LOW)

---

## §3 `/work/assign` Decision Input

### Current state (confirmed from code)

`POST /work/assign` is **NOT IMPLEMENTED** in `harness.py`. The route does not appear in the FastAPI route declarations (`@app.post`). The only reference to `/work/assign` logic in the code is the EAD's `_alias_for_role_class` + `target_alias` field emission — which IS implemented and fully functional.

The spec in HARNESS-ARCH.md §4.3 and AGENT-RUNTIME §8.3 describes `/work/assign` as the explicit routing endpoint, but the band-aid note at HARNESS-ARCH §4.3 states: "NOT IMPLEMENTED — tracked in #12495. Live work-routing mechanism is EAD emitting `assigned-to` events directly."

`tracker.py` does NOT call `/work/assign` — it writes forge labels via `gh issue edit` directly, and the EAD picks up the label change and emits `assigned-to` automatically.

### Recommendation: **Retire `/work/assign` as currently specced; formalize EAD-only routing**

**Rationale:**

1. **EAD already does the job.** Every workflow that would call `/work/assign` — status transitions triggering re-assignment — is handled by `tracker.py` writing the `role:*` label, which EAD detects and turns into an `assigned-to` event. The routing table in AGENT-RUNTIME §8.3 is effectively implemented by EAD today.

2. **The value of `/work/assign` was the harness-level `role:*` label rewrite.** Per HARNESS-ARCH §4.1 line 50, the harness is supposed to write `role:<target_alias>` on every `/work/assign` call. But the EAD path gets this for free: `tracker.py transition` calls `gh issue edit --add-label role:<alias>`, which IS the forge-truth update, and EAD reads it. No separate harness-side rewrite is needed.

3. **Implementing `/work/assign` now adds scope without unblocking anything.** No agent currently calls it. Adding it would require: validating `target_alias`, duplicating the forge label write (which `tracker.py` already does), and emitting `assigned-to` (which EAD already does). Pure duplicate machinery.

4. **The spec is fiction and actively confusing.** AGENT-RUNTIME §8.3 documents `tracker.py transition` as calling `POST /work/assign`, but the code shows `tracker.py` calls `gh` directly and EAD handles the event. Keeping the unimplemented spec creates doc-to-code drift. Retiring it removes the drift.

**Action:** Update HARNESS-ARCH §4.3 and AGENT-RUNTIME §8.3 to describe EAD-only routing as the canonical path. Mark `POST /work/assign` as "retired before implementation" with rationale. Close #12495 as won't-implement with this justification. This is a PM-owned doc change; no code change needed.

---

## §4 Phased Migration Plan

Follows the v1-coexistence pattern (memory item `project_v1_coexistence_pattern`): old names remain functional during the transition window; new names are added alongside; one atomic switch at the end flips defaults and removes old names.

### Phase 1 — Pure Doc Renames (PM-owned)

**What changes:**
- Docs: `docs/HARNESS-ARCH.md`, `docs/AGENT-RUNTIME.md`, `docs/INSTALLER-ARCH.md`, `docs/COMPOSE-ARCHITECTURE.md` — remove band-aid notes and update prose to use `alias` / `role-class` terminology correctly everywhere.
- Decision: retire `/work/assign` spec per §3 above; update §4.3 HARNESS-ARCH and §8.3 AGENT-RUNTIME.
- `CLAUDE.md` root: the `SQUIDSQUAD_ROLE=` auto-boot stanza stays unchanged (env var rename is Phase 2/3).

**Blast radius:** Docs only. No runtime impact. No agent coordination needed.

**Owner:** PM

**Risk:** Low. Only risk is introducing doc drift in a different direction — mitigated by DS review before merging.

**Deliverable:** PR updating the 4 TRD docs + #12495 closed as won't-implement.

---

### Phase 2 — Internal Code Renames (skill-owned)

**What changes (all internal, no wire-format impact):**
- `AgentState.role` attribute → `AgentState.alias` (slot + `__init__` param)
- All internal loop variables: `for role in ...` → `for alias in ...` in health poll, boot, stop loops
- `HarnessState.get_agent(role)` / `set_agent(role)` → `get_agent(alias)` / `set_agent(alias)`
- `_validate_role()` → `_validate_alias()`
- `EventLifecycle.get_cursor(role)` / `advance_cursor(role)` → `get_cursor(alias)` / `advance_cursor(alias)`
- `boot_remote._get_all_roles()` → `_get_all_aliases()`; `_get_clone_path(role)` → `_get_clone_path(alias)`; `boot_agent(role)` → `boot_agent(alias)`; `--role` CLI flag → `--alias`
- `reboot_agent._read_claude_pid(clone_path, role)` → `(clone_path, alias)`
- `event_bus.emit(event_type, role)` → `emit(event_type, alias)` — **note:** the event body `"role"` key is NOT changed here (that's Phase 3 external contract)
- `cycle.py` all `role` params → `alias`
- `cycle_pre.py` CLI arg variable `role` → `alias` (not the ROLE_BUILDERS dict key — that stays role-class-keyed)
- `cycle_post.py` internal function params
- `squidsquad_cli.py` function params
- `compose.py` CLI positional arg name in source
- All internal comments, docstrings

**Does NOT change yet:** `to_dict()` key, `cycle-input.json` field, HTTP path params, env vars, event body fields, hook headers.

**Blast radius:** Medium. Risk of missed references. Mitigated by DS review per change (`feedback_ds_review_per_change`) and running the full test suite after.

**Owner:** skill

**Risk:** Medium. Pure internal refactor; test suite covers most paths. Key mitigation: grep-audit for `"role"` string after rename to catch any missed string literals that should also be `"alias"`.

---

### Phase 3 — External Contract Dual-Support (skill-owned, high coordination)

Add `alias` alongside `role` everywhere on the wire; accept both; emit both for a transition window.

**What changes:**

**HTTP path params (dual routing):**
- Add new routes `/agents/{alias}/...` and `/events/for/{alias}` etc. alongside the existing `/{role}/` routes.
- Old `/{role}/` routes become **301 redirects** to `/{alias}/` routes (or just duplicate handlers, whichever FastAPI handles more cleanly with path deduplication).
- `_validate_role()` → `_validate_alias()` already done in Phase 2; the dual-path just means both path tokens route through the same validator.

**`AgentState.to_dict()` dual-emit:**
- Emit both `"role": self.alias` (backward compat) AND `"alias": self.alias` (new name) simultaneously.
- Consumers reading `"role"` continue to work; new consumers use `"alias"`.

**Event body field `"role"` dual-emit:**
- `event_bus.emit()` builds event with both `"role": alias` AND `"alias": alias`.
- Harness handlers accept either field (check `alias` first, fall back to `role`).

**`ack-cursor` payload:**
- `payload={"event_id": ..., "role": role, "alias": alias}` — send both.

**`cycle-input.json` / `cycle_post.py`:**
- `cycle_pre.py` writes both `"role": alias` and `"alias": alias` into `cycle-input.json`.
- `cycle_post.py` `REQUIRED_FIELDS` accepts either key (check `alias` first, fall back to `role`).

**`SQUIDSQUAD_ROLE` env var:**
- `thin_launcher.py` sets BOTH `SQUIDSQUAD_ROLE=<alias>` (backward compat) AND `SQUIDSQUAD_ALIAS=<alias>` (new).
- All consumers read `SQUIDSQUAD_ALIAS` first, fall back to `SQUIDSQUAD_ROLE`.
- `compose.py` settings.json template emits BOTH `X-Agent-Role` and `X-Agent-Alias` headers; `allowedEnvVars` includes both env vars.

**`X-Agent-Role` hook header:**
- Harness hook handlers check `X-Agent-Alias` first, fall back to `X-Agent-Role` (already has this pattern per `harness.py:2783-2798` uninterpolated-token check).

**Blast radius:** High. Touches every agent's settings.json (requires recompose of all agents). Requires coordinated deploy across all clones. Per `feedback_ds_review_per_change`, DS review mandatory before each sub-change.

**Owner:** skill (code); PM (coordinates compose redeployment)

**Risk:** High. This is the blast-radius phase. Key risks:
1. Missing a caller that only reads the old name — harness serves 404 when old path disappears in Phase 4.
2. Settings.json hook configs in deployed agents are stale (old env var only) until recompose runs — mitigated by running `compose.py deploy-all` + harness redeployment as part of the Phase 3 PR.
3. Test coverage gaps — all harness endpoint tests must be updated to call both old and new paths and verify both work.

---

### Phase 4 — Atomic Flip + Remove Old Names (skill-owned)

Single PR that:
- **Removes** old `/{role}/` route handlers (or removes redirects, whichever was used in Phase 3).
- **Changes** `to_dict()` to emit ONLY `"alias"` (removes `"role"` key).
- **Changes** event body to emit ONLY `"alias"` field.
- **Changes** `thin_launcher.py` to set ONLY `SQUIDSQUAD_ALIAS` (removes `SQUIDSQUAD_ROLE`).
- **Changes** `compose.py` settings template to emit ONLY `X-Agent-Alias` header + `allowedEnvVars`.
- **Removes** `SQUIDSQUAD_ROLE` reads throughout (cycle.py, event_bus.py, activity_hook.py, statusline.sh).
- **Updates** `CLAUDE.md` root auto-boot stanza from `SQUIDSQUAD_ROLE=<role>` to `SQUIDSQUAD_ALIAS=<alias>`.
- **Removes** CHANGELOG/docs band-aid notes (Phase 1 already retired the larger ones; this removes any residual).
- **Updates** test fixtures from `SQUIDSQUAD_ROLE` to `SQUIDSQUAD_ALIAS`.

**Blast radius:** High but bounded — this is the "remove training wheels" step after Phase 3 has been live long enough to confirm all consumers updated.

**Owner:** skill

**Risk:** Medium (lower than Phase 3 because Phase 3 validated the dual-support window worked). Residual risk: external operators or scripts not in this repo that still use `/{role}/` paths or `SQUIDSQUAD_ROLE`. Mitigate by deprecation-warning log line in Phase 3 on old-path hits (so logs show if anyone's still using them before Phase 4 drops them).

---

## §5 Effort / Risk Summary

| Phase | Effort | Risk | Owner | Gating |
|---|---|---|---|---|
| Phase 1 — Doc renames + /work/assign retire | ~2-3 dev cycles (PM) | Low | PM | None (can start now post-E6) |
| Phase 2 — Internal code renames | ~3-5 dev cycles (skill) | Medium | skill | Phase 1 done; PRD-D #10781 confirmed shipped |
| Phase 3 — External-contract dual-support | ~5-8 dev cycles (skill) | High | skill | Phase 2 done; DS review per-change |
| Phase 4 — Atomic flip + remove | ~2-3 dev cycles (skill) | Medium | skill | Phase 3 dual-window validated (log-based confirmation) |

**Total rough sizing**: 12-19 skill-dev cycles + 2-3 PM cycles.

### Top 3 Risks

1. **`SQUIDSQUAD_ROLE` env var** — This is the deepest coupling. It's set in `thin_launcher.py` (spawn-time), read in `cycle.py` / `event_bus.py` / `activity_hook.py` / `statusline.sh`, AND embedded in composed `settings.json` hook configs in every agent's clone. The settings.json embedding means a recompose + redeploy of every agent is required in Phase 3, and Phase 4 can't ship until all live clones have been recomposed on the Phase 3 version. Any agent running a stale settings.json after Phase 4 will have a broken hook header chain. **Mitigation**: Phase 3 must include `compose.py deploy-all` + harness redeploy as part of the PR; Phase 4 includes a pre-flight check that all clones have been recomposed.

2. **FastAPI path param rename blast radius** — There are 9+ route declarations all using `{role}` today. Each has client call sites in: `squidsquad_cli.py`, `cycle_post.py` (reads intent), `reboot_agent.py`, `event_poll.py`, TUIs, and potentially external operators. In Phase 3, 301 redirects prevent breakage; in Phase 4, the old paths die. Any operator curl commands or external tooling not in this repo breaks silently. **Mitigation**: add deprecation log warning in Phase 3 when old `{role}` paths are hit; monitor logs before Phase 4.

3. **`AgentState.to_dict()` JSON shape** — The `"role"` key is the most-consumed API response field. `squidsquad_cli.py` reads it, TUIs display it, `GET /agents` consumers use it. If Phase 4 removes `"role"` before all consumers are updated, silent breakage (callers get `None` from `a.get("role")`). **Mitigation**: Phase 3 dual-emit ensures both keys exist simultaneously; consumers that switch to `"alias"` during Phase 3 are safe; Phase 4 removes `"role"` only after confirming no consumer still reads only the old key.

---

## §6 Out-of-Scope (Explicit)

- **`role:*` forge labels** — D1 decision from #10839: labels stay as `role:*`. The value is alias-typed (already correct); renaming the label prefix would be massive tracker churn with no architectural gain. Not in scope.
- **`references/roles/<role-class>/` directory names** — These are role-class-keyed (correctly named). No rename needed.
- **`cycle_pre.py` `ROLE_BUILDERS` dict** — Keys are role-class names (`"pm"`, `"skill"`, `"verifier"`, `"dm"`). Already correctly named as role-class keyed. No rename.
- **`.squidsquad/project/<role-class>.md`** — Already correctly named. No rename.
- **`thin_launcher.py` collapse (#12416)** — Separate cleanup tracked separately; don't conflate with this rename.
