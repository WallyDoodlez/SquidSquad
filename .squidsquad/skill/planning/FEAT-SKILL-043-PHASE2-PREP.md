# FEAT-SKILL-043 Phase 2 Prep — Open Question Analysis

## Optimal Question Order

Resolve in this order (dependencies first, controversial last):

1. **Q4** (Agent Discovery) — foundational; Q2/Q3/Q5 all depend on knowing how QA finds its targets
2. **Q5** (Loop Interval) — low-controversy, but needed before template design begins
3. **Q3** (qa-log.md Location) — migration decision that shapes file layout before coding starts
4. **Q2** (Fallback Structure) — template organization depends on Q3/Q4 answers
5. **Q1** (Bug Filing Authority) — most controversial (human-in-the-loop policy), least blocking for initial scaffolding

**Rationale**: Q4 and Q5 are infrastructure decisions that affect every other file. Q3 and Q2 are structural choices that shape the template layout. Q1 is a policy decision that can be toggled later without rearchitecting.

---

## Q1 — Should QA file bugs directly for test-discovered failures?

**Category**: Scope / Policy (human-in-the-loop boundary)

### Option A: QA files directly for all findings (no human approval)

| Pros | Cons |
|------|------|
| Fastest feedback loop; bugs filed same cycle they are discovered | Human loses visibility into what gets filed |
| Matches QA's role as an independent verification agent | Subjective findings (coherence issues) may produce false-positive bugs |
| No round-trip through PM saves 1-2 cycles per bug | Dev agents may get noisy bug backlog from overzealous QA |

### Option B: QA files directly for objective failures only; flags subjective findings via Discussion

| Pros | Cons |
|------|------|
| Clear bright line: test pass/fail = objective, everything else = flagged | Requires QA to classify findings as objective vs. subjective |
| Human stays in the loop for judgment calls | Slightly more complex QA template (two code paths) |
| Keeps bug tracker high-signal | Subjective findings may sit in Discussion unaddressed |

### Option C: QA always uses Bug Discussion Flow (human approval required)

| Pros | Cons |
|------|------|
| Human approves every bug — maximum control | Adds 1-2 cycle latency for every bug, even obvious test failures |
| Consistent with PM's existing Bug Discussion Flow | Defeats the purpose of an independent QA agent |
| No risk of false-positive bugs in tracker | QA becomes a suggestion engine rather than a verification agent |

**Recommended: Option B.** This is the research doc's own recommendation and it strikes the right balance. E2E test failures are objective (the test either passes or fails) so QA should file immediately. Subjective findings (spotting inconsistencies while reading files) should be flagged in Discussion for PM to surface to the human. This keeps the bug tracker high-signal while preserving QA's autonomy for its core job.

---

## Q2 — Should PM's QA-absent fallback be a separate include or inline?

**Category**: Architecture (template organization)

### Option A: Separate include (`pm-specific/qa-fallback.md`)

| Pros | Cons |
|------|------|
| PM template stays lean (~200 lines without fallback) | One more file to maintain and keep in sync |
| Fallback logic is self-contained and testable in isolation | Conditional include adds composition engine complexity |
| Clean separation: PM-only concerns vs. QA-replacement concerns | Developers must check two files to understand PM behavior |
| Matches sub-skill architecture pattern (FEAT-SKILL-030) | |

### Option B: Inline in PM template with conditional block

| Pros | Cons |
|------|------|
| Single file — everything about PM is in one place | PM template stays large (~330 lines, same as today) |
| No composition engine complexity | Conditional block is ~100 lines of "dead code" when QA is present |
| Easier to read linearly | Violates sub-skill decomposition philosophy |

### Option C: Two separate PM templates (pm-with-qa.md, pm-standalone.md)

| Pros | Cons |
|------|------|
| No conditional logic at all — each template is simple | Two templates to maintain; drift risk is high |
| Composition engine picks the right one at setup time | Upgrade flow must detect which template is active |
| Each template is optimally sized for its scenario | Violates DRY — shared PM logic duplicated across both |

**Recommended: Option A.** The sub-skill architecture (FEAT-SKILL-030) already established the include pattern. A conditional include (`qa-fallback.md` loaded only when `.squidsquad/qa/` is absent) keeps the PM template clean and follows existing conventions. The ~100 lines of verification logic are substantial enough to warrant their own file.

---

## Q3 — Should qa-log.md stay in pm/ or move to qa/?

**Category**: Migration (file ownership and history)

### Option A: QA creates new `qa/qa-log.md`; PM's `pm/qa-log.md` preserved as history

| Pros | Cons |
|------|------|
| Clean ownership: QA owns its own file from day one | Two qa-log files exist in the repo (potential confusion) |
| No file move — git blame on old entries preserved | PM's old qa-log.md becomes a dead file (no new writes) |
| Simple migration: QA starts fresh, PM stops writing | Searching for QA history requires checking two locations |
| Matches "QA is a new agent" mental model | |

### Option B: Move `pm/qa-log.md` to `qa/qa-log.md` via git mv

| Pros | Cons |
|------|------|
| Single file for all QA history | git mv may or may not preserve blame (depends on similarity detection) |
| No dead files left behind | PM must be updated atomically with the move |
| Clean directory structure | Migration step is more complex (must happen in upgrade flow) |
| | Breaks any hardcoded paths referencing pm/qa-log.md |

### Option C: QA writes to `pm/qa-log.md` (shared location)

| Pros | Cons |
|------|------|
| No migration needed at all | Violates agent directory ownership (QA writing to pm/) |
| Single location for all history | Confusing: file is in pm/ but QA writes it |
| Zero breaking changes | Does not scale if QA gets its own directory for other files |

**Recommended: Option A.** Clean break is the right call. QA is a new agent with its own directory; it should own its files from the start. The old `pm/qa-log.md` is preserved with full git history for auditing. PM stops writing to it when QA is present (PM's QA-absent fallback would continue writing to `pm/qa-log.md` if QA is absent, maintaining backward compatibility). The brief period of "two files" resolves naturally as the old one ages out of relevance.

---

## Q4 — How does QA discover which agents to scan?

**Category**: Architecture (agent discovery mechanism)

### Option A: Read `Dev Agents` from config.md + check directory existence for designer

| Pros | Cons |
|------|------|
| Consistent with how PM and DM already discover agents | Config.md can get out of sync with actual directories |
| No new mechanism to implement or document | Two discovery methods (config for dev, directory for designer) — slight inconsistency |
| Already tested and working in production | Adding a new agent type requires updating the discovery logic |
| Minimal code in QA template | |

### Option B: Pure directory scan (list `.squidsquad/*/` directories, exclude pm/qa/dm)

| Pros | Cons |
|------|------|
| Always in sync — no config drift possible | Must maintain an exclusion list (pm, qa, dm) |
| Works automatically when new agent types are added | Stale directories (deleted agents) would still be scanned |
| Single discovery mechanism for all agent types | Breaks the convention PM/DM already use |
| | Harder to control scan order or priority |

### Option C: New config.md section listing all scannable agents explicitly

| Pros | Cons |
|------|------|
| Explicit is better than implicit — every agent listed | Yet another config.md section to maintain |
| Supports future per-agent configuration (scan frequency, priority) | Requires config.md schema change |
| Single source of truth | Over-engineered for current needs (1-2 dev agents typical) |
| | Drift risk between config and actual directories |

**Recommended: Option A.** This is the established pattern. PM and DM both use `Dev Agents` from config.md plus directory checks for designer. QA should use the same mechanism for consistency. Introducing a new discovery mechanism would create a maintenance burden and diverge from proven patterns. If the discovery mechanism needs improvement later, it should be improved for all agents at once.

---

## Q5 — What is QA's default loop interval?

**Category**: Pipeline (operational cadence)

### Option A: Same global interval as all agents (from config.md `Iteration Interval > Minutes`)

| Pros | Cons |
|------|------|
| Simple — one interval for the whole system | QA may need different cadence than dev (faster when lots pending, slower when idle) |
| Consistent behavior across all agents | Cannot tune QA independently without affecting dev/PM |
| Already implemented via Step 1d Interval Sync | Suboptimal if QA is bottleneck (can't speed up just QA) |
| No config.md schema changes needed | |

### Option B: Per-agent interval in config.md

| Pros | Cons |
|------|------|
| Each agent tuned to its workload | Config.md schema change required |
| QA can run faster during heavy verification periods | More complexity for users to configure |
| Dev agents can run slower when QA is fast | Interval Sync logic must change for all agents |
| | Over-engineered for most installs (1-2 agents) |

### Option C: QA uses 2x the global interval (runs half as often)

| Pros | Cons |
|------|------|
| QA runs less often, saving resources when verification is light | Arbitrary multiplier — not responsive to actual workload |
| Simple to implement (read interval, multiply by 2) | Slower verification when features are waiting |
| No config changes needed | Hard to justify the specific multiplier |
| | Inconsistent with other agents' behavior |

**Recommended: Option A.** Use the global interval. QA's workload is naturally self-regulating: when there are no `Pending Test` features or `Fixed` bugs, QA's cycle is a quick scan and skip (quiet cycle). When verification work exists, QA processes it at the same cadence as other agents. Per-agent intervals (Option B) can be added later as a separate feature if real-world usage shows QA needs independent tuning. Starting simple and adding complexity only when needed is the right approach.

---

## Summary Table

| Question | Category | Recommended | Key Rationale |
|----------|----------|-------------|---------------|
| Q4 | Architecture | Option A (config + dir check) | Consistency with PM/DM discovery |
| Q5 | Pipeline | Option A (global interval) | Simple, self-regulating, extend later if needed |
| Q3 | Migration | Option A (new file, preserve old) | Clean ownership, no history loss |
| Q2 | Architecture | Option A (separate include) | Sub-skill pattern, keeps PM template lean |
| Q1 | Scope/Policy | Option B (direct for objective, flag subjective) | Balances autonomy with human control |
