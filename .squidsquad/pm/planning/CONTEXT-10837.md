# PRD: HARNESS-ARCH alignment (TRD audit follow-up)

## Source

DS audit of `docs/HARNESS-ARCH.md` against shipped + in-flight work (2026-06-03).
Audit doc: `.squidsquad/pm/planning/AUDIT-TRD-HARNESS-ARCH-DS.md`.

## Verdict tally

16 CONFIRMED · 0 IN PROGRESS · 0 HELD · **9 GAP** · **8 DRIFT** · 3 STALE

**Note**: HARNESS-ARCH currently has NO active PRD coverage. Drift accumulated.

## Critical findings (must address)

### HIGH severity (architectural integrity)

1. **`POST /events/{event_id}/complete` exists in code but doc says "no completion endpoint"** (TRD §4.2)
   - The "no completion endpoint" is a LOCKED architectural principle in the TRD.
   - Code has the endpoint. This is a code/doc contradiction on something the TRD explicitly fences.
   - **Decision needed**: remove the endpoint from code OR remove the "no completion endpoint" principle from the TRD?

2. **`POST /work/assign` documented but not implemented** (TRD §4.3)
   - TRD describes `/work/assign` as the backbone of the target routing architecture (both HARNESS-ARCH AND AGENT-RUNTIME describe it).
   - Reality: endpoint doesn't exist; routing happens via tracker label transitions.
   - **Decision needed**: implement the endpoint OR rewrite TRD to describe label-transition-based routing?

### MEDIUM severity

3. **`POST /merge` exists in code, not in TRD** (audit cross-cutting finding)
   - Reality: `POST /merge` is documented and used by DM workflow (we've used it in this very session).
   - TRD: not mentioned.
   - **Decision needed**: add to TRD §4.x.

4. **#10182 permission table removal** (TRD §13.5)
   - TRD §13.5 references it as a gate "PR #10004 merge."
   - Not in active manifest; status unknown.
   - **Decision needed**: confirm #10182 status; either reactivate or close.

5. **#10358 role → alias rename** (TRD §4.1 response shapes + cross-cutting)
   - TRD §4.1 response shapes use `alias` but code uses `role` in path params.
   - Referenced throughout but no active tracking.
   - **Coordinate with**: cross-TRD rename umbrella (separate PRD filed alongside).

6. **§4.1 `/shutdown` aspirational scope ambiguity** (low-medium drift)

### LOW severity GAPS

- §13.1 no deque persistence (TRD self-reports)
- §13.2 no API authentication
- §13.3 no multi-host support
- §13.4 EAD forge-specific
- §13.6 `/queue/{alias}` generalization

(Mostly TRD-self-reported "out of scope" items; decide whether to revisit.)

### STALE items

- §13.5 gate "PR #10004 merge" — likely stale; PR #10004 may have shipped or been superseded.
- §14 proposed `wt→claude` simplification — untracked.
- §14.3 #8692, #10101 referenced as deletable — untracked.

## Scope / what this PRD delivers

Phase 1 (Research) decides per finding: implement / update TRD / defer.
Phase 2 (Discussion) with operator on the 2 HIGH items especially (those are architectural).
Phase 3 (AC drafting) produces story breakdown.

## Gating

- Independent of E6 (#10685) — touches `harness.py`, endpoint shapes; no overlap with E6 compose changes.
- Can proceed to Phase 1 research now.

## Pre-implementation review requirement (HARD GATE)

**By the time this PRD reaches implementation, COMPOSE-ARCHITECTURE PRDs A–E will have completed** (E6 cutover shipped + PRD-D Skill materialization either shipped or in flight). Several COMPOSE-ARCH outcomes change the harness landscape this PRD operates in:

- **Post-E6**: agent role-class/alias resolution centralizes in `parse_aliases_registry()`; `role` path params may be renamed via the cross-cutting #10358 rename PRD (separate, sequenced after E6 + PRD-D).
- **Post-PRD-D**: Skill tool invocations replace some Read-tool sub-skill calls; harness's `POST /events/{event_id}/complete` semantics may need to coordinate with Skill-tool-based event handlers.
- **The `POST /work/assign` HIGH-severity finding** in particular hinges on the post-cutover routing semantics — may dissolve, may grow.

**Skill must, before starting implementation**:
1. Re-read `docs/COMPOSE-ARCHITECTURE.md` (post-cutover state) and `docs/HARNESS-ARCH.md` (current).
2. Confirm each Finding in this CONTEXT still applies — some may have been resolved as side effects of E6 or PRD-D.
3. Confirm the chosen direction for each Finding (from Phase 2 lock) is still feasible given the new arch.
4. Note any newly-introduced contradictions for re-discussion with PM before coding.

If a Finding no longer applies, document why and drop it from scope.

## Related

- DS audit: `.squidsquad/pm/planning/AUDIT-TRD-HARNESS-ARCH-DS.md`
- TRD: `docs/HARNESS-ARCH.md`
- Cross-cutting: #10358 (role→alias rename) — separate PRD
