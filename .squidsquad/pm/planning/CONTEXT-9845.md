# CONTEXT-9845 — noop Event Type for Harness Stress Testing + Latency Probing

**Issue**: #9845
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21
**Status**: planning → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9845 + this CONTEXT-9845.md combined are the contract for skill at pickup.

> **NOTE**: Human +1'd the noop concept and the diagnostic-tool framing (cycle 1539). The noop-ack response-event model (D3 below) was locked by PM judgment in lieu of the broken `/events/{id}/complete` path (which returns HTTP 410 post-#9741/#9813). Human can override D3 if they prefer to unblock the larger ack-rework path instead — see §8.

---

## Scope

Add a `noop` event type to the harness event catalog (RECOGNIZED tier), define an agent contract that emits a `noop-ack` response event and does nothing else, create a new standalone diagnostic CLI `references/scripts/harness_ping.py`, patch `l1-base.md` Case E, run the compose pipeline for all four roles, and regenerate comprehension fixtures. This ships as a pre-flip readiness tool: before `event-driven: yes` is flipped, operators can confirm event delivery end-to-end. The `noop-ack` response model is the only viable RTT measurement path post-#9813 — no dependency on the dormant dispatch/complete path.

---

## 1. Locked Decisions

### D1. Option A wins — noop event type + noop-ack response + new harness_ping.py CLI + l1-base Case E patch

**Locked**: implement all four components together in a single PR. Option B (out-of-band endpoint, no agent path) does not test the actual delivery pipeline. Option C (working-state.md file-watching) has cross-platform file-watching issues and measures the wrong latency point (poll-receipt, not agent processing). Option A is the only path that exercises the full emit → harness-storage → event_poll → Monitor → agent → noop-ack → harness-storage → CLI-polls RTT.

### D2. noop + noop-ack both registered in event_catalog.py RECOGNIZED tier

**Locked**: add two entries to the RECOGNIZED tier in `references/scripts/event_catalog.py`:
- `noop` — `planned_source: "operator/CLI"`. Not agent-emitted.
- `noop-ack` — `planned_source: "agent/event-mode"`. Emitted by agents in response to a noop.

Note from RESEARCH-9845.md §2.1: the harness does NOT enforce catalog membership at the HTTP ingestion boundary (POST /events accepts unknown event types). RECOGNIZED registration is authoritative documentation and filter configuration — not a hard gate. The entries are required for catalog integrity and for operators running `event_catalog.py describe noop`.

### D3. Ack semantics — agent emits a noop-ack response event via event_bus.emit()

**Locked**: "agent acks a noop" means the agent calls `event_bus.emit()` with `event_type="noop-ack"` and payload `{"noop_id": <original event_id>, "ack_ts": <iso timestamp>}`. This is the ONLY viable ack mechanism post-#9813:

- `event_bus.ack()` was deleted in #9813 (no live producer).
- `POST /events/{event_id}/complete` returns HTTP 410 for all events since `dispatch()` is dormant (harness.py lines 628–644).
- The cursor advance in `event_poll.py` is the canonical "received" signal, but it is not observable from outside the agent process on Windows without platform-specific file-watching.

The noop-ack event is stored in the harness event stream. The CLI polls `GET /events?event_type=noop-ack` and correlates via `noop_id` in the payload.

### D4. Latency metric definition — noop received_at → noop-ack received_at

**Locked**: the canonical latency metric is `noop-ack.received_at − noop.received_at` (both float-precision epoch timestamps from the harness, in `.squidsquad/.event-state.json` / event stream). This measures full agent RTT from the harness's perspective: harness-ingests-noop → agent-processes → agent-emits-noop-ack → harness-ingests-noop-ack. This is the path where the 5s stalls observed in cycles 1535–1539 would manifest.

The CLI also records `emit_ts` (wall-clock at time of `event_bus.emit()` call) for the emit→harness-storage leg, but `received_at`-to-`received_at` is the primary latency column.

### D5. CLI location and surface — new standalone references/scripts/harness_ping.py

**Locked**: new file `references/scripts/harness_ping.py`. Do NOT add to `tracker.py` (GitHub Issues operations only) or `squidsquad_cli.py` (agent lifecycle only). The proposed `harness_admin.py` in the issue body does not exist; a new standalone file matches the pattern of `event_poll.py` / `event_bus.py`.

CLI surface:
```
python references/scripts/harness_ping.py [--role R] [--count N] [--interval S] [--timeout T]
```
- `--role R`: target a specific agent role. Default: broadcast to all 4 roles (emit one noop per role with `target_role` set in payload).
- `--count N`: number of noop probes per role. Default: 1.
- `--interval S`: seconds between successive probes. Default: 1.0.
- `--timeout T`: seconds to wait for noop-ack per probe before marking timeout. Default: 30.

Output: one row per emitted noop event:
```
emit_ts | event_id | role | ack_received | ack_latency_ms | status
```
`status` values: `ok` | `timeout` | `error`

### D6. noop delivery mechanism — target_role in payload (not reacts-to config change)

**Locked**: the CLI sets `target_role=<role>` in the noop event payload. Harness role filtering (`GET /events/for/{role}`) delivers events where `payload.target_role == role`. This requires no change to `config.md` `## Event Reactions` lists and no additional compose cycle for config. Ambient canary use-cases (harness-emitted periodic noops) that would benefit from `reacts-to` registration are explicitly deferred to a future task.

### D7. Agent contract — emit noop-ack + do nothing else

**Locked**: on receiving a `noop` event, an agent in event mode MUST:
1. Emit a `noop-ack` event via `event_bus.emit()` with payload `{"noop_id": <original event_id>, "ack_ts": <iso>}`.
2. Do NOTHING else — no `work_queue()` scan, no status transition, no tracker comment, no working-state edit, no git operation.
3. Cursor advance continues as normal (driven by `event_poll.py`, not by agent contract).

This is a behavioral contract change requiring an explicit Case E entry in `l1-base.md` (see D8). Without the explicit entry, agents treat `noop` as an unknown event type (RESEARCH-9845.md §2.6: current Case E logs a warning and does nothing — close but missing the explicit noop-ack emit and the explicit prohibition on `work_queue()`).

### D8. Compose pipeline + fixture regen — MANDATORY in same PR

**Locked**: after all source edits land, skill runs `compose.py deploy` for all four roles and regenerates `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` for all four roles. Both are committed in the same PR. Per `feedback_l1_l4_only`.

Note: `l1-base.md` is a RUNTIME_READ_FRAGMENTS fragment — agents read it at runtime, compose does not inline it. The compose run is still required to keep composed CLAUDE.md fixtures current and CI green.

### D9. CQ spec — REQUIRED for the l1-base.md Case E patch

**Locked**: per `feedback_comprehension_tests_required`, skill writes a comprehension-question spec alongside the l1-base.md edit. The spec must cover the new Case E noop behavior. Core questions:
- Given a noop event arrives, what does the agent do?
- Expected: emits noop-ack via event_bus.emit() with noop_id + ack_ts; does NOT run work_queue(); does NOT post a tracker comment; does NOT perform a status transition.
- The "do nothing else" boundary must be explicit — the CQ must name the prohibited actions, not just the required action.

### D10. Event-mode only — CLI warns on polling-mode roles

**Locked**: noop is meaningful only in event-mode. Polling-mode agents (`event-driven: no` in `config.md`) do not run `event_poll.py` actively, so noop events land in the harness stream but are never seen. The CLI MUST check `event-driven` (and any per-role override `event-driven-<role>`) in `config.md` before probing. If the target role is in polling mode, the CLI still emits the noop (harness accepts it), but prints a warning: `WARNING: role <R> is not event-driven — noop emitted but no noop-ack expected`. The CLI does NOT refuse to emit.

---

## 2. Grounded File References

| File | Relevance |
|------|-----------|
| `references/scripts/event_catalog.py` lines 91–143 | RECOGNIZED tier — add `noop` and `noop-ack` entries here |
| `references/scripts/event_bus.py` lines 85–125 | `emit()` function — agents call this to send noop-ack; CLI calls this to send noop |
| `harness.py` lines 1470–1565 | `POST /events` ingestion — stamps `received_at` (line 1509); stores via `event_lifecycle.append()` |
| `harness.py` lines 1660–1666 | `GET /events/for/{role}` filtering — `payload.target_role == role` path used for noop delivery (D6) |
| `references/sub-skills/common-events/l1-base.md` lines 80–84 | Case E — Special events — patch here to add explicit noop handling |
| `references/scripts/harness_ping.py` | **NEW FILE** — diagnostic CLI (D5) |
| `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` | Regenerated by compose in this PR (all 4 roles) |

---

## 3. Acceptance Criteria

**AC-1 (catalog — noop accepted by harness emit)**: Emitting a `noop` event via `event_bus.emit()` or `POST /events` succeeds (2xx response). The event appears in the harness event stream retrievable via `GET /events?event_type=noop`.

**AC-2 (catalog — noop-ack accepted by harness emit)**: Emitting a `noop-ack` event via `event_bus.emit()` succeeds. The event appears in the harness event stream with `payload.noop_id` and `payload.ack_ts` fields.

**AC-3 (agent contract — noop-ack emitted on receipt)**: An event-mode agent that receives a `noop` event emits a `noop-ack` event with `payload.noop_id` equal to the received noop's event_id and `payload.ack_ts` set to a valid ISO timestamp.

**AC-4 (agent contract — no side effects)**: After processing a `noop` event, the agent's tracked issue status is unchanged, no tracker comment is posted, no commit is made, and `working-state.md` is not modified by the noop processing path. The agent does not pick up queued work as a direct result of the noop.

**AC-5 (CLI — latency table on success)**: Running `python references/scripts/harness_ping.py --count 1` against a live event-mode agent produces a table row with `emit_ts`, `event_id`, `role`, `ack_received=true`, `ack_latency_ms` (a positive number), and `status=ok`.

**AC-6 (CLI — timeout handled cleanly)**: When `--timeout` expires with no noop-ack received, the CLI outputs a row with `ack_received=false`, `ack_latency_ms` blank or N/A, and `status=timeout`. Exit code is non-zero to allow scripted detection. No unhandled exception.

**AC-7 (CLI — polling-mode warning)**: When the target role has `event-driven: no` in `config.md`, the CLI emits the noop and prints a warning that no noop-ack is expected, then waits the full timeout and records `status=timeout` (expected). It does not refuse to emit or exit early with an error.

**AC-8 (comprehension — CQ spec for l1-base Case E)**: A comprehension-question spec is present in the PR covering the Case E noop patch. A fresh agent given only the modified `l1-base.md` can correctly answer: (a) what action to take on receiving a noop event, (b) what actions are explicitly prohibited (work_queue, tracker comment, status transition), and (c) what payload fields the noop-ack must include.

**AC-9 (compose + fixtures)**: `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` for all four roles are regenerated and committed in the same PR. CI comprehension-fixture tests pass.

---

## 4. Out of Scope

- **Reviving dispatch/complete**: `POST /events/{event_id}/complete` returns HTTP 410 (dispatch() dormant). Reactivating the dispatch/in-flight path is a separate Phase 4 concern, out of scope here. Do NOT block #9845 on this.
- **Per-agent ack throttling**: rate-limiting noop-ack emissions, de-duplication of rapid-fire probes.
- **CLI dashboard or UI**: real-time visual display of latency trends.
- **Persistent latency metrics storage**: writing latency history to disk, time-series DB, or log file.
- **Alerting**: threshold-based notifications when latency exceeds a target.
- **reacts-to config registration**: adding `noop` to roles' `reacts-to` lists in `config.md`. Deferred to an ambient canary task.
- **Harness-emitted ambient canary**: periodic noop from a harness health poller. Separate task.
- **Root cause analysis of the 5s stalls**: this task ships the diagnostic tool; root-cause work is a follow-on after data collection.
- **Polling-mode latency measurement**: noop targets event-mode agents only.

---

## 5. Sequencing

**Tier**: 1 — pre-flip readiness. This task ships BEFORE the fleet is flipped to `event-driven: yes`. It becomes part of the fleet-flip readiness checklist: on flip day, an operator runs `harness_ping.py` against the live fleet to confirm event delivery is working end-to-end before declaring the flip stable.

**Ordering relative to active pipeline**:

| Issue | Description | Relationship |
|-------|-------------|--------------|
| #9740 | Cursor re-anchor race in event_poll.py | Sibling Tier 1 — independent, ship in parallel |
| #9742 | Boot TOCTOU Monitor hang | Sibling Tier 1 — independent, ship in parallel |
| Fleet event-driven flip | `event-driven: yes` in config | Blocked on #9845 + siblings all merged |

**Concurrent work**: skill may pick up #9845 in parallel with #9740 and #9742. All three must merge before the flip. No ordering dependency between them.

**Pre-flip validation protocol**: after #9845 merges and before the flip, operator runs:
```
python references/scripts/harness_ping.py --count 3 --interval 2
```
All rows must show `status=ok` and `ack_latency_ms` well under 5000 ms. Any `timeout` or `error` row is a flip blocker.

---

## 6. Risk Notes for Skill at Pickup

1. **noop-ack must NOT cascade**: the harness emits noop-ack to the event stream. `cycle_pre.py`'s `mechanical_reactions` block and any agent event filter must ignore `noop-ack` — it should not trigger a new cycle, wake an agent, or appear in any role's `reacts-to` list. Skill must confirm `mechanical_reactions` in `cycle_pre.py` does not have a handler for `noop-ack`. If the agent's `reacts-to` filter in `config.md` is the only gate, and `noop-ack` is not in any `reacts-to` list, delivery is already blocked. Verify this at pickup.

2. **work_queue() incidental trigger risk**: RESEARCH-9845.md §2.9 identifies that a noop arriving at an idle agent (Case B) could incidentally trigger a `work_queue()` scan if the agent's event handling falls through to the idle-wake path. The Case E instruction MUST explicitly prohibit `work_queue()` on noop receipt — not merely instruct the noop-ack emit. Skill must write the Case E bullet to name the prohibited actions.

3. **noop_id correlation for burst probes**: when `--count N` > 1, multiple noops are in-flight simultaneously. The CLI must correlate `noop-ack.payload.noop_id` to the originating noop event_id — not rely on order of receipt. Skill must design the CLI with explicit (noop_event_id, role) → noop-ack correlation.

4. **event_bus.emit() is fire-and-forget with 500ms timeout**: per RESEARCH-9845.md §2.2, `event_bus.emit()` has no retry and fails silently. The CLI must record `emit_ts` before calling emit and handle silent failures (no exception raised on timeout). If the harness is down, the CLI will appear to emit successfully but no noop will arrive. Consider a post-emit confirmation check against `GET /events`.

5. **target_role delivery path**: noop delivery relies on `payload.target_role == role` filtering (harness.py lines 1660–1666). The CLI must set `target_role` in the noop payload explicitly. Without it, the noop will not be delivered to any role. Skill confirms the exact payload field name in the harness filter code before implementing.

6. **l1-base.md is runtime-read, not composed-inline**: changes to `l1-base.md` take effect on next agent boot even before CI runs. The compose run is still mandatory for fixture currency (D8), but the behavioral change is live immediately after merge + agent restart.

---

## 7. Open Questions Resolved

| Q | From RESEARCH | Resolution |
|---|---------------|------------|
| Q1 — Latency definition: which delta? | §5 Q1 | **LOCKED**: `noop.received_at` → `noop-ack.received_at` (full agent RTT from harness perspective). emit_ts also recorded for the emit→storage leg. |
| Q2 — Polling-mode agents: refuse probe or warn? | §5 Q2 | **LOCKED**: emit + warn (D10). CLI never refuses to emit. |
| Q3 — Delivery: target_role or reacts-to? | §5 Q3 | **LOCKED**: `target_role` in payload (D6). reacts-to registration deferred to ambient canary task. |
| Q4 — noop-ack emitter identity / burst correlation | §5 Q4 | **LOCKED**: CLI correlates via `payload.noop_id` field (D3). Emitter identity is the agent's own role. |
| Q5 — CLI usable before fleet flip? | §5 Q5 | **LOCKED**: CLI ships before flip as part of readiness checklist. If probed before any agent is in event mode, all rows will show `status=timeout` (expected — warnings per D10). |
| Q6 — CQ spec scope | §5 Q6 | **LOCKED**: spec covers three behavioral questions (what to do, what not to do, what payload to include). Both required action and prohibited actions must be in scope. |
| "Use existing POST /events/{id}/complete path?" | §2.3 | **NO** — returns HTTP 410 for all events post-#9741/#9813 since dispatch() is dormant. noop-ack response event via event_bus.emit() is the only viable path. Separate concern to revive dispatch/complete. |

---

## 8. Next Step

PM transitions #9845 `planning` → `planned`. Human reviews CONTEXT-9845.md. On approval, PM transitions `planned` → `approved` and skill picks up.

**Human override note**: the noop-ack response-event model (D3) was locked by PM judgment based on the post-#9813 state of the ack path. If the human prefers to instead unblock the larger dispatch/complete ack-rework (revive `EventLifecycleManager.dispatch()` and restore `POST /events/{id}/complete` as a live endpoint), D3 and D4 would need to be rewritten and the scope of this task expands significantly. PM recommends the response-event model as the minimal viable path — but human can redirect before approval.
