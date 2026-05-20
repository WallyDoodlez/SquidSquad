**Reported By**: pm-lead
**Priority**: Medium

**Reported By**: pm-lead (human direction, cycle 1535)
**Priority**: Medium
**Supersedes**: #9580 (incorporates its scope + broader architecture change)

## Goal

Today, `compose.py` reads the `event-driven` config flag at deploy time and inlines either polling-mode (`ralph-loop-overview.md`) OR event-mode (`common-events/l1-base.md` + 5 others) fragments into the composed CLAUDE.md. Result: large composed file with the wrong half potentially inlined.

Switch to a **boot-time lazy-load model**: compose.py emits a small bootstrap snippet that tells the agent to read `config.md` on startup, then Read the appropriate fragment based on event-driven + harness-reachability state.

## Why now (not deferred to event-mode flip)

- Polling mode is the current default. Polling agents today carry the full polling instruction set inline — fine, but the architecture should be uniform.
- Event-mode fallback to polling (per #9580) is already going to need 'read polling fragment on demand' — so the mechanism is being built anyway. Generalize it once instead of doing it twice.
- Smaller composed CLAUDE.md across the board (only the mode-specific instructions move out — agent identity, role L2, project L4 still inline).

## Proposed mechanism

`compose.py` emits a boot bootstrap section in every role's CLAUDE.md, replacing the current mode-specific inline includes:

```
## Boot — Mode Detection (Lazy Load)

On first invocation, do this BEFORE any other action:

1. Read `.squidsquad/config.md` to determine the active wake mode:
   - If `event-driven: yes` → POLL harness at `.squidsquad/.harness-port`. On reachable, Read `references/sub-skills/common-events/l1-base.md` and follow its boot sequence. On unreachable, fall through to step 2.
   - If `event-driven: no` OR fallthrough from above → Read `references/sub-skills/common/ralph-loop-overview.md` and follow its instructions (which include invoking `/loop 30m execute one Ralph Loop cycle`).

2. The loaded instructions become your active wake-mode contract.

3. Re-check mode at each cycle boundary (`cycle_post.py` already loads config — extend it to emit a `reload_mode` signal on flag change).
```

## What stays compose-time inline

- L1 agent foundation (identity, tracker protocol, git protocol — mode-agnostic).
- L2 role responsibilities.
- L3 domain variant.
- L4 project-specific (`shared-instructions.md` etc.).
- All cycle-runner / mechanical-script directives.

## What moves to lazy-load

- `ralph-loop-overview.md` — polling-mode Ralph Loop cycle definition.
- `common-events/*` — event-mode boot + listening + idle-cooldown + comment-handling + cursor management.

## Acceptance

- `compose.py` no longer includes polling-OR-event fragments in composed CLAUDE.md. Emits the bootstrap boot-mode block instead.
- Polling-mode agents (default today) read `ralph-loop-overview.md` on boot via the bootstrap directive — observable in the agent's first message logs (`Read references/sub-skills/common/ralph-loop-overview.md`).
- Event-mode agents (post-flip): if harness reachable, Read event fragments; if unreachable, fall back to Read polling fragment.
- Mode flip (config.md change) takes effect on next agent cycle boundary without recompose.
- Composed CLAUDE.md size measurably smaller — at least 30% reduction expected by moving the larger of the two fragment sets out.
- Regression: existing polling agents continue to cycle correctly. Existing event-mode tests (#9398 work) continue to pass once the bootstrap is in place.

## Risk

- Agent must Read the fragment on every fresh session (not just first boot). Cost: one file read per boot. File is small. Acceptable.
- Bootstrap directive itself must be unambiguous — same prompt-following concern as #9581. Mitigated by making the Read call imperative and tied to step 1 of boot.
- Mode-flip detection in `cycle_post.py` must NOT trigger a reload mid-cycle (only at cycle boundary). Easy to enforce.

## Sequencing

1. Land this BEFORE `event-driven: yes` flip (per the broader event-mode-readiness plan).
2. #9581 (Monitor imperative wording) folds in here — the bootstrap directive itself uses the same imperative pattern.
3. #9580 closes as superseded.

## Out of scope

- Reorganizing the L1-L4 fragment hierarchy further. The bootstrap pattern is additive; existing fragments stay where they are.
- Renaming `ralph-loop-overview.md`. Path can change later if we want; this task uses current path.

## Related

- #9580 (degraded fallback to /loop) — superseded.
- #9581 (Monitor imperative wording) — fold in.
- #9574 (CQ runner prompt-following) — same risk family, separate file.
