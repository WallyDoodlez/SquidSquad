### Step 2b — Implement Task (continued from Step 2)

_This step is reached when Step 2 (deterministic triage) picks a task from the work queue._

Print: `[🦑 HH:MM:SS] Implementing #[NUMBER]...`

1. Comment and transition status:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   ```
1b. **Branch checkout** (#3296): `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]` — checks out the task's feature branch if branch-workflow is enabled.
2. **Read planning artifacts** — PM creates these during task intake. Check both locations:
   - `.squidsquad/pm/planning/` (PM's planning directory — primary location)
   - `.squidsquad/[ROLE]/planning/` (your own planning directory — fallback)
   - Look for files matching the issue number (e.g. `FEAT-SKILL-195-CONTEXT.md`)
   - RESEARCH.md, CONTEXT.md, TEST-PLAN.md — respect locked decisions, note dev discretion areas
   - If PM comments reference planning artifacts but you cannot find them, **push back** (see Prohibitions)
2c. **Consult the vault** (#5572) — before implementing, search the vault for relevant context:
   ```bash
   grep -rl "[keyword]" .squidsquad/vault/ --include="*.md" | head -5
   ```
   Check for: decisions that constrain the approach, patterns to follow, learnings from similar past work, and human preferences. Especially check `[[human-profile]]` and BRIEFING.md. This takes seconds and prevents rework from missed context.
3. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`, planned approach, and acceptance criteria checklist.
4. Implement the task according to the acceptance criteria. Respect locked decisions from CONTEXT.md. Implement required side effect mitigations. Update working state as you complete sub-steps.
5. Run the test command: `[ROLE_TEST_CMD]`
6. **Run smoke tests** from TEST-PLAN.md (if it exists) before marking as Pending Test.
7. **Update docs**: Update only technical documentation (API docs, code comments, architecture notes). User-facing docs are handled by DM. If the change affects user-facing behavior, comment delivery notes on the Issue.
8. **Copy changed references to live**: If any files in `references/` were modified (e.g. `statusline.sh`, `hints-*.txt`), copy them to the live `.squidsquad/` location so changes take effect immediately.
9. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false`, do NOT transition — re-read the acceptance criteria and apply the implementation.
9b. **Self-verification reflection** — before marking pending-test, stop and critically review your own work:
   - **Regression**: Does this change break existing behavior? Read the code paths you touched — what else depends on them?
   - **Integration**: Does this work correctly with the current system setup? Is it compatible with config, compose, and the deployed state?
   - **Philosophy**: Does this violate any project philosophy, vault decisions, or established patterns?
   - **Personas**: Will this break workflows for any agent role (PM, QA, DM, human)? Think through each consumer of your change.
   If ANY of these checks reveal a concern — fix it before transitioning. Do not ship known concerns for QA to catch.
9c. **External code review** — after self-review passes, run an external model review before marking pending-test. Self-review catches what you know; external review catches what you missed.

   **Stage all changes first**:
   ```bash
   git add -A
   ```

   **Locate planning artifacts** — when a task has a CONTEXT/TEST-PLAN
   in `.squidsquad/pm/planning/`, the review must check the diff against
   those architectural locks, not only code quality (#8950 Gate #2 / #8916
   §9c). Discover by task-number match — this covers both legacy
   `FEAT-PM-<NUMBER>-TEST-PLAN.md` and new `TEST-PLAN-<NUMBER>.md`
   conventions, and any sibling `CONTEXT-<NUMBER>.md`:
   ```bash
   ARTIFACTS=$(ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null | paste -sd, -)
   ```

   **Get changed files and run review**:
   ```bash
   CHANGED_FILES=$(git diff --cached --name-only | paste -sd, -)
   # If $ARTIFACTS is non-empty, append it after a comma so the review
   # agent sees both the diff and the planning contract.
   INPUT_FILES="$CHANGED_FILES${ARTIFACTS:+,$ARTIFACTS}"
   python references/scripts/model_router.py code-review \
     --task-id "#[NUMBER]" \
     --input-files "$INPUT_FILES" \
     --output-file ".squidsquad/[ROLE]/planning/CODE-REVIEW-[NUMBER].md" \
     --context "Task: [title]. ACs: [acceptance criteria summary]. Project philosophy: [key constraints]. If planning artifacts (CONTEXT-*, TEST-PLAN-*) are present in --input-files, verify the diff conforms to the architectural locks documented there — not only code quality."
   ```

   **If external model unavailable** (exit code 1 or 2): fall back to Claude via the Agent tool with the same review prompt (read the changed files, review against ACs and project philosophy, output structured findings).

   **Process findings** — for each finding, choose one disposition:
   - **Fix**: Apply the suggested fix. Re-run tests after fixing.
   - **File-to-PM**: The finding reveals a design-level flaw (AC gap, philosophy violation, wrong approach). The review loop **exits immediately**. Transition to `planning`:
     ```bash
     python references/scripts/tracker.py create-issue --title "[finding summary]" --body "[evidence from review]" --role pm --severity medium --reporter [ROLE]-lead
     python references/scripts/tracker.py transition [NUMBER] in-progress planning --role [ROLE]-lead
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "External review found design-level flaw. Filed #[NEW]. Status → Planning for PM to re-plan."
     ```
     Stop here — do NOT proceed to pending-test.
   - **Justified-ignore**: The finding is not applicable to this context. Document why in the PR comment. This is a valid, non-shameful outcome — not every finding is correct.

   **Post dispositions as PR comment** (audit trail):
   ```bash
   gh pr comment [PR_NUMBER] --body "## External Code Review — Iteration [N]

   [For each finding: finding summary + disposition (fix/file-to-pm/justified-ignore) + rationale]"
   ```

   **Re-run review** after applying fixes. Loop until:
   - Clean review (zero findings) → exit loop immediately, proceed to step 10
   - 5 iterations reached with remaining findings → proceed to step 10 with all findings noted in PR comment. QA decides whether to accept.
   - File-to-PM disposition → exit loop, transition to planning (see above)

   **Escalation**: If >50% of findings across 3+ iterations are justified-ignore, note in the PR comment: "High justified-ignore rate — review model or prompt may need tuning." This is a process signal for the human.

10. If tests and smoke tests pass and changes exist:
   - Transition status:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. All tests passing. Status → Pending Test."
     ```
   - `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]` — return to working branch.
   - Clear working state.
11. If tests fail: fix the failure before changing status.
