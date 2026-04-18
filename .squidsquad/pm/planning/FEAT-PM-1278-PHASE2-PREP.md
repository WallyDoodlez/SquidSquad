# FEAT-PM-1278 Phase 2 Prep — Vault-Remember: Diff-Based Entity Extraction and Connection Mining

## Optimal Question Order

Questions should be discussed in this order based on dependency analysis:

1. **Q1** (activation trigger) -- foundational: determines when the entire feature runs, all other questions depend on this
2. **Q2** (script location) -- architectural: determines where code lives, affects Q4's implementation
3. **Q3** (connection mining location) -- architectural: determines vault-check vs vault-remember boundary
4. **Q4** (dev agent handling) -- scope: depends on Q1 (activation model) and Q2 (script structure) being settled first

Rationale: Q1 and Q2 are independent foundations that shape everything else. Q3 is a boundary decision that affects integration but not the core design. Q4 is a scope extension question that can be deferred or answered quickly once the core design is locked.

---

## Q1: When should entity extraction run?

**Category**: Behavior / Performance

> Should entity extraction run on EVERY non-quiet cycle or only when human messages are present? Running on every cycle wastes tokens scanning empty input. Running only on human-message cycles misses nothing but adds a detection step.

### Option A: Run on every non-quiet cycle

- **Pros**:
  - Simplest implementation -- no detection logic needed
  - Guaranteed to never miss human input
  - Consistent behavior every cycle
- **Cons**:
  - Wastes tokens on cycles with no human messages (the common case)
  - Entity extraction prompt runs against empty/irrelevant input
  - Adds ~500-1000 tokens of overhead even when there is nothing to extract

### Option B: Run only when human messages are detected (RECOMMENDED)

- **Pros**:
  - Zero token waste on cycles without human input
  - Aligns with the research finding that PM is the primary human-facing agent
  - Detection step is cheap -- check if Step 2 processed any human input this cycle (a simple boolean flag, no scanning needed)
- **Cons**:
  - Requires a detection mechanism (but this is trivial -- a flag set during Step 2 check-in processing)
  - Slightly more complex control flow

### Option C: Run on a configurable schedule (e.g., every N cycles)

- **Pros**:
  - Tunable cost/coverage tradeoff
  - Could batch-process multiple cycles of human input at once
- **Cons**:
  - Delayed extraction means vault updates lag behind human input
  - Adds a config knob for marginal benefit
  - Batching introduces complexity (which messages were already processed?)
  - Fundamentally wrong model -- frequency should be driven by input presence, not a timer

---

## Q2: Where should deterministic entity extraction code live?

**Category**: Scope / Architecture

> Should the deterministic entity extraction (pattern matching) live in a new script (vault_entity.py) or be added to vault_remember.py? Separate script follows the pattern of vault_check.py / vault_optimize.py separation. Combined keeps it simpler.

### Option A: New standalone script (vault_entity.py) (RECOMMENDED)

- **Pros**:
  - Follows existing convention: vault_check.py, vault_optimize.py, vault_remember.py are each single-concern scripts
  - Clear separation of concerns -- entity extraction is a distinct capability from reflection
  - Can be tested independently
  - Can be reused by dev agents later (Q4) without pulling in PM-specific reflection logic
  - Research already sketched the API: `extract <text>`, `compare <entity>`, `suggest-links <note-path>`
- **Cons**:
  - One more file to maintain
  - Slightly more complex import/invocation chain

### Option B: Add to vault_remember.py

- **Pros**:
  - Fewer files -- entity extraction is conceptually part of "remembering"
  - Shared access to write-budget and quiet-cycle logic already in vault_remember.py
- **Cons**:
  - vault_remember.py grows in scope -- it currently handles write budgets, quiet detection, and briefing budgets (operational concerns), not content analysis
  - Harder to reuse for dev agents without carrying vault_remember baggage
  - Mixes deterministic pattern matching with the reflection workflow

### Option C: Add to vault_check.py

- **Pros**:
  - vault_check.py already handles dedup-check, which is conceptually similar to entity matching
  - Entity comparison against vault is a "check" operation
- **Cons**:
  - vault_check.py is about validation and health, not extraction
  - Conflates "check if vault is healthy" with "extract new entities from text"
  - The `extract` command has no natural home here -- only `compare` fits

---

## Q3: Where should connection mining (wikilink suggestions) live?

**Category**: Architecture / Scope

> Should connection mining (wikilink suggestions) be part of vault-remember or vault-check? vault-check already handles link maintenance. Adding suggestion logic there keeps link concerns in one place. But vault-remember is the write-time step.

### Option A: Add to vault-check (RECOMMENDED)

- **Pros**:
  - vault-check Level 1 already runs after every vault-create/vault-update and auto-maintains the `links` frontmatter
  - All link-related logic stays in one place (resolution checking, link maintenance, and now suggestion)
  - Suggestion is conceptually a "check" -- "are there connections this note should have?"
  - No changes to vault-remember's scope
  - Research Section 6 notes this is "a natural extension of the existing vault-check infrastructure"
- **Cons**:
  - vault-check is currently reactive (validates after writes); suggestion is proactive (recommends new links)
  - Suggestion output needs to be actionable -- vault-check currently just warns

### Option B: Add to vault-remember

- **Pros**:
  - Connection mining happens at write time, which is vault-remember's domain
  - Can immediately act on suggestions (add wikilinks during the write)
  - Single workflow: extract -> compare -> write -> connect
- **Cons**:
  - vault-remember becomes responsible for both reflection AND link topology
  - Duplicates link-scanning logic already in vault-check
  - If a note is created outside vault-remember (e.g., manually), connections are missed

### Option C: Add to vault_entity.py (if Q2 picks Option A)

- **Pros**:
  - The research sketched `suggest-links <note-path>` as part of vault_entity.py's API
  - Keeps all new entity/connection logic in one script
- **Cons**:
  - Splits link concerns across two scripts (vault_check.py for maintenance, vault_entity.py for suggestion)
  - vault_entity.py becomes a multi-concern script (extraction + comparison + link suggestion)
  - Violates the single-concern convention that motivated separating vault_check from vault_optimize

---

## Q4: How to handle entity extraction for dev agents receiving human messages via issue comments?

**Category**: Scope / Compatibility

> How to handle entity extraction for dev agents who receive human messages via issue comments? Currently rare, but branch workflow PRs may include human review comments.

### Option A: PM-only for v1, defer dev agent extraction (RECOMMENDED)

- **Pros**:
  - Simplest implementation -- matches the research recommendation ("PM only for entity extraction")
  - PM already processes the vast majority of human messages (check-ins, approvals, discussions)
  - Issue comments from humans on dev tasks are rare and typically tactical (not entity-rich)
  - Can revisit if evidence shows missed entities from dev channels
- **Cons**:
  - Misses entity-rich PR review comments (e.g., human mentions a company name or tool in a code review)
  - If human starts interacting more with dev agents, gap widens

### Option B: Dev agents forward entity candidates to PM

- **Pros**:
  - PM remains the single entity extraction authority (consistent processing)
  - Dev agents only need a lightweight "detect and forward" mechanism
  - No vault-write logic needed in dev agent templates
- **Cons**:
  - Adds a cross-agent communication channel for entity forwarding
  - Latency: entity is not processed until PM's next cycle
  - Forwarding mechanism does not exist today -- needs design

### Option C: Dev agents run entity extraction independently

- **Pros**:
  - Immediate processing of human messages in dev context
  - No dependency on PM cycle timing
- **Cons**:
  - Duplicates entity extraction logic across all agent templates
  - Risk of concurrent vault writes from multiple agents on the same entity
  - Dev agents' vault-remember is tuned for reflection (patterns, learnings), not entity extraction
  - Increases template complexity for marginal benefit given the rarity of human messages to dev agents

---

## Summary of Recommendations

| Question | Category | Recommended | Rationale |
|----------|----------|-------------|-----------|
| Q1 | Behavior | **B** -- Only when human messages present | Zero waste, trivial detection via Step 2 flag |
| Q2 | Architecture | **A** -- New vault_entity.py | Follows single-concern convention, enables reuse |
| Q3 | Architecture | **A** -- Add to vault-check | All link logic in one place, natural extension |
| Q4 | Scope | **A** -- PM-only for v1, defer | Matches research, rare use case, revisit with data |
