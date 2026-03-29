# FEAT-SKILL-037 Context — Status Bar Step Display + Rotating Hints

## Locked Decisions

### D1: Health icon positioning
**Decision**: Move health icons to line 1 (right-aligned). Line 2 is fully dedicated to step/hint text.
**Decided by**: Human
**Why**: Keeps line 1 as the "status overview" (role, health, context, countdown) and line 2 as the "activity/hint" line. Clean separation.

### D2: Hint rotation timing
**Decision**: Rotate every 60 seconds, phase-aware (current phase determines which hint sub-pool is used).
**Decided by**: Human
**Why**: 60 seconds is frequent enough to feel dynamic but slow enough to read. Phase awareness ensures hints are contextually relevant.

### D3: Max step text width
**Decision**: 60 characters for all roles, truncated with "..." if exceeded.
**Decided by**: Human
**Why**: With health icons moved to line 1, all roles have the same line 2 budget. 60 chars covers most step descriptions comfortably.

### D4: DM hint pool
**Decision**: Defer until FEAT-SKILL-035 (Delivery Manager) ships.
**Decided by**: PM recommendation (no objection from human)
**Why**: DM steps are not defined yet. Graceful fallback (no hint file = no hints on line 2). Adding hints-dm.txt later is trivial.

### D5: Boot script cleanup
**Decision**: Boot script clears current-state file (`rm -f`) AND agent writes "Initializing..." as first action.
**Decided by**: Human
**Why**: Belt and suspenders. No stale state from crashes, plus informative display during startup.

## Dev Discretion Areas

- Exact hint wording — PM will review during QA but dev chooses initial hint text
- State file write pattern (direct write vs temp+mv) — research notes direct write is fine for small files
- Staleness threshold value — research suggests 2x loop interval, dev can adjust
- awk pattern for hint pool section matching — implementation detail
- How to integrate health icons into line 1 without crowding existing content

## Key Constraints

- `current-state` files MUST be gitignored (ephemeral runtime state)
- Hint pool files live in `references/` and are copied to `.squidsquad/templates/` during setup
- State file format: `<unix_timestamp>|<step_id>|<display_text>` (single pipe-delimited line)
- Hint pool format: plain text, one hint per line, `@section` headers for sub-pools, `#` comments
- All affected files are already in the upgrade regeneration scope — no new upgrade agent needed
- Phase-aware means the 60-second rotation uses the current step_id to select the matching `@section` in the hint pool
