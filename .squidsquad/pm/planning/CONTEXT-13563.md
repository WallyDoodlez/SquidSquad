# CONTEXT-13563 — BRIEFING.md diet: trim to budget and make the 2000-token budget corrective

**Light mode** (small, well-scoped doc/process change; research already covered by `PLAN-TOKEN-EFFICIENCY.md` §T2).

## Scope

One-time trim of `.squidsquad/vault/BRIEFING.md` from 40KB/~6.7K tokens down to its documented ~2000-token / ~50-line budget, plus a durable process fix so the existing every-cycle staleness check treats future budget overage as a must-fix (trim-on-contact), not just a block on new additions.

## Locked Decisions (human decided)

- **Archive destination confirmed**: historical "Active Priorities" increments (back through 2026-06-15) graduate to `vault/archives/`, following the existing `archives/shipped-pre-2026-05-19.md` precedent. Operator confirmed 2026-07-18: fine with this history moving out of the boot-loaded file — nothing needs to stay inline beyond the ~50-line target shape.

## Worker Discretion (worker agent can choose)

- Exact archive filename/grouping (e.g. one file vs date-ranged files) — follow the existing `archives/` convention.
- Precise wording of the retained ~50-line summary, as long as Active Priorities / Recent Decisions / Constraints / Team State survive in condensed form.

## Side Effect Mitigations (required)

- No loss of operator-facing sections — condensed, not deleted; archived content must remain reachable via a pointer from BRIEFING.md.

## Upgrade Path (required)

- N/A — no upgrade impact (vault-local content change + a sub-skill wording change, not a schema/config change existing installs need to migrate).

## Out of Scope

- Auto-generated BRIEFING digest from telemetry — deferred to a later web/vault-plan item (per issue body).
