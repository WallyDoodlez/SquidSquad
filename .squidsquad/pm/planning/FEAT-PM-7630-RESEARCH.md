# FEAT-PM-7630 Research — Event-Driven Agent Architecture

## Summary

This task proposes the most significant architectural shift since the cycle runner (#2057): **the harness owns the entire agent cycle, and agents react to events rather than running multi-step cyclic prose**. The current architecture, while improved by #2057 (which split mechanical pre/post from creative work), still relies on LLM agents reading prose instructions and faithfully executing a 5-10 step cycle script. Evidence from the vault and human-profile is damning: PM dropped improvement scanning for 15+ cycles, proving LLM cycle discipline is unreliable under context pressure. The proposed 4-phase EPIC would move all mechanical cycle steps into harness.py (deterministic Python), leaving agents with creative-only templates that describe *what* they do, not *how* they loop.

**Recommendation**: Feasible with caveats. The event bus infrastructure (#4709, #5622) is already in place — harness has an event stream, event catalog, event filtering, and mechanical reactions. Phase 1 (continuous monitors) is largely done. The hard part is Phase 2 (event waking): agents currently use `/loop [INTERVAL]m` to self-schedule; replacing that with harness-triggered wake-on-event requires a signaling mechanism between harness and Claude Code that does not exist today. Phase 3 (remove cycle from templates) is straightforward mechanical work. Phase 4 (creative-only templates) is a template editing task. No migration needed (pre-public).

**Primary risks**: (1) Harness→agent wake signaling is the critical missing piece — currently harness can only spawn/kill/reboot agents, not trigger creative work within a running session. (2) The interval-based polling model must be replaced with event-triggered activation, which requires a reliable event detection → agent notification chain. (3) Context pressure management currently relies on agents checking context-pressure files; harness must take this over.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority, supersedes #6056/#5775/#5613, labeled "next major architectural shift — all mechanical cycle steps move to harness"
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 is the immediate predecessor; this EPIC removes the remaining agent-owned cycle orchestration that #2057 left in place. The decision explicitly notes #7630 as the next evolution.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — directly applicable: cycle orchestration prose in templates must be replaced with deterministic harness code. The pattern's threshold ("more than 2 conditional branches → script") applies to the entire cycle flow.
- **Human preferences**: **Critical** — "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" and "agents should react to events, not run multi-step cycles." Also: "prefers direct/mechanical checks over indirect state files" — harness PID checks are already the primary liveness mechanism, which aligns.
- **Related learnings**: [[learning-commit-code-state-exclusion]] — the original motivation for #2057 (branch switching bugs from agent-managed git). Same class of problem: LLMs cannot be trusted to execute mechanical sequences reliably.

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` (lines 1–1415) — major expansion: new cycle-ownership API endpoints, event-triggered agent activation, cycle pre/post absorption
  - `references/scripts/cycle_pre.py` (lines 1–1058) — becomes harness-internal; agent no longer invokes directly
  - `references/scripts/cycle_post.py` (lines 1–746) — becomes harness-internal; cycle_output.json semantics change
  - `references/scripts/cycle.py` (lines 1–287) — status bar, iteration logging, counter ops may be absorbed or stay as harness utilities
  - `references/scripts/event_bus.py` (lines 1–103) — may add agent-wake event emission
  - `references/scripts/event_bus_reader.py` (lines 1–89) — may be superseded by harness-pushed events
  - `references/scripts/event_catalog.py` (lines 1–216) — new event types: `agent-wake`, `work-available`, `cycle-request`, `cycle-complete`
  - `references/scripts/boot_remote.py` (lines 1–80+) — agent boot may change from interval-based to event-triggered
  - `references/scripts/thin_launcher.py` (lines 1–117) — hardcoded `"Boot. Begin your first Ralph Loop cycle now."` prompt must change; no `/loop` command
  - `references/scripts/config.py` (lines 1–330+) — new config values for event-driven mode, possibly deprecating `interval`
  - `references/sub-skills/common/cycle-runner.md` (lines 1–93) — **removed** from all manifests or drastically shrunk to creative-only reference
  - `references/sub-skills/common/context-pressure.md` (lines 1–19) — absorbed by harness; agent no longer checks context pressure
  - `references/sub-skills/common/event-reactions.md` (lines 1–32) — becomes metadata reference only; harness drives reactions
  - `references/sub-skills/common/self-restart.md` (lines 1–21) — absorbed; harness manages restarts via intent API (already partially true, line 2–5)
  - `references/sub-skills/common/agent-lifecycle.md` (lines 1–46) — rewritten to describe event-driven model
  - `references/sub-skills/common/interval-sync.md` — removed; interval becomes internal harness concern
  - `references/sub-skills/common/resume-working-state.md` — agent may still read working-state on wake but harness manages it
  - `references/roles/dev/instructions.md` (lines 1–119) — stripped of Ralph Loop prose (lines 35–93), cycle markers, step markers, status bar writes
  - `references/roles/pm/instructions.md` (lines 1–185) — same stripping
  - `references/roles/qa/instructions.md` (lines 1–153) — same stripping
  - `references/roles/dm/instructions.md` (lines 1–144) — same stripping
  - `references/roles/*/includes.yml` (24 files) — `common/cycle-runner`, `common/context-pressure`, `common/self-restart`, `common/interval-sync` removed from all manifests
  - `tests/test_cycle_pre.py` — tests become harness-internal or rewritten
  - `tests/test_cycle_post.py` — tests become harness-internal or rewritten
  - `tests/test_harness.py` — expanded with new cycle-ownership tests
  - `tests/integration/test_harness.py` — expanded
  - `tests/integration/test_status_flow.py` — may need updates

- **Behavior changes**:
  1. Agents no longer call `cycle_pre.py` / `cycle_post.py` — harness invokes them before/after agent work
  2. Agents no longer write `cycle-output.json` directly — harness reads agent output and processes it
  3. Agents no longer run `/loop [INTERVAL]m` — harness manages activation timing
  4. Agents no longer check context pressure — harness monitors and triggers restart
  5. Agents no longer write status bar states — harness writes them based on agent activity
  6. Agent template instructions shrink by ~40-60% (all cycle mechanical prose removed)
  7. Harness becomes the sole owner of: git pull, branch enforcement, triage queries, commit/push, status transitions, iteration logging, version bumps
  8. Event bus becomes the primary agent activation mechanism instead of interval polling

- **Dependencies**:
  - FastAPI + uvicorn (already in harness.py, line 51–52)
  - `boot_remote.py` for agent spawn (already imported, line 47)
  - `health_check.py` for legacy fallback (already imported, line 48)
  - `event_bus.py` / `event_bus_reader.py` for event emission/consumption (already imported in cycle_pre, line 1007–1009; cycle_post, line 719–720)
  - `git_ops.py` for git operations (already imported in cycle_post, line 1099)
  - `tracker.py` for status transitions (called via subprocess in cycle_post, line 189)
  - `config.py` for configuration (already imported in cycle_pre, line 73–76; cycle_post, line 70–71)
  - Claude Code CLI for agent processes (thin_launcher.py, line 81)

## Side Effects

- **Risk 1**: Harness-to-agent wake signaling gap — Severity: H — Mitigation: The current architecture has no mechanism for the harness to trigger creative work inside a running Claude session. Claude Code sessions are conversational; once booted, the agent waits for `/loop` to re-invoke it. Three options: (A) harness kills and respawns the agent with a "wake" system prompt on each event (works but loses session continuity), (B) harness writes a file that the agent's statusline hook detects, triggering work (requires Claude Code hook support), (C) harness manages the cycle externally — agent runs once, produces output, exits, harness processes output, spawns again when work is available (stateless model, clean but breaks working-state continuity).

- **Risk 2**: Context pressure detection moves to harness — Severity: M — Mitigation: Currently the statusline hook writes context pressure to `.squidsquad/<role>/context-pressure` after every assistant message (context-pressure.md, line 5). The harness doesn't have access to this file for agent clones. After #7630, harness must either read the pressure file from the agent clone or use an alternative signal (e.g., agent session token count from Claude API). The existing harness health endpoint (line 676, `GET /agents/{role}/health`) already reads context-pressure from the primary repo, but clones may have their own.

- **Risk 3**: Loss of agent situational awareness — Severity: M — Mitigation: Agents currently read `cycle-input.json` which contains the full pipeline state (work queue, verification queue, open PRs, agent health, recent events). If harness drives the cycle, agents may receive a narrower "work item" rather than the full picture. This could reduce the cross-role awareness that PM's SOUL.md emphasizes ("examine the pipeline state — don't just scan for your own work items"). The event-driven model must preserve this holistic awareness.

- **Risk 4**: Single point of failure — Severity: M — Mitigation: Harness already owns agent lifecycle (health polling, crash recovery, intent state machine). Adding cycle ownership makes harness more critical. Current harness has crash recovery via `.harness-state.json` (line 315–341). This must be extended to persist in-flight cycle state. If harness crashes mid-cycle, the agent's work could be lost or duplicated.

## Edge Cases

- **Agent produces output but harness can't process it**: If the harness crashes between agent work completion and `cycle_post` execution, the `cycle-output.json` must be preserved and re-processed on harness restart. Current crash recovery only handles PID/intent state, not in-flight cycle data.

- **Agent wakes but no work exists**: Current "quiet cycle" concept (cycle type `quiet` in cycle-output.json, line 51) must be preserved. Harness must detect "no work available" and either skip waking the agent or wake it with an explicit "quiet" signal. The quiet cycle counter in working-state.md (cycle.py, line 82–85) must be maintained by the harness.

- **Agent needs to spawn subagents (Agent tool)**: Dev agents currently spawn subagents via the Agent tool for directed subtasks (instructions.md, line 17). This is creative work that doesn't fit the harness-owned cycle. The event-driven model must distinguish between "main agent cycle" (harness-owned) and "subagent work" (agent-initiated).

- **Branch workflow with feature branches**: Skill agent with branch workflow currently has split commits: code to feature branch, state to working branch (cycle_post.py, lines 316–393). Harness must handle this split correctly, including checkout gymnastics.

- **DM version bump**: DM's version bump (cycle_post.py, lines 415–464) is harness-owned post-cycle work that requires careful ordering (commit, tag, push, reset counter). Harness must ensure this executes correctly.

- **Verification-failed events from QA**: Currently in `cycle_pre.py` (lines 413–421), `verification-failed` events trigger `rework-needed` mechanical reactions for skill agents. In the event-driven model, this becomes the primary wake trigger — QA verification fails → harness wakes skill agent with rework context.

## Integration Risks

- **Event bus race conditions**: Current event bus uses a thread-safe deque with lock (harness.py, lines 348–384). If harness is both emitting events (cycle-start, cycle-end) AND processing them to trigger agent wakes, there's a risk of re-entrant event processing. The `_update_agent_from_event` method (line 737) modifies AgentState directly — if called from both the event ingestion thread and the wake-decision thread, state could be inconsistent.

- **Compose → reboot chain**: Harness currently reboots agents after compose when templates change (harness.py, lines 1179–1223, `_reboot_affected_agents`). In event-driven mode, a `compose-completed` event should wake affected agents rather than rebooting them — but if templates changed significantly, a full reboot may still be needed.

- **Startup race**: Harness auto-starts all agents on boot (harness.py, lines 475–491) and then health-polling begins. In event-driven mode, agents should not start working until the harness signals "ready" (event bus initialized, state loaded, monitors active). Current deferred-init thread (line 492) races with agent startup.

- **Tracker comment/transition idempotency**: Currently `cycle_post.py` executes status transitions and tracker comments (lines 163–220). If harness crashes and re-processes a cycle, these must not be duplicated. The tracker.py transition command has some idempotency protection (validates from→to), but comments are append-only and would duplicate.

## Upgrade & Migration

- **New config values**:
  - `event-driven` (Event Driven, Enabled): `yes`/`no`, default `no` — gates the new behavior
  - `interval` (Iteration Interval, Minutes): **behavior change** — in event-driven mode, becomes maximum idle timeout before forced wake, not cycle interval. Default remains `30`.
  - `wake-on-events` (Event Driven, Wake Events): comma-separated event types that wake this agent. Default per-role from event catalog.

- **New files**: None expected — harness absorbs functionality into existing files.

- **Template changes**: 
  - `common/cycle-runner.md` removed from all 24 includes.yml manifests
  - `common/context-pressure.md` removed from all manifests  
  - `common/interval-sync.md` removed from dev/dm/qa manifests (PM never had it)
  - `common/self-restart.md` removed or reduced to "harness manages restarts"
  - `common/event-reactions.md` rewritten as reference metadata
  - All `instructions.md` files stripped of Ralph Loop prose, step markers, cycle markers, status bar bash commands
  - New sub-skill `common/event-driven-workflow.md` added that describes: "when you are woken, read the work context from `.squidsquad/[ROLE]/work-context.json`, do your role's creative work, write results to `.squidsquad/[ROLE]/work-result.json`, then signal completion"

- **Upgrade steps**: N/A — no migration needed (pre-public). The feature is gated behind `event-driven: yes` config. Existing teams continue with cyclic model until they opt in.

- **Graceful degradation**: If `event-driven: no` (default), current cycle-runner behavior is preserved unchanged. compose.py continues to include cycle-runner.md and related sub-skills. Harness continues to function as today (health polling + intent API). The event bus continues to operate as today (observational only, no agent waking).

## Open Questions

- **Q1**: How does the harness wake an agent to do creative work? — **Why**: This is the critical architectural gap. Claude Code sessions are conversational — the harness can spawn a session but cannot inject work mid-session. Options (spawn-on-event vs. persistent session with file polling vs. Claude Code tool-based wake) have fundamentally different reliability and latency characteristics. Getting this wrong means rebuilding the wake mechanism.

- **Q2**: Does the agent still write `cycle-output.json` or does the harness extract work results differently? — **Why**: The cycle-output.json format (93 lines of schema in cycle-runner.md) is the contract between agent creative work and mechanical post-processing. If the harness owns the full cycle, this contract changes — but the status transitions, tracker comments, iteration logs, and git commits still need structured input. The format question affects every role's template.

- **Q3**: What replaces the `/loop` command? — **Why**: `/loop [INTERVAL]m` is the current agent scheduling mechanism built into Claude Code. Removing it means either: (a) harness spawns a new agent session per work item (stateless), (b) agent runs once and exits, harness respawns when next event arrives, or (c) a new Claude Code mechanism for external wake signals. Each has different implications for session continuity, context cost, and working-state persistence.

- **Q4**: How does PM's improvement scanning work in event-driven mode? — **Why**: PM's improvement scan (improvement-scan.md, 103 lines of prose) is the canonical example of LLM-unreliable cyclic discipline (PM dropped it 15+ cycles). In event-driven mode, the harness should trigger improvement scans deterministically (e.g., every N cycles without active work, or on `compose-completed` events). But the scan itself is creative work — the harness can't do it. The harness must wake the PM for scanning without relying on PM's prose instructions to remember.

## Recommendation

**Feasible with caveats.** The event bus infrastructure is solid, the vault context is clear, and the human's preferences are unambiguous. Phases 1, 3, and 4 are straightforward engineering. Phase 2 (agent event waking) is the hard part — it requires designing a wake signaling mechanism that doesn't exist today. Recommend prototyping Phase 2 in isolation before committing to the full EPIC. The stateless spawn-per-event model (option A from Q1) is the simplest and most reliable, but loses session continuity — this may be acceptable if working-state.md checkpointing is robust.

## Vault Candidates

- **Type**: decision — Cycle ownership transfer: harness owns pre/post, agent owns creative only — **Why**: This is the architectural decision that distinguishes #7630 from #2057. The boundary line (what's mechanical vs. creative) will drive template design for years.

- **Type**: pattern — Stateless agent sessions: spawn fresh per work item, checkpoint via working-state.md — **Why**: If adopted, this is a reusable pattern that applies to all roles. The cycle-runner architecture (#2057) already proved that working-state.md can persist context across sessions. Extending this to per-work-item sessions is a natural evolution.

- **Type**: learning — LLM cycle discipline is unreliable at scale: PM dropped improvement scanning 15+ cycles — **Why**: Concrete, measured evidence that supports the core motivation for #7630. Worth preserving as justification for why mechanical cycle work must be deterministic code, not prose.

- **Type**: decision — Event-driven wake signal mechanism (to be determined) — **Why**: Once designed, the wake mechanism is a fundamental architectural choice that affects harness, thin_launcher, and all agent templates. Should be vaulted as a decision when settled.

- **Type**: pattern — Harness as single source of truth for agent state — **Why**: #7630 completes the trend from #4966 (harness owns lifecycle) and #2057 (harness owns mechanical pre/post). The pattern of "harness owns state, agents are stateless workers" is emerging and worth codifying.