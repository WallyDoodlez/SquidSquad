# FEAT-PM-1077 Research — Add Comprehension Testing to QA Verification

## Summary

Comprehension testing is already in active use in SquidSquad but is not standardized. It was first formalized in #1074 (auto-merge PRs) where the test plan included a "Comprehension Questions" section with 12 derived questions, and was extensively planned for #475 (token efficiency audit) with 7 comprehension test cases (TC-11 through TC-17). The proposal is to make this a first-class, standard part of the QA verification flow and test plan template, rather than an ad-hoc technique applied inconsistently.

The primary risk is token cost (each comprehension test spawns a subagent that must read files and answer questions). The primary benefit is catching behavioral drift in LLM-consumed instructions that traditional tests cannot verify. The recommendation is: feasible, standardize it as an optional section in test plans, with QA executing comprehension tests alongside traditional verification.

## Impact Analysis

- **Files touched**:
  - `references/sub-skills/qa-specific/verification.md` — add comprehension test execution step
  - `references/sub-skills/pm-specific/task-intake.md` — add comprehension questions section to test plan template
  - `references/roles/qa/includes.yml` and `references/roles/pm/includes.yml` — no change (sub-skills already included)
  - Composed CLAUDE.md files for QA and PM — regenerated via `compose.py deploy-all`
- **Behavior changes**: QA gains a new verification method for template/instruction changes. PM test plan template gains a new optional section.
- **Dependencies**: Requires the Agent tool (already available in Claude Code). No new scripts or libraries.

## Side Effects

- **Risk 1**: Token cost increase per QA cycle — Severity: M — Mitigation: Only spawn comprehension agents when task touches LLM-consumed instructions. Traditional-only tasks skip this step entirely.
- **Risk 2**: False positives (agent answers correctly but implementation is actually wrong) — Severity: L — Mitigation: Comprehension tests are paired with at least one real smoke test. The comprehension test validates clarity, the smoke test validates runtime behavior.
- **Risk 3**: False negatives (agent answers wrong but implementation is fine) — Severity: L — Mitigation: The comprehension agent reads the actual files, not a summary. A wrong answer almost always means the instructions are ambiguous, which is a legitimate finding even if the intended behavior works.
- **Risk 4**: QA cycle time increases — Severity: M — Mitigation: Comprehension tests only run for pending-test tasks that have comprehension questions in their test plan. Most tasks (script changes, config changes) won't have them.

## Edge Cases

- **Task with mixed changes (both script and template)**: Apply both traditional tests (for scripts) and comprehension tests (for templates). The test plan should have both sections.
- **Comprehension agent has access to training data about SquidSquad**: The agent might answer from prior knowledge rather than reading the files. Mitigation: The questions should be specific enough that only reading the actual implementation gives correct answers (e.g., "What is the default Auto Merge value for upgrades?" requires reading the specific code).
- **Empty comprehension questions section**: If PM creates a test plan for a pure script change, the comprehension section should be omitted entirely, not left empty. QA skips the step if no questions exist.
- **Comprehension test disagrees with smoke test**: If comprehension says PASS but smoke says FAIL (or vice versa), both results are reported. QA investigates the discrepancy. The zero-gap gate still applies — any failure = back to dev.

## Integration Risks

- **Interaction with existing QA subagent flow**: QA already spawns a subagent to execute test plans (Phase 5 / Step 5). Comprehension testing would be executed by the same subagent as part of the test plan, OR as a separate subagent spawn. Recommendation: same subagent, since comprehension questions are part of the test plan.
- **Interaction with #475 (token efficiency)**: #475 already planned 7 comprehension TCs. If #1077 standardizes the format, #475's existing TCs should conform. No conflict — #475 was ahead of the curve.
- **PR Flow interaction**: None. Comprehension testing is internal to QA verification and does not affect PR approval, merge, or status transitions.

## Upgrade & Migration

- **New config values**: None — comprehension testing is opt-in per test plan, not a global config toggle.
- **New files**: None — changes are to existing sub-skill files and the test plan template format.
- **Template changes**: PM's task-intake sub-skill (test plan template) gains an optional `## Comprehension Questions` section. QA's verification sub-skill gains a comprehension test execution step.
- **Upgrade steps**: `compose.py deploy-all` propagates the changes. No manual migration needed.
- **Graceful degradation**: If an existing install doesn't upgrade, test plans simply won't have a comprehension section, and QA won't execute comprehension tests. No breakage.

## Capability Gaps

- **Agent tool**: Available. All agents can spawn subagents via the Agent tool. No gap.
- **File reading by subagent**: Available. Subagents can read any file. No gap.

## Detailed Findings

### 1. Current QA Verification Flow

QA verification (Steps 4-5 in the Ralph Loop) works as follows:

**For issues (bug fixes, Step 4)**:
- Query pending-test issues per dev role
- Read issue details, check for feature branch
- Run relevant test or manually verify the fix
- If verified: transition to pending-ship
- If not verified: transition back to in-progress with specific failures

**For tasks (features, Step 5)**:
- Query pending-test tasks per dev role
- If a TEST-PLAN.md exists: spawn a QA subagent to execute all test cases, write results to QA-RESULTS.md. QA reviews results and makes final decision.
- If no TEST-PLAN.md: test against acceptance criteria manually
- Zero-gap gate: ANY gap = back to in-progress. No exceptions without human override.

**Key insight**: The subagent already reads files, runs commands, and records PASS/FAIL. Comprehension testing fits naturally into this flow — it's just a different type of test case that the subagent executes by reading files and answering questions instead of running commands.

### 2. Current Test Plan Template

The PM test plan template (Phase 3 of task-intake) has these sections:
- `## Test Cases` — TC-N entries with Precondition, Steps, Expected, Verification
- `## Smoke Tests` — checklist items
- `## Regression Risks` — risk descriptions

**Where comprehension questions fit**: Two proven patterns exist:

**Pattern A (used in #1074)**: A `## Verification Method` section after the test cases, with a `### Comprehension Questions` subsection. Questions are derived 1:1 from test cases. The comprehension test IS the primary verification method, paired with a secondary smoke test.

**Pattern B (used in #475)**: A `## Section 2: Comprehension Tests` with full TC-N format entries. Each comprehension TC has Precondition, Method, Quiz Questions (with expected answers), Pass Criteria, and Fail Action. More structured but more verbose.

**Recommendation**: Pattern A is simpler and fits more naturally. Pattern B is appropriate for large template changes with many affected sub-skills.

### 3. Existing Comprehension Testing Usage

**Git history**: One commit references comprehension testing: `17d83d8 pm: updated #1074 test plan with comprehension testing method, filed #1077`.

**Active usage**:
- **#1074 test plan**: 12 comprehension questions derived from 13 TCs. Each question maps to a specific TC. Pass criteria: agent answers all 12 correctly without hints. This was the first explicit use.
- **#475 test plan**: 7 comprehension TCs (TC-11 through TC-17) covering tracker-protocol, vault-protocol, and boot-remote-agents removal. Each has structured quiz questions with expected answers and pass criteria.
- **#329 QA results**: SM-8 (comprehension test for iteration log format) was SKIPPED with note "Manual comprehension test, cannot be automated." This shows the gap: QA knew a comprehension test was appropriate but had no standard way to execute it.

**Memory layer**: `feedback_comprehension_testing.md` documents the standard: "Spawn a fresh agent with no prior context, point it at modified files, ask comprehension questions derived from test cases." Scoped to "non-deterministic logic consumed by LLMs" only.

### 4. Agent Tool Capabilities for Subagents

The Agent tool spawns a subagent within the same Claude Code session:
- **Fresh context**: The subagent has no prior conversation context — it only knows what you tell it in the prompt.
- **File access**: The subagent can read any file in the working directory.
- **Tool access**: The subagent has access to the same tools (Read, Bash, Grep, etc.).
- **Results**: The subagent writes output to a file (e.g., QA-RESULTS.md) that the parent agent then reads.
- **Limitations**: The subagent shares the parent's context window budget. Each spawn consumes tokens.

**For comprehension testing**: The prompt would instruct the subagent to read specific files, then answer a list of questions. The subagent writes answers to a results file. The parent (QA or PM) reviews the answers against expected answers.

### 5. What Needs Comprehension Testing vs Traditional Testing

| Change Type | Testing Method | Examples |
|---|---|---|
| Template/instruction changes (CLAUDE.md, sub-skills) | Comprehension test + smoke test | #1074 delivery-fallback, #475 vault-protocol condensation |
| Python scripts | Unit tests + integration tests | compose.py, tracker.py, config.py, git_ops.py |
| Config changes | Programmatic verification (read config, check values) | Auto Merge default, PR Flow setting |
| Mixed (script + template) | Both methods | #1074 (git_ops.py pr_merge + delivery-fallback sub-skill) |
| Behavioral specifications (SOUL.md, vault notes) | Comprehension test only | Style preferences, process constraints |

**Rule of thumb**: If the change is consumed by an LLM at runtime (read as part of CLAUDE.md or sub-skills), it needs comprehension testing. If it's executed deterministically (Python, shell), it needs traditional testing. If both, use both.

### 6. Side Effects Analysis

**Token cost**: Each comprehension test spawn consumes roughly 5K-15K tokens depending on file sizes and number of questions. For a 12-question test like #1074, expect ~10K tokens. At current Claude pricing, this is negligible per task but could add up if every task has comprehension tests (most shouldn't — only template-touching tasks).

**Time**: A comprehension test adds 30-90 seconds to QA verification depending on file sizes. This is well within acceptable bounds since QA cycles are 30-minute intervals.

**False positives**: Possible but unlikely. The agent reads actual files, so if it answers correctly, the instructions are at minimum clear. The smoke test catches cases where clear instructions have a runtime bug.

**False negatives**: More concerning. Possible causes:
- Agent misreads the file (rare with Read tool)
- Question is ambiguous (fix the question, not the implementation)
- Agent's training data contradicts the file content (mitigated by asking implementation-specific questions)

**Recommendation**: Accept false negatives as legitimate findings. If a fresh agent can't answer correctly from the instructions, the instructions may need clarification even if they technically work.

### 7. Design Questions

**Q1: Who generates comprehension questions — PM in test plan, or QA at verification time?**
- Recommendation: **PM generates them in Phase 3 (test plan)**. This is already the pattern in #1074 and #475. PM has the context from research and discussion to derive meaningful questions. QA could add supplementary questions during verification if gaps are found.

**Q2: How many questions per test case?**
- Recommendation: **1 question per TC that touches LLM-consumed logic**. Not every TC needs a comprehension question — only those testing behavioral understanding. #1074 had 12 questions for 13 TCs (nearly 1:1). #475 had ~15 questions across 7 comprehension TCs (2-4 per TC). The right number depends on the change scope.

**Q3: What constitutes a pass vs fail?**
- Recommendation: **All questions must be answered correctly without hints**. This is the standard from #1074: "Agent answers all 12 correctly without hints. Any wrong answer = implementation gap." For large question sets, a threshold (e.g., 90%) could be used, but the zero-gap gate philosophy suggests 100% is the right target.

**Q4: Should the quizzed agent see ONLY the changed files, or the full CLAUDE.md?**
- Recommendation: **The full composed CLAUDE.md** (or the specific sub-skill files being tested). The goal is to test whether an agent following the instructions would behave correctly. A production agent reads the full CLAUDE.md, so the comprehension test should mirror that context. However, for efficiency, pointing at specific sub-skill source files is acceptable (as done in #1074 with delivery-fallback.md).

**Q5: Where in the test plan template does the comprehension section go?**
- Recommendation: **After the standard Test Cases section, before Smoke Tests**. Format:

```markdown
## Comprehension Questions

**Method**: Spawn a fresh agent. Point it at [list of files]. Ask each question. Record answers.
**Pass criteria**: All [N] questions answered correctly without hints.

### CQ-1: [Question derived from TC-N]
- **Question**: "[natural language question]"
- **Expected**: [what a correct answer includes]
- **Derived from**: TC-N

### CQ-2: ...
```

**Q6: Is comprehension testing mandatory or optional?**
- Recommendation: **Conditionally mandatory**. If the task modifies LLM-consumed instructions (sub-skills, CLAUDE.md templates, SOUL.md, behavioral specs), the test plan MUST include comprehension questions. If the task is pure script/config, comprehension questions are omitted. PM determines this during Phase 3 based on the files-touched list from research.

**Q7: Does the QA subagent execute comprehension questions, or does a separate agent?**
- Recommendation: **Same subagent that executes the test plan**. Comprehension questions are test cases — they belong in the test plan and are executed alongside traditional TCs. No need for a separate spawn.

### 8. Upgrade & Migration

This is a template-only change. Existing installs get it via `compose.py deploy-all` on their next upgrade or recompose cycle. No config values, no scripts, no migration steps.

Existing test plans without comprehension sections continue to work — QA simply doesn't execute comprehension tests for those tasks.

## Open Questions

- **Q1**: Should comprehension test results be recorded in a separate section of QA-RESULTS.md, or inline with other TC results? — **Why**: Separating them makes it easy to see which TCs are comprehension-based, but inline keeps the unified pass/fail format.
- **Q2**: Should the comprehension agent be told "You are a [role] agent, answer based on your instructions" or given a neutral prompt? — **Why**: Role-priming might cause the agent to draw on training data rather than file content. Neutral prompts force file reading but may miss role-specific context.
- **Q3**: For very large template changes (like #475 with 7 comprehension TCs), should comprehension testing be split into multiple subagent spawns (one per sub-skill) or done in a single spawn? — **Why**: Single spawn is cheaper but risks context pollution between sub-skills. Multiple spawns ensure each test is truly fresh but cost more tokens.

## Recommendation

Straightforward. The pattern is already proven across #1074 and #475. Standardization requires:
1. Add a `## Comprehension Questions` section template to the PM's test plan template (Phase 3)
2. Add comprehension test execution logic to QA's verification step (Step 5)
3. Document when comprehension questions are required vs optional (based on files-touched analysis)

No new infrastructure, scripts, or config values needed. Pure template update.
