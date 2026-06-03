# PRD: VAULT-ARCH alignment (TRD audit follow-up)

## Source

DS audit of `docs/VAULT-ARCH.md` against shipped + in-flight work (2026-06-03).
Audit doc: `.squidsquad/pm/planning/AUDIT-TRD-VAULT-ARCH-DS.md`.

## Verdict tally

12 CONFIRMED · 0 IN PROGRESS · 0 HELD · **4 GAP** · **6 DRIFT** · 6 STALE

**Note**: VAULT-ARCH has NO active PRD coverage. Some drift items already filed as bugs (#10098, #10099) but status unclear.

## Critical findings (must address)

### MEDIUM severity

1. **`source: code` value retained in code despite spec drop** (TRD §4.3 — audit Finding 3)
   - TRD §4.3 spec lists `source: conversation | review | observation | research` (no `code`).
   - Reality: `vault-protocol.md:35` AND `vault_check.py:27` BOTH still accept `code`.
   - Decision needed: drop `code` everywhere (and migrate existing notes) OR restore `code` in spec?

2. **`links` field auto-maintain + `source: code` documented but not implemented** (TRD §7.1 — audit Finding 2)
   - `vault-protocol.md:33` lists `links` as required frontmatter.
   - `vault-protocol.md:88` describes auto-maintain behavior.
   - `vault_check.py` doesn't implement either.
   - Tracked at #10098 — confirm still active.

3. **Confidence Decay Days hardcoded** (TRD §4.4 — audit Finding 1)
   - TRD says configurable.
   - Reality: `vault_optimize.py:42` hardcodes `STALE_DAYS = 60`. Config field never read.
   - Tracked at #10099 — confirm still active.

### LOW severity

4. **Owner label drift** (TRD §10.3 — audit Finding 7)
   - Spec §4.3: `owner: pm | worker | verifier | dm | shared`.
   - Reality: 8 notes use `<role>-lead` (e.g., `skill-lead`, `pm-lead`).
   - Self-reported in TRD §10.3.
   - Decision: sweep notes to match spec OR update spec to allow `-lead` suffix?

### STALE / planned items (6)

Likely items referenced as "planned" in TRD that may have shipped or been superseded. Phase 1 research confirms each:
- (full list in audit doc)

## Scope / what this PRD delivers

Phase 1 (Research) confirms #10098 + #10099 status; decides per remaining finding.
Phase 2 (Discussion) per-finding direction.
Phase 3 (AC drafting) produces story breakdown.

## Gating

- Independent of E6 (#10685) — touches `vault_check.py`, `vault_optimize.py`, `vault-protocol.md` source; no overlap with E6.
- Can proceed to Phase 1 research now.

## Pre-implementation review requirement (HARD GATE)

**By the time this PRD reaches implementation, COMPOSE-ARCHITECTURE PRDs A–E will have completed** (E6 cutover shipped + PRD-D Skill materialization either shipped or in flight). Several COMPOSE-ARCH outcomes change the vault landscape this PRD operates in:

- **Post-PRD-D**: vault-related sub-skills (`vault-remember`, `vault-optimize`, `vault-synthesis`, `vault-protocol`) become Claude Skills at `.claude/skills/<name>/SKILL.md`. Their bodies move from inline composition to on-demand Skill-tool invocation. Behavior should be identical but the touch surface shifts.
- **`vault-protocol.md` source** is referenced by both PRD-D (becomes a Skill) and this PRD (drift fix). Coordinate ordering so a single source-of-truth update doesn't get clobbered by the other PRD.

**Skill must, before starting implementation**:
1. Re-read `docs/COMPOSE-ARCHITECTURE.md` (post-cutover state) and `docs/VAULT-ARCH.md` (current).
2. Confirm each Finding in this CONTEXT still applies — some may have been resolved as side effects of PRD-D.
3. Confirm #10098 and #10099 are still active (not silently closed during PRD-D execution).
4. Note any newly-introduced contradictions for re-discussion with PM before coding.

If a Finding no longer applies, document why and drop it from scope.

## Related

- DS audit: `.squidsquad/pm/planning/AUDIT-TRD-VAULT-ARCH-DS.md`
- TRD: `docs/VAULT-ARCH.md`
- Existing trackers: #10098 (vault-protocol sync), #10099 (confidence-decay config)
