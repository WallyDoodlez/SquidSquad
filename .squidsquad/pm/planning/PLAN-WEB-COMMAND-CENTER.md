# Web Command Center — Plan

- **Date:** 2026-07-12
- **Operator vision (2026-07-12):** agents continuously send status to the harness; a web interface displays it and becomes the final command center — control the harness/agents, chat with agents, an agent↔agent chat room humans can watch, edit L4s (and L1–L3 for SquidSquad's own development), and control model routing.
- **Inputs:** full harness API/event-bus/comms/compose/model-routing groundwork audit (verified against `harness.py` @6155 lines, `comms_adapter.py`, `l4_file_watcher.py`, `thin_launcher.py`, `model_router.py`, `config.py`, docs + epic #3963 history).
- **Relationship to existing work:** supersedes the phasing of epic **#3963** (web dashboard, deferred to "Phase 7") with a concrete architecture; builds directly on **#13561** (server-authoritative `/status` fields) and `PLAN-STATUSLINE-V2.md` S1 (operator-language status strings — the web shows the same `operator_msg`/`detail` pair). The old `harness-architecture.md` PTY/xterm/chat-room diagram is the ancestor vision; this plan implements it incrementally rather than all-at-once.

---

## 1. What already exists vs what's missing

| Capability | Today |
|---|---|
| Agent/harness control | ✅ **Complete over HTTP**: `POST /agents/{role}/{start,stop,restart}`, `/agents/all/*`, `/shutdown`, `/restart`, `/merge` — a web UI can drive the entire lifecycle with `fetch()` now |
| Fleet status | ✅ `/status` snapshot (being enriched by #13561: `current_task`, `work_state`, `context_pressure`, …) |
| Live push | ❌ None — REST poll only; no SSE/WebSocket anywhere; event deque is tailable only by polling `GET /events?since=<cursor>` |
| Web serving | ❌ Harness serves JSON only — no static files, no CORS, no auth (hardcoded `127.0.0.1`, documented gap §13.2) |
| Human→agent chat | ❌ Wake channel is deliberately payload-free (`NUDGE` → Monitor); inline mode requires the physical terminal; no PTY, no stdin path on Windows/macOS |
| Agent↔agent chat | 🟡 Designed, unbuilt: `chat-etiquette` / `mention-protocol` / `consensus-protocol` sub-skills fully specified but not composed; `CommsAdapter` ABC has only a `NullAdapter`; prior decision (epic #3415) was **Telegram-first** — needs superseding |
| L4 editing | 🟡 Consumption side done: harness file-watcher on `.squidsquad/project/` auto-recomposes + emits `restart-required` within 0.5s of any write. Missing: an HTTP write surface + server-side safety gates (today's DS-audit/mini-CQ/dry-run gates live only in agent conversation) |
| L1–L3 editing | ❌ Normal git/PR path only (correct — these are shipped product content); no live-edit path and there shouldn't be one |
| Model routing | 🟡 Subagent routing (`config.md ## Model Routing`) is hot-reloadable but CLI-only. Primary agent model: **not configurable at all** (launcher passes `--effort` only, no `--model`) |

**Architecture principle:** serve the web UI **from the harness itself** (same origin — kills the CORS problem, keeps the localhost-only security model), a single self-contained static SPA (no build step, vendored assets — same zero-dep philosophy as the vault viewer), and **SSE over WebSocket** for push (one-way push + plain POST actions = simpler, auto-reconnecting, proxy-friendly; chat sends are POSTs, not socket writes).

---

## 2. Continuous status: what "agents keep sending" means concretely

Most of the pipe already exists or is in flight — the web plan adds only two pieces:

1. **Already flowing:** activity heartbeats (`/hooks/activity` per tool call), pause/compaction/session hooks, `assigned-to` + `status-transition` + `cycle-*` events, context pressure (statusline → file today; `POST /hooks/context` in #13561 P3).
2. **New — make `phase-change` real:** the event is RECOGNIZED in the catalog with **no emitter**, so `current_phase` is always `None`. Fix: `cycle_pre.py`/`status_bar()` emit `phase-change {phase, operator_msg, detail}` on every transition (piggybacks Statusline-v2 S1's structured contract). The web's per-agent timeline is then live phase history, not just tool heartbeats.
3. **New — `GET /stream` (SSE):** single multiplexed channel pushing `{type: event|status-delta|chat}` frames. Implementation: asyncio condition variable signaled on deque append + a 5s status-delta coalescer (aligns with the health-poll tick). Poll fallback stays for old clients (the TUI keeps polling — no forced migration).

---

## 3. Phases

### W0 — Foundations (small)
- `StaticFiles` mount at `/ui` (SPA shell); `GET /` gains `"ui": "/ui"` pointer (keep JSON contract).
- `GET /stream` SSE endpoint (events + status deltas), cursor-resumable via `Last-Event-ID` mapped to event ids.
- Optional bearer-token auth behind a config flag (`web-auth-token` in config.md), default off while localhost-only; binding stays `127.0.0.1` until auth ships (closes TRD gap §13.2 in the same doc pass).
- TRD: HARNESS-ARCH gains a §"Web surface" (routes, SSE contract, auth posture). Doc-first, human-reviewed.

### W1 — Fleet panel + controls (the immediate payoff)
- Fleet grid = #13561's fields (`work_state`+reason, `current_task`, `context_pressure`, lag, mode) rendered live via SSE; per-agent drill-down = phase timeline (from `phase-change`) + recent events + `detail` strings.
- Control bar: start/stop/restart/force per agent + all, `/merge`, harness restart/shutdown — all existing endpoints; destructive actions get confirm dialogs and are logged as events (`operator-action` event type, new, EMITTED by harness itself) so the audit trail lives on the same bus.
- Needs-You panel from `/human/queue` (and `/queue/{alias}` when #13173 lands).

### W2 — Chat (human↔agent + agent room)
The wake transport already delivers sub-second nudges into live sessions (`event_poll` → Monitor) — chat rides it rather than inventing a PTY:
- **Store + API:** harness-owned chat store (per-thread JSONL under harness state, gitignored — same posture as vault telemetry): `POST /chat/{thread}` (human or agent sends), `GET /chat/{thread}`, threads = `human:<alias>` (1:1) + `room` (all-agents). Sends emit a `chat-message` event targeted at the recipient alias(es) → existing nudge wakes the agent.
- **Agent side:** un-park the comms layer — implement `HarnessChatAdapter` (the first real `CommsAdapter`; POSTs to `/chat/*`), compose-include `chat-etiquette` + `mention-protocol` (+ `consensus-protocol` for the room), care-filter learns `chat-message`, and a small chat sub-skill defines read→reply discipline (reply via adapter, keep working, mention-protocol noise budget applies to human pings). **CQ specs required** (major agent-instruction change).
- **Web side:** chat pane per agent + the room view (humans watch, can post; posts by humans in the room are visible to all agents on their next nudge).
- **Supersedes the Telegram-first decision** (vault `agent-communication-layer.md`, epic #3415): the adapter interface was built for exactly this — web/harness becomes the first concrete adapter; Telegram can still land later as a second adapter. Needs an operator-approved vault decision update (`status: superseded`).
- Honest latency framing: replies arrive on the agent's next wake (seconds when idle-listening, longer mid-tool-call) — chat is "async with fast delivery," not a terminal takeover.

### W3 — Instruction editors
- **L4 (per-install):** `GET/PUT /l4/{role-class}` — PUT runs the server-side gate chain before accepting: schema/grammar validation (H2/H3 op-block grammar), `compose.py deploy --check` dry-run, optional DS-audit hook (config-gated), then write → existing file-watcher recomposes + wakes agents. UI: markdown editor with diff preview + "agents affected will restart" warning. The conversational gates (mini-CQ) are replaced by the human being the editor — but the dry-run/audit gates stay mechanical so a bad save can't brick compose.
- **L1–L3 (SquidSquad self-dev):** *propose, don't write*: the editor produces a branch + PR via the normal pipeline (`gh` shell-out), never a live write to `references/`. The web is a convenient PR-authoring surface; review/merge stays in the existing flow (post-merge handler already recomposes + deploy-signals).

### W4 — Model & effort routing panel
- `GET/PUT /config/model-routing` wrapping `config.py set` (subagent routing is already hot-reload — takes effect next task, no restart).
- `PUT /config/effort/{role}` + optional "apply now" (graceful restart — effort is spawn-time).
- **New capability — per-role primary model pinning:** add `model-<role>` to config.md + `--model <tier-alias>` in `thin_launcher.py` (tier aliases per house rule, never dated versions). Web exposes it with the same "applies on next restart" affordance. This is also the enforcement point for the token-efficiency plan's model-tiering recommendations (see `PLAN-TOKEN-EFFICIENCY.md`).

### W5 — Later / optional
- **Web terminal (xterm.js)**: requires replacing the OS-window spawn model with harness-owned PTYs (ConPTY/pywinpty on Windows) — high effort, high blast radius on the launcher/liveness stack; only worth it if chat (W2) proves insufficient. Keep as the deliberate last resort it was in the old vision doc.
- Pipeline kanban (#3963 scope), vault explorer route (ties to `VAULT-COMPARISON-DMPWEB.md` §9.4 viewer), OTEL dashboards.

---

## 4. Sequencing & dependencies

| Phase | Depends on | Size |
|---|---|---|
| W0 foundations | — | S |
| W1 fleet + controls | W0, #13561 P1 | M |
| W2 chat | W0; CQ; vault decision supersede | M–L |
| W3 editors | W0 (W1 useful) | M |
| W4 routing panel | W0 | S–M |
| W5 terminal/kanban/vault | all | L |

Deliberate call: **TUI stays** as the zero-dependency terminal fallback (it now shares all its fields with the web via #13561); statusline stays as the in-session glance (Statusline-v2). Three surfaces, one source of truth, no duplicated derivation.

## 5. Open decisions for the operator
1. **Chat room scope in W2** — 1:1 human↔agent only first, or ship the all-agents room (and consensus-protocol) in the same phase? Recommendation: 1:1 + read-only room first; agent-posting etiquette in a fast-follow once CQ results look good.
2. **Auth posture** — stay localhost-only (recommended until there's a remote-access need) vs bearer token + LAN binding in W0.
3. **Supersede Telegram-first** (#3415/#3418) in favor of the harness-adapter-first path — needs your sign-off since it reverses a locked decision.
4. **DS-audit gate on web L4 saves** — mechanical gate on every save (slower, safer) vs dry-run-only with DS audit reserved for agent-authored writes (faster; human is the reviewer). Recommendation: dry-run-only.
