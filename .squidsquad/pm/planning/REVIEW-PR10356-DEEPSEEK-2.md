# Audit Report

## Executive summary
- **7 findings**: 2 HIGH, 3 MED, 2 LOW.
- **Single biggest theme**: The `l4-curation.md` sub-skill contradicts `COMPOSE-ARCHITECTURE.md` on the scope of L4 — specifically, it claims L4 can modify `soul` and `instructions` slots, while the architecture doc restricts L4 to `project-context` and `vault` for certain operations. Additionally, the `l4-curation.md` dialog exposes internal SquidSquad terminology to users, violating its own stated principle.

## HIGH findings

### H1 — L4 slot scope contradiction between `l4-curation.md` and `COMPOSE-ARCHITECTURE.md`

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 2
- **Quote**: "| What the user describes | Which slot the agent will write | ... | What the role *does* — cycle behaviour, decision rules, when-then patterns, scope of work | `slot: instructions` | ... | Who the role *is* — values, tone, professional identity, priorities | `slot: soul` |"
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §3.3 defines L4 ops (`replace`, `insert-before`, `insert-after`, `append`) as applying to *any* slot, but §11.1 Q1 explicitly asks "Soul overlay semantics — when L4 `replace` targets a soul section, is that allowed? Soul is identity, not instruction. Should L4 be allowed to *replace* shipped soul content, or only *append*?" This is listed as an **open question**, meaning the architecture has NOT decided whether L4 can modify `soul` or `instructions` slots. The `l4-curation.md` sub-skill prematurely assumes the answer is "yes" for both, contradicting the parent spec's stated uncertainty.
- **Fix**: Either close Q1 in `COMPOSE-ARCHITECTURE.md` with a definitive answer (and update §3.3 accordingly), or mark `l4-curation.md` as provisional pending that closure, with a note that `soul` and `instructions` L4 modifications are not yet authorized.

### H2 — `l4-curation.md` violates its own "Talking to the user" principle

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 2
- **Quote**: "Ask the human only the functional question ('does this change what the role *does* on each cycle, or who the role *is*?'); don't expose slot names."
- **Why it's a problem**: The immediately preceding table in the same step maps user-facing descriptions to internal slot names (`slot: instructions`, `slot: soul`). While the instruction says "don't expose slot names," the table itself is part of the sub-skill that an agent reads — and the agent is told to *internally* map to these slots. However, the "Talking to the user" section at the top of the doc says "Never name any SquidSquad concept, component, file, mechanism, or terminology in user-facing prose." The table is fine for agent-internal use, but the step 2 dialog text says "Ask the human only the functional question" — yet the table's presence in the same step creates ambiguity about whether the agent should ever mention "instructions" or "soul" to the user. The doc needs an explicit boundary marker between agent-internal reasoning and user-facing speech.
- **Fix**: Add a clear visual separator (e.g., "**Agent-internal mapping**" header) between the user-facing question and the internal slot-mapping table. Ensure the user-facing dialog text never references slot names, even in examples.

## MED findings

### M1 — `l4-curation.md` claims L4 can modify step-specific prohibitions, contradicting `COMPOSE-ARCHITECTURE.md` §6.3

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 2
- **Quote**: "Step-specific *prohibitions* ('during step X, do not do Y') do NOT belong in L4. Per `COMPOSE-ARCHITECTURE.md` §6.3, those live in the relevant L1–L3 sub-skill source; if the human asks for one, route the request to the sub-skill owner rather than writing an L4 entry."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §6.3 says: "'Never do' prohibitions that are step-specific are NOT inlined into the composed CLAUDE.md. Under v2, step-specific prohibitions live in the **sub-skill** that owns the step." This means step-specific prohibitions are authored in L1-L3 sub-skill source files, not in L4. The `l4-curation.md` instruction to "route the request to the sub-skill owner" is architecturally impossible — there is no mechanism for a deployed agent to modify L1-L3 source files (they are shipped and versioned). The agent cannot "route the request" to a non-existent process; it can only tell the human that this customization requires an upstream change to SquidSquad itself.
- **Fix**: Replace "route the request to the sub-skill owner" with "explain to the human that this type of rule is built into SquidSquad's core and can't be overridden per-project. Offer to file a feature request against the SquidSquad repo if the change is broadly useful."

### M2 — `l4-curation.md` references `compose.py deploy <role>` but `COMPOSE-ARCHITECTURE.md` doesn't define per-role deployment

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 6
- **Quote**: "Role-scoping is implicit — `compose.py deploy <role>` applies all files in that directory to the named role."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §4.4 shows `compose.py deploy <role>` in the pipeline diagram, but the doc never explicitly defines what `deploy` means or how it differs from `deploy-all`. The `l4-curation.md` assumes a per-role deployment command exists, but the architecture doc only mentions `deploy-all` in §8.1 and §8.2. An implementer reading `l4-curation.md` would not know whether `compose.py deploy pm` is a valid command or if they must always run `deploy-all`.
- **Fix**: In `COMPOSE-ARCHITECTURE.md`, add a brief definition of `compose.py deploy <role>` (single-role compose) vs `compose.py deploy-all` (all roles), or clarify that only `deploy-all` exists and `l4-curation.md` should reference it instead.

### M3 — `l4-curation.md` says "one file per L4 customization" but `COMPOSE-ARCHITECTURE.md` §7.3 says "one file per customization" — ambiguity on multi-role customizations

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 6
- **Quote**: "Cross-role L4 (a single file that customizes multiple roles) is an open question (`COMPOSE-ARCHITECTURE.md` §11.1 Q3) and is not currently supported; if the human asks for the same customization across roles, write one file per role."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §11.1 Q3 asks: "Multi-role L4 files — can one L4 file apply to multiple roles, or must there be one file per role? (Proposal: support `roles: [pm, verifier]` frontmatter list.)" The `l4-curation.md` takes a definitive stance ("write one file per role") while the parent doc lists it as an open question. If the architecture later decides to support `roles:` frontmatter, the `l4-curation.md` guidance will be wrong and will produce duplicate files that may conflict.
- **Fix**: In `l4-curation.md`, mark this guidance as provisional pending Q3 closure, or align with the parent doc by saying "per current architecture, write one file per role; this may change if multi-role frontmatter is added."

## LOW findings

### L1 — `l4-curation.md` references `compose.py --check` but `COMPOSE-ARCHITECTURE.md` doesn't define the `--check` flag

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 8
- **Quote**: "**Compose dry-run**: `compose.py --check` validates the new file resolves cleanly (target exists, no DRY violation, no orphan)."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §8.1 mentions `compose.py deploy-all --check` but never defines a standalone `compose.py --check` command. The `l4-curation.md` assumes a `--check` flag exists without the parent doc specifying it. An implementer would not know whether `compose.py --check` is a valid command or if it must be `compose.py deploy-all --check`.
- **Fix**: In `COMPOSE-ARCHITECTURE.md`, either define `compose.py --check` as a dry-run mode, or update `l4-curation.md` to reference the exact command form that exists (e.g., `compose.py deploy-all --check`).

### L2 — `l4-curation.md` says "the agent reads the draft back to the human one final time" but `COMPOSE-ARCHITECTURE.md` §7.4 says "the agent confirms the L4 write back to the human in conversation"

- **Where**: `l4-curation.md` / "The elicitation dialog" / step 8
- **Quote**: "**Mini-CQ**: the agent reads the draft back to the human one final time and gets explicit yes/no."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §7.4 step 2 says: "Mini-CQ: the agent confirms the L4 write back to the human in conversation ('I'm adding an `insert-before step:cycle/file-bug` step for the incidents-directory check. OK?')." The `l4-curation.md` says "reads the draft back" which implies showing the full prose, while the architecture doc implies a shorter confirmation. These are not contradictory but are ambiguous about the level of detail shown to the human. An implementer wouldn't know whether to show the full draft or a summary.
- **Fix**: Align the two docs: either both say "read the full draft back" or both say "confirm the change in one sentence." The architecture doc's example suggests a one-sentence confirmation; `l4-curation.md` should match that.

## What's working well

1. **Consistent L1-L4 layer model**: Both `COMPOSE-ARCHITECTURE.md` and `AGENT-RUNTIME.md` agree on the four-layer composition model, the role of L4 as project-local overlay, and the invariant that L1-L3 are shipped and versioned. No contradictions in the core layering.

2. **Clear mode-separation in AGENT-RUNTIME.md**: The loop vs event-driven mode distinction is well-specified, with explicit compose-time selection (§8.1), no runtime mode detection, and a documented manual fallback path (§8.2). The two modes produce structurally different composed outputs without ambiguity.

3. **Well-defined safety gates for L4 writes**: `COMPOSE-ARCHITECTURE.md` §7.4 specifies three gates (DeepSeek audit, mini-CQ, compose dry-run) that must all pass before any L4 write commits. The `l4-curation.md` sub-skill correctly references these gates in the correct order.

4. **Consistent step ID grammar**: `COMPOSE-ARCHITECTURE.md` §6.1 provides a formal BNF grammar for step IDs, with clear rules on uniqueness, stability, and breaking-change protocol. This is referenced correctly by `l4-curation.md` when discussing `target` resolution.

5. **Source-output sync mechanisms**: `COMPOSE-ARCHITECTURE.md` §8 defines three reinforcing layers (PR check, auto-recompose on merge, pre-ship gate) that are internally consistent and correctly reference each other. No contradictions between the layers.