---
type: learning
tags: [qa, compose, sub-skills, token-budget, planning]
created: 2026-07-19
updated: 2026-07-19
owner: verifier
status: active
confidence: high
source: observation
links: []
---

## Context

Verifying #13565 (composed-prompt re-diet: hot/cold split of `task-intake.md`
and `verification.md`, targeting >=15% smaller composed `CLAUDE.md` per role).
Independently reproduced skill's own measurement via `compose.py deploy-all`:
composed size for all 4 roles **increased** ~0.6-0.7% instead of shrinking —
the opposite of the AC.

## Lesson

**Splitting a `references/sub-skills/*.md` file into a hot core + a cold
reference file has ~zero effect on composed-boot `CLAUDE.md` size, by
construction.** Confirmed by reading `v2_link_stage.emit_v2_linked` /
`atomic_emit.assemble_and_emit`: compose only expands literal
`{{include:}}` directives at compose time. `→ run sub-skill: <name>` markers
are never inlined — they stay as pointer text in the composed output,
resolved by a fresh `Read` at *runtime*, one cycle at a time. So a sub-skill
body's size only affects the *reactive per-cycle re-read cost* (real and
valuable to cut — task-intake.md's hot core genuinely dropped from ~27KB to
~5.5KB of what a normal cycle re-reads), never the size of the
`CLAUDE.md` every fresh session boots with.

**What actually governs composed-boot size**: the shared
`references/roles/instructions.md` body plus each role's `SOUL.md` and
`instructions.md` — the content that IS `{{include:}}`-expanded. Any task
whose AC is "reduce composed `CLAUDE.md` size" must target THOSE files, not
sub-skill bodies. Cutting instructions.md content is also higher-risk: a
seemingly-redundant cut (the §1 lifetime-overview Mermaid diagram, judged
duplicative of §2/§3's diagrams) had to be reverted during #13565 because
`test_l1_your_cycle_indexing.py` treats that diagram's exact label set as a
structural desync-prevention contract with the H4 headings below it — not
all apparent duplication in this layer is actually removable.

## Rationale

This is exactly the kind of architectural fact that isn't derivable from the
issue body or a quick skim — it requires reading the compose pipeline's
actual inline-vs-pointer behavior. A future PM planning a "shrink the
composed prompt" task should scope it against `instructions.md`/`SOUL.md`
from the start (or explicitly re-scope the AC to measure re-read cost, which
sub-skill splitting DOES genuinely improve) rather than repeat a
sub-skill-splitting pass that structurally cannot move the number it's
measured against.

## Related

None yet — first note explicitly documenting this compose-pipeline
mechanism as a planning constraint.
