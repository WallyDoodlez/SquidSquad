# Audit Report

## Executive summary
- **8 findings**: 2 HIGH, 3 MED, 3 LOW.
- **Single biggest theme**: The `l4-curation.md` sub-skill contradicts `COMPOSE-ARCHITECTURE.md` on the scope of L4 — it claims L4 cannot override step-specific prohibitions, while the architecture doc explicitly allows `replace` on the `instructions` slot, which would include prohibitions embedded in step content. Additionally, the sub-skill's "Talking to the user" rule about hiding SquidSquad internals conflicts with the architecture doc's expectation that agents reference sub-skills by name in user-facing output.

## HIGH findings

### H1 — Contradiction: L4 scope for step-specific prohibitions
- **Where**: `l4-curation.md` / "When the request can't be fulfilled" / paragraph 2
- **Quote**: "Step-specific *prohibitions* ('during step X, do not do Y') do NOT belong in L4. Per `COMPOSE-ARCHITECTURE.md` §6.3, those live in the relevant L1–L3 sub-skill source — they are built into SquidSquad's shipped behaviour and **cannot be overridden per-project**."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §3.3 explicitly allows `replace` on the `instructions` slot, which would let L4 replace an entire step's content — including any prohibitions embedded in that step. The architecture doc says nothing about prohibitions being non-overridable. The `l4-curation.md` claim directly contradicts the architecture's stated L4 capability.
- **Fix**: Remove the prohibition-immutability claim from `l4-curation.md`. Either align with the architecture (L4 `replace` can override step content including prohibitions) or add an explicit constraint to `COMPOSE-ARCHITECTURE.md` §3.3 if prohibitions are truly meant to be non-overridable.

### H2 — Contradiction: User-facing language vs. sub-skill reference grammar
- **Where**: `l4-curation.md` / "Talking to the user" / bullet 1
- **Quote**: "Never name any SquidSquad concept, component, file, mechanism, or terminology in user-facing prose."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §5.3 defines the composed CLAUDE.md's Instructions section as containing explicit sub-skill references like "→ see sub-skill `pipeline-sentinel`". The agent reads these references as part of its own instructions — they are user-facing in the sense that the agent sees them. The `l4-curation.md` rule would forbid the agent from ever saying "sub-skill" to a human, but the architecture doc expects the agent to understand and act on sub-skill names. This creates an impossible situation where the agent must reference sub-skills internally but cannot discuss them with the human.
- **Fix**: Clarify that the "never name internals" rule applies to *explaining the system's architecture* to the human, not to referencing sub-skills by name when describing what the agent will do. Add an exception: "You may reference sub-skills by name when describing what action you'll take, but don't explain the sub-skill system itself."

## MED findings

### M1 — Ambiguity: L4 file naming collision rules
- **Where**: `COMPOSE-ARCHITECTURE.md` / §11.2 G5
- **Quote**: "v2 proposal: file names must be globally unique within `.squidsquad/project/`; compose aborts on collision."
- **Why it's a problem**: This is listed as an "open gap" with a "v2 proposal" — but the doc is already v2. An implementer reading §7.3 (which says "named `<slot>-<short-kebab-description>.md`") has no way to know whether the collision rule from §11.2 is authoritative or still provisional. The doc claims to be the target architecture, but this gap undermines that claim.
- **Fix**: Either close the gap by promoting the proposal to a requirement in §7.3, or mark it explicitly as deferred to a follow-up PR with a concrete issue number.

### M2 — Ambiguity: Cross-role L4 file support
- **Where**: `l4-curation.md` / "Pick the file" / paragraph 2
- **Quote**: "**Provisional**: cross-role L4 (a single file that customizes multiple roles) is an open question (`COMPOSE-ARCHITECTURE.md` §11.1 Q3). Until that question is closed, write one file per role for any customization that applies to multiple roles."
- **Why it's a problem**: The sub-skill instructs agents to write one file per role, but `COMPOSE-ARCHITECTURE.md` §7.3 says "Each L4 customization is one file in `.squidsquad/project/`" — implying one file per customization, not one per role. If a human says "all agents should do X", the sub-skill would produce 4 files while the architecture expects 1. The implementer of `compose.py` doesn't know which to support.
- **Fix**: Either close Q3 in `COMPOSE-ARCHITECTURE.md` (add `roles:` frontmatter support) and update `l4-curation.md` to match, or explicitly state that multi-role L4 is not supported and the sub-skill's one-file-per-role approach is the correct behavior.

### M3 — Logical gap: L4 soul `append`-only vs. `replace` in per-slot table
- **Where**: `COMPOSE-ARCHITECTURE.md` / §3.3 / Per-slot op constraints table
- **Quote**: "| `soul` | **`append` only** | no `ordinal`, no `target`, no `insert-*`, no `replace`."
- **Why it's a problem**: The table says soul is `append`-only, but §3.4 says "L4 may append project-specific tone adjustments or `replace` core traits as needed." The prose contradicts the table — `replace` is mentioned as a valid soul operation in §3.4 but forbidden in §3.3. An implementer cannot tell which is correct.
- **Fix**: Remove the word "replace" from §3.4's soul description, or update the table to allow `replace` on soul if that was the intent. The two sections must agree.

## LOW findings

### L1 — Stale cross-reference: `AGENT-RUNTIME.md` §8.1
- **Where**: `AGENT-RUNTIME.md` / §8.1 / paragraph 2
- **Quote**: "See [COMPOSE-ARCHITECTURE §6.5](COMPOSE-ARCHITECTURE.md#65-wake-mode-handling--two-parallel-manifests-compose-time-selection) for the manifest + fragment composition mechanics."
- **Why it's a problem**: The anchor `#65-wake-mode-handling--two-parallel-manifests-compose-time-selection` doesn't match the actual heading in `COMPOSE-ARCHITECTURE.md`, which is `#65-wake-mode-handling--two-parallel-manifests-compose-time-selection` (the heading uses "manifests" not "manifests"). This is a minor link breakage.
- **Fix**: Verify the actual anchor ID generated by the markdown renderer and update the cross-reference.

### L2 — Inconsistent naming: "sub-skill" vs "sub-skill catalog" in `l4-curation.md`
- **Where**: `l4-curation.md` / "When the request can't be fulfilled" / paragraph 2
- **Quote**: "those are built into SquidSquad's shipped L1–L3 sources (`COMPOSE-ARCHITECTURE.md` §6.3) and cannot be overridden per-project"
- **Why it's a problem**: This references §6.3 of `COMPOSE-ARCHITECTURE.md` which discusses where prohibitions live, but the actual prohibition-immutability claim is not in §6.3 — it's invented by `l4-curation.md`. The cross-reference is misleading because it implies the architecture doc supports a claim it doesn't make.
- **Fix**: Either remove the cross-reference or add the prohibition-immutability rule to `COMPOSE-ARCHITECTURE.md` §6.3 if that's the intended design.

### L3 — Missing detail: L4 `ordinal` semantics for `append` on non-instructions slots
- **Where**: `COMPOSE-ARCHITECTURE.md` / §3.3 / Per-slot op constraints table
- **Quote**: "| `soul` | **`append` only** | no `ordinal`, no `target`, no `insert-*`, no `replace`."
- **Why it's a problem**: The table says soul `append` has "no `ordinal`", but §4.2 step 3.iii says "Ordering rule: sort by `ordinal` ascending where present" for all `append` ops. If soul `append` entries cannot have `ordinal`, how are multiple soul `append` entries ordered? The table says no `ordinal`, but the ordering algorithm expects one.
- **Fix**: Clarify the ordering rule for soul `append` entries (e.g., "sorted by file name ascending" or "in commit order") and update the table to match.

## What's working well

1. **The L1-L4 composition model is clearly specified** — the slot/ordinal/op grammar, the five-section output structure, and the deterministic pipeline are well-defined and internally consistent across `COMPOSE-ARCHITECTURE.md` §2-§5.

2. **The event-driven vs. polling mode handling is rigorous** — `AGENT-RUNTIME.md` §6-§7 and `COMPOSE-ARCHITECTURE.md` §6.5 together define a clean compose-time selection with no runtime branching, and the worked examples in §5.6 make the divergence explicit and testable.

3. **The source-output sync mechanisms (§8) are well-designed** — three redundant layers (PR check, auto-recompose, pre-ship gate) with clear failure modes and escalation paths. The `compose.py deploy-all --check` pattern is consistently referenced.

4. **The step ID grammar (§6.1) is precise** — BNF, character set, nesting depth, global uniqueness, and the step↔sub-skill mapping rules (1:1 default, N:1 allowed, 1:N forbidden) leave no ambiguity for implementers.

5. **The cursor model and at-least-once delivery semantics** in `AGENT-RUNTIME.md` §4.3 are well-specified — harness-owned cursor, `HTTP 410 Gone` for eviction, recovery paths, and the explicit invariant that agents never write the cursor directly.