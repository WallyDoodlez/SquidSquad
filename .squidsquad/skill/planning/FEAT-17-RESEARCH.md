# FEAT-17 Research: Vault Phase 3 — vault-remember + End-of-Cycle Reflection

**Date**: 2026-04-05
**Researcher**: PM research agent
**Feature**: #17 — Vault Phase 3: vault-remember + end-of-cycle reflection
**Prior art**: `.squidsquad/skill/planning/VAULT-P3-SECOND-BRAIN-RESEARCH.md` (coleam00 analysis)

---

## 1. Codebase Impact

### Files That Need Changes

| File / Location | Change Type | Description |
|---|---|---|
| `references/sub-skills/common/vault-protocol.md` | **Extend** | Add vault-remember sub-section documenting the reflection protocol, write budget (max 2/cycle), skip criteria, and structured reflection prompt |
| `references/sub-skills/common/iteration-log.md` | **Extend** | Add vault-remember invocation after logging, before git-commit. Currently 18 lines — add ~5 lines calling the new step |
| `references/sub-skills/roles/dev-agent.md` | **No change** | Already includes `{{include: common/iteration-log}}` at line 178, which chains to git-commit at line 180. New vault-remember step slots between them via the iteration-log or a new include |
| `references/sub-skills/roles/pm-agent.md` | **No change** | Same — includes iteration-log at line 242, git-commit at line 244. Vault-remember slots between via a new include |
| `references/vault-templates/areas-template.md` | **No change** | Already suitable for human-profile.md |
| `references/vault-templates/BRIEFING.md` | **No change** | Template already exists |
| `.squidsquad/vault/areas/human-profile.md` | **Create** | Missing — vault-init spec (vault-protocol.md line 24) says to create it, but it was never seeded. Phase 3 should create this as part of initial vault-remember work |
| `references/scripts/vault_check.py` | **Extend** | Add `dedup-check` command — given a candidate note title/tags, search vault for near-matches and return results. Used as a deterministic gate before vault-create |
| `references/scripts/cycle.py` | **Extend** | Implement the `is-quiet` command (documented in docstring at line 14 but not implemented — no function body exists). Add `vault-write-count` command to track writes per cycle |
| `references/scripts/compose.py` | **No change** | Already resolves `{{include:}}` directives. New sub-skill file will be picked up automatically |
| `.squidsquad/config.md` | **Extend** | Add vault-remember config section: `vault-remember: yes/no`, `vault-writes-per-cycle: 2`, `briefing-token-budget: 2000` |

### New Files Needed

| File | Purpose |
|---|---|
| `references/sub-skills/common/vault-remember.md` | New sub-skill defining the end-of-cycle reflection step. Included between iteration-log and git-commit in both dev-agent.md and pm-agent.md |
| `references/scripts/vault_remember.py` | Deterministic gates for vault-remember: quiet-cycle check, dedup search, write counter enforcement, BRIEFING.md token budget check, confidence decay scan |
| `references/vault-templates/human-profile-seed.md` | Seed template for `areas/human-profile.md` with sections for: communication style, quality expectations, decision-making preferences, technical preferences, schedule/availability |

### Composition Changes

The dev-agent.md entry file (line 178-180) currently has:

```
{{include: common/iteration-log}}

{{include: common/git-commit}}
```

This becomes:

```
{{include: common/iteration-log}}

{{include: common/vault-remember}}

{{include: common/git-commit}}
```

Same change in pm-agent.md (lines 242-244). The PM's step numbering shifts: iteration-log stays Step 8, vault-remember becomes Step 8b, git-commit stays Step 9.

For the dev agent: iteration-log stays Step 4, vault-remember becomes Step 4b, git-commit stays Step 5. This matches the recommendation from the coleam00 research.

---

## 2. Deterministic vs LLM Boundary

This section is the core of the human's question: "Would it make sense that some of such functionality be deterministic?" The answer is YES — maximum determinism, LLM judgment only where unavoidable.

### DETERMINISTIC (Python script — `vault_remember.py`)

| Gate | Implementation | Rationale |
|---|---|---|
| **Quiet-cycle skip** | `cycle.py is-quiet <role>` — check if iteration log was created this cycle. If no log exists, skip reflection entirely. Exit code 0 = quiet, 1 = non-quiet | No LLM needed. Presence/absence of iter-N.md is binary |
| **Write counter enforcement** | Track writes in working-state.md: `**Vault Writes This Cycle**: N`. Script checks N < max (default 2). Returns remaining budget | Pure counter. Config-driven max |
| **Dedup check** | `vault_check.py dedup-check --title "candidate-name" --tags "tag1,tag2"` — grep vault for notes with matching title keywords or overlapping tags. Return list of potential matches with similarity signal (shared keyword count) | Text matching is deterministic. The script finds candidates; the LLM decides if they truly overlap |
| **BRIEFING.md token budget** | `vault_remember.py briefing-budget` — count tokens (words * 1.3 approximation) in current BRIEFING.md. Return remaining budget vs. cap (default 2000 tokens, ~50 lines). If over budget, block BRIEFING.md updates until trimmed | Line/word counting is deterministic |
| **Confidence decay** | `vault_remember.py decay-scan` — find all galaxy notes with `status: active` and `updated` date older than 60 days. For notes with `confidence: medium`, flag for decay to `low`. For `confidence: high`, flag for decay to `medium` | Date arithmetic is deterministic. Decay trigger is rule-based |
| **Galaxy note size guard** | Already exists in `vault_check.py` line 100 — warns if galaxy note exceeds 500 lines | Already deterministic |
| **Note count guard** | `vault_remember.py note-count` — count total `.md` files in vault. Warn if approaching a configurable threshold (e.g., 500 notes) | Simple file counting |

### LLM-JUDGED (Agent — in vault-remember sub-skill)

| Judgment | Why LLM Is Required | Constraint |
|---|---|---|
| **"Is this insight reusable?"** | Requires understanding whether a cycle's outcome has future value beyond this specific task. A regex can't assess conceptual reusability | Structured prompt narrows the judgment to 5 explicit categories (see below). Agent must cite which category applies |
| **Categorization into 5 types** | Deciding whether something is a "decision" vs. "learning" vs. "pattern" requires semantic understanding | Agent picks from exactly 5 categories: decision, pattern, learning, human-preference, project-context. No freeform |
| **Writing note content** | The actual vault note body must be coherent, atomic, and follow the galaxy-template structure | Template-constrained. Agent fills in sections from galaxy-template.md, does not invent structure |
| **Update vs. create decision** | When dedup-check returns near-matches, agent must decide if the new insight is truly the same, a refinement, or a distinct idea | Dedup script narrows candidates to max 3. Agent decides for each: same (update), distinct (create), or skip |
| **BRIEFING.md triage** | When BRIEFING.md is at token budget and a new high-priority insight arrives, deciding what to trim requires understanding relative importance | Agent must justify the trim in the commit message. Trimmed content moves to a galaxy note, never deleted |

### HYBRID (Deterministic structure + LLM fills in)

| Component | Deterministic Part | LLM Part |
|---|---|---|
| **Structured reflection prompt** | The prompt template itself is fixed text in vault-remember.md. 5 categories, 4 skip criteria, explicit output format | Agent evaluates each category against this cycle's iteration log and produces 0-2 candidates |
| **Dedup resolution** | Script returns candidate matches with keyword overlap score | Agent reads the candidates and the new insight, decides: update existing / create new / skip |
| **human-profile.md updates** | Script checks if human-profile.md exists and was last updated this cycle (prevent double-write) | Agent extracts the preference and writes it to the correct section |

### The Structured Reflection Prompt (deterministic template)

This is the vault-remember sub-skill's core. It is a fixed template that agents follow — no freeform "what did you learn today?"

```
## vault-remember Reflection

Review this cycle's iteration log (iter-N.md) and answer each category:

1. DECISIONS: Any architecture, pattern, or trade-off decisions made?
   -> If yes: vault-create galaxy/decision-*.md
2. PATTERNS: Any reusable patterns discovered or confirmed?
   -> If yes: vault-create galaxy/pattern-*.md
3. LEARNINGS: Anything fail or succeed unexpectedly?
   -> If yes: vault-create galaxy/learning-*.md
4. HUMAN PREFERENCES: Did the human express any preference, style, or value?
   -> If yes: vault-update areas/human-profile.md
5. PROJECT CONTEXT: Did project goals, constraints, or architecture change?
   -> If yes: vault-update projects/<name>.md or BRIEFING.md

For each candidate, apply these deterministic gates IN ORDER:
  Gate 1: python vault_remember.py write-budget <role>  -> if 0 remaining, STOP
  Gate 2: python vault_check.py dedup-check --title "<candidate>" --tags "<tags>"
          -> if exact match found, SKIP (already in vault)
          -> if near-match found, DECIDE: update or create
  Gate 3: Is this specific to only this cycle with no future value? -> SKIP
  Gate 4: Would a fresh agent in a new context benefit from this? -> WRITE

Output exactly:
  - WRITE: <type> — <one-line description> (gate 3+4 passed)
  - UPDATE: <existing-note> — <what to add> (dedup found near-match)
  - SKIP: <reason>

Max 2 writes per cycle. If >2 candidates pass gates, prioritize:
  1. Human preferences (always highest — they shape all future work)
  2. Decisions (architectural choices compound)
  3. Learnings (failure lessons prevent repeat mistakes)
  4. Patterns (useful but can wait a cycle)
```

---

## 3. Side Effects

### Impact on Existing Agents Mid-Cycle

- **No breaking change**: vault-remember is a new optional step between iteration-log and git-commit. If `vault-remember: no` in config, the step is skipped entirely. Agents that haven't been redeployed via `compose.py deploy` simply won't have the step in their CLAUDE.md
- **Backward compatibility**: The new `{{include: common/vault-remember}}` directive produces no output for agents that don't understand it (compose.py silently includes the content, but the step has an explicit config gate at the top)

### Cycle Time Impact

| Scenario | Added Time | Notes |
|---|---|---|
| Quiet cycle | 0 seconds | Deterministic skip — `is-quiet` exits immediately |
| Non-quiet, 0 candidates | ~5 seconds | Agent reads iter log, runs reflection prompt, produces all SKIPs |
| Non-quiet, 1 write | ~15-20 seconds | One vault-search (dedup), one vault-create, one vault-check L1 |
| Non-quiet, 2 writes | ~25-35 seconds | Two vault-searches, two vault-creates, two vault-check L1s |
| Worst case | ~45 seconds | 2 writes + 1 BRIEFING.md update + vault-check |

On a 30-minute cycle, 45 seconds is 2.5% overhead. Acceptable.

### Vault Growth Rate Projections

**Worst case (theoretical max)**:
- 3 agents x 2 writes/cycle x 48 cycles/day = 288 notes/day
- At ~30 lines/note average = 8,640 lines/day = ~260 KB/day
- Over 30 days = 8,640 notes, ~7.8 MB

**Realistic case (estimated)**:
- Most cycles are quiet (no feature work). Estimated 30% non-quiet cycles
- Of non-quiet cycles, maybe 50% produce vault-worthy insights
- Average 0.5 writes per non-quiet cycle
- 3 agents x 0.5 writes x 14.4 non-quiet cycles/day = ~22 notes/day
- Over 30 days = ~660 notes, ~500 KB
- Over 1 year = ~8,000 notes, ~6 MB

**Sustainability verdict**: Git handles this fine. `.squidsquad/vault/` is small text files. The real concern is not disk space but **discoverability** — vault-search via grep becomes slower at 8,000+ files. This is when FEAT-SKILL-062 (SQLite/RAG backend) becomes necessary. For now, grep over 1,000 files takes <1 second.

### Git Repo Bloat

- Each vault note is a small markdown file (~500 bytes - 2 KB)
- Git is extremely efficient at storing/diffing small text files
- The `.git/` directory growth from vault notes is negligible compared to code changes
- Risk: many small commits from vault writes. Mitigated by batching vault writes into the existing cycle commit (vault-remember runs before git-commit step)

---

## 4. Edge Cases

### 4a. Near-Duplicate Detection

**Scenario**: `vault_check.py dedup-check` finds a note with 3/5 keyword overlap but different framing.

**Resolution**: The dedup-check script returns candidates with an overlap score. The agent must read each candidate and decide:
- Score >= 80% keyword overlap: likely same insight -> UPDATE existing note
- Score 40-79%: possibly related -> agent reads both and decides
- Score < 40%: distinct -> CREATE new note

**Implementation**: `vault_check.py dedup-check` performs keyword extraction from the candidate title and existing note titles/tags. Returns a ranked list of matches with overlap percentage. Max 3 results to bound LLM evaluation cost.

### 4b. More Than 2 Candidates

**Scenario**: A productive cycle yields 4 vault-worthy insights.

**Resolution**: The write budget is enforced deterministically (script returns 0 remaining after 2 writes). The structured reflection prompt specifies a priority order:
1. Human preferences (always first)
2. Decisions
3. Learnings
4. Patterns

Remaining candidates are noted in the iteration log's Notes field: `Vault-worthy but deferred (budget): [description]`. They can be picked up next cycle if the agent re-reads the previous iteration log.

**Risk**: Deferred insights may never get written if subsequent cycles are also productive. Mitigation: the improvement scan (quiet cycle activity) could include a "deferred vault items" check.

### 4c. human-profile.md Concurrent Writes

**Scenario**: PM and skill agent both detect a human preference in the same cycle and both try to update `areas/human-profile.md`.

**Resolution**: Already handled by existing vault concurrent access rules (vault-protocol.md lines 88-93):
- Each agent appends to different sections (PM adds communication preferences, skill adds technical preferences)
- Append-only changelogs merge cleanly in git
- If a true merge conflict occurs, git marks it and the next `git pull --rebase` surfaces it

**Additional mitigation**: The write counter is per-agent, so both agents can write to human-profile.md independently. The vault-check L1 after each write ensures consistency.

### 4d. Race Condition: Same Galaxy Insight

**Scenario**: PM and skill both independently discover that "REST is preferred over GraphQL" and both try to create `galaxy/decision-rest-over-graphql.md`.

**Resolution**: Git prevents silent overwrite — the second agent's `git pull --rebase` will either:
1. Auto-merge if the files are identical (unlikely but possible)
2. Conflict if different content for same filename

**Prevention**: Dedup-check runs before vault-create. If agent B pulls agent A's commit before reflecting, dedup-check will find agent A's note and agent B will UPDATE instead of CREATE. The window for this race is narrow (both agents reflecting in the same ~30 second window between pulls).

**Residual risk**: Low. In the rare case of conflict, the existing rule applies: "Keep both versions."

### 4e. BRIEFING.md Token Budget Exceeded

**Scenario**: BRIEFING.md is at 48 lines (near the ~50 line / 2000 token cap) and a new high-priority decision needs to be added.

**Resolution**: The `vault_remember.py briefing-budget` script returns the current budget status. If over budget:
1. Agent may NOT add to BRIEFING.md without trimming
2. Agent identifies the least-current section (checking `updated` dates of referenced items)
3. Trimmed content is moved to a galaxy note (never deleted — vault-update rule)
4. Agent adds the new content to the freed space
5. Net change must not exceed the budget

**Who decides what to trim**: The agent (LLM judgment). The script only enforces the cap — it does not choose what to cut. The agent must justify the trim in its iteration log.

### 4f. Reflection on Reflection

**Scenario**: The vault-remember step itself produces an insight about the reflection process (meta-learning).

**Resolution**: This counts against the 2-write budget like any other insight. The agent can file it as `galaxy/learning-reflection-process-X.md`. No special handling needed.

---

## 5. Integration Risks

### 5a. Interaction with Improvement Scanning

Both improvement scanning and vault-remember produce vault-worthy insights. Differences:

| Aspect | Improvement Scan | vault-remember |
|---|---|---|
| Trigger | 3+ consecutive quiet cycles | Every non-quiet cycle end |
| Output | GitHub Issues (bugs/features) | Vault notes |
| Max items | 2 per scan | 2 writes per cycle |
| Domain | Code quality, doc drift | Decisions, patterns, learnings |

**Risk**: Improvement scan findings are filed as GitHub Issues, not vault notes. But the scan might also produce vault-worthy observations (e.g., "this codebase consistently uses pattern X"). Currently there is no mechanism for scan findings to become vault notes.

**Recommendation**: Keep them separate for Phase 3. Improvement scan -> Issues. Vault-remember -> vault notes. A future Phase 4 could add a bridge where closed improvement-scan issues get promoted to vault patterns. Adding this now increases scope without clear value.

### 5b. Interaction with Context Pressure Exits

**Risk**: If an agent hits the context pressure threshold (config.md: 80%), it saves state and exits BEFORE reaching the vault-remember step. Insights from that cycle are lost.

**Current flow**: Context pressure check is Step 1b (pm-agent.md line 79). If triggered, agent saves working-state and exits immediately.

**Mitigation options**:
1. **Accept the loss** — iteration log is already written by cycle.py at the point of work, so the raw data is preserved. A future cycle can reflect on it. Simplest approach.
2. **Move vault-remember earlier** — but this breaks the "reflect after all work is done" principle. Rejected.
3. **Add a "deferred reflection" marker** to working-state.md — on the next fresh session, the agent reads the marker and reflects on the previous cycle's iteration log before starting new work. Adds complexity but preserves insights.

**Recommendation**: Option 1 for Phase 3 (accept the loss). The iteration log preserves the raw data. Option 3 can be a follow-up feature if context pressure exits prove frequent.

### 5c. compose.py Changes

`compose.py` needs no code changes — it already resolves `{{include:}}` directives. The only change is:

1. Create the new file: `references/sub-skills/common/vault-remember.md`
2. Add `{{include: common/vault-remember}}` to both `dev-agent.md` and `pm-agent.md` entry files
3. Run `compose.py deploy <role>` to regenerate CLAUDE.md files

The sub-skill manifest (`references/sub-skills/manifest.md`) should be updated to list the new sub-skill.

### 5d. Interaction with QA Subagent

The QA subagent (spawned by PM for feature verification) does NOT run the Ralph Loop — it runs a one-shot test plan. QA subagent should NOT have vault-remember. It operates within PM's cycle and PM's write budget. No change needed for QA.

---

## 6. Upgrade & Migration

### Via /squidsquad-upgrade

The upgrade flow needs to:

1. **Add new files**:
   - `references/sub-skills/common/vault-remember.md`
   - `references/scripts/vault_remember.py`
   - `references/vault-templates/human-profile-seed.md`

2. **Modify existing files**:
   - `references/sub-skills/roles/dev-agent.md` — add `{{include: common/vault-remember}}` between iteration-log and git-commit
   - `references/sub-skills/roles/pm-agent.md` — same
   - `references/scripts/vault_check.py` — add `dedup-check` command
   - `references/scripts/cycle.py` — implement `is-quiet` command (currently documented but not implemented)
   - `references/sub-skills/manifest.md` — add vault-remember entry

3. **Config additions** (`.squidsquad/config.md`):
   ```markdown
   ## Vault Remember

   - **Enabled**: yes
   - **Writes Per Cycle**: 2
   - **BRIEFING Token Budget**: 2000
   - **Confidence Decay Days**: 60
   ```

4. **Regenerate CLAUDE.md** for all active roles: `compose.py deploy skill`, `compose.py deploy pm`, etc.

5. **Seed human-profile.md** (if missing): Create `vault/areas/human-profile.md` from the seed template. This is idempotent — if it already exists, skip.

### Graceful Degradation

If a user does not upgrade:
- **No vault-remember sub-skill in CLAUDE.md** — agents simply don't have the step. No error, no crash.
- **No vault_remember.py script** — not called by any existing code.
- **No config values** — vault-remember sub-skill should check for the config key and default to `no` if missing. This means even if the sub-skill text is present but config is absent, it skips.
- **Existing vault operations (create, update, search, check)** — completely unaffected.

### Migration for Existing Vaults

No data migration needed. Existing vault notes are untouched. The only new vault content is:
- `areas/human-profile.md` (created if missing, via vault-init idempotency)
- New galaxy notes from reflection (created organically over time)

---

## 7. Open Questions

### Q1: Should vault-remember be enabled by default?

**Why it matters**: If enabled by default, every new SquidSquad installation writes vault notes from cycle 1. Benefit: immediate value. Risk: noise before the vault has enough content for meaningful dedup, and new users may not understand what's being written.

**Recommendation**: YES, enabled by default with the 2-write cap. The deterministic gates prevent noise. Users can set `vault-remember: no` to disable.

### Q2: Should the DM agent also run vault-remember?

**Why it matters**: DM manages documentation and releases. It could produce vault-worthy insights about user communication patterns, changelog style, docs structure. But DM is optional and not always active.

**Recommendation**: YES for DM if present. Same sub-skill include, same budget. DM's insights about doc patterns and release processes are valuable. The DM entry file (`dm-agent.md`) would need the same `{{include: common/vault-remember}}` insertion.

### Q3: What happens to "deferred vault items" (budget exceeded)?

**Why it matters**: If productive cycles consistently produce >2 candidates, valuable insights accumulate in iteration logs without promotion. Over time, the iteration logs get cleaned up (keep 20), and the deferred insights are lost.

**Options**:
- A: Accept the loss — the 2-write cap is the quality gate. If it's not in the top 2, it probably isn't vault-worthy.
- B: Add a "deferred-vault" section to working-state.md. On the next non-quiet cycle's reflection, check deferred items first.
- C: Allow the improvement scan to process deferred vault items during quiet cycles.

**Consequence of getting it wrong**: Option A risks losing valuable insights. Options B and C add complexity. Recommend starting with A and monitoring — if iteration logs consistently show deferred items that look high-value, add B in a follow-up.

### Q4: Should confidence decay be automatic or advisory?

**Why it matters**: Automatic decay modifies vault notes without explicit agent or human action. This could decay a genuinely stable high-confidence note just because nobody touched it in 60 days.

**Options**:
- A: Automatic — `vault_remember.py decay-scan` runs as part of vault-check Level 2 and applies decay directly.
- B: Advisory — the script flags notes for decay but an agent (or human) must confirm.
- C: Automatic with exemption tag — notes tagged `evergreen` skip decay.

**Consequence of getting it wrong**: Option A may decay stable knowledge incorrectly. Option B requires human attention, which may never come. Recommend Option C — automatic with an `evergreen` tag exemption.

### Q5: What is the human-profile.md seeding strategy?

**Why it matters**: An empty human-profile.md provides no value. But pre-populating it with guesses could be wrong. The coleam00 research shows their USER.md is human-curated.

**Options**:
- A: Create an empty template with section headers only (Communication Style, Quality Expectations, Technical Preferences, etc.). Agents populate it organically as they observe preferences.
- B: Pre-seed with known preferences from BRIEFING.md and existing MEMORY.md feedback files.
- C: Ask the human to fill it out during setup.

**Consequence of getting it wrong**: Option A means the note is useless for several cycles until enough observations accumulate. Option B may contain stale or inaccurate inferences. Option C blocks on human action. Recommend Option B (pre-seed from known sources) with `confidence: medium` on all pre-seeded entries so agents know to update them when the human confirms or contradicts.

### Q6: How should vault-remember interact with the designer agent?

**Why it matters**: The designer agent (when present) works with visual patterns, design tokens, and UI decisions. These are vault-worthy but may need the `style-` galaxy prefix. The current reflection prompt doesn't have a "design decisions" category.

**Recommendation**: The 5 categories already cover design via "DECISIONS" (design choices) and "PATTERNS" (design patterns). No special handling needed for Phase 3. If the designer agent produces insights that don't fit the 5 categories, it can use the "agents may introduce new prefixes" escape hatch (vault-protocol.md line 48).

---

## 8. Recommendation

**Feasible with caveats.**

The architecture is sound. The coleam00 research validates the capture-reflect-promote pattern. The existing vault infrastructure (vault-create, vault-update, vault-search, vault-check) provides most of the machinery. The main new work is:

1. **vault_remember.py** — deterministic gate script (~200 lines)
2. **vault-remember.md** — sub-skill document (~80 lines)
3. **Entry file changes** — 2 lines each in dev-agent.md and pm-agent.md
4. **cycle.py `is-quiet`** — implement the documented but missing command (~15 lines)
5. **vault_check.py `dedup-check`** — new command (~50 lines)
6. **human-profile.md seed** — template + one-time creation
7. **Config additions** — 4 new config keys

**Caveats**:

1. **Context pressure exit risk**: Insights from the cycle that triggered a context pressure exit are not reflected. Accept this for Phase 3; consider "deferred reflection" marker in Phase 4.
2. **Dedup accuracy**: Keyword-based dedup is imperfect. Near-misses will happen. The LLM judgment layer for dedup resolution is the safety net, but it adds ~5 seconds per candidate.
3. **Step numbering shift**: Adding vault-remember between iteration-log and git-commit shifts step references in existing documentation. All documentation referencing "Step 5" (git-commit) for dev agents must be audited.
4. **Testing complexity**: vault-remember is hard to unit test because it combines deterministic gates with LLM judgment. Test the deterministic parts (vault_remember.py) with standard unit tests. Test the LLM judgment via the existing QA subagent flow (PM verifies that vault notes written by vault-remember are well-formed and non-duplicate).

**Estimated implementation effort**: 2-3 full cycles for the skill agent. Breakdown:
- Cycle 1: vault_remember.py + cycle.py is-quiet + vault_check.py dedup-check + unit tests
- Cycle 2: vault-remember.md sub-skill + entry file changes + human-profile.md seed + config additions
- Cycle 3: compose.py deploy + integration testing + documentation audit for step number shifts
