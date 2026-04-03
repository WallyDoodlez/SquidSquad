# FEAT-SKILL-029 Phase 2 Prep — Open Question Analysis

## Optimal Question Order

Resolve in this order (dependencies first, controversial last):

1. **Q9** (Search Layer) — foundational infrastructure decision; affects vault-search design, Phase 2 scope, and every downstream query pattern
2. **Q12** (Lifecycle Hooks / Context Injection) — determines how vault context reaches agents; shapes vault-search usage patterns and boot sequence
3. **Q10** (Core Memory Files) — depends on Q12 (injection mechanism); defines what files exist and their "always-loaded" contract
4. **Q6** (Links Frontmatter) — architectural plumbing; affects vault-check, vault-create, and vault-update implementations
5. **Q8** (Confidence Field) — schema decision that shapes note templates and conflict resolution logic; low-controversy
6. **Q5** (Max Note Size) — simple threshold; needed before vault-check implementation but not blocking other questions
7. **Q2** (Wikilink Syntax) — affects vault-search grep patterns and Obsidian rendering; low-controversy
8. **Q3** (Vault README) — minor UX decision, no downstream dependencies
9. **Q1** (Inbox Processing Placement) — PM Ralph Loop integration point; depends on Q12 answer but mostly a scheduling question
10. **Q11** (Daily Logs + Reflection) — pipeline design that depends on Q10 (MEMORY.md) and Q1 (PM cycle structure)
11. **Q7** (Vault vs MEMORY.md Interaction) — cross-cutting concern; benefits from Q10/Q11/Q12 being settled first
12. **Q4** (Vault-Remember: Agent vs Hook) — most controversial (cost vs architecture tradeoff); least blocking since vault-remember is Phase 3

**Rationale**: Q9 and Q12 are load-bearing infrastructure choices that constrain everything else. Q10/Q6/Q8/Q5 are schema and template decisions needed before coding. Q2/Q3/Q1 are lower-stakes design choices. Q11/Q7/Q4 are pipeline and policy decisions that can be deferred or toggled later without rearchitecting.

---

## Q1 — Should inbox processing be a dedicated PM Ralph Loop step or integrated into Check In?

**Category**: Pipeline / Scheduling

### Option A: Dedicated new step (Step 2.5 — Process Vault Inbox)

| Pros | Cons |
|------|------|
| Clean separation of concerns; inbox processing is its own atomic unit | Adds cycle time to every PM cycle, even when inbox is empty |
| Easier to skip/disable independently | One more step in an already complex PM loop |
| Timing is predictable — always runs after pull, before feature work | PM context usage increases even on quiet cycles |

### Option B: Integrated into Step 2 (Check In With Human)

| Pros | Cons |
|------|------|
| Natural pairing: human input often generates captures that should be processed immediately | Muddies the "check in" step's responsibility |
| No additional cycle time — piggybacks on existing step | If human check-in is skipped (human absent), inbox processing also skips |
| Human can see vault captures in real-time during check-in | Harder to reason about independently; two concerns in one step |

### Option C: Conditional step — only runs when inbox is non-empty

| Pros | Cons |
|------|------|
| Zero overhead on quiet cycles (no inbox notes = step is skipped) | Slightly more complex loop logic (check-then-run) |
| Dedicated step when active, invisible when idle | Still adds structural complexity to the Ralph Loop |
| Best of both: clean separation without wasted cycles | Edge case: inbox check itself costs a file read |

**Recommended: Option C.** A conditional dedicated step gives clean separation without penalizing quiet cycles. The cost of checking whether `vault/inbox/` has files is trivial (one `ls`). When captures exist, PM gets a clean, focused processing phase. When empty, the step is invisible. This avoids coupling inbox processing to human check-in availability.

---

## Q2 — Should wikilinks use alias syntax or bare form only?

**Category**: Search / Syntax

### Option A: Bare form only (`[[note-name]]`)

| Pros | Cons |
|------|------|
| Grep-friendly — one pattern to search for all references | Less readable in Obsidian graph view and rendered notes |
| Zero ambiguity in link tracking and vault-check validation | Filenames must be descriptive enough to serve as display text |
| Simplest implementation — no parsing of pipe characters | Long filenames clutter inline text |

### Option B: Allow aliases (`[[note-name|Display Text]]`) from Phase 1

| Pros | Cons |
|------|------|
| Better readability in Obsidian and in raw markdown | Grep for backlinks must handle both `[[note]]` and `[[note|...]]` patterns |
| Standard Obsidian feature; human expects it | vault-check link validation becomes more complex |
| Decouples display from filename | Agents may use inconsistent aliases for the same note |

### Option C: Bare form in Phase 1, evaluate aliases in Phase 2+

| Pros | Cons |
|------|------|
| Simplest start; grep patterns are trivial | Migration cost if aliases are added later (existing links stay bare) |
| Avoids premature complexity in vault-check and vault-search | Obsidian readability is degraded in the interim |
| Can assess whether bare form is actually painful before adding aliases | Two-phase approach means vault-search must eventually handle both |

**Recommended: Option C.** The research doc already recommends this. Bare form keeps grep patterns simple (`grep -r "\[\[note-name\]\]"`), and vault-check does not need to parse pipe-separated display text. If bare form proves awkward after real usage, aliases can be added in Phase 2+ with a straightforward grep pattern update (`\[\[note-name(\|[^\]]+)?\]\]`).

---

## Q3 — Should the vault have a README.md homepage?

**Category**: UX / Maintenance

### Option A: Yes — vault-init creates a README.md with health stats and navigation

| Pros | Cons |
|------|------|
| Human gets an overview when opening vault in Obsidian | Must be kept up to date (another file for vault-optimize to maintain) |
| Can display vault health, note counts, recent updates | Stale README is worse than no README |
| Natural landing page for Obsidian's file explorer | Adds maintenance overhead to every vault-optimize cycle |

### Option B: Yes — static README.md with usage instructions only (no dynamic stats)

| Pros | Cons |
|------|------|
| Zero maintenance — written once during vault-init, never updated | No dynamic health info; human must run vault-optimize for stats |
| Warns human not to edit vault files directly | Less useful as a vault homepage |
| Serves as documentation, not a dashboard | May become inaccurate if vault structure evolves |

### Option C: No README.md — vault is self-documenting via Obsidian graph

| Pros | Cons |
|------|------|
| Zero maintenance overhead | No guardrails for human exploring the vault |
| Vault structure (IPARAG folders) is self-explanatory | Human may edit notes directly without knowing the consequences |
| Fewer files to manage | Misses opportunity to document the "do not edit directly" warning |

**Recommended: Option B.** A static README.md costs nothing to maintain and provides the critical "do not edit directly" warning. Dynamic stats are vault-optimize's job and do not belong in a file that agents might read into context. The README is written once during vault-init and only updated during major vault structure changes (upgrades).

---

## Q4 — Should vault-remember run as agent hooks or as a dedicated vault-agent?

**Category**: Architecture / Cost

### Option A: Hooks in each agent's Ralph Loop (current research recommendation)

| Pros | Cons |
|------|------|
| Zero additional Claude sessions — no cost increase | Adds instructions to every agent template (context usage) |
| Captures happen in-context (agent just did the work, has full context) | Each agent needs vault-remember trigger logic |
| No coordination overhead between vault-agent and work agents | Agents with tight context budgets may not want vault overhead |

### Option B: Dedicated vault-agent handles all vault operations

| Pros | Cons |
|------|------|
| Clean separation — work agents never touch the vault directly | Additional Claude session cost for every cycle |
| Vault-agent can be specialized (optimized context, focused instructions) | Loses in-context capture — vault-agent must reconstruct what happened from logs |
| Easier to disable/tune vault behavior (one agent to configure) | Adds latency: work happens in cycle N, capture happens in cycle N+1 or later |
| Avoids bloating work agent templates | Cross-agent communication overhead (vault-agent reads all trackers) |

### Option C: Hybrid — agents write to inbox (lightweight), vault-agent does processing + optimization

| Pros | Cons |
|------|------|
| Agents keep the lightweight inbox-write hook (minimal overhead) | Still requires a vault-agent session for processing |
| Processing and optimization are centralized (not just PM) | PM loses inbox processing responsibility (role confusion) |
| vault-agent can run less frequently (every 2-3 hours) | More moving parts than either pure approach |

**Recommended: Option A.** The research doc's hook approach is correct. Vault-remember as a hook is lightweight (write one inbox note, <1 second). The capture happens when the agent has maximum context about what just occurred. A dedicated vault-agent would need to reconstruct context from logs, losing fidelity. The cost of adding vault instructions to agent templates is ~200 tokens per agent — negligible compared to the context window. PM already handles inbox processing, which is the heavier operation.

---

## Q5 — What is the maximum note size before vault-check warns?

**Category**: Schema / Quality

### Option A: Warn at 500 lines for galaxy/ notes, no limit for area/ notes

| Pros | Cons |
|------|------|
| Enforces atomic knowledge principle in galaxy/ | 500 lines may be too generous — a 500-line "atomic" note is not atomic |
| Area notes can grow naturally (design systems, code conventions) | No limit on area notes means they can become unwieldy |
| Simple rule: one threshold for galaxy/, no limit elsewhere | Does not account for resource/ or project/ notes |

### Option B: Tiered limits — galaxy/ 200 lines, area/ 500 lines, project/ 300 lines, resource/ unlimited

| Pros | Cons |
|------|------|
| Enforces appropriate sizes per note type | More complex vault-check logic |
| Galaxy notes stay truly atomic (200 lines forces splitting) | Agents must know the limits per folder |
| Area notes get reasonable room to grow | May require frequent splitting, adding maintenance overhead |

### Option C: Single threshold (300 lines) for all vault notes, with explicit exceptions

| Pros | Cons |
|------|------|
| Simple single rule, easy to remember and enforce | Some area notes legitimately need >300 lines |
| vault-check implementation is trivial (one comparison) | Exceptions list adds complexity back |
| Forces all notes toward conciseness | May create churn as agents split notes unnecessarily |

**Recommended: Option B.** Tiered limits match the purpose of each folder. Galaxy notes should be atomic (one idea = 200 lines max). Area notes are living documents that accumulate over time (500 lines max). Project notes are summaries (300 lines max). Resource notes are references that may be long (no limit, but vault-optimize can flag very large ones). The implementation cost is minimal — vault-check reads the folder path and applies the appropriate threshold.

---

## Q6 — Should the `links` frontmatter field be auto-maintained or manually curated?

**Category**: Architecture / Automation

### Option A: Auto-maintained (vault-check extracts wikilinks from content and updates frontmatter)

| Pros | Cons |
|------|------|
| Always accurate — no drift between content links and frontmatter | vault-check must parse markdown content (regex for `[[...]]`) |
| Enables fast link queries without reading note content | Frontmatter changes on every write (noisy git diffs) |
| Single source of truth for the link graph | Circular: vault-check modifies the file it is checking |

### Option B: Manually curated (agents add links to frontmatter when creating/updating notes)

| Pros | Cons |
|------|------|
| vault-check is read-only (validation only, no writes) | Drift is guaranteed — agents will forget to update frontmatter |
| Git diffs are cleaner (frontmatter only changes when agents explicitly update) | Two sources of truth: content wikilinks vs frontmatter links |
| Simpler implementation | vault-search cannot trust frontmatter for link traversal |

### Option C: Remove `links` from frontmatter entirely — derive link graph from content at query time

| Pros | Cons |
|------|------|
| Single source of truth (content wikilinks only) | Every link query must scan note content (slightly slower) |
| No drift possible — there is nothing to drift from | Cannot do fast frontmatter-only queries for link graph |
| Simplest note template (fewer frontmatter fields) | Loses the "quick glance at frontmatter to see connections" benefit |
| Matches how Obsidian itself works (backlinks from content, not frontmatter) | |

**Recommended: Option C.** Remove `links` from frontmatter. Obsidian itself derives its graph from content wikilinks, not from metadata fields. Grep is fast enough to extract `[[...]]` patterns from note content at query time. This eliminates an entire class of drift bugs and simplifies both the template and vault-check. The "quick glance" benefit is not worth the maintenance cost — agents do not glance at frontmatter, they search.

---

## Q7 — How should the vault interact with `.claude/projects/*/MEMORY.md`?

**Category**: Context Management / Integration

### Option A: Intentionally separate — vault and MEMORY.md serve different purposes

| Pros | Cons |
|------|------|
| Clean separation: MEMORY.md = Claude Code's memory, vault = SquidSquad's memory | Human must maintain two knowledge systems |
| No sync logic needed | Same preference may be recorded in both places, diverging over time |
| Each system evolves independently | Agents reading MEMORY.md may miss vault context and vice versa |
| MEMORY.md is auto-injected by Claude Code; vault requires explicit search | |

### Option B: One-way sync — vault-remember also writes key items to MEMORY.md

| Pros | Cons |
|------|------|
| Important decisions and preferences surface in every Claude session (not just SquidSquad) | MEMORY.md format is simple (bullet points); vault notes are richer |
| Non-SquidSquad Claude sessions benefit from institutional knowledge | Sync logic adds complexity; must decide what "key items" means |
| Human gets a condensed view in MEMORY.md | MEMORY.md could become bloated with vault syncs |
| Vault remains the source of truth; MEMORY.md is a projection | Write conflicts if human also edits MEMORY.md |

### Option C: Vault replaces MEMORY.md — migrate existing memory entries to vault, stop using MEMORY.md

| Pros | Cons |
|------|------|
| Single source of truth for all institutional knowledge | MEMORY.md is auto-injected by Claude Code; vault is not |
| No sync, no drift, no duplication | Non-SquidSquad Claude sessions lose memory context |
| Vault's richer structure (typed, tagged, linked) subsumes MEMORY.md | Cannot control Claude Code's MEMORY.md injection behavior |
| | Breaking change for human's existing workflow |

**Recommended: Option A.** Keep them intentionally separate. MEMORY.md is Claude Code's native mechanism — it is auto-injected into every session, works outside SquidSquad, and follows a simple bullet-point format. The vault is SquidSquad's structured institutional memory — typed, tagged, linked, and agent-maintained. They serve different scopes. Attempting to sync them creates maintenance burden and drift risk. If the human wants something in both, they can add it manually. Over time, if MEMORY.md entries become redundant with vault content, the human can prune MEMORY.md.

---

## Q8 — Should vault notes support a `confidence` field?

**Category**: Schema / Quality

### Option A: Yes — add `confidence: high | medium | low` to frontmatter

| Pros | Cons |
|------|------|
| Agents can weigh conflicting information (high-confidence wins) | Agents must assess confidence at capture time (subjective judgment) |
| Human-confirmed items get `high`, agent-inferred get `low` — clear signal | Adds a field to every note template |
| vault-search can filter by confidence for high-stakes decisions | Confidence may not be updated when new evidence arrives |
| Supports graceful degradation of inferred knowledge | Three-level scale may be too coarse or too fine |

### Option B: No — use `source` field to imply confidence

| Pros | Cons |
|------|------|
| Simpler template — fewer fields | Agents must infer confidence from source, which is indirect |
| Source already exists in research doc's template design | "Human said" vs "agent observed" is a rough proxy, not a real confidence score |
| No subjective confidence assessment needed | Cannot filter by confidence in vault-search |

### Option C: Yes, but only for galaxy/ notes (decisions, patterns, learnings)

| Pros | Cons |
|------|------|
| Confidence is most relevant for galaxy/ notes (competing decisions, evolving patterns) | Inconsistent schema across note types |
| Area notes and project notes are inherently high-confidence (curated by owner) | Agents must remember which note types have the field |
| Reduces template bloat for non-galaxy note types | vault-check must handle two template schemas |

**Recommended: Option A.** Add the confidence field to all vault notes. The cost is one frontmatter line. The benefit is significant: when an agent finds two conflicting decisions, confidence provides a clear tiebreaker. Default to `medium` at creation. Set to `high` when the human explicitly confirms. Set to `low` for agent-inferred observations. vault-remember can set confidence automatically based on trigger type (human statement = high, agent observation = low). This is cheap to add now and expensive to retrofit later.

---

## Q9 — What search layer should SquidSquad use?

**Category**: Search / Infrastructure (NEW — from second architecture reference)

### Option A: Pure grep (COG approach, zero infrastructure)

| Pros | Cons |
|------|------|
| Zero dependencies — ripgrep is already available everywhere | No semantic search — keyword mismatch misses relevant notes |
| No embedding models, no SQLite, no vector math | Cannot rank results by relevance (all matches are equal) |
| Fastest possible implementation — vault-search is 20 lines of bash | As vault grows, keyword-only search returns too many or too few results |
| Matches COG philosophy perfectly | No fuzzy matching — "error handling" does not find "exception management" |
| Battle-tested in SquidSquad's existing codebase search patterns | |

### Option B: SQLite hybrid RAG from Phase 1 (sqlite-vec + FTS5 + FastEmbed ONNX)

| Pros | Cons |
|------|------|
| Semantic search from day one — finds conceptually related notes | Adds infrastructure: SQLite DB, embedding model (ONNX), vector index |
| Hybrid scoring (0.7 vector + 0.3 keyword) is best-of-both-worlds | FastEmbed ONNX requires Python environment and model download (~100MB) |
| FTS5 full-text search is better than grep (tokenization, ranking, stemming) | Index must be kept in sync with vault files (write-through or rebuild) |
| SQLite is embedded (no server), fits single-developer use case | Violates COG philosophy (adds non-markdown infrastructure) |
| Relevance ranking reduces context pressure (top-K, not all matches) | Increases setup complexity for new installs |
| | Embedding quality depends on model choice; small ONNX models may underperform |

### Option C: Start with grep, migrate to SQLite hybrid RAG in a later phase

| Pros | Cons |
|------|------|
| Phase 1-3 stay simple and infrastructure-free | Migration cost: vault-search interface must be abstracted from day one |
| Proves the vault concept before adding search complexity | Grep limitations may frustrate users before the migration happens |
| SQLite RAG can be introduced as FEAT-SKILL-062 or a new feature when vault reaches 500+ notes | Two implementations to maintain during migration period |
| Follows SquidSquad's "each phase independently valuable" principle | Delaying semantic search means early vault usage may feel "dumb" |
| Grep performance is fine for <500 notes (research doc confirms this) | |

**Recommended: Option C.** Grep is sufficient for Phase 1-3 when the vault is small (<500 notes). The research doc already confirms grep/ripgrep handles thousands of files in milliseconds. Adding SQLite + embeddings in Phase 1 would be premature optimization that violates COG philosophy and increases setup friction. However, the vault-search sub-skill interface should be designed as an abstraction layer from day one, so the underlying search implementation can be swapped from grep to SQLite RAG later without changing how agents call vault-search. The migration to hybrid RAG becomes its own feature when the vault reaches a scale where keyword search fails to surface relevant results. The 500-note threshold from the research doc is a good trigger.

---

## Q10 — Should the vault include always-loaded core memory files (USER.md, MEMORY.md)?

**Category**: Context Management (NEW — from second architecture reference)

### Option A: Yes — add USER.md + MEMORY.md as always-loaded vault files injected at boot

| Pros | Cons |
|------|------|
| Every agent starts with full human context — no cold-start search needed | Adds to every agent's context budget (~500-1000 tokens per file) |
| Mirrors the second reference architecture's proven pattern | Overlaps with existing `areas/human-profile.md` (USER.md) |
| MEMORY.md as condensed active context prevents agents from missing critical info | Two memory systems (vault MEMORY.md + Claude Code MEMORY.md) — confusing naming |
| Lifecycle hooks already exist to inject these at session start | Content must be kept very small to justify always-loading |

### Option B: No separate files — use existing vault structure (areas/human-profile.md serves as USER.md)

| Pros | Cons |
|------|------|
| No new file types; human-profile.md already covers "who is the human" | areas/human-profile.md may grow too large for always-loading |
| No naming confusion with Claude Code's MEMORY.md | No condensed "active context" file — agents must search for current priorities |
| Vault structure stays pure IPARAG | Misses the "nightly reflection promotes important items" pattern |
| Fewer files to maintain | Cold start requires vault-search to find relevant context |

### Option C: Add only MEMORY.md (concise active context) — USER.md is areas/human-profile.md

| Pros | Cons |
|------|------|
| Gets the high-value piece (active context injection) without redundant USER.md | MEMORY.md naming still overlaps with Claude Code's MEMORY.md |
| areas/human-profile.md already serves as USER.md — no duplication | Must define strict size limit for MEMORY.md to keep it always-loadable |
| MEMORY.md acts as a "briefing document" — top 10-20 items every agent needs | One more file to maintain and keep current |
| Clean separation: MEMORY.md = "what is active now", areas/ = "what is always true" | |

**Recommended: Option C.** Add a vault-level `MEMORY.md` (or name it `BRIEFING.md` to avoid collision with Claude Code's MEMORY.md) as a concise active-context file. Keep it under 50 lines / 1000 tokens. It contains: current milestone focus, top 3 active decisions, any human preferences that override defaults, and blockers. This is the "briefing" that every agent gets at boot via lifecycle hooks. `areas/human-profile.md` serves as the USER.md equivalent — no need to duplicate it. The briefing file is maintained by PM during inbox processing (promote important items, demote completed ones).

---

## Q11 — Should SquidSquad adopt daily logs + reflection pipeline?

**Category**: Pipeline / Knowledge Management (NEW — from second architecture reference)

### Option A: Yes — adopt daily append-only logs + nightly reflection to MEMORY.md/BRIEFING.md

| Pros | Cons |
|------|------|
| Chronological capture ensures nothing is lost | SquidSquad already has iteration logs per agent — this adds another log layer |
| Nightly reflection is a natural "promote to long-term memory" pipeline | Reflection requires a scheduled agent run (cost) |
| Daily logs are a debugging goldmine (what happened when) | Daily files accumulate fast (365 files/year) |
| Matches the second reference architecture's proven pattern | Duplication: iteration logs + daily logs capture overlapping info |

### Option B: No — existing iteration logs are sufficient; vault-remember handles knowledge promotion

| Pros | Cons |
|------|------|
| No new log infrastructure — iteration logs already capture per-cycle activity | Iteration logs are per-agent, not unified — no single "what happened today" view |
| vault-remember already promotes important observations to the vault | No "reflection" step that consolidates daily activity into long-term memory |
| Fewer files, less maintenance | Important context may be buried across 6 agent iteration logs |
| SquidSquad's existing architecture handles this need | Misses the chronological daily narrative that aids debugging |

### Option C: Hybrid — unify iteration logs into a daily digest, add reflection step to PM cycle

| Pros | Cons |
|------|------|
| PM already reads all agent trackers — generating a daily digest is natural | Adds a step to PM's cycle (digest generation) |
| Daily digest replaces scattered iteration logs with one unified view | Must define when "end of day" occurs (timezone, last cycle, etc.) |
| Reflection step in PM's cycle promotes key items to BRIEFING.md | Digest generation has a cost (reading all iteration logs, summarizing) |
| No new log files — digest IS the iteration log for the day | PM cycle becomes even more complex |
| Bridges SquidSquad's existing patterns with the second reference's approach | |

**Recommended: Option B.** SquidSquad already has iteration logs per agent and vault-remember for knowledge promotion. Adding daily logs creates redundancy. The existing pattern works: agents log per-cycle activity in iteration logs, vault-remember captures noteworthy observations to the inbox, PM processes inbox into vault notes. The "reflection" pattern is valuable but is effectively what PM's inbox processing already does — consolidating captures into structured vault notes. If a unified daily view is needed later, it can be generated from iteration logs on demand (a reporting feature, not a pipeline change).

---

## Q12 — How should vault context be injected into agent sessions?

**Category**: Context Management / Lifecycle (NEW — from second architecture reference)

### Option A: Inject at session start via lifecycle hooks (SOUL.md + BRIEFING.md)

| Pros | Cons |
|------|------|
| Every agent starts with essential context — no cold start | Fixed context cost at every boot (~1000-2000 tokens) |
| Lifecycle hooks already exist in SquidSquad | Injected context may be irrelevant for some cycles |
| Matches second reference architecture's proven pattern | Must keep injected files small to avoid context pressure |
| Consistent baseline — all agents share the same foundational context | If injected files are stale, every agent starts with stale context |

### Option B: Load on-demand — agents search vault when they need context

| Pros | Cons |
|------|------|
| Zero context overhead on cycles that do not need vault context | Cold start on every task — agent must search before it can act |
| Agents only load what is relevant to their current task | Search may miss important context (keyword mismatch) |
| No stale-injection risk — always reads latest vault state | Inconsistent context across agents (each searches differently) |
| Maximizes available context window for actual work | Repeated vault searches across cycles waste tokens |

### Option C: Hybrid — core files at startup, deeper vault queries on-demand

| Pros | Cons |
|------|------|
| Best of both: baseline context + targeted deep queries | Slightly more complex boot sequence |
| BRIEFING.md (50 lines) at boot is cheap; vault-search for specifics is precise | Must define what is "core" vs "on-demand" |
| Agents never start completely cold, but also do not load unnecessary context | Two code paths for context loading |
| Matches SquidSquad's existing pattern (CLAUDE.md is injected at boot, deeper files read on demand) | |

**Recommended: Option C.** This matches SquidSquad's existing architecture. Agents already boot with CLAUDE.md (role instructions) injected at session start — adding BRIEFING.md (~50 lines of active context) is a natural extension. For deeper vault queries (specific decisions, patterns, learnings), agents use vault-search on demand when their current task requires it. This keeps boot cost low (~1000 tokens for BRIEFING.md) while ensuring agents are never completely cold. SOUL.md (FEAT-SKILL-059) would also be injected at boot once it ships, completing the SOUL + BRIEFING duo.

---

## Summary of Recommendations

| Question | Category | Recommended | Key Rationale |
|----------|----------|-------------|---------------|
| Q1 | Pipeline | **C — Conditional dedicated step** | Clean separation, zero overhead on quiet cycles |
| Q2 | Search/Syntax | **C — Bare form Phase 1, evaluate later** | Keep grep simple; aliases are a refinement, not a necessity |
| Q3 | UX | **B — Static README** | Zero maintenance, provides "do not edit" warning |
| Q4 | Architecture | **A — Hooks in each agent** | In-context capture beats reconstructed capture; no extra cost |
| Q5 | Schema | **B — Tiered limits per folder** | Matches note purpose; galaxy=atomic, area=living doc |
| Q6 | Architecture | **C — Remove links from frontmatter** | Single source of truth; grep derives links from content |
| Q7 | Integration | **A — Intentionally separate** | Different scopes, different mechanisms; sync creates drift |
| Q8 | Schema | **A — Add confidence field** | Cheap to add now, expensive to retrofit; enables conflict resolution |
| Q9 | Search | **C — Grep now, SQLite RAG later** | COG philosophy for <500 notes; abstract the interface for future swap |
| Q10 | Context Mgmt | **C — Add BRIEFING.md only** | High-value active context injection without USER.md duplication |
| Q11 | Pipeline | **B — Existing iteration logs sufficient** | vault-remember + PM inbox processing already covers this need |
| Q12 | Lifecycle | **C — Hybrid injection** | Core files at boot + on-demand deep queries; matches existing patterns |

### Decisions to Lock Before Phase 1 Implementation

1. **Vault-search is grep-only in Phase 1-3** but the sub-skill interface must be search-backend-agnostic (Q9)
2. **Remove `links` from frontmatter** — derive link graph from content wikilinks (Q6)
3. **Add `confidence` field to all vault note templates** (Q8)
4. **Tiered note size limits**: galaxy 200, area 500, project 300, resource unlimited (Q5)
5. **Bare wikilinks only** (`[[note-name]]`, no aliases) in Phase 1 (Q2)
6. **BRIEFING.md** (~50 lines) injected at agent boot via lifecycle hooks (Q10 + Q12)
7. **Vault and MEMORY.md are intentionally separate systems** (Q7)
