### Step 2b — Implement Task (continued from Step 2)

_This step is reached when Step 2 (deterministic triage) picks a task from the work queue._

Print: `[🦑 HH:MM:SS] Implementing #[NUMBER]...`

1. Comment and transition status:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   ```
1b. **Branch checkout** (#3296): `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]` — checks out the task's feature branch if branch-workflow is enabled.
2. **Read the AC list from the issue body, with CONTEXT.md as the locked decisions companion** (#8916, #9184).

   The **GitHub issue body is the authoritative source of the acceptance criteria.** PM no longer produces a test plan (#9184) — the AC list in the issue body IS the contract, and dev implements against it. CONTEXT.md captures locked decisions, scope boundaries, and side-effect mitigations agreed during Phase 2 discussion.

   Before writing any code, check for planning artifacts:
   - `.squidsquad/pm/planning/CONTEXT.md` (bundle-level; the per-task section is `### 5.X #<NUMBER> — …`)
   - `.squidsquad/pm/planning/CONTEXT-<NUMBER>.md` (per-task)
   - Fallback location: `.squidsquad/[ROLE]/planning/` (your own planning directory) — same file patterns

   Read the relevant CONTEXT section (`### 5.X #<NUMBER>` for bundle CONTEXT.md, OR the full per-task `CONTEXT-<NUMBER>.md`) AND the **Acceptance Criteria** section of the issue body **in full** before writing code. The issue body lists the ACs; CONTEXT.md states the locked architectural decisions that shape *how* to satisfy them.

   **Divergence handling**:
   - If the issue body and CONTEXT.md **agree**, proceed normally.
   - If the issue body and CONTEXT.md **disagree**, CONTEXT.md wins (locked decisions outrank body bullets — see #8917). Implement to the locked decisions. Flag the divergence in your implementation PR description (one sentence pointing PM at the body/CONTEXT mismatch) so PM can update the body via the #8917 workflow.

   If PM comments reference planning artifacts but you cannot find them, **push back** (see Prohibitions). If no CONTEXT artifact exists (bug fix or trivial task), the issue body's AC list is the contract; proceed to step 2c.

   **Do NOT look for a PM-side `TEST-PLAN-<NUMBER>.md`** — under the new workflow (#9184) PM does not produce one. QA writes its own test plan at `.squidsquad/qa/planning/TEST-PLAN-<NUMBER>.md` during verification. Dev's job is to implement against the AC list, not against a pre-written test plan.
2c. **Consult the vault** (#5572) — before implementing, search the vault for relevant context:
   ```bash
   grep -rl "[keyword]" .squidsquad/vault/ --include="*.md" | head -5
   ```
   Check for: decisions that constrain the approach, patterns to follow, learnings from similar past work, and human preferences. Especially check `[[human-profile]]` and BRIEFING.md. This takes seconds and prevents rework from missed context.
3. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`, planned approach, and acceptance criteria checklist.
4. Implement the task according to the acceptance criteria from the issue body. Respect locked decisions from CONTEXT.md. Implement required side effect mitigations. Update working state as you complete sub-steps.
4b. **Write unit tests for your implementation** (#9184). Dev's unit tests cover the code you actually wrote — concrete assertions on functions, scripts, modules, or behavior added or changed. They commit in the **same PR** as the implementation.

   - Dev's unit tests are a correctness check on the code, **not** the verification contract. They prove "I implemented what I think the AC says." They are **not** sufficient to satisfy the AC — QA executes its own AC-derived test plan against a live instance and that is the gate (see `qa/verification.md`).
   - Put tests under `tests/` using the existing layout (`tests/test_<feature>_<NUMBER>.py` or the area-appropriate location). Run them as part of the existing `[ROLE_TEST_CMD]` suite so they cannot regress silently.
   - If the implementation has no testable surface (pure prose / instruction edits with no executable code), state that explicitly in the PR description and rely on QA's CQ coverage instead of fabricating shallow tests.
5. Run the test command: `[ROLE_TEST_CMD]` — your new unit tests must pass alongside the existing suite.
6. **Update docs**: Update only technical documentation (API docs, code comments, architecture notes). User-facing docs are handled by DM. If the change affects user-facing behavior, comment delivery notes on the Issue.
7. **Copy changed references to live**: If any files in `references/` were modified (e.g. `statusline.sh`, `hints-*.txt`), copy them to the live `.squidsquad/` location so changes take effect immediately.
8. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false`, do NOT transition — re-read the acceptance criteria and apply the implementation.
8b. **Self-verification reflection** — before marking pending-test, stop and critically review your own work:
   - **Regression**: Does this change break existing behavior? Read the code paths you touched — what else depends on them?
   - **Integration**: Does this work correctly with the current system setup? Is it compatible with config, compose, and the deployed state?
   - **Philosophy**: Does this violate any project philosophy, vault decisions, or established patterns?
   - **Personas**: Will this break workflows for any agent role (PM, QA, DM, human)? Think through each consumer of your change.
   If ANY of these checks reveal a concern — fix it before transitioning. Do not ship known concerns for QA to catch.
8c. **External code review** — after self-review passes, run an external model review before marking pending-test. Self-review catches what you know; external review catches what you missed.

   **Stage all changes first**:
   ```bash
   git add -A
   ```

   **Locate planning artifacts** — when a task has a `CONTEXT-<NUMBER>.md`
   (or bundle section in `CONTEXT.md`) in `.squidsquad/pm/planning/`, the
   review must check the diff against those architectural locks, not only
   code quality (#8950 Gate #2 / #8916 §9c / #9184). PM-side `TEST-PLAN-*.md`
   files are legacy historical artifacts and may exist for older tasks;
   include them if present, but do not require them — under the new workflow
   (#9184) PM produces no test plan. Discover by task-number match:
   ```bash
   ARTIFACTS=$(ls .squidsquad/pm/planning/CONTEXT*[NUMBER]* .squidsquad/pm/planning/*[NUMBER]*TEST-PLAN* 2>/dev/null | paste -sd, -)
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
     --context "Task: [title]. ACs: [acceptance criteria summary from the issue body]. Project philosophy: [key constraints]. If a CONTEXT-* planning artifact is present in --input-files, verify the diff conforms to the architectural locks documented there. Legacy TEST-PLAN-* artifacts may also appear for older tasks — treat them as informational; the authoritative AC list is the issue body (#9184)."
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
   - Clean review (zero findings) → exit loop immediately, proceed to step 9
   - 5 iterations reached with remaining findings → proceed to step 9 with all findings noted in PR comment. QA decides whether to accept.
   - File-to-PM disposition → exit loop, transition to planning (see above)

   **Escalation**: If >50% of findings across 3+ iterations are justified-ignore, note in the PR comment: "High justified-ignore rate — review model or prompt may need tuning." This is a process signal for the human.

9. If unit tests and changes exist (and code-review iteration converged):
   - Transition status:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. All tests passing. Status → Pending Test."
     ```
   - `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]` — return to working branch.
   - Clear working state.
10. If tests fail: fix the failure before changing status.
