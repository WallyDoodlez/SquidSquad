# FEAT-PM-475 Discussion Prep — Token Efficiency Audit

## Question Inventory

| # | Question | Category | Dependencies |
|---|----------|----------|-------------|
| Q4 | Acceptable minimum instruction density for reliable agent behavior? | behavior | None (foundational) |
| Q1 | Extract Label Taxonomy to a reference file? | scope | Depends on Q4 (density threshold informs how aggressively to extract) |
| Q2 | Remove boot-remote-agents from non-PM includes.yml? | scope | None |
| Q3 | Split vault-protocol into core + reference? | scope | Depends on Q4 (density threshold) |
| Q5 | Shorten subagent prompt templates in task-intake? | behavior | Depends on Q4 (density threshold) |

---

## Optimal Question Order

**Rationale**: Q4 is foundational — the answer to "how terse is too terse" gates decisions on Q1, Q3, and Q5. Q2 is independent and low-controversy (clear win). Order controversial/subjective questions last.

1. **Q4** — Minimum instruction density (foundational, gates other decisions)
2. **Q2** — Remove boot-remote-agents from non-PM roles (independent, low-controversy)
3. **Q1** — Extract Label Taxonomy (depends on Q4, medium controversy)
4. **Q3** — Split vault-protocol (depends on Q4, higher complexity)
5. **Q5** — Shorten subagent prompts (depends on Q4, most controversial — affects output quality of spawned agents)

---

## Q4: Acceptable minimum instruction density for reliable agent behavior?

**Category**: Behavior

**Why it matters**: Without a threshold, every trimming decision is a guess. Too terse = agents hallucinate or improvise. Too verbose = token waste. This answer sets the standard for Q1, Q3, and Q5.

### Option A: Comprehension test suite as the gate (RECOMMENDED)

Define "acceptable" empirically: after any template change, spawn a fresh agent and quiz it on 5-10 behavioral questions derived from the changed instructions. Pass threshold: 100% correct on safety-critical items, 80% on operational items.

- **Pros**: Objective, repeatable, catches real drift. Aligns with existing comprehension testing standard in project memory. No need to define a word-count threshold (behavior is what matters, not word count).
- **Cons**: Adds a verification step to every template change. Quiz design is itself subjective — bad quizzes give false confidence. Costs tokens to run the quiz agent.

### Option B: Word-count floor per instruction type

Set minimum word counts: safety rules min 50 words each, operational procedures min 30 words each, reference data min 10 words per item. Any reduction that drops below the floor is rejected.

- **Pros**: Simple, deterministic, easy to enforce in code review. No extra agent spawns needed.
- **Cons**: Arbitrary — a well-written 20-word instruction may outperform a poorly written 50-word one. Doesn't account for instruction complexity. May block valid improvements or allow bad ones.

### Option C: Dual threshold — word-count floor + comprehension spot-check

Combine B's word-count floors with A's comprehension testing, but only spot-check (test 2-3 questions per change, not a full suite). Full suite reserved for large changes.

- **Pros**: Balances speed and rigor. Word-count floor catches obvious over-trimming early. Spot-check catches behavioral issues without full test overhead.
- **Cons**: Two systems to maintain. Spot-check may miss edge cases that a full quiz would catch. Still has the arbitrary floor problem from Option B.

---

## Q2: Remove boot-remote-agents from non-PM includes.yml?

**Category**: Scope

**Why it matters**: 640 words of dead weight across 4 roles. The PM-only gate already prevents execution, but the instructions still consume tokens in every non-PM template.

### Option A: Remove from all non-PM includes.yml (RECOMMENDED)

Delete the `boot-remote-agents` entry from `qa`, `skill/dev`, `dm`, and `designer` includes.yml files. Only PM retains it.

- **Pros**: Saves 640 words (~832 tokens) immediately. Cleaner separation of concerns — non-PM agents don't even see boot instructions. Zero behavioral risk (the gate already makes it a no-op).
- **Cons**: If a future role needs boot capability, it must be re-added manually. Minor: requires touching 4 includes.yml files.

### Option B: Keep in all roles but add a "skip if not PM" one-liner

Replace the full 160-word sub-skill with a 1-line stub: "Boot-remote-agents: PM-only — skip this step."

- **Pros**: Documents the existence of the capability for all roles. Easy to re-enable by expanding the stub. Saves ~600 words (stub is ~10 words vs 160).
- **Cons**: Still wastes ~50 tokens per non-PM role on a stub that does nothing. Adds clutter to templates. Partially defeats the purpose of the cleanup.

### Option C: Keep as-is (no change)

Leave the full 160-word sub-skill in all roles with the PM-only gate.

- **Pros**: Zero risk. No migration work. Future roles automatically have boot capability if the gate is ever widened.
- **Cons**: 640 words of permanent waste. The gate pattern (include everywhere, check at runtime) is an anti-pattern when only one role uses it.

---

## Q1: Extract Label Taxonomy to a reference file?

**Category**: Scope / Compatibility

**Why it matters**: ~1,500 words saved across 5 roles. But agents currently have label names in their instructions — extracting means they either `cat` a file or rely on tracker.py error messages for correction.

### Option A: Extract to reference file, rely on tracker.py enforcement (RECOMMENDED)

Move the Label Taxonomy section (~300 words, ~40 lines) out of tracker-protocol into `references/docs/label-taxonomy.md`. Agents that need label info `cat` the file on demand. tracker.py already validates labels and returns errors for invalid ones, so agents self-correct.

- **Pros**: Saves ~1,500 words across 5 roles. Single source of truth for labels (reference file). tracker.py enforcement means agents rarely need to look up labels — they use the script's API. Labels change in one place instead of recomposing all templates.
- **Cons**: Agents lose passive awareness of available labels. First-time label use in a cycle requires a file read (adds ~300 tokens to that cycle's context). New roles must know to `cat` the reference file.

### Option B: Slim the taxonomy inline (keep names, remove descriptions)

Keep label names in tracker-protocol but remove the descriptions and examples. Reduce from ~300 words to ~80 words (just the label names in a compact list).

- **Pros**: Agents retain passive awareness of label names. No extra file reads needed. Saves ~1,100 words across 5 roles (less than Option A but still significant). No behavior change.
- **Cons**: Less savings than full extraction. Label names without descriptions may cause misuse (e.g., confusing `status:planned` with `status:approved`). Still duplicated across 5 roles.

### Option C: Keep as-is (no change)

Leave the full Label Taxonomy inline in tracker-protocol.

- **Pros**: Zero risk. Agents always have full label context. No migration needed.
- **Cons**: 1,500 words of redundancy across 5 roles. Any label change requires recomposing all templates.

---

## Q3: Split vault-protocol into core + reference?

**Category**: Scope / Performance

**Why it matters**: vault-protocol is 1,712 words per inclusion (included in PM and skill/dev = 3,424 words total). Splitting could save ~800 words per inclusion. But vault operations are complex — agents need to understand entity models and search modes to use the vault correctly.

### Option A: Split into vault-protocol-core + vault-protocol-reference

Create two sub-skills: `vault-protocol-core` (~900 words — operational rules: vault-create, vault-update, vault-check Level 1, rules, concurrent access) and `vault-protocol-reference` (~800 words — entity model table, search modes, check Level 2, note size guidance). PM and skill/dev include only core; reference is a file they `cat` when doing vault operations that need it.

- **Pros**: Saves ~800 words per inclusion (~1,600 total). Core operational rules stay inline where agents see them every cycle. Reference material is available on demand. Matches the existing vault-protocol / vault-protocol-slim pattern.
- **Cons**: Agents may skip vault-search or use incorrect entity types because they don't see the reference by default. Vault-check Level 2 becomes less discoverable. Two files to maintain instead of one. Risk of agents not knowing when to `cat` the reference.

### Option B: Compress vault-protocol inline (no split) (RECOMMENDED)

Rewrite vault-protocol to be more concise without splitting. Remove redundant examples, compress the entity model table into a one-liner per entity, shorten search mode descriptions. Target: ~1,200 words (save ~500 words per inclusion, ~1,000 total).

- **Pros**: No split complexity — single file, single inclusion. Agents still see all vault information every cycle. Easier to maintain. Moderate savings without the risk of agents missing reference material.
- **Cons**: Less savings than Option A. Still duplicated in PM and skill/dev. Requires careful rewriting to preserve clarity (comprehension testing needed).

### Option C: Keep as-is (no change)

Leave vault-protocol at 1,712 words per inclusion.

- **Pros**: Zero risk. Vault operations are complex and benefit from verbose instructions. No comprehension testing needed.
- **Cons**: 3,424 words total for a section that could be more concise. Contributes to the PM template being the heaviest at 14,373 tokens.

---

## Q5: Shorten subagent prompt templates in task-intake?

**Category**: Behavior / Performance

**Why it matters**: task-intake is the single largest sub-skill at 2,088 words. It contains 3 subagent prompt templates (research, discussion prep, test plan) at ~5-10 lines each. These prompts are instructions for spawned agents, not the host PM agent — trimming them risks subagent output quality.

### Option A: Keep subagent prompts as-is (RECOMMENDED)

Do not shorten the subagent prompt templates. They are already concise (5-10 lines each) and directly control subagent output quality. Focus token savings elsewhere.

- **Pros**: Zero risk to subagent output quality. Subagent prompts are a small fraction of task-intake's total word count (~150 words out of 2,088). The real verbosity is in process instructions around the prompts (artifact resume logic, Phase 2A/2B flow, open-in-editor flow), not the prompts themselves.
- **Cons**: Misses a potential savings area. Leaves task-intake as the largest sub-skill.

### Option B: Condense process instructions around the prompts (not the prompts themselves)

Keep subagent prompts intact but compress the surrounding process instructions: artifact resume logic, Phase 2A/2B orchestration, AskUserQuestion examples, open-in-editor flow. Target: reduce task-intake from 2,088 to ~1,500 words.

- **Pros**: Addresses the actual source of verbosity (process, not prompts). ~588 word savings. Subagent output quality preserved. Process instructions are for the PM agent (which has strong instruction-following), not for subagents.
- **Cons**: Process instructions contain safety-critical flows (artifact resume, approval gates). Compression risks PM skipping steps. Requires comprehension testing. Medium effort to rewrite.

### Option C: Replace subagent prompts with references to template files

Move subagent prompts to `references/templates/research-prompt.md`, `discussion-prep-prompt.md`, `test-plan-prompt.md`. PM reads the file before spawning the subagent.

- **Pros**: Saves ~150 words in task-intake per template (~450 total). Prompt templates become independently editable. Single source of truth for each prompt.
- **Cons**: Adds a file read before each subagent spawn (3 reads per full intake). Prompts are small — savings are minimal. Adds indirection that may cause PM to forget to read the file before spawning.

---

## Summary of Recommendations

| # | Question | Recommended | Savings | Risk |
|---|----------|-------------|---------|------|
| Q4 | Minimum instruction density | Option A: Comprehension test suite | N/A (methodology) | Low |
| Q2 | Remove boot-remote-agents from non-PM | Option A: Remove from non-PM includes | ~640 words | None |
| Q1 | Extract Label Taxonomy | Option A: Extract to reference file | ~1,500 words | Low |
| Q3 | Split vault-protocol | Option B: Compress inline (no split) | ~1,000 words | Medium |
| Q5 | Shorten subagent prompts | Option A: Keep as-is (focus elsewhere) | 0 words | None |

**Total estimated savings from recommended options**: ~3,140 words (~4,082 tokens), roughly **11% of total**.

If Option B for Q5 (condense process instructions) is also adopted after comprehension testing validates it: additional ~588 words, bringing total to ~3,728 words (~4,846 tokens, ~13%).
