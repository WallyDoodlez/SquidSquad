# FEAT-PM-1077 Test Plan — Add Comprehension Testing to QA Verification

## Test Cases

### TC-1: Happy path — QA runs comprehension tests on a template change, all pass
- **Precondition**: A task (#1077 itself) modifies `references/sub-skills/qa-specific/verification.md` and `references/sub-skills/pm-specific/task-intake.md`. The TEST-PLAN.md includes a `## Comprehension Questions` section with CQ-1 through CQ-N. `compose.py deploy-all` has been run so composed CLAUDE.md files reflect the changes.
- **Steps**:
  1. QA picks up the task at `pending-test`.
  2. QA subagent reads TEST-PLAN.md, encounters the `## Comprehension Questions` section.
  3. QA subagent spawns a comprehension agent with the neutral prompt: "Read these files and answer ONLY from what you find."
  4. Comprehension agent reads the specified files, answers each CQ.
  5. QA subagent compares answers to expected values and records results.
- **Expected**: All CQs answered correctly. Results appear in a `## Comprehension Tests` section of QA-RESULTS.md with per-CQ PASS/FAIL entries. Overall comprehension verdict is PASS.
- **Verification**: Read QA-RESULTS.md. Confirm `## Comprehension Tests` section exists. Confirm each CQ entry has `Result: PASS`. Confirm no CQ entry has `Result: FAIL`.

### TC-2: Comprehension agent answers wrong — failure path
- **Precondition**: Same as TC-1, but the implementation has a deliberate ambiguity or error (e.g., a CQ asks "When is comprehension testing required?" and the template says "optional" instead of "conditionally mandatory").
- **Steps**:
  1. QA subagent spawns comprehension agent with neutral prompt.
  2. Comprehension agent reads the files and answers based on what it finds.
  3. QA subagent compares answers to expected values.
- **Expected**: At least one CQ is marked FAIL. The `## Comprehension Tests` section in QA-RESULTS.md shows the failure with the wrong answer noted. Overall task verdict is FAIL (zero-gap gate applies). QA transitions the task back to `in-progress`.
- **Verification**: Read QA-RESULTS.md. Confirm at least one CQ has `Result: FAIL`. Confirm QA did NOT mark the task `pending-ship`. Confirm a Discussion comment was appended listing the failed CQ(s).

### TC-3: Neutral prompt enforces file-scope — agent cannot use training data
- **Precondition**: A CQ is crafted to ask about a project-specific value that has no correct answer in training data (e.g., "What is the exact pass rate percentage required for comprehension tests?" — answer: 100%, only derivable from the template).
- **Steps**:
  1. QA subagent spawns comprehension agent with the neutral prompt: "Read these files and answer ONLY from what you find."
  2. The agent is pointed at the specific sub-skill file(s).
  3. The agent answers the question.
- **Expected**: The agent's answer matches the file content exactly (e.g., "100%"), not a hedged or generic response. If the file is ambiguous, the agent says it cannot determine the answer from the files alone (which counts as a failure, correctly catching the ambiguity).
- **Verification**: Review the comprehension agent's raw answer. Confirm it references or quotes the file content. Confirm it does not say "based on common practice" or similar training-data hedging.

### TC-4: Mixed changes — task touches both a script and a template
- **Precondition**: A task modifies both `references/scripts/tracker.py` (script) and `references/sub-skills/qa-specific/verification.md` (template). The TEST-PLAN.md has both standard TCs (for the script) and a `## Comprehension Questions` section (for the template).
- **Steps**:
  1. QA subagent executes all standard TCs (script verification commands, file checks).
  2. QA subagent encounters the `## Comprehension Questions` section.
  3. QA subagent spawns a comprehension agent for the template CQs.
  4. Both sets of results are recorded in QA-RESULTS.md.
- **Expected**: QA-RESULTS.md contains standard TC results (TC-1, TC-2, etc.) AND a `## Comprehension Tests` section with CQ results. Both must pass for the task to pass. A failure in either section triggers the zero-gap gate.
- **Verification**: Read QA-RESULTS.md. Confirm both `## Test Cases` results and `## Comprehension Tests` results are present. Confirm the final verdict considers both.

### TC-5: Script-only task — no comprehension section, skip comprehension
- **Precondition**: A task modifies only `references/scripts/compose.py` (pure script change). The TEST-PLAN.md has standard TCs but NO `## Comprehension Questions` section.
- **Steps**:
  1. QA subagent reads TEST-PLAN.md.
  2. QA subagent executes standard TCs.
  3. QA subagent checks for a `## Comprehension Questions` section — none found.
- **Expected**: No comprehension agent is spawned. QA-RESULTS.md contains only standard TC results. No `## Comprehension Tests` section appears. The task passes or fails based on standard TCs alone.
- **Verification**: Read QA-RESULTS.md. Confirm no `## Comprehension Tests` section exists. Confirm no comprehension agent spawn occurred (no "Comprehension" header in results).

### TC-6: 4+ sub-skills affected — adaptive multi-spawn
- **Precondition**: A large template change affects 4 or more sub-skills (e.g., modifying `pull-latest.md`, `verification.md`, `task-intake.md`, and `improvement-scan.md`). The TEST-PLAN.md `## Comprehension Questions` section lists CQs grouped by sub-skill.
- **Steps**:
  1. QA subagent reads TEST-PLAN.md and identifies 4+ sub-skills in the comprehension section.
  2. QA subagent spawns multiple comprehension agents (one per sub-skill or logical group), each with a neutral prompt scoped to the relevant file(s).
  3. Each comprehension agent answers its CQs independently (fresh context, no cross-contamination).
  4. Results from all spawns are collected into QA-RESULTS.md.
- **Expected**: Multiple comprehension agent spawns occur. Each spawn's results are recorded separately in QA-RESULTS.md (grouped by sub-skill or spawn). All must pass. Context isolation is maintained — no agent sees another agent's answers.
- **Verification**: Read QA-RESULTS.md `## Comprehension Tests` section. Confirm results are grouped by sub-skill. Confirm 2+ separate spawn groups are visible. Confirm each spawn group has independent PASS/FAIL entries.

### TC-7: Fewer than 4 sub-skills — single spawn
- **Precondition**: A template change affects 2 sub-skills. The TEST-PLAN.md has CQs for both.
- **Steps**:
  1. QA subagent reads TEST-PLAN.md and identifies fewer than 4 sub-skills.
  2. QA subagent spawns a single comprehension agent with all CQs.
- **Expected**: Only one comprehension agent spawn occurs. All CQs answered in a single session. Results appear in one block in QA-RESULTS.md.
- **Verification**: Read QA-RESULTS.md. Confirm comprehension results are in a single group, not split across multiple spawns.

### TC-8: PM generates comprehension questions in Phase 3 test plan
- **Precondition**: PM is running the Phase 3 (Planning) step for a task that modifies LLM-consumed instruction files (sub-skills or CLAUDE.md).
- **Steps**:
  1. PM spawns the test plan subagent for Phase 3.
  2. The subagent reads RESEARCH.md and CONTEXT.md.
  3. The subagent drafts the test plan including a `## Comprehension Questions` section.
  4. PM reviews and finalizes the test plan.
- **Expected**: The test plan contains a `## Comprehension Questions` section with: a `**Method**` line specifying files to read and neutral prompt, a `**Pass criteria**` line stating 100% correct, and CQ-N entries each with `Question`, `Expected`, and `Derived from` fields.
- **Verification**: Read the generated TEST-PLAN.md. Confirm the `## Comprehension Questions` section exists and follows the format from RESEARCH.md Q5 recommendation. Confirm at least one CQ exists. Confirm each CQ has all three required fields.

### TC-9: PM does NOT generate comprehension questions for script-only task
- **Precondition**: PM runs Phase 3 for a task that only modifies Python scripts (no template/instruction changes).
- **Steps**:
  1. PM spawns the test plan subagent.
  2. The subagent reads RESEARCH.md (which lists only script files in "Files touched").
- **Expected**: The generated test plan does NOT contain a `## Comprehension Questions` section. Only standard TCs, smoke tests, and regression risks are present.
- **Verification**: Read the generated TEST-PLAN.md. Confirm no `## Comprehension Questions` section exists.

### TC-10: 100% pass rate required — partial pass still fails
- **Precondition**: 5 CQs in the test plan. Comprehension agent answers 4 correctly and 1 incorrectly.
- **Steps**:
  1. QA subagent runs comprehension tests.
  2. 4/5 CQs pass, 1 fails.
- **Expected**: Overall comprehension result is FAIL. Zero-gap gate applies. Task goes back to `in-progress`. The Discussion comment lists the specific failed CQ.
- **Verification**: Read QA-RESULTS.md. Confirm 4 PASS and 1 FAIL entries. Confirm overall verdict is FAIL. Confirm the task was NOT marked `pending-ship`.

## Side Effect Regression Tests

### TC-11: Existing QA verification unchanged for script-only tasks
- **Precondition**: A script-only task is at `pending-test` with a TEST-PLAN.md that has no comprehension section (written before #1077).
- **Steps**: QA runs its normal verification flow (Step 5 in verification.md).
- **Expected**: QA executes standard TCs exactly as before. No comprehension step is attempted. The verification flow, Discussion comments, and status transitions are identical to pre-#1077 behavior.
- **Verification**: Compare QA-RESULTS.md output with a known-good pre-#1077 result for a script-only task. Confirm format and flow are unchanged.

### TC-12: Zero-gap gate still works with comprehension tests present
- **Precondition**: A task with both standard TCs and comprehension CQs. Standard TC-1 fails, all CQs pass.
- **Steps**: QA subagent runs all tests.
- **Expected**: Task is marked FAIL and returned to `in-progress` because of the standard TC failure, even though comprehension tests passed. The zero-gap gate applies across ALL test types, not just comprehension.
- **Verification**: Read QA-RESULTS.md. Confirm standard TC failure is listed. Confirm task status is `in-progress` (not `pending-ship`).

### TC-13: Smoke tests still required alongside comprehension
- **Precondition**: A task with CQs in the test plan AND a `## Smoke Tests` section.
- **Steps**: QA subagent executes all TCs, all CQs, AND all smoke tests.
- **Expected**: Smoke tests appear in QA-RESULTS.md alongside TC results and comprehension results. A smoke test failure triggers the zero-gap gate regardless of comprehension pass.
- **Verification**: Read QA-RESULTS.md. Confirm smoke test results are present. Confirm they are evaluated as part of the overall pass/fail verdict.

### TC-14: Comprehension testing is conditionally mandatory — only for LLM-consumed instruction changes
- **Precondition**: Two tasks at `pending-test`: Task A modifies `verification.md` (LLM-consumed), Task B modifies `compose.py` (deterministic script).
- **Steps**: QA verifies both tasks.
- **Expected**: Task A's test plan has a `## Comprehension Questions` section and QA runs comprehension tests. Task B's test plan has no such section and QA does not run comprehension tests. Neither task is penalized for the presence/absence of the section — the section is simply included or omitted based on what files the task touched.
- **Verification**: Read both QA-RESULTS.md files. Confirm Task A has comprehension results, Task B does not.

## Upgrade Verification

### TC-15: compose.py deploy-all propagates changes
- **Precondition**: The changes to `references/sub-skills/qa-specific/verification.md` and `references/sub-skills/pm-specific/task-intake.md` have been made.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Read the composed CLAUDE.md files for QA (`.squidsquad/qa/CLAUDE.md`) and PM (`.squidsquad/pm/CLAUDE.md`).
- **Expected**: QA's composed CLAUDE.md includes the new comprehension test execution step in its verification section. PM's composed CLAUDE.md includes the updated test plan template with the `## Comprehension Questions` section format.
- **Verification**: `grep -c "Comprehension" .squidsquad/qa/CLAUDE.md` returns > 0. `grep -c "Comprehension" .squidsquad/pm/CLAUDE.md` returns > 0.

### TC-16: Graceful degradation — old installs without #1077 still work
- **Precondition**: An install that has NOT applied #1077 (old verification.md and task-intake.md).
- **Steps**: QA runs its normal verification on a task with a standard TEST-PLAN.md (no comprehension section).
- **Expected**: Everything works exactly as before. No errors, no missing section warnings, no behavioral change. The absence of comprehension sections is a silent no-op.
- **Verification**: Confirm old verification.md does not reference "Comprehension" (it should not, pre-#1077). Confirm QA-RESULTS.md from old flow has no comprehension section.

### TC-17: QA template updated — verification.md contains comprehension execution step
- **Precondition**: #1077 implementation is complete.
- **Steps**: Read `references/sub-skills/qa-specific/verification.md`.
- **Expected**: The file contains instructions for QA to: (a) detect a `## Comprehension Questions` section in the test plan, (b) spawn a comprehension agent with a neutral prompt, (c) record results in a `## Comprehension Tests` section of QA-RESULTS.md, (d) apply 100% pass rate, (e) use adaptive spawn (single vs multi) based on sub-skill count.
- **Verification**: Read the file and confirm each of the 5 elements (a-e) is present.

### TC-18: PM template updated — task-intake.md includes comprehension questions format
- **Precondition**: #1077 implementation is complete.
- **Steps**: Read `references/sub-skills/pm-specific/task-intake.md`.
- **Expected**: The Phase 3 test plan template includes a `## Comprehension Questions` section with the format: `**Method**`, `**Pass criteria**`, and CQ-N entries with `Question`, `Expected`, `Derived from` fields. The section is documented as conditionally mandatory (required when task touches LLM-consumed instructions, omitted otherwise).
- **Verification**: Read the file and confirm the comprehension section format is present in the Phase 3 template. Confirm conditional-mandatory language is present.

## Comprehension Questions

**Method**: Spawn a fresh agent. Point it at `references/sub-skills/qa-specific/verification.md` and `references/sub-skills/pm-specific/task-intake.md` (post-#1077 versions). Ask each question below. Record answers.
**Pass criteria**: All 8 questions answered correctly without hints.

### CQ-1: When is comprehension testing required?
- **Question**: "Read these files. Under what conditions must a test plan include comprehension questions?"
- **Expected**: When the task modifies LLM-consumed instructions (sub-skills, CLAUDE.md templates, SOUL.md, behavioral specs). Script-only or config-only tasks do not require them.
- **Derived from**: TC-14

### CQ-2: What prompt style is used for the comprehension agent?
- **Question**: "How should the comprehension agent be prompted? What constraint is placed on how it answers?"
- **Expected**: Neutral prompt with file-scope constraint — "Read these files and answer ONLY from what you find." The agent must derive answers from the actual files, not training data.
- **Derived from**: TC-3

### CQ-3: What is the pass rate for comprehension tests?
- **Question**: "If a comprehension test has 5 questions and the agent answers 4 correctly, does it pass?"
- **Expected**: No. 100% pass rate is required. Any wrong answer = failure. Zero-gap gate applies.
- **Derived from**: TC-10

### CQ-4: When does multi-spawn trigger?
- **Question**: "Under what condition does QA spawn multiple comprehension agents instead of one?"
- **Expected**: When 4 or more sub-skills are affected by the change. Below 4, a single spawn handles all CQs.
- **Derived from**: TC-6, TC-7

### CQ-5: Where do comprehension results go in QA-RESULTS.md?
- **Question**: "In what section of QA-RESULTS.md are comprehension test results recorded?"
- **Expected**: In a separate `## Comprehension Tests` section within QA-RESULTS.md. Results are in the same file as standard TC results, under the unified zero-gap gate.
- **Derived from**: TC-1

### CQ-6: Who generates comprehension questions?
- **Question**: "At what phase of the task lifecycle are comprehension questions created, and by which role?"
- **Expected**: PM generates them during Phase 3 (Planning/test plan creation). They are part of the test plan, not generated ad-hoc by QA.
- **Derived from**: TC-8

### CQ-7: What happens when a comprehension test fails?
- **Question**: "If a comprehension agent answers a question incorrectly, what does QA do?"
- **Expected**: QA marks the CQ as FAIL in QA-RESULTS.md, the overall task verdict is FAIL, the task transitions back to in-progress, and a Discussion comment is appended listing the specific failed CQ(s). The failure is treated as a legitimate finding (either the implementation is wrong or the instructions are ambiguous).
- **Derived from**: TC-2

### CQ-8: What is the format of a CQ entry in the test plan?
- **Question**: "What fields must each comprehension question entry contain in the test plan?"
- **Expected**: Each CQ-N entry must have: `Question` (the natural language question), `Expected` (what a correct answer includes), and `Derived from` (which TC it traces to).
- **Derived from**: TC-8, TC-18

## Smoke Tests

- [ ] `references/sub-skills/qa-specific/verification.md` contains the word "Comprehension" (case-sensitive)
- [ ] `references/sub-skills/pm-specific/task-intake.md` contains the word "Comprehension" (case-sensitive)
- [ ] `python references/scripts/compose.py deploy-all` exits with code 0
- [ ] `.squidsquad/qa/CLAUDE.md` contains "Comprehension" after deploy-all
- [ ] `.squidsquad/pm/CLAUDE.md` contains "Comprehension" after deploy-all
- [ ] No new Python scripts, config values, or migration steps introduced (template-only change)
- [ ] Existing TEST-PLAN.md files (e.g., FEAT-SKILL-1074-TEST-PLAN.md) are unmodified by the change

## Regression Risks

- **QA subagent prompt breakage**: If the QA subagent prompt in verification.md is modified incorrectly, it could break existing test plan execution (not just comprehension). Verify the existing subagent prompt for standard TCs is unchanged.
- **Test plan template inflation**: Adding the comprehension section to the Phase 3 template could cause the subagent to generate comprehension questions for every task, even script-only ones. Verify the conditional-mandatory language is clear and tested (TC-9).
- **compose.py deploy-all ordering**: If compose.py processes files in a different order after the template changes, it could produce different CLAUDE.md output. Verify deploy-all is idempotent (running twice produces identical output).
- **Token budget for QA cycles**: Comprehension agent spawns consume tokens. If a QA cycle verifies multiple tasks with comprehension tests, it could exceed context limits. Monitor token usage during testing.
- **Interaction with #475 (token efficiency)**: #475 already planned comprehension TCs in a different format (Pattern B). If #1077 standardizes Pattern A, ensure #475's existing TCs can be adapted without conflict.
- **Adaptive spawn threshold ambiguity**: The "4+ sub-skills" threshold is a locked decision, but the exact counting method (unique sub-skill files vs. logical groups) is dev discretion. If the heuristic is too aggressive, unnecessary multi-spawns waste tokens. If too conservative, large changes get insufficient isolation. Watch for edge cases at exactly 4 sub-skills.
