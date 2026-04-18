# FEAT-PM-1077 Phase 2 Prep — Add Comprehension Testing to QA Verification

## Question Analysis

### Optimal Question Order

1. **Q2** (agent prompt style) — foundational: affects how comprehension tests work at the most basic level. All other decisions depend on getting the prompt approach right.
2. **Q3** (single vs multiple spawns) — structural: determines how results are organized, which feeds into Q1.
3. **Q1** (results format) — presentation: least controversial, no upstream dependencies. Can be decided last.

Rationale: Q2 is a dependency for Q3 (if we choose role-primed prompts, splitting by sub-skill becomes more natural since each spawn gets a different role context). Q1 is purely a formatting decision that can adapt to whatever Q2 and Q3 produce.

---

## Q2: Should the comprehension agent be role-primed or given a neutral prompt?

**Category**: Behavior

**Why it matters**: Role-priming might cause the agent to draw on training data rather than file content. Neutral prompts force file reading but may miss role-specific context.

### Option A: Neutral prompt (no role identity)

**Description**: The subagent is told "Read these files and answer the following questions based solely on the file contents."

**Pros**:
- Forces the agent to read and reason from the actual files, not prior knowledge
- Cleanest test of whether the instructions are self-contained and clear
- Eliminates the risk of training data contamination (agent "knowing" SquidSquad conventions without reading them)
- Simpler prompt template — no role-specific customization needed

**Cons**:
- May miss context that a real agent would have (e.g., understanding that "the Ralph Loop" is a cycle, not a person)
- Could produce false negatives on questions that assume domain familiarity
- Does not mirror the actual runtime context (production agents always have a role identity)

### Option B: Role-primed prompt (full role identity)

**Description**: The subagent is told "You are a [role] agent. Read your instructions at [path] and answer the following questions."

**Pros**:
- Mirrors the actual runtime context — tests what a real agent would understand
- Catches issues where instructions assume role context that is provided at boot
- More realistic end-to-end test

**Cons**:
- Risk of training data contamination — agent may answer from prior knowledge of SquidSquad rather than from the files
- Harder to isolate whether a correct answer came from reading the file or from memorized patterns
- Makes the test less of a "clarity test" and more of a "role simulation test"

### Option C: Neutral prompt with file-scope hint (RECOMMENDED)

**Description**: The subagent is told "Read the following files. Answer each question based ONLY on what these files say. Do not use any prior knowledge. If the files do not contain enough information to answer, say so."

**Pros**:
- Forces file reading (like Option A) while being explicit about the constraint
- The "say so if insufficient" instruction catches gaps where the instructions are incomplete — a genuine finding
- Simple, reusable template
- If the agent can answer correctly from file content alone, the instructions are definitively clear
- Aligns with the memory-layer standard: "Spawn a fresh agent with no prior context, point it at modified files"

**Cons**:
- Still does not mirror production context (production agents have role identity)
- May produce false negatives for questions that require cross-file context not included in the file list

**Recommendation**: Option C. The purpose of comprehension testing is to verify that instructions are clear and self-contained. A neutral-with-constraint prompt is the strongest test of that property. If the instructions require role context to be understood, that is itself a finding worth surfacing.

---

## Q3: For large template changes, single spawn or multiple spawns?

**Category**: Performance / Scope

**Why it matters**: Single spawn is cheaper but risks context pollution between sub-skills. Multiple spawns ensure each test is truly fresh but cost more tokens.

### Option A: Always single spawn

**Description**: All comprehension questions for a task are asked in one subagent session, regardless of how many sub-skills are affected.

**Pros**:
- Cheapest option — one spawn overhead instead of N
- Simplest to implement — no spawn-routing logic needed
- Consistent with current QA subagent pattern (one spawn per test plan)

**Cons**:
- Context pollution: answers to early questions may influence later answers (agent "learns" the domain mid-test)
- For large changes (like #475 with 7 sub-skills), the agent accumulates context that a fresh production agent would not have
- Harder to isolate which sub-skill has unclear instructions if multiple questions fail

### Option B: Always multiple spawns (one per sub-skill)

**Description**: Each sub-skill or logical group of files gets its own subagent spawn with its own set of questions.

**Pros**:
- Each test is truly fresh — no context contamination
- Easy to isolate failures to a specific sub-skill
- Most rigorous test of instruction clarity

**Cons**:
- Most expensive option — N spawns instead of 1
- Slower (spawns are sequential)
- Overkill for tasks that touch only 1-2 sub-skills (the majority of tasks)

### Option C: Adaptive — single spawn by default, multiple for large changes (RECOMMENDED)

**Description**: Use a single spawn when the task touches 1-3 sub-skills. Split into multiple spawns when the task touches 4+ sub-skills. The threshold is documented in the test plan template so PM can override per task.

**Pros**:
- Efficient for the common case (most tasks touch 1-2 sub-skills)
- Rigorous for the uncommon case (large cross-cutting changes like #475)
- PM retains control — can override the threshold in the test plan if needed
- Balances cost and quality

**Cons**:
- Slightly more complex template (needs to document when to split)
- The threshold (4 sub-skills) is somewhat arbitrary — may need tuning

**Recommendation**: Option C. Most tasks are small and a single spawn is sufficient. The 4+ threshold catches genuinely large changes where context pollution is a real risk. PM can always override in either direction.

---

## Q1: Should comprehension test results be in a separate section or inline?

**Category**: Compatibility / Presentation

**Why it matters**: Separating them makes it easy to see which TCs are comprehension-based, but inline keeps the unified pass/fail format.

### Option A: Inline with other TC results

**Description**: Comprehension test results appear in the same `### TC-N` or `### CQ-N` sequence as traditional test cases in QA-RESULTS.md, using the same PASS/FAIL format.

**Pros**:
- Unified format — one place to scan for any failures
- Consistent with existing QA-RESULTS.md structure
- Zero-gap gate applies uniformly — no need to check two sections

**Cons**:
- Harder to quickly see "how did comprehension tests do as a group"
- Mixed methods in one list (some TCs run commands, some ask questions) — could confuse reviewers
- If a comprehension test fails, the failure notes look different from traditional TC failures (no command output, just Q&A)

### Option B: Separate section in QA-RESULTS.md (RECOMMENDED)

**Description**: QA-RESULTS.md has two sections: `## Test Case Results` (traditional TCs) and `## Comprehension Test Results` (CQ results). Both use the same PASS/FAIL format. The final summary counts both sections.

**Pros**:
- Easy to see comprehension results at a glance
- Clear separation of methods — readers know which tests verify code behavior vs instruction clarity
- The summary section still applies zero-gap gate across both — any failure in either section = back to dev
- Matches the test plan structure (which already has a separate `## Comprehension Questions` section per the research recommendation)

**Cons**:
- Two sections to check instead of one (minor — the summary catches everything)
- Slightly more verbose template

### Option C: Separate file (CQ-RESULTS.md)

**Description**: Comprehension test results go in a dedicated file alongside QA-RESULTS.md.

**Pros**:
- Complete isolation — easy to find, easy to archive
- Could be generated by a different subagent without merging output

**Cons**:
- Splits the "single source of truth" for test results into two files
- QA must check two files before making a pass/fail decision
- More files to manage and clean up after shipping
- Inconsistent with current pattern (one QA-RESULTS.md per task)

**Recommendation**: Option B. A separate section within QA-RESULTS.md gives clear visibility into comprehension results while keeping all test results in one file. The summary section enforces the zero-gap gate uniformly.

---

## Summary of Recommendations

| Question | Category | Recommended | Key Rationale |
|----------|----------|-------------|---------------|
| Q2: Agent prompt style | Behavior | C: Neutral with file-scope hint | Tests instruction clarity without training-data contamination |
| Q3: Single vs multiple spawns | Performance | C: Adaptive (single default, split at 4+ sub-skills) | Efficient for common case, rigorous for large changes |
| Q1: Results format | Compatibility | B: Separate section in QA-RESULTS.md | Clear visibility, single file, unified zero-gap gate |
