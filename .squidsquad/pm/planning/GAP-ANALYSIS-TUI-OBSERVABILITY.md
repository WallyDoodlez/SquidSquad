# TUI / Harness Observability — Gap Analysis & Implementation Plan

- **Date:** 2026-07-12
- **Reporter:** operator (2026-07-11, via interactive session acting as PM): "TUI doesn't show correct task information; agent status isn't accurate; no context pressure display."
- **Inputs:** `docs/HARNESS-ARCH.md` (v30), `docs/AGENT-RUNTIME.md`, `.squidsquad/pm/planning/TUI-INTERFACE-DESIGN.md` (approved contract, 2026-06-19), `references/tui/*`, `references/scripts/harness.py`, Claude Code observability docs (statusline / hooks / OTEL).
- **Status:** research artifact for the implementation task. Doc-first applies: Phase 0 (TRD reconciliation) precedes code.

---

## 1. Executive summary

All three operator symptoms are **wiring gaps, not missing subsystems**. The harness already computes accurate liveness (progress-liveness, #12492), already receives real task identity (`assigned-to` events), and already collects context pressure (statusline hook → `context-pressure` file, enforced at 70% by the health poller). None of it reaches `/status`, and the TUI mis-derives its own state client-side. The fix is: make the harness the single source of display truth, widen `/status`, and make the TUI a thin renderer.

| # | Symptom | Root cause | Severity |
|---|---|---|---|
| 1 | Task column wrong | TUI renders `current_cycle` — a loop-iteration counter — as "Task". Real identity (`assigned-to` event with `issue_number` + `title`, `harness.py:5888-5893`) is received and **discarded**: `_update_agent_from_event` (`harness.py:3154-3175`) has no `assigned-to` branch. | High |
| 2 | Status inaccurate | TUI's client-side `derive_work_state()` (`harness_client.py:33-52`) treats `current_cycle is not None` as "working"; `current_cycle` is set once and **never cleared** (`harness.py:3169`; no reset path, not even `reset_session_telemetry()` `harness.py:388-410`). Every agent reads "● working" permanently after its first cycle; "idle" is unreachable in steady state. The server's rich state machine (paused/crash-looping/deploying/zombie classification) is collapsed to 3 miscomputed buckets. | High |
| 3 | No context pressure | `context_pressure` exists per agent (`statusline.sh:65-73` → `.squidsquad/<role>/context-pressure`), is read every 5s by the harness (`_read_agent_pressure`, `harness.py:1484-1502`) and even triggers auto-restart at threshold (`_enforce_context_pressure`, `harness.py:1504-1595`) — but is exposed only on `GET /agents/{role}/health` (`harness.py:3124`), which the TUI never calls; `/status` (`AgentState.to_dict()`, `harness.py:619-656`) omits it entirely. | High |
| 4 | (found during analysis) Lag column fake | `TUI-INTERFACE-DESIGN.md:48` flags `lag` as a **to-be-added** backend field. It was never added: `/status` has no `lag` field; `harness_client.py:133` reads `a.get("lag", 0)` defensively, so the bar renders permanently empty. | Medium |
| 5 | (found during analysis) Mode + Health columns missing | Approved contract (`TUI-INTERFACE-DESIGN.md:30-31`) requires per-agent `mode (event/polling)` and `health` columns; `_AGENT_COLUMNS` (`app.py:34`) ships neither. | Medium |

---

## 2. Spec-vs-shipped inventory

The operative contract is `TUI-INTERFACE-DESIGN.md` (operator-approved 2026-06-19, contract for #12801). `HARNESS-ARCH.md:3` itself says operator display (#12410) is the open remainder of the liveness/observability work (#12271).

| Contract item | Spec cite | Shipped? |
|---|---|---|
| Agents panel: role, work-state, mode, current task, activity age, health, lag bar | TUI-INTERFACE-DESIGN.md:30-31 | Partial — role/state/task/age/lag columns exist (`app.py:34`) but task+state are wrong values, lag is always 0, mode+health absent |
| Work-state vocabulary working/idle/down w/ colors | :34-39 | Mis-derived (symptom 2) |
| `lag` field added to `/status` | :48 | **Never implemented** |
| Needs You panel (`/human/queue`) | :51 | Not shipped (client fetches the endpoint; no panel renders it) |
| Pipeline panel | :55 | Not shipped |
| Activity panel (`/events/lifecycle`) | :58 | Not shipped |
| Action bar r/R/f/q | :62 | Shipped (#12801/#13277) |
| Wake button | decomposition Story 4 | Not shipped |
| Context/token display | — | **Never specified** — contract gap, this task adds it |

Also relevant: `phase-change` is RECOGNIZED-tier with **no emitter** (`event_catalog.py:141-145`), so `current_phase` is always `None`; `agent-health` event is planned, never emitted.

---

## 3. Documentation contradictions to reconcile (Phase 0, doc-first)

1. **Context-pressure ownership:** `HARNESS-ARCH.md:628` (§15.1) — "context pressure never causes a restart. The harness only observes it" — directly contradicts `references/sub-skills/common/context-pressure.md:27` (#13335) and the shipped enforcer (`harness.py:1504-1595`) which flips `intent=restarting` at threshold. The TRD is stale; reconcile to the shipped behavior.
2. **"No context-% field exists in any hook payload"** (`HARNESS-ARCH.md:720`) — true for *hook* payloads but misleading: Claude Code's **statusline** JSON carries `context_window.used_percentage`, `context_window_size`, and a full `current_usage` token breakdown per turn (verified against current CC docs), and SquidSquad already consumes `used_percentage`. TRD §16 should document the statusline channel as a first-class telemetry source.
3. **Endpoint naming drift:** `AGENT-RUNTIME.md:1281` says TUI polls `/events/recent`; the real endpoint is `/events/lifecycle` (`HARNESS-ARCH.md:99`).
4. **`HARNESS-ARCH.md §4.1` response shapes are self-declared "aspirational"** and omit fields the TUI contract depends on (`current_cycle`, `in_flight_until`, and this task's new fields). Update to actual + new shape.
5. **`docs/ARCHITECTURE.md:79-81`** still describes `.claude-pid` as wrapper-PID (corrected in HARNESS-ARCH v25). Fix on contact.
6. **Status-enum drift:** HARNESS-ARCH §7.1.1 documents `booting/ready/stopping/stopped/crashed/crash-looping`; the code produces `unknown/starting/running/stopped/stalled/error/crash-looping/paused/deploying` (`harness.py:954-1063`). Reconcile the TRD to the shipped enum (or rename in code if the TRD's names are preferred — implementer's call, flagged in the plan).

---

## 4. Target design

Principle (house rule "health checks use facts, not context"): **the harness computes display truth server-side once; the TUI renders verbatim.** No client-side state derivation.

### 4.1 Task identity pipeline (fixes symptom 1)

- `AgentState` gains `current_task: {"issue": int|None, "title": str|None, "assigned_at": ts, "source": "ead"|"manual"}`.
- `_update_agent_from_event` gains an `assigned-to` branch (payload already carries `issue_number`, `title`, `target_alias` — `event_catalog.py:152-156`).
- **Clearing/refresh rules:** replaced by the next `assigned-to`; cleared when a `status-transition` event (already EMITTED by `tracker.py`) moves that same `issue_number` out of an in-progress-class status (`in-progress → pending-test|pending-ship|planning|approved|pending-human-*`). Persist `current_task` in `save_state()` so a harness restart doesn't blank the column.
- TUI Task cell: `#13454 pr_merge draft self-heal…` (truncated title), `—` when none. Keep the cycle counter out of this column (optionally show as a small `c41` suffix in the State cell).
- Note: `working-state.md` stays agent-private (per `AGENT-RUNTIME.md:617`) — the harness does not read agent clones for this; events are the bus.

### 4.2 Server-authoritative work-state (fixes symptom 2)

- New fields in `AgentState.to_dict()`: `work_state` (`working|idle|waiting|compacting|booting|down|crash-looping`) and `work_state_reason` (short human string).
- Derivation (server-side, in/next to `update_health()` which already owns every input):
  - `status` not alive-class → `down` (reason from status: stalled/error/stopped/deploying) or `crash-looping` (with `n/3 deaths, backoff Xs`).
  - `bootup_complete` false → `booting`.
  - **in-cycle tracking:** `cycle-start` sets `in_cycle=true`, `cycle-end` clears it (the pairing that `current_cycle` never had). `in_cycle` or live `in_flight_until` → `working`.
  - `waiting_since`/`compacting_since` active (same windows `active_pause()` uses, `harness.py:412-438`) → `waiting` / `compacting`.
  - otherwise → `idle` (reason: `no dispatch` / `idle since HH:MM`).
- Zombie kills (`candidate-zombie` path, `harness.py:882-899`) set `work_state_reason="zombie killed, respawning"` so the operator can distinguish it from a plain crash (gap §5.6 of spec sweep).
- TUI keeps the approved 3-color scheme (green working / yellow idle-waiting-compacting-booting / red down) but prints the fine-grained word + reason: `● working #13454`, `◌ waiting (perm prompt 3m)`, `✖ crash-loop (2/3, retry 240s)`.
- `derive_work_state()` in `harness_client.py` shrinks to "read the field" (kept only as fallback for old harnesses, versioned via `/status.harness.code_version`).

### 4.3 Context-pressure surfacing (fixes symptom 3)

- **v1 (this task):** include the already-read pressure in `/status`: `context_pressure: {"pct": float|None, "threshold": int, "age_seconds": float}` (threshold from `_read_context_threshold()`, default 70). TUI column `Ctx`: bar + percentage, yellow ≥50%, red ≥ threshold (i.e. "restart imminent"), `—` when unknown; stale readings (age > 10 min) rendered dim with `?`.
- **v1.5 (same task, small):** extend `statusline.sh` to also async-POST the full `context_window` JSON (`used_percentage`, `context_window_size`, `current_usage` token breakdown) + `session_id` to a new `POST /hooks/context` — replaces file-scrape as primary, file remains fallback. Split the `PreCompact`/`PostCompact` hook matchers into `auto` vs `manual` so auto-compaction (context exhaustion) is a distinct, counted event; surface `compactions_this_session` in `/status` and dim-flag agents that auto-compacted (context churn indicator).
- **Later (out of scope, note in TRD):** OTEL layer (`claude_code.token.usage`, `claude_code.compaction` pre/post token counts) for cross-session dashboards.

### 4.4 Honest Lag + contract completion

- Implement the spec'd `lag` field server-side (cursor position vs deque head — the EventLifecycleManager owns both) and remove the defensive default. If deferred, **delete the Lag column** rather than render fake data — a dashboard must not display invented values.
- Add the contract's `mode` column (event/polling — harness knows from bootup event / config).

### 4.5 Sketch (target Agents panel)

```
Role   State                        Task                          Ctx        Age   Lag
pm     ● working                    #13554 guard-fix plan         ▃ 42%      12s   ▁
skill  ● working                    #13454 pr_merge self-heal     ▅ 61%      3s    ▁
qa     ◌ waiting (perm prompt 3m)   #13538 verify launcher        ▂ 18%      3m    ▁
dm     ○ idle (no dispatch 1h)      —                             ▂ 11%      1h    ▁
web    ✖ crash-loop (2/3, 240s)     #13390 dashboard              —          22m   ▃▃
```

---

## 5. Implementation plan (for the dev pickup — sized for an Opus worker)

**Phase 0 — TRD reconciliation (doc-first, blocks code):**
Update `docs/HARNESS-ARCH.md` (§4.1 actual response shapes incl. new fields; §7.1.1 status enum ↔ code reconciliation; §15.1 context-pressure ownership corrected to shipped enforcer behavior; §16 statusline channel documented) + `docs/AGENT-RUNTIME.md:1281` endpoint name + `docs/ARCHITECTURE.md` `.claude-pid` fix + a v2 amendment section in `TUI-INTERFACE-DESIGN.md` (Ctx column, reason strings, server-side work_state). Human review gate before Phase 1.

**Phase 1 — Harness truth (`harness.py` + tests):**
1. `assigned-to` ingestion → `current_task` (+ clearing via `status-transition`, + persistence in `save_state()`/load).
2. `in_cycle` pairing from `cycle-start`/`cycle-end`.
3. `work_state`/`work_state_reason` computation (single function, exhaustive unit-test matrix over status × intent × in_cycle × pause-windows × dispatch/activity ordering).
4. `/status` additions: `current_task`, `work_state`, `work_state_reason`, `context_pressure{pct,threshold,age_seconds}`, `lag`, `mode`.
5. **Regression test that fails pre-fix** (house rule): agent with `current_cycle=41`, `cycle-end` received, idle 30 min → `work_state == "idle"` (old code path yields "working").

**Phase 2 — TUI rendering (`references/tui/*` + render tests):**
Columns `Role | State | Task | Ctx | Age | Lag | Mode`; render server fields verbatim; color rules as §4.2/4.3; extend `test_tui_render_12801.py` patterns; harness-version fallback for old `/status` shapes.

**Phase 3 — Context channel v1.5:**
`POST /hooks/context` endpoint + `statusline.sh` async POST (keep file write as fallback); `PreCompact`/`PostCompact` matcher split (`.claude/settings.json` + composed hook templates); `compactions_this_session` counter. CQ specs required for any changed agent-facing instruction fragments (`context-pressure.md`, statusline docs).

**Out of scope (explicit):** Needs-You/Pipeline/Activity panels + Wake button (remaining #12801 stories — file follow-up), web dashboard (#3963), SSE/websocket push, OTEL exporter, `/queue/{alias}` generalization (#13173).

**Verification notes for QA:** live-system checks per AC below; state-matrix unit tests; TUI render tests headless (`App.run_test()`); do not mutate shared live state in tests (vault learning: tests-must-not-mutate-shared-live-state); prove regression test red on pre-fix code.

---

## 6. Acceptance criteria (mirrored in the tracker issue)

- AC1: `/status` per-agent payload carries `current_task{issue,title}`, `work_state`, `work_state_reason`, `context_pressure{pct,threshold,age_seconds}`, `lag`, `mode` — documented in HARNESS-ARCH §4.1 (updated first, human-reviewed).
- AC2: TUI Task column shows the assigned issue (`#N <title>`) sourced from `assigned-to` ingestion; never the cycle counter; `—` when unassigned; survives harness restart (persisted).
- AC3: TUI State column reflects server-computed `work_state`; an agent that completed its last cycle and received no new dispatch shows `idle` within one poll interval (regression-tested; old behavior showed `working` forever).
- AC4: Context pressure visible per agent with threshold-aware coloring; unknown/stale readings render as `—`/dim, never as fake values.
- AC5: Lag column shows a real server-computed value or is removed — no defaulted-to-0 rendering.
- AC6: `PreCompact`/`PostCompact` hooks distinguish `auto` vs `manual`; auto-compaction count surfaced in `/status`.
- AC7: TRD contradictions in §3 (items 1-4 minimum) reconciled in the same PR-chain, doc change reviewed before implementation lands.
- AC8: Unit + render test coverage for the state matrix and all new columns; regression test proving the never-cleared-`current_cycle` bug is fixed; CQ specs accompany any changed agent-instruction fragments.
