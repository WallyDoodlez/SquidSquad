# FEAT-SKILL-059 Phase 2 Prep: Open Questions Analysis

**Date**: 2026-04-02
**Prepared by**: research-analysis

---

## Optimal Question Order

**Recommended sequence**: Q3 -> Q4 -> Q2 -> Q1

| Order | Question | Rationale |
|-------|----------|-----------|
| 1st   | Q3 -- Communication style prescriptiveness | **Dependency**: Sets the tone/detail level for all soul files. Every other decision builds on knowing how prescriptive the soul text should be. |
| 2nd   | Q4 -- Example Discussion entries | **Dependency**: Directly depends on Q3's answer (if we're prescriptive, examples reinforce; if vague, examples become the primary guidance). |
| 3rd   | Q2 -- Vault references in soul | **Architectural**: Determines whether soul files are self-contained or cross-reference. Affects file authoring but not other questions. |
| 4th   | Q1 -- PM soul split for pm-agent vs pm-lean | **Lowest dependency, most controversial**: This is a scoping/identity question specific to one role. Other roles are unaffected. Also the most likely to spark debate about PM/QA boundary. |

---

## Q3: How prescriptive should the communication style be?

**Category**: Content granularity / authoring guideline

### Option A: Structural prescriptions only (e.g., "lead with conclusions")

**Pros**:
- Leaves room for natural variation across sessions -- agents don't sound robotic
- Easier to maintain -- fewer words to update when soul evolves
- Aligns with the research's own recommendation

**Cons**:
- Vague enough that agents may ignore it or interpret inconsistently
- Hard for QA to verify ("did the agent lead with a conclusion?")

### Option B: Structural prescriptions + explicit anti-patterns (e.g., "lead with conclusions; never open with 'I checked X and Y'")

**Pros**:
- Anti-patterns are concrete and verifiable -- QA can grep for them
- Gives agents guardrails without dictating exact phrasing
- Balances flexibility with consistency

**Cons**:
- Anti-pattern lists tend to grow over time (maintenance burden)
- Risk of over-constraining edge cases where the anti-pattern is actually appropriate

### Option C: Full style guide with sentence templates (e.g., "Status updates must follow: '[What changed]. [Impact]. [Next step].'")

**Pros**:
- Maximum consistency -- all agents of the same role sound identical
- Easiest for QA to verify (pattern match against template)
- Fastest to implement -- less ambiguity for the author

**Cons**:
- Agents sound mechanical and formulaic
- Contradicts the soul's purpose (identity, not procedure)
- Templates belong in the template, not the soul

**>> Recommended: Option B** -- Structural prescriptions plus 2-3 explicit anti-patterns per role. This is verifiable without being robotic, and anti-patterns can be pruned if the list grows.

---

## Q4: Should the soul include example Discussion entries?

**Category**: Content format / teaching method

### Option A: No examples -- prose description only

**Pros**:
- Forces agents to internalize the style rather than pattern-match
- Keeps soul files shorter (targeting 30-50 lines)
- No risk of verbatim copying

**Cons**:
- Prose style descriptions are inherently ambiguous
- Harder for new contributors to understand what "evidence-first" actually looks like
- QA has no reference point for verification

### Option B: 1-2 brief examples per role, clearly marked as illustrations (research recommendation)

**Pros**:
- Concrete -- shows the voice in action
- "Illustration, not template" framing reduces verbatim copying risk
- Keeps files within the 30-50 line budget (2 examples add ~6-8 lines)

**Cons**:
- Some agents will still copy structure/phrasing
- Examples may not cover the scenario the agent actually faces
- Adds maintenance surface (examples must stay consistent with soul text)

### Option C: Examples in a separate companion file (e.g., `souls/examples/qa-examples.md`)

**Pros**:
- Keeps the soul file itself clean and concise
- Examples can be extensive without bloating the template
- Can be updated independently

**Cons**:
- Adds file count and composition complexity
- Another `{{include}}` to manage
- Over-engineering for 2 short examples

**>> Recommended: Option B** -- Include 1-2 brief examples inline, labeled "Example (illustrative, not a template):". This is the pragmatic middle ground. If verbatim copying becomes a problem, the examples can be removed in a later iteration.

---

## Q2: Should the soul reference the vault explicitly?

**Category**: Architectural coupling / separation of concerns

### Option A: No vault references -- soul is fully self-contained (research recommendation)

**Pros**:
- Soul files work even without a vault (new projects, minimal setups)
- Clean separation: soul = identity, vault protocol = adaptation
- No circular dependency risk (soul references vault, vault modulates soul)

**Cons**:
- Agents may not connect the dots between soul defaults and vault overrides
- The "how does the vault modulate the soul?" logic lives only in the research doc, not in any runtime artifact

### Option B: Single generic pointer (e.g., "Your vault's BRIEFING.md may adjust how you express these defaults.")

**Pros**:
- One sentence bridges the two systems without tight coupling
- Helps agents understand the soul-vault relationship at runtime
- Does not reference specific vault file paths

**Cons**:
- Even a generic pointer creates an implicit dependency
- May prompt agents to over-consult the vault when the soul alone is sufficient

### Option C: Explicit file references (e.g., "Consult `areas/human-profile.md` to adapt your communication style.")

**Pros**:
- Maximum clarity -- agents know exactly where to look
- Reduces the chance of agents ignoring vault context

**Cons**:
- Tight coupling to vault file structure (paths change, soul breaks)
- Contradicts the "soul is static" principle -- vault paths are dynamic
- The vault protocol already tells agents to consult these files

**>> Recommended: Option A** -- Keep the soul self-contained. The vault protocol already handles vault consultation. Adding even a generic pointer risks the soul becoming a routing table for other files. The soul-vault interaction is an emergent property, not something that needs to be declared in the soul itself.

---

## Q1: Should the PM soul differ between pm-agent.md and pm-lean.md?

**Category**: Role identity / variant management

### Option A: Single shared soul file for both PM variants (research recommendation)

**Pros**:
- One soul = one PM identity, regardless of whether QA is bolted on
- Simpler maintenance -- changes propagate to both variants automatically
- The QA bolt-on in pm-agent is procedural (what to do), not identity (who you are)

**Cons**:
- pm-agent has verification responsibilities that shape how it thinks about quality
- A combined PM/QA agent arguably has a different professional identity than a pure PM
- The "collaboration posture" toward QA is awkward when you ARE the QA

### Option B: Shared base soul + a short QA addendum for pm-agent

**Pros**:
- Preserves the shared PM identity while acknowledging the QA dimension
- The addendum can address the "you are also your own QA" dynamic explicitly
- Composition is straightforward: `{{include: souls/pm}}` then `{{include: souls/pm-qa-addendum}}`

**Cons**:
- Adds a file and composition step for a minor variant
- The addendum may be only 5-10 lines -- is it worth a separate file?
- Risk of the addendum growing to duplicate QA soul content

### Option C: Two separate soul files (pm-soul.md and pm-lean-soul.md)

**Pros**:
- Each variant has a fully tailored identity
- No awkward "ignore the QA collaboration posture" for the combined agent
- Maximum flexibility for future divergence

**Cons**:
- Duplicates 80%+ of content between the two files
- Maintenance burden: PM identity changes must be applied twice
- Contradicts the research finding that the soul defines the PM identity, not the QA bolt-on

**>> Recommended: Option A** -- Single shared soul file. The QA responsibilities in pm-agent are procedural additions handled by the template, not identity-level changes. The soul defines "what kind of PM are you?" and the answer is the same regardless of whether QA procedures are also loaded. If the combined agent needs specific guidance about self-verification, that belongs in the template's QA section, not the soul.

---

## Summary of Recommendations

| Question | Recommended | Key Rationale |
|----------|-------------|---------------|
| Q3 (prescriptiveness) | Option B: Structure + anti-patterns | Verifiable without being robotic |
| Q4 (examples) | Option B: 1-2 inline illustrations | Concrete but clearly not templates |
| Q2 (vault refs) | Option A: Self-contained, no refs | Clean separation; vault protocol handles it |
| Q1 (PM soul split) | Option A: Single shared soul | Soul = PM identity, QA bolt-on is procedural |
