# Vault Phase 3 Research: coleam00/second-brain-starter Analysis

**Source**: https://github.com/coleam00/second-brain-starter
**Date**: 2026-04-05
**Purpose**: Extract patterns for SquidSquad end-of-cycle reflection and vault-remember system
**Files analyzed**: architecture-reference.md, SKILL.md, README.md, example-my-second-brain-requirements.md, my-second-brain-requirements.md, repo tree

---

## A. When to Write: Memory Gating Criteria

The second-brain system uses a **two-stage gating** model: capture everything first, filter later.

### Stage 1: Capture Everything (Low Bar)
- **Daily logs** (`daily/YYYY-MM-DD.md`) are append-only. Every session flushes to them via the `SessionEnd` hook. No filtering at this stage — the philosophy is "capture first, curate later."
- The `PreCompact` hook also extracts "key decisions/facts" from the JSONL transcript before Claude's auto-compaction destroys context. This is a safety net, not a quality gate.

### Stage 2: Promote Selectively (High Bar)
- **Daily Reflection** (`memory_reflect.py`, runs daily at 8 AM) reviews yesterday's daily log and promotes only "important items (decisions, lessons, facts)" to `MEMORY.md`.
- Key constraint: **MEMORY.md must stay concise** because it is loaded into every conversation via the SessionStart hook. Size pressure creates natural selectivity.
- The architecture doc does NOT specify algorithmic criteria for "important" — this is delegated to LLM judgment during the reflection step.

### Noise Prevention
Their noise prevention is structural, not rule-based:
1. Daily logs absorb all noise freely (cheap storage, never injected in full)
2. Promotion to MEMORY.md is gated by a dedicated reflection pass
3. MEMORY.md size pressure forces curation (injected every session = bloat costs tokens)

**Gap we can improve on**: They define no explicit write/skip rules. The LLM decides during reflection with no criteria. We should provide structured reflection prompts with explicit categories.

---

## B. Reflection Mechanics

### Their Model: Time-Based (Nightly Batch)
- `memory_reflect.py` runs at a **fixed schedule** (8 AM daily), not event-triggered
- Reviews the previous day's daily log as a batch
- Promotes items to MEMORY.md using LLM judgment
- Metaphor from the architecture doc: "short-term experiences -> sleep consolidation -> long-term storage"

### The Three Lifecycle Hooks (Event-Based Capture, Not Reflection)
These are raw capture points, not reflection:

| Hook | Script | Trigger | Action |
|------|--------|---------|--------|
| SessionStart | `session-start-context.py` | Conversation init | Reads SOUL.md + USER.md + MEMORY.md + recent daily logs, injects into context |
| PreCompact | `pre-compact-flush.py` | Before auto-compaction | Extracts decisions/facts from JSONL transcript, appends to daily log |
| SessionEnd | `session-end-flush.py` | Session termination | Saves conversation context to daily log |

### Hook Configuration
Hooks are configured in `.claude/settings.json` (the file itself is not in the repo — it is generated during the PRD build phase). The pattern:

```
SessionStart  -> inject memory context (read)
PreCompact    -> save before context loss (write to daily log)
SessionEnd    -> flush session to daily log (write to daily log)
```

### SquidSquad Implication
Their nightly batch model does not map to our 30-minute cycles. We need **end-of-cycle reflection** (every 30 min), not end-of-day. But their two-step pattern (capture -> reflect -> promote) is the right skeleton.

---

## C. Memory Lifecycle: Three-Tier Architecture

```
Tier 1: Session Context (ephemeral)
  - Lives in conversation context only
  - Injected by SessionStart hook
  - Lost on session end unless captured

Tier 2: Daily Logs (append-only, medium-term)
  - Path: daily/YYYY-MM-DD.md
  - Written by PreCompact + SessionEnd hooks
  - Everything goes here — no filtering
  - Reviewed by daily reflection

Tier 3: Long-Term Memory (curated, permanent)
  - MEMORY.md — decisions, lessons, facts
  - SOUL.md — agent personality/behavioral rules (rarely changes)
  - USER.md — user preferences/integration config (occasionally changes)
```

### The Core Files

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `SOUL.md` | Agent personality, behavioral guidelines | Rarely (manual edit) |
| `USER.md` | User profile, integration settings, drafting criteria | Occasionally |
| `MEMORY.md` | Curated decisions, lessons, facts | Daily (via reflection) |
| `daily/YYYY-MM-DD.md` | Timestamped session logs | Every session end |

### Lifecycle Flow
```
Session events --> SessionEnd hook --> daily/YYYY-MM-DD.md (append)
                                            |
                                            v
                                  memory_reflect.py (daily @ 8AM)
                                            |
                                            v
                                       MEMORY.md (curated long-term)
```

### How This Maps to SquidSquad

| second-brain | SquidSquad equivalent |
|---|---|
| `SOUL.md` | `.squidsquad/<role>/CLAUDE.md` (agent instructions) |
| `USER.md` | `vault/areas/human-profile.md` |
| `MEMORY.md` | `vault/BRIEFING.md` + galaxy notes |
| `daily/YYYY-MM-DD.md` | `.squidsquad/<role>/iterations/iter-N.md` |
| `memory_reflect.py` | End-of-cycle vault-remember step (new) |

---

## D. Quality Control / Pruning / Dedup

### What They Do
1. **Size pressure on MEMORY.md**: Loaded every session, so bloat directly costs tokens. Natural pressure to keep concise.
2. **Daily log rotation**: Date-stamped files. Old logs are not loaded (only "recent" daily logs injected at SessionStart).
3. **Hybrid search as fallback**: SQLite + vector embeddings + FTS5 can retrieve from old daily logs on demand, even if not promoted to MEMORY.md.

### What They Do NOT Do (Gaps)
- **No explicit dedup** — same decision logged across multiple sessions may appear multiple times
- **No pruning rules** — MEMORY.md entries are never automatically removed
- **No confidence scoring** — all promoted memories treated equally
- **No decay** — old memories do not age out or get re-evaluated
- **No categories/tags** — MEMORY.md is a flat list (requirements template has categories, architecture does not enforce)
- **No size cap** — MEMORY.md can grow without bound

### SquidSquad Improvement Opportunities
We already have better quality infrastructure than they do:
- **Vault notes have frontmatter** with `confidence`, `status`, `type`, `tags` — built-in categorization
- **vault-check** validates structure and catches orphans/staleness
- **Wikilinks** create a graph that reveals connected vs. isolated knowledge
- **Galaxy notes are atomic** (one idea per note) vs. their monolithic MEMORY.md

What we should add for Phase 3:
- Dedup check on write (search vault before creating)
- Confidence decay (medium -> low after 60 days without update)
- BRIEFING.md token budget cap (e.g., 2000 tokens)

---

## E. Multi-Agent Considerations

### What They Have: Single-Agent Only
The second-brain-starter is designed for a **single user with a single agent**. No multi-agent memory sharing, no locking, no conflict resolution, no role-based access.

### Patterns That Could Extend to Multi-Agent
- **SOUL.md per agent** = each SquidSquad role already has its own CLAUDE.md
- **USER.md shared** = our `vault/areas/human-profile.md` (shared across roles)
- **MEMORY.md split** = our vault already splits into per-topic galaxy notes rather than one monolith
- **Daily logs per agent** = our `iterations/iter-N.md` per role already does this

### What Is Missing for Multi-Agent (We Must Build)
- Concurrent write protection (git merge handles most of this, but vault-check should detect conflicts)
- Memory visibility rules (which agents can write to which vault sections)
- Cross-agent memory propagation (when one agent learns something, how do others find it)
- Conflict resolution for contradictory memories (e.g., two agents disagree on a pattern)

Our vault already addresses most of these via git-native design: one-note-per-topic minimizes conflicts, append-only changelogs merge cleanly, and vault-search lets any agent find any note.

---

## F. What We Should Steal for SquidSquad

### Pattern 1: Three-Hook Lifecycle (ADAPT)

Their hooks map to our Ralph Loop steps:

```
Their SessionStart  --> Our Step 1c (resume from working state + read BRIEFING.md)
Their PreCompact    --> Our Step 1b (context pressure check, save state)
Their SessionEnd    --> Our Step 6 (cycle end — NEW: add reflection here)
```

For 30-min cycles, merge SessionEnd and Reflection into a single end-of-cycle step rather than deferring reflection to a separate nightly job.

### Pattern 2: Two-Tier Write Strategy (STEAL)

```
Tier 1: Cycle log (unfiltered, append-only)
  - Already exists: .squidsquad/<role>/iterations/iter-N.md
  - Everything from this cycle goes here
  - No change needed

Tier 2: Vault memories (curated, promoted)
  - NEW: end-of-cycle vault-remember step
  - Only items that pass the reflection filter
  - Uses existing vault-create/vault-update sub-skills
  - Path: .squidsquad/vault/galaxy/<type>-<descriptive-name>.md
```

### Pattern 3: MEMORY.md Size Pressure as Quality Gate (STEAL)

Their best quality-control mechanism is accidental: MEMORY.md is injected every session, so bloat costs tokens. Apply the same constraint:
- BRIEFING.md is injected at cycle start (already true)
- Cap BRIEFING.md at ~50 lines / ~2000 tokens (already specified)
- This forces agents to be selective about what goes in BRIEFING.md vs. galaxy notes
- Galaxy notes are discovered via vault-search, not injected — so they can grow freely

### Pattern 4: State Diffing from Heartbeat (ADAPT)

Their heartbeat uses `build_snapshot() -> diff_snapshot()` to avoid redundant notifications. Apply to cycle reflection:
- At cycle end, diff what changed vs. cycle start
- Only write memories about actual deltas, not status quo
- Prevents "nothing happened but I'll write something anyway"
- Implementation: compare iteration log to previous iteration — if nothing substantive happened (quiet cycle), skip reflection entirely

### Pattern 5: Structured Reflection Prompt (NEW — They Don't Have This)

They delegate reflection to unstructured LLM judgment. We should define explicit criteria. Proposed end-of-cycle reflection prompt:

```markdown
## End-of-Cycle Reflection (vault-remember)

Review this cycle's iteration log and answer:

1. **DECISIONS**: Were any decisions made? (architecture, pattern choice, trade-off)
   -> vault-create galaxy/decision-*.md [confidence: high if human-stated, medium if agent-decided]

2. **PATTERNS**: Were any reusable patterns discovered or confirmed?
   -> vault-create galaxy/pattern-*.md [confidence: medium]

3. **LEARNINGS**: Did anything fail or succeed unexpectedly?
   -> vault-create galaxy/learning-*.md [confidence: medium]

4. **HUMAN PREFERENCES**: Did the human express any preference, style, or value?
   -> vault-update areas/human-profile.md [confidence: high]

5. **PROJECT CONTEXT**: Did project goals, constraints, or architecture change?
   -> vault-update projects/<name>.md or vault-update BRIEFING.md

For each candidate memory, apply these gates:
- Already in vault? -> SKIP (dedup — use vault-search to check)
- Specific to this cycle only, no future value? -> SKIP (leave in iteration log)
- Would help a future agent in a fresh context? -> WRITE
- Contradicts existing vault note? -> UPDATE existing note, don't create duplicate
```

### Pattern 6: Git-Tracked Vault (IMPROVE ON THEIR DESIGN)

They use local markdown + SQLite RAG. We improve by using git as the storage layer:
- Full history via `git log` and `git blame`
- PR-visible vault changes (vault edits show in cycle commits)
- No separate database to maintain
- Merge conflicts are explicit and resolvable
- Vault is portable (clone the repo, get all knowledge)

Trade-off: no vector search. Mitigated by:
- Structured frontmatter enables grep-based search (already implemented in vault-search)
- Wikilink graph enables traversal-based discovery
- Future: FEAT-SKILL-062 adds SQLite/RAG layer as optional enhancement

---

## Architecture Comparison

| Aspect | coleam00/second-brain | SquidSquad Target |
|--------|----------------------|-------------------|
| Agent model | Single agent | Multi-agent (PM, Skill, QA, Designer, DM) |
| Cycle length | Session (variable) | 30 minutes (fixed) |
| Capture | Hooks → daily log | Iteration log (already exists) |
| Reflection | Nightly batch (8 AM) | Per-cycle (every 30 min, end of cycle) |
| Storage | Local markdown + SQLite RAG | Git-tracked markdown only |
| Quality gate | LLM judgment (unstructured) | Structured reflection prompt with dedup |
| Dedup | None | vault-search before write |
| Multi-agent | Not supported | Per-agent iteration logs + shared vault |
| Retrieval | Hybrid vector + keyword (SQLite) | grep + frontmatter + wikilinks (git-native) |
| Pruning | None | vault-check staleness detection (existing) |

---

## Concrete Recommendations for Phase 3 Implementation

### 1. Add `vault-remember` sub-skill to the Ralph Loop

Insert between Step 4 (Log Iteration) and Step 5 (Commit and Push). Only runs on non-quiet cycles.

```
Step 4  — Log Iteration (existing)
Step 4b — vault-remember (NEW)
Step 5  — Commit and Push (existing)
```

### 2. vault-remember logic

```
IF quiet cycle: SKIP entirely
IF cycle produced work:
  1. Read this cycle's iteration log
  2. Run structured reflection prompt (5 categories above)
  3. For each candidate:
     a. vault-search for existing coverage (dedup gate)
     b. If new and reusable: vault-create
     c. If updates existing: vault-update
     d. If already covered: skip
  4. If any vault writes touched project context: consider BRIEFING.md update
```

### 3. Budget constraint
- Max 2 vault writes per cycle (matches improvement scan's "max 2 items" precedent)
- Prevents runaway vault growth
- Forces prioritization of highest-value memories

### 4. Skip criteria (explicit noise prevention)
- Debugging steps that led nowhere -> iteration log only
- Status changes with no decision behind them -> skip
- Repeated observations already in vault -> skip (dedup)
- Transient blockers that resolved within the cycle -> skip

---

## Key Takeaway

The coleam00 architecture validates our core design: markdown files, lifecycle hooks, two-tier capture-then-promote. But it is built for a single passive agent with nightly reflection. SquidSquad needs the same skeleton with three upgrades:

1. **Cycle-frequency reflection** instead of nightly (30-min cycles demand it)
2. **Structured reflection criteria** instead of open-ended LLM judgment (5 categories with explicit gates)
3. **Multi-agent vault namespacing** with shared vault + per-agent iteration logs (already in place)
