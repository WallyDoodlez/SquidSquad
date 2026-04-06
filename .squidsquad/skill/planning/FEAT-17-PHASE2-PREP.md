# FEAT-17 Phase 2 Prep: Open Question Analysis

**Date**: 2026-04-05
**Source**: FEAT-17-RESEARCH.md Section 7
**Purpose**: Structured options analysis for each open question to accelerate Phase 2 decision-making

---

### Q5: What is the human-profile.md seeding strategy?
**Category**: Configuration / Bootstrap
**Dependency**: None — this is a foundational decision that other questions don't block on, but it shapes how quickly vault-remember produces value.

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Empty template with section headers only. Agents populate organically as they observe preferences. | Clean start, no risk of wrong data. Agents learn ground truth only. | Useless for first N cycles. Cold-start problem — vault-remember has nothing to reference. |
| B | Pre-seed from MEMORY.md feedback files and BRIEFING.md. Mark all pre-seeded entries `confidence: medium`. | Immediate value from day 1. Existing data is already human-validated (MEMORY.md entries are real feedback). Confidence tagging signals "verify me." | Some entries may be stale or misinterpreted. Requires a one-time migration script. |
| C | Ask the human to fill it out during setup (interactive wizard). | Highest accuracy — human curates directly. | Blocks on human action. Most humans won't do it. Setup friction kills adoption. |

**Recommended**: B — Pre-seeding from known sources gives immediate value without blocking on human action. The `confidence: medium` tag is the safety valve — agents treat pre-seeded entries as provisional until the human confirms or contradicts them. The MEMORY.md files in this repo already contain real human feedback (e.g., "Never ship with failed TCs", "No cd in Bash"), so the data quality is high.

---

### Q1: Should vault-remember be enabled by default?
**Category**: Configuration / Defaults
**Dependency**: Q5 (seeding strategy affects whether enabled-by-default produces immediate value or noise)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Enabled by default (`vault-remember: yes`). All new installations write vault notes from cycle 1. | Immediate value. Users don't need to discover and enable the feature. Deterministic gates prevent noise even without a mature vault. | New users may not understand what's being written. Early notes may be low-quality before the vault has enough content for meaningful dedup. |
| B | Disabled by default (`vault-remember: no`). Users opt in after understanding the vault. | No surprise behavior. Users consciously decide to enable. Zero risk of unwanted writes. | Most users never discover opt-in features. Vault stays empty, defeating the purpose. |
| C | Enabled by default but in "advisory mode" — the reflection runs and logs candidates to the iteration log, but does NOT write vault notes. User flips to "write mode" when ready. | Low risk: users see what would be written without committing. Smooth on-ramp. | Two modes to maintain. Advisory mode adds cycle time for zero vault content. Users may never flip to write mode. |

**Recommended**: A — Enabled by default. The deterministic gates (write budget, dedup, quiet-cycle skip) already prevent noise. The 2-write cap bounds risk. Users who don't want it can set `vault-remember: no`. This follows the principle of "useful out of the box." Advisory mode (C) adds complexity for marginal safety gain.

---

### Q2: Should the DM agent also run vault-remember?
**Category**: Scope / Agent Coverage
**Dependency**: Q1 (if vault-remember is disabled by default, DM inclusion is moot until enabled)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Yes — DM gets the same `{{include: common/vault-remember}}` insertion as dev and PM. Same budget, same gates. | DM captures doc patterns, release processes, user communication insights. Consistent architecture — all agents use the same sub-skill. | DM is optional and intermittent. DM's insights may be lower-value (changelog style is less architecturally significant). Adds one more agent's writes to vault growth. |
| B | No — DM skips vault-remember entirely. DM's observations stay in iteration logs only. | Simpler Phase 3 scope (fewer entry files to modify). DM is already optional — adding features to an optional agent delays shipping. | Lost insights about doc patterns and release processes. Inconsistency — "some agents reflect, some don't." |
| C | Defer — ship Phase 3 without DM support, add DM in a fast-follow Phase 3.1. | Smaller initial scope. Can assess vault-remember's value on dev/PM before extending. Ship faster. | Two-phase rollout complexity. If Phase 3.1 never happens, DM permanently lacks the feature. |

**Recommended**: C — Defer to Phase 3.1. DM is optional per project config, and Phase 3 already has substantial scope (vault_remember.py, sub-skill, entry file changes for dev + PM, cycle.py, vault_check.py, config, human-profile seed). Adding DM increases the test matrix. Ship for dev and PM first, validate the pattern works, then add DM in a small follow-up. The entry file change for DM is 2 lines — trivial to add later.

---

### Q4: Should confidence decay be automatic or advisory?
**Category**: Behavior / Automation Level
**Dependency**: None — independent of other questions, but affects vault maintenance burden.

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Fully automatic — `decay-scan` runs as part of vault-check Level 2 and applies decay directly. No confirmation needed. | Zero maintenance burden. Vault self-corrects over time. No human attention required. | May decay genuinely stable knowledge (e.g., "we use REST" is still true after 60 days of no changes). Silent decay could erode trust in vault accuracy. |
| B | Advisory only — script flags notes for decay but an agent or human must confirm each one. | No false positives. Human stays in control. High trust in vault accuracy. | Requires human attention that may never come. Flagged notes accumulate without action. Advisory fatigue — humans ignore advisory lists. |
| C | Automatic with `evergreen` tag exemption — notes tagged `evergreen` skip decay. All others decay automatically on schedule. | Best of both worlds: stable knowledge is protected, transient knowledge decays naturally. Simple opt-out mechanism. | Requires agents (or humans) to remember to tag stable notes as `evergreen`. If tagging is forgotten, stable notes decay incorrectly. Adds a new concept to the vault model. |

**Recommended**: C — Automatic with `evergreen` exemption. The `evergreen` tag is a simple, well-understood concept (many knowledge management systems use it). The default behavior (decay) is correct for most notes — decisions and patterns DO become stale over time. The small set of truly permanent knowledge (core architecture choices, fundamental human preferences) gets the `evergreen` tag. This keeps the vault healthy without requiring ongoing human curation.

---

### Q3: What happens to "deferred vault items" (budget exceeded)?
**Category**: Behavior / Data Loss Prevention
**Dependency**: Q1 (only relevant if vault-remember is enabled), Q4 (decay behavior affects whether deferred items stay findable in iteration logs)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Accept the loss — the 2-write cap is the quality gate. If it's not in the top 2, it's probably not vault-worthy. Deferred items stay in iteration logs only. | Simplest. No new mechanisms. The budget IS the quality filter. Iteration logs preserve raw data for 20 cycles. | Valuable insights can be lost when iteration logs are cleaned up (keep 20). Productive cycles are penalized. |
| B | Add a `deferred-vault` section to working-state.md. Next non-quiet cycle's reflection checks deferred items first before evaluating new candidates. | No insight is permanently lost (until working-state is cleared). Deferred items get a second chance. Minimal added complexity. | Working-state grows with deferred items. Deferred items compete with next cycle's fresh insights. Could create a backlog that never clears. |
| C | Allow improvement scanning to process deferred vault items during quiet cycles. Scanner reads iteration logs for "Vault-worthy but deferred" markers and promotes them. | Uses existing quiet-cycle mechanism. Deferred items are handled when the agent has spare capacity. Natural backpressure — busy agents defer, idle agents catch up. | Couples two independent features (improvement scan + vault-remember). Adds complexity to scan logic. Quiet cycles may not come often enough for busy projects. |

**Recommended**: A — Accept the loss for Phase 3. The 2-write cap exists precisely as a quality gate. If a cycle produces 4 vault-worthy insights, the top 2 are written and the others survive in the iteration log for 20 cycles. If they're truly important, they'll resurface in a future cycle's work. Monitor iteration logs post-launch — if "deferred" markers appear frequently with high-value content, add Option B in a follow-up. Starting simple avoids building machinery for a problem that may not materialize.

---

### Q6: How should vault-remember interact with the designer agent?
**Category**: Compatibility / Agent Extension
**Dependency**: Q2 (DM scope decision informs the general pattern for optional agents), Q1 (must be enabled)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | No special handling — the existing 5 categories (decisions, patterns, learnings, human preferences, project context) already cover design via "DECISIONS" and "PATTERNS." Designer uses the existing escape hatch for new prefixes if needed. | Zero additional work. Keeps the category model clean and simple. Designer is already supported implicitly. | Design-specific insights may not map cleanly to generic "decisions" or "patterns." Designer may underuse vault-remember because the categories don't feel like a natural fit. |
| B | Add a 6th category: "DESIGN DECISIONS" with a dedicated `style-` galaxy prefix. The reflection prompt explicitly asks about visual patterns, design tokens, and UI choices. | Designer gets first-class support. Design insights are clearly categorized. Better discoverability for design-related vault notes. | Adds scope to Phase 3. The `style-` prefix already exists in the vault model (galaxy/style-*.md). Adding a 6th category to the reflection prompt makes it longer for all agents, not just designer. |
| C | Defer — ship Phase 3 with 5 categories. If designer agents produce vault notes that consistently don't fit, add a design category in Phase 3.1 alongside DM support. | Smaller scope. Evidence-driven decision — only add complexity if the problem manifests. | Designer may feel like a second-class citizen. If design insights are systematically miscategorized in Phase 3, cleanup is needed later. |

**Recommended**: A — No special handling. The research document already notes that `style-` is a valid galaxy prefix and agents can introduce new prefixes via the escape hatch (vault-protocol.md line 48). The 5 categories are intentionally abstract — "DECISIONS" covers design decisions just as well as architecture decisions. Adding a 6th category increases prompt length for all agents to serve one optional role. If designer feedback shows the categories are insufficient, it's a trivial prompt edit in a follow-up.

---

## Suggested Walk-Through Order

| Order | Question | Rationale |
|-------|----------|-----------|
| 1 | **Q5** (human-profile.md seeding) | Foundational — determines what data exists when vault-remember starts. No dependencies. Quick to resolve. |
| 2 | **Q1** (enabled by default?) | Core configuration decision. Depends on Q5 (seeding affects whether default-on produces value). Sets the stage for all other questions. |
| 3 | **Q2** (DM agent inclusion) | Scope decision that affects implementation effort. Depends on Q1. Clear defer option keeps Phase 3 focused. |
| 4 | **Q4** (confidence decay: auto vs advisory) | Independent behavior decision. No controversial trade-offs — the `evergreen` exemption pattern is well-established. Quick consensus expected. |
| 5 | **Q3** (deferred vault items) | Depends on Q1 (only matters if enabled) and Q4 (decay affects iteration log lifespan). The "accept the loss" recommendation is the simplest but may provoke discussion about data loss tolerance. |
| 6 | **Q6** (designer agent interaction) | Least urgent — designer is optional, and the existing model handles it implicitly. Save for last as it's most likely to be resolved quickly with "no action needed." |

**Rationale for this order**: Dependencies flow top-down (Q5 informs Q1, Q1 informs Q2/Q3, Q4 is independent). The most foundational decisions come first so later questions can reference resolved answers. Q6 is last because it's the most likely to be a quick "no change needed" consensus. Q3 is positioned late because it's the question most likely to generate discussion about acceptable data loss — better to have all other context established first.
