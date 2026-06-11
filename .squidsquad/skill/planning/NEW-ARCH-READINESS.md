# New-Arch Readiness Assessment

**Date**: 2026-06-11
**Question**: Are we ready to turn on the new (event-driven, harness-supervised) architecture?
**Verdict**: **Not yet — 3 gates remain.** The runtime backbone is proven; the gaps are merge + one runtime migration + one dependency.

## What "turn on the new arch" actually means

There is **no flag to flip**. Per `docs/AGENT-RUNTIME.md` §2/§10 (rev 11, 2026-05-30), event mode is **unconditional**: each agent binds its wake mechanism at boot by probing the harness. Harness reachable → event mode; unreachable → automatic loop-mode fallback. No `event-driven:` config field, no compose-time gate, no operator-flip ceremony.

So "ready to turn on" = "can the team run correctly under harness-supervised event mode with the polished instructions and a functional harness?"

## Ready ✅

| Item | Evidence |
|---|---|
| Composed CLAUDE.md production-ready | CQ Pass 2: PM/QA/DM/Skill all 0 FAIL / 0 GAP / 0 contradictions (`cq-pass-2/REPORT.md`) |
| Composed ↔ harness ↔ sub-skill integration | Integration audit 8/8 findings fixed (`AUDIT-REPORT.md`) |
| Wire-format canonical | `target_alias` unified across all 7 call sites (Iter 63), DS NO_FINDINGS |
| Event-bus + Monitor backbone | **Live e2e verified** (see below) + 23 integration tests green |
| AGENT-RUNTIME doc-codify (#11328) | shipped |
| Sub-skill alignment (#11330) | shipped |

### Monitor mechanism — live e2e verification (2026-06-11)

Ran the real chain against a harness on isolated port 7399 (`--no-auto-start --no-auto-reboot --no-freshness-check`):

```
POST /events (assigned-to, role=pm, target_alias=skill, id=ev-assigned-to-e2e99999)
  → harness stores + target-filters via GET /events/for/skill
  → event_poll.py skill --wait 5 --target  (real subprocess, real HTTP)
  → prints JSON event line to stdout
  → Claude Monitor tool streams the line
  → agent woken with the exact event   ✅ PASS
```

Two transient "failures" during the run were **malformed test events, not system bugs**:
- emitter `role=harness` is dropped by the `POST /events` role guard (real EAD bypasses via internal `_emit_event`);
- an event without an `id` is silently skipped by `event_poll` (real emit path auto-assigns ids).
Both incidentally surfaced robustness gaps → filed as **#11404** (low).

Plus 23 pytest integration tests pass: `test_event_mode_e2e` (12 — cursor advance, skim-then-advance, handoff, comment-handling, eviction) + `test_event_mode_agent_subprocess` (11 — bootup, stop-intent, harness-down fallback).

## Gates ⏳ — must close before flip

### Gate 1 — Ship #11329 (runtime ack-cursor migration). HARD prerequisite.
`event_poll.py:299` still uses the **pre-migration cursor**: writes a local cursor file instead of POSTing `ack-cursor` to the harness. But the polished agent instructions (forge-read-pattern, cursor-management, event-mode-contract) all describe per-event `ack-cursor` POST. → **doc-vs-runtime contradiction**. The harness consumer side already exists (`harness.py:2018-2035`, audit-verified); #11329 is the emit side + `working-state.md` schema cleanup. **Status: approved + open, not done.**

**Ordering resolution**: #11329 is a *prerequisite*, not a follow-up. Recommend it ships onto the polish bundle so one merge brings polished docs + matching runtime together. (Its own AC6 requires a DS audit.)

### Gate 2 — Merge PR #11402.
The production-ready composed CLAUDE.md lives only on the branch. `main` still carries pre-polish versions; an agent booting off `main` today gets unpolished instructions.

### Gate 3 — Provision `watchdog` (#11403). NEW — surfaced by the e2e test.
Harness runtime deps (`watchdog`, and even `fastapi`/`uvicorn`) are undeclared in any requirements manifest. Without `watchdog`, **PRD-E E3 L4 file-watch auto-recompose is silently dead** — after an L4 edit, no agent gets the recompose nudge. The event bus + Monitor work without it; only the L4 file-watch subsystem is down. **Status: filed #11403 (medium).** Either declare+provision the deps, or accept manual `compose.py deploy-all` after L4 edits as an interim.

## Not a blocker

- **#11400** (sub-skill-guide cleanup) — pending, gated on the flip, but it's *post-flip* cleanup.
- **#11404** (POST /events robustness) — low; real emit paths unaffected.
- **#6274.3** (`Dev Agents:` → `Workers:` config rename) — the one remaining compose warning; scheduled migration, orthogonal to the flip.

## Recommended sequence

1. Skill picks up **#11329** onto the polish branch (Gate 1) — with its DS audit.
2. Resolve **#11403** (Gate 3) — declare + provision harness runtime deps, or accept the interim.
3. DM merges **PR #11402** (Gate 2) — polished docs + matching runtime + (if landed) declared deps, one merge to main.
4. New arch is live the next time agents boot against a reachable harness.
5. **#11400** post-flip cleanup.
