# PRD: Cross-TRD `role` → `alias` rename (#10358 umbrella)

## Source

DS audits of HARNESS-ARCH, AGENT-RUNTIME, INSTALLER-ARCH (2026-06-03) all flag the `role` → `alias` rename as a cross-cutting concern referenced by multiple TRDs but untracked in the active manifest.

The TRDs themselves describe the target: `alias` is the install-time identifier; `role-class` is the type (pm/dm/qa/skill). Today the code uses `role` (often interchangeably) — historical naming from when there was 1:1 correspondence.

#10358 was filed earlier as the tracking issue but is currently inactive.

## Why a separate PRD

The rename cuts across:
- `harness.py` endpoint path params (`{role}` → `{alias}`)
- `compose.py` aliases registry (already started in PRD-A)
- `wizard.py` install flow (alias-keyed clones)
- `tracker.py` role labels (`role:*` → `alias:*` is debatable — see below)
- Sub-skill source files (placeholders)
- TRD docs

A unified rename PRD coordinates the change as one atomic move (or staged migration), preventing partial-state drift.

## Decision points for Phase 2

### D1 — Do we rename `role:*` tracker labels to `alias:*`?
- Pro: consistent terminology.
- Con: massive churn on tracker history; existing scripts that filter by `role:*` need updating; coordination with team-aware operations.
- Recommendation: NO — `role:*` labels are operationally fine; rename is purely internal naming.

### D2 — Path parameter rename in harness endpoints
- HARNESS-ARCH §4.1+ documents `{alias}`; code uses `{role}`.
- Backwards-compatible: support both during transition window OR atomic switch?

### D3 — Code identifier rename in scripts
- `role_name`, `role` variable references across `compose.py`, `harness.py`, etc.
- Bigger refactor; lots of touched files. Per `feedback_ds_review_per_change` would need careful staging.

### D4 — Scope: full rename or just the high-touch interfaces?
- Full: cleaner but bigger blast radius.
- Partial: rename only public interfaces (HTTP paths, file paths), leave internal variables.

## Hard gate

**Cannot start until E6 (#10685) ships.** E6 touches many of the same files (`compose.py`, `harness.py` configuration). Concurrent rename work would create massive merge conflicts.

## Scope / what this PRD delivers

Phase 1 (Research): inventory every `role` reference; classify into:
- public interface (HTTP path, file path, label key) — high priority rename
- internal variable / comment — low priority
- doc reference — clean as we touch

Phase 2 (Discussion): D1–D4 decisions locked.
Phase 3 (AC drafting): story breakdown (probably 3-5 stories).
Implementation: DS-review-per-change per `feedback_ds_review_per_change`.

## Gating

**E6 #10685 must ship first.** Then PRD-D (#10781) ships. Then this rename can proceed.

## Pre-implementation review requirement (HARD GATE)

**This PRD is explicitly sequenced AFTER COMPOSE-ARCHITECTURE completes** (E6 + PRD-D). The COMPOSE-ARCH work itself already starts the role → alias rename in `compose.py` (alias-keyed deploy, `parse_aliases_registry`, alias output paths). By the time this PRD starts:

- Substantial chunks of the rename may already be done — survey first, don't duplicate.
- The remaining surface is the `role` references in `harness.py`, `tracker.py`, `wizard.py`, scripts, comments, docs.
- D1 (whether to rename `role:*` labels) is the highest-blast-radius decision.

**Skill must, before starting implementation**:
1. Re-read `docs/COMPOSE-ARCHITECTURE.md`, `docs/HARNESS-ARCH.md`, `docs/AGENT-RUNTIME.md`, `docs/INSTALLER-ARCH.md` (post-cutover).
2. **Inventory all remaining `role` references** outside `compose.py` (since `compose.py` will already use alias semantics post-E6).
3. Re-confirm the Phase 2 decisions (D1–D4) are still aligned with the post-cutover terminology.
4. Coordinate ordering with any in-flight HARNESS-ARCH or INSTALLER-ARCH PRD work — both touch identifier renames.
5. Note any drift between TRDs and post-cutover code for re-discussion with PM before coding.

## Related

- TRDs flagging the rename: HARNESS-ARCH §4.1, AGENT-RUNTIME (Finding 11), INSTALLER-ARCH (Finding 25 indirectly)
- Original tracking: #10358
- E6: #10685
- PRD-D: #10781
