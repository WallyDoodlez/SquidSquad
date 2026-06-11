# Composed CLAUDE.md ↔ Harness Integration Audit

Audited: 2026-06-11  
Branch: squidsquad/task/11334  
Auditor: Claude Sonnet 4.6 (agent-as-auditor mode)

---

## A. Boot sequence

**Verdict**: PARTIAL

### What CLAUDE.md says (all 4 roles)

Step:cycle/boot block (`.squidsquad/skill/CLAUDE.md:453–526`, identical in pm/qa/dm):

1. Run `python references/scripts/tracker.py check-gh`; exit on failure.
2. Read `.squidsquad/.harness-port`; default `7373` if absent/unreadable/non-integer.
3. `curl -sf --max-time 5 http://127.0.0.1:<port>/status` — exit 0 = EVENT mode, non-zero = POLLING fallback.
4. EVENT mode: Read 6 sub-skills in order: `event-driven-workflow`, `event-mode-contract`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`.
5. POLLING mode: invoke `/loop 30m execute one Ralph Loop cycle` exactly once; Read `references/sub-skills/roles/<role>/ralph-loop-overview.md`.

### What harness.py actually does

- **`/status` endpoint**: EXISTS at `harness.py:1601` — `@app.get("/status")`. Returns `{"harness": {"status": "running", ...}, "agents": [...]}`. Responds 200 OK on a live harness. **ALIGNED.**
- **`.harness-port` write**: `harness.py:1372–1378` — `HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"` (`harness.py:67`). Written atomically (tmp+replace) **early in lifespan before `yield`** so the server can accept probes as soon as the port file lands. **ALIGNED.**
- **Port-discovery convention**: The agent reads `SQUID_DIR / ".harness-port"` where `SQUID_DIR = REPO_ROOT / ".squidsquad"`. `harness.py` writes `SQUIDSQUAD_DIR / ".harness-port"` where `SQUIDSQUAD_DIR = _resolve_squidsquad_dir()` which defaults to `REPO_ROOT / ".squidsquad"` (harness.py:62). **ALIGNED.**  
  Also: `cycle_pre._discover_harness_port` (cycle_pre.py:277–306) and `cycle_post._discover_harness_port` (cycle_post.py:774–808) both do an identical 5-level parent-dir walk after the primary path — so even clones resolve the correct port. **ALIGNED.**
- **6 EVENT-mode sub-skill files**: All 6 exist at `references/sub-skills/common-events/`:
  - `event-driven-workflow.md` ✓
  - `event-mode-contract.md` ✓
  - `cursor-management.md` ✓
  - `forge-read-pattern.md` ✓
  - `idle-cooldown-loop.md` ✓
  - `comment-handling.md` ✓
  **ALIGNED.**
- **Polling fragment paths** — all 4 role fragments exist:
  - `references/sub-skills/roles/pm/ralph-loop-overview.md` ✓
  - `references/sub-skills/roles/verifier/ralph-loop-overview.md` ✓
  - `references/sub-skills/roles/worker/ralph-loop-overview.md` ✓ (Skill agent uses this path)
  - `references/sub-skills/roles/dm/ralph-loop-overview.md` ✓
  **ALIGNED.**

### Issues

None blocking. The boot path is well-aligned. Minor: `cycle_pre._discover_harness_port` (cycle_pre.py:286) vs `event_poll._discover_port` (event_poll.py:70) — `event_poll` does NOT do the 5-level parent walk, only reads `SQUID_DIR / ".harness-port"`. Harmless for primary clones but could silently use default 7373 if the port file is missing in a deep-nested clone scenario. Not a runtime bug for the canonical install layout.

---

## B. Per-nudge cycle

**Verdict**: PARTIAL — one field-name mismatch in the care filter (not blocking for primary `assigned-to` events but produces silent miss for l4-watcher events)

### What CLAUDE.md says

`.squidsquad/skill/CLAUDE.md:370–372` (identical in pm/qa/dm):

> The canonical eager loop: GET next event past cursor → **care filter** (`does this event's \`target_alias\` field equal my own alias?`) → cycle wrapper if cared → POST `ack-cursor` per event → re-check.

`cursor-management.md:44` (runtime-loaded sub-skill):

> POST `ack-cursor` with `event_id` inside `payload.event_id`.

`event-mode-contract.md:41–52` (runtime-loaded sub-skill):

> Monitor invocation: `python references/scripts/event_poll.py <role> --wait 5 --target`. Each line of stdout wakes you. **Monitor exit → exit session immediately.**

### What harness.py/event_poll.py actually does

- **`event_poll.py` stdout**: Writes `json.dumps(event)` — one JSON object per line (`event_poll.py:301`). The CLAUDE.md calls each line a "NUDGE line". The prose says "Each `NUDGE\n` line" (CLAUDE.md:385) but `event_poll.py` actually emits a full JSON event object per line, not a bare string `NUDGE`. This is a **terminology mismatch** in the CLAUDE.md prose but the loaded sub-skill (`event-mode-contract.md:50`) corrects it: "Each line wakes you to process exactly one event." The agent would correctly interpret the JSON line. **EFFECTIVELY ALIGNED** — the L1 prose misleads but the runtime sub-skill corrects it.
- **GET next event endpoint**: `harness.py:2141` — `GET /events/for/{role}` with `since=` and `--target` flag in `event_poll.py`. Exists and functions as described. **ALIGNED.**
- **POST `ack-cursor`**: `harness.py:2018–2044` — `receive_event` handles `event_type == "ack-cursor"`, reads `body.get("payload").get("event_id")`. `cursor-management.md:44` specifies exactly this shape. **ALIGNED.**
- **Care filter field name — MISMATCH**:
  - CLAUDE.md (`.squidsquad/skill/CLAUDE.md:372`) says: `target_alias field equal my own alias`
  - Harness `GET /events/for/{role}` filter (`harness.py:2181`): `e.get("payload", {}).get("target_role", "")`
  - Harness `ExternalActivityDetector._check_for_changes` emits (`harness.py:3106`): `"target_role": target_role`
  - `l4_file_watcher.py` emits (`l4_file_watcher.py:189`): `"target_alias": r.alias`
  
  **GAP**: Two different field names are in play. The `ExternalActivityDetector` (the issue-watcher that emits `assigned-to` for new/updated tracker issues) uses `payload.target_role`. The `l4_file_watcher` (CLAUDE.md recompose events) uses `payload.target_alias`. The harness `/events/for/{role}` filter reads only `payload.target_role` — so **l4_file_watcher-sourced events with `target_alias` will NOT be pre-filtered by the harness** into the agent's targeted stream. They pass through only if they match the role's `relevant_types` (event_type filter). The agent's own care filter logic (as stated in CLAUDE.md) uses `target_alias`, but for the primary `assigned-to` events the harness emits, the field is `target_role`. In practice the `--target` mode's pre-filter at the harness already handles routing, so the agent-side care filter fires rarely; but the field name inconsistency means the care filter description in CLAUDE.md is wrong for all non-l4-watcher events, and the l4-watcher events are silently dropped by the harness pre-filter.

---

## C. Cycle pre/post wrappers

**Verdict**: ALIGNED

### What CLAUDE.md says

`.squidsquad/skill/CLAUDE.md:554` (Step 5) and `.squidsquad/skill/CLAUDE.md:558` (Step 6):

> The mechanical commit and push are part of the **post-cycle** wrapper (`cycle_post.py` — you don't execute it).

`self-restart.md:16`:

> `cycle_post.py` checks the `context_pressure` field of your `cycle-output.json` (falling back to `cycle-input.json` if you did not pass it through). If exceeded, POSTs `/agents/[ROLE]/restart`, then exits with code 42.

`cycle-runner.md:13–24`:

> Phase 1: `python references/scripts/cycle_pre.py [ROLE]` → writes `.squidsquad/[ROLE]/cycle-input.json`

`cycle-runner.md:50–74`:

> Phase 3: agent writes `.squidsquad/[ROLE]/cycle-output.json`; runs `python references/scripts/cycle_post.py [ROLE]`.

### What the scripts actually do

- **`cycle_pre.py` exists** and does: git pull (`_do_pull`), working-state read (`_read_working_state`), branch enforcement (`_enforce_branch`), harness query (`_query_harness_status`), writes `cycle-input.json`. (`cycle_pre.py:161–424`). **ALIGNED.**
- **`cycle_post.py` exists** and does: reads `cycle-output.json`, validates it, does commit/push, status transitions, tracker comments, working-state update, iteration log, version bump (DM), orphan cleanup, emits `cycle-end` event, then does intent+context-pressure check at the end (`cycle_post.py:935–1043`). **ALIGNED.**
- **`cycle-input.json`** is consumed by the agent per `cycle-runner.md`. The `cycle_pre.py:main()` (not yet read in full) writes it to `SQUID_DIR / role / "cycle-input.json"`. The `cycle_post.py:_do_stop_after_cycle_check` reads `cycle-input.json` as a fallback if `context_pressure` absent from `cycle-output.json` (`cycle_post.py:890–897`). **ALIGNED.**
- **`cycle-output.json` is written by the agent** per `cycle-runner.md:50`. No harness script writes it — it's the agent's output file. `cycle_post.py:943–964` reads and validates it. **ALIGNED.**
- **`cycle_post.py exit 42`**: `cycle_post.py:1036–1038` — `if stop_for_restart: return 42`. `stop_for_restart` is set by `_do_stop_after_cycle_check` when intent is `stopping`/`restarting` OR context-pressure exceeded. **ALIGNED.**
- **Status transitions in `cycle_post.py`**: done by `_do_status_transitions` at line 227. Tracker comments by `_do_tracker_comments` at line 265. Iteration logging by `_do_iteration_log` at line 287. **ALIGNED.**

### Issues

None blocking. The event-mode sub-skills (specifically `event-mode-contract.md:100`) say "The harness owns git — pull, commit, and push are managed at boot and shutdown by the harness." This is slightly misleading for loop-mode agents where `cycle_pre.py`/`cycle_post.py` own git, but the sub-skills are loaded only in event mode, so it's internally consistent.

---

## D. Self-restart / exit codes

**Verdict**: ALIGNED

### What CLAUDE.md says

`.squidsquad/skill/CLAUDE.md:564`:

> If `cycle_post.py` exits with code 42 → invoke `/quit` → harness respawns.

`.squidsquad/skill/CLAUDE.md:389`:

> If Monitor exits for any reason → end session immediately, no retry.

`self-restart.md:22–26`:

> After `cycle_post.py` exits with code 42, immediately invoke `/quit`. The harness observes process exit and either marks stopped or respawns per intent.

### What harness.py actually does

- **exit-42 → respawn**: `harness.py:400–430` — `update_health()`. When `is_dead and was_alive and should_reboot`, if `intent == INTENT_RESTARTING`, the agent is added to `reboot_roles` and `boot_remote.boot_agent(role)` is called. `cycle_post._post_harness_restart` POSTs `/agents/{role}/restart` before the exit, flipping intent to `RESTARTING` (`cycle_post.py:832–863`, `harness.py:2471–2546`). **ALIGNED.**
- **STOPPING intent → no respawn**: `harness.py:390–436` — when `is_dead and intent == INTENT_STOPPING`, intent transitions to `INTENT_STOPPED`, no reboot. **ALIGNED.**
- **Other exit codes**: The harness health poller only detects process death (PID check) — it does not distinguish exit codes. Any non-zero exit from the claude process that causes process death will trigger the same `is_dead` branch. So exit codes other than 42 are treated the same as 42 by the harness (if intent is RUNNING). The prose doesn't need to enumerate other codes because the harness doesn't dispatch on them. **No gap.**
- **`/quit` via claude session**: The `/quit` slash command terminates the claude session, which causes the claude PID to exit, which is what the harness health poller detects. `harness.py` does not expose a `/quit` HTTP endpoint; the prose instructs the agent to invoke the `/quit` SLASH COMMAND (Claude's built-in), not an HTTP call. **ALIGNED.**
- **Monitor exits → session ends**: The `event_poll.py --wait` mode exits (sys.exit(2)) after `_WAIT_MAX_CONSECUTIVE_FAILURES = 10` consecutive transient errors (`event_poll.py:63–66`, `event_poll.py:384–396`). Monitor tool exit signals the agent to end session. **ALIGNED.**

---

## E. Role-specific scripts

### PM: `boot_remote.py --role <name>`

**Verdict**: ALIGNED

`pm/CLAUDE.md` `boot-remote-agents.md` sub-skill instructs PM to call `boot_remote.py --role <name>` to spawn agents. `references/scripts/boot_remote.py` exists with `--role` argument (`boot_remote.py:1`). The harness calls `boot_remote.boot_agent(role)` internally for auto-reboot (`harness.py:459`). The CLI `--role` flag exists. **ALIGNED.**

### QA: `gh pr review --approve` + `git_ops.py pr-merge`

**Verdict**: ALIGNED

`qa/CLAUDE.md:599`:

> Auto-merge enabled. When verification passes: `gh pr review --approve` + `python references/scripts/git_ops.py pr-merge`.

`references/scripts/git_ops.py` exists (confirmed in Glob). `gh pr review --approve` is a standard GitHub CLI command. The CLAUDE.md instructs the agent to call these directly, not via cycle_post.py, which is consistent with verification being a creative work step (Step 7.1). **ALIGNED.**

### DM: `tracker.py transition <issue> pending-ship shipped` + `delivery:skip` detection

**Verdict**: ALIGNED

**`tracker.py transition ... pending-ship shipped`**: `tracker.py:28` documents `DM (--role dm or dm-lead): pending-ship → shipped`. The transition authority matrix at `tracker.py:196` maps `("status:pending-ship", "status:shipped"): {"dm"}`. **ALIGNED.**

**`delivery:skip` detection**: `dm/CLAUDE.md:458` says "Check the issue's Discussion comments for a `delivery: skip` marker (the canonical signal — `cycle_pre.py` reads the marker from comment bodies, not from labels)."

`cycle_pre.py:1129–1134` — in `_build_dm_input()`, iterates `tagged.get("comments")`, checks `if "delivery: skip" in body or "delivery:skip" in body`, sets `delivery_skip = True`. The prose correctly identifies `cycle_pre.py` as the reader. The line number reference in the audit prompt says `cycle_pre.py:1131` — actual logic is at lines 1129–1134. **ALIGNED** (line reference in audit prompt was approximate but the logic is there).

### Skill: `model_router.py code-review` for DS-review

**Verdict**: ALIGNED

`skill/CLAUDE.md:707`:

> For high-blast-radius skill changes: spawn a DeepSeek review subagent via `python references/scripts/model_router.py code-review`. On exit code 1/2/3, fall back to Sonnet subagent.

`model_router.py:144` — `"code-review": "code-review-model"` in the routing table.  
`model_router.py:543` — `"code-review": "code-review.md.j2"` in the template map.  
`model_router.py:1026` — `"code-review"` listed as a subcommand alias.  
Exit codes 1/2/3 are described at `model_router.py:17–21` (0=success, 1=API failure/claude-only task, 2=config error). **ALIGNED.**

---

## Summary

- **Items audited**: 20 (5 boot sub-items, 4 per-nudge sub-items, 5 pre/post sub-items, 3 exit/restart sub-items, 4 role-specific scripts)
- **Aligned**: 18
- **Partial / Gap**: 2

### Top issues

**1. Care filter field name mismatch (PARTIAL — not blocking for primary flow)**

- CLAUDE.md prose (`skill/CLAUDE.md:372`, identical in all 4 roles): agent care filter checks `event.target_alias`
- Harness `ExternalActivityDetector` emits: `payload.target_role` (`harness.py:3106`)
- Harness `/events/for/{role}` endpoint filters on: `payload.target_role` (`harness.py:2181`)
- `l4_file_watcher.py` emits: `payload.target_alias` (`l4_file_watcher.py:189`)

Runtime consequence: In `--target` mode the harness pre-filters events before the agent sees them, so the agent-side care filter is mostly defensive. But `l4_file_watcher`-sourced `assigned-to` events use `target_alias`, not `target_role` — the harness endpoint at `harness.py:2181` will NOT match them on `target_role == role` (the field is absent). They can only reach the agent via the `relevant_types` fallback filter (if `assigned-to` is in the role's reaction types). The agent-side care filter description in the CLAUDE.md is also wrong for the mainstream `ExternalActivityDetector` events (which use `target_role`, not `target_alias`). Agents following the CLAUDE.md care filter logic with `target_alias` will silently skip mainstream events if they ever execute the agent-side filter instead of relying on the harness pre-filter.

**2. `event_poll.py` stdout described as `NUDGE\n` lines in L1 prose (MISLEADING — corrected by runtime sub-skills)**

- CLAUDE.md (`.squidsquad/skill/CLAUDE.md:385`): "Each `NUDGE\n` line that arrives wakes you"
- `event_poll.py:301`: prints `json.dumps(event)` — a full JSON object per line, never the bare string `NUDGE`
- The runtime sub-skill `event-mode-contract.md:50` correctly says "Each line wakes you to process exactly one event" (without the NUDGE framing)

Runtime consequence: Low risk — the agent loads `event-mode-contract.md` before arming Monitor, which overrides the NUDGE framing. But an agent reading only the L1 CLAUDE.md and not loading the sub-skill would misidentify the Monitor output format. The correction path depends on sub-skill loading being reliable.

### Non-blocking observations

- `cycle_pre._discover_harness_port` does a 5-level parent-dir walk but `event_poll._discover_port` does not — minor portability difference for deep-nested clones.
- `event-mode-contract.md:100` says "the harness owns git" — factually incorrect for loop mode, but that sub-skill is only loaded in event mode so it is internally consistent.
- `cycle-runner.md` (loop mode sub-skill) is a legacy path that describes the agent writing `cycle-output.json` and calling `cycle_post.py` manually — this is the loop-mode contract, not event-mode. In event mode `cycle_post.py` is called by the harness/thin_launcher, not directly by the agent. The role of the two paths is documented but not always clearly separated in the composed CLAUDE.md.
