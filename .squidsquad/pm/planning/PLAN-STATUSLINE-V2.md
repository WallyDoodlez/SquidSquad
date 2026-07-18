# Statusline v2 — Improvement Plan

- **Date:** 2026-07-12
- **Operator concern (2026-07-12):** "each role has its own statusline, but not everything is working well — the messages aren't really helping too much, the agent health doesn't really help too much either." Context: a TUI exists (#12801, being upgraded via #13561) and a web interface on harness APIs is coming (see `PLAN-WEB-COMMAND-CENTER.md`).
- **Inputs:** segment-by-segment audit of `references/statusline.sh` (487 lines, byte-identical to the deployed `.squidsquad/statusline.sh`), `references/scripts/statusline_data.py`, `cycle.py status_bar()`, #12451 planning doc + tests, commit history.

---

## 1. Diagnosis

### 1.1 The "messages" segment — root cause

Line 2 renders the agent's self-written free-text description **verbatim** (`statusline.sh:200-207`), and the authoring convention embeds internal sub-skill names into that text by design — `ralph-loop-overview.md:32` templates `status-bar-self "phase" "sub-skill — description"`, so the operator sees strings like `tracker-protocol — Building work queue...` (live on disk in `.squidsquad/dm/current-state` right now). This **directly violates the repo's own style rule** — `style-operator-comms-no-internal-mechanics.md:14` explicitly covers status lines — but nothing in the `status_bar()` → `get_line2()` path sanitizes the text. The genuinely operator-friendly rotating hints (`hints-<role>.txt`) only render when the jargon string is empty, i.e. almost never during work.

### 1.2 The "agent health" segment — root cause

The PM-only health string (`statusline.sh:320-367`) fails on three axes:

1. **Unlabeled** — `🦑🦑👻❓` gives no agent names; the operator cannot tell which glyph is which agent.
2. **Wrong freshness model** — it classifies on raw `current-state` mtime vs `2×INTERVAL`, reimplementing the exact pre-#12451 heuristic that the codebase already fixed for the own-role path (`statusline_data.py cmd_phase` queries the live harness in event mode). An idle event-mode agent legitimately writes nothing between nudges, so it falsely renders `👻`. The #12451 tests cover only the timer/phase segments; the health block is untested and unfixed.
3. **PM-only** — DM/worker/verifier statuslines carry no health at all, so the one surface that has the problem is also the only surface offering the feature.

### 1.3 The structural problem

The statusline is being asked to be a **fleet dashboard**, which it is structurally the worst surface for (per-session, anonymous, no interaction, cross-clone file reads). Its unique value is the opposite: an **always-visible, zero-interaction glance at THIS agent's own vitals**. Fleet views now have two better homes: the TUI (#13561 makes `/status` authoritative) and the coming web command center.

---

## 2. Design principles for v2

1. **Self-scope only.** The statusline shows the session's own vitals. Fleet awareness lives in TUI/web/`/squidsquad-status`.
2. **Operator language only.** No sub-skill names, no internal mechanics (enforce the existing vault style rule, don't just cite it).
3. **One freshness source.** Everything state-like comes from the harness (with the existing 1.5s-timeout + file fallback pattern in `statusline_data.py`); no segment re-derives staleness from mtimes.
4. **Second job: telemetry emitter.** The statusline hook is the only per-turn channel that receives Claude Code's `context_window` JSON — it should POST that to the harness (already scoped as #13561 Phase 3; do not duplicate).

## 3. Target layout

```
Line 1:  🦑 skill v0.45 │ 🔨 #13454 pr_merge self-heal │ 🧠 42% │ 📡 events │ ↑2
Line 2:  🚧 Implementing the fix — running unit tests
```

| Segment | Source | Change vs today |
|---|---|---|
| Role + version | env + config.md | unchanged |
| Task `#N <title>` | harness `/agents/{role}` → `current_task` (new in #13561) | replaces `working-state.md` scrape; falls back to it when harness down |
| Context `🧠 NN%` | stdin JSON (unchanged) + POST to `/hooks/context` | keep; add emitter side-job (#13561 P3) |
| Mode/timer `📡`/`🔄` | statusline_data.py (unchanged, #12451) | unchanged |
| Git sync `↑N ↓N` | git (unchanged) | unchanged |
| Line 2 status | **structured** `status_bar()` operator-message field | jargon eliminated at the source (§4.1) |
| PM health block | **removed** | replaced by labeled fleet chips, opt-in, harness-sourced (§4.2) |
| Vault-questions, backlog, planning badge, rest-nudge | as today | keep; all are cheap and operator-meaningful |

## 4. Workstreams

### S1 — Kill the jargon at the source (highest value, no new infra)

- Change the `status_bar()` contract (`cycle.py:68-131`) from `phase|description` to `phase|operator_msg|detail`: `operator_msg` is the only thing the statusline renders; `detail` (sub-skill name, internals) flows to logs/`/agents/{role}` for the TUI/web to show in expanded views.
- Update every `status-bar-self` call site in `references/sub-skills/` to author an operator-facing message (the audit's grep list: ralph-loop-overview, pipeline-sentinel, vault-synthesis, task-intake, event-mode-contract, ...). Authoring rule added to the sub-skill: *"the message must make sense to someone who has never read the codebase"* — with examples.
- Defensive sanitizer in `get_line2()`: if the rendered text matches a known sub-skill filename pattern (`[a-z-]+ — `), strip the prefix — belt-and-braces against instruction drift (the #12854 lesson: agent discipline alone drifts).
- **CQ specs required** (agent-instruction change, house rule).

### S2 — Replace the PM health block with honest, labeled, harness-sourced chips

- Delete `statusline.sh:320-367` (the mtime reimplementation).
- Optional replacement (config-gated, default on for PM, available to all roles): one compact labeled chip row from a single `GET /status` call (cached ~10s in a temp file to keep the bar snappy): `pm● sk● qa◌ dm✖` using #13561's server-computed `work_state`. Harness down → `fleet:?` (honest unknown, never a fake ghost).
- This depends on #13561 Phase 1; until it ships, the interim state is **no health segment** — a removed lie beats a broken feature. `/squidsquad-status` remains the labeled ad-hoc fleet view.

### S3 — Task segment upgrade

- Line-1 work item reads harness `current_task` (again #13561) instead of scraping `working-state.md`; keeps the file as fallback. This makes statusline, TUI, and web show the *same* task string from the *same* source.

### S4 — Drift fixes on contact (small, bundled)

- `statusline_data.py:13` docstring says `/agents/{role}/health`; code queries `/agents/{role}` — fix docstring.
- `docs/HARNESS-ARCH.md:76` documents a `/health` response shape that doesn't match the handler (`harness.py:3097-3104`); `last_cycle` is set nowhere (dead field) — reconcile in #13561's Phase 0 TRD pass (cross-reference, don't duplicate).

## 5. What the statusline explicitly stops doing

- Fleet health (→ TUI/web). - Cross-clone file reads (→ harness API only). - Free-text internals (→ `detail` field for TUI/web expanded views). - Nothing else changes: hints, vault-question fire, backlog counts, rest-nudge all stay.

## 6. Sequencing & dependencies

| Step | Depends on | Size |
|---|---|---|
| S1 jargon kill + CQ | — | S–M (many call sites, mechanical) |
| S4 drift fixes | — (docs w/ #13561 P0) | XS |
| S2 health chips | #13561 P1 (`work_state` in `/status`) | S |
| S3 task segment | #13561 P1 (`current_task`) | XS |

S1 can ship immediately and is the single biggest perceived-quality win. S2/S3 ride behind #13561 and should be filed as a follow-up task once #13561 is approved, or folded into its Phase 2 if the operator prefers one PR-chain.
