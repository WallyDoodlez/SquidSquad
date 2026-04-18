## Task Lifecycle (5-Phase)

When the human suggests a new task, do NOT immediately file it. Run the full 5-phase lifecycle. Issues are excluded — they use the current lightweight fix → verify → close flow.

**Light mode**: For trivial/cosmetic tasks (typo fixes, config tweaks, doc-only changes), skip Phase 1 (Research) and Phase 2A (prep), abbreviate Phase 2. Phase 3 (test plan subagent) and Phase 5 (QA subagent) still run. Use your judgment: if the task touches behavior or user-facing systems, use the full flow.

### Artifact Resume Logic

Before starting each planning phase, check if its output artifact already exists in `.squidsquad/[ROLE]/planning/`:

1. **File exists but uncommitted** (in working tree or staged but not pushed): Skip the phase automatically. Print: `[🦑 HH:MM:SS] RESEARCH.md already exists (uncommitted) — skipping Phase 1.`
2. **File exists and committed**: Check for code changes since the artifact was created:
   ```bash
   ARTIFACT_COMMIT=$(git log -1 --format="%H" -- .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md)
   CHANGES=$(git log --oneline "$ARTIFACT_COMMIT"..HEAD -- references/ SKILL.md CHANGELOG.md)
   ```
   - If no changes: auto-reuse silently. Print: `[🦑 HH:MM:SS] RESEARCH.md exists and code unchanged — reusing.`
   - If changes found: ask the user via `AskUserQuestion`: "RESEARCH.md exists from a previous session but code has changed since. Re-research or reuse?" Options: `["Re-research (recommended)", "Reuse existing"]`.
3. **File doesn't exist**: Run the phase normally.

Apply this logic to: `RESEARCH.md` (Phase 1), `PHASE2-PREP.md` (Phase 2A), `CONTEXT.md` (Phase 2), `TEST-PLAN.md` (Phase 3).

### Phase 1 — Research

Write current state: `python references/scripts/cycle.py status-bar [ROLE] researching "Researching FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/pm/working-state.md` to include `- **Phase**: researching FEAT-[ROLE_UPPER]-XXX` so that cron-triggered cycles are suppressed during this phase.

**Check artifact resume** (see above) for `FEAT-[ROLE_UPPER]-XXX-RESEARCH.md`. If skipping, proceed to Phase 2A.

**Vault consultation** (before spawning research agent):

1. Read `.squidsquad/vault/BRIEFING.md` for active priorities and constraints.
2. Search vault for notes related to the task:
   ```bash
   grep -rl "<keywords from task title>" .squidsquad/vault/ --include="*.md" | head -10
   ```
3. Read any matching notes (decisions, patterns, learnings, human-profile).
4. Include a summary of relevant vault context in the `--context` argument below so the research agent can incorporate it.

Route to the configured model for research:

```bash
python references/scripts/model_router.py research \
  --task-id FEAT-[ROLE_UPPER]-XXX \
  --input-files "[comma-separated input file paths]" \
  --output-file ".squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md" \
  --context "Task: [title]. [body summary]"
```

If exit code is **0**: output file written by external model. Continue to review.
If exit code is **non-zero** (1 or 2): fall back to spawning a Claude subagent via the Agent tool with the same research prompt.

The research agent (whether external or Claude) analyzes:
1. **Codebase impact**: files, templates, systems touched; behavior changes
2. **Side effects**: what could break for users with existing configs, different team shapes, different OS/shells, different project types
3. **Edge cases**: unusual inputs, failure modes, race conditions, empty states
4. **Integration risks**: how this interacts with other tasks
5. **Upgrade & migration**: how do existing installs get this task? What config values, files, templates, or behavioral changes need migration steps? What happens if an existing install doesn't upgrade — does it break or gracefully degrade? This section is ALWAYS required — even trivial tasks must state "N/A — no upgrade impact."
6. **Prior art**: has something similar been done? What can we learn?
7. **Capability gap analysis**: check the target agent's role manifest for `requires_sub_skills`. For each declared capability, run `python references/scripts/capability_check.py [TARGET_ROLE]` and report any missing capabilities. If a required capability is unavailable, note it as a risk and check for fallback capabilities in the manifest's `any_of` list.

The agent writes its findings to `.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md`:

```markdown
# FEAT-[ROLE_UPPER]-XXX Research — [Title]

## Summary
[2-3 paragraphs: what was researched, recommendation, primary risks]

## Vault Context
- **BRIEFING.md priorities**: [relevant priorities — or "none"]
- **Related decisions**: [[note-name]] — [how it constrains this task]
- **Related patterns**: [[note-name]] — [how to apply]
- **Human preferences**: [relevant from human-profile — or "none"]
- **Related learnings**: [[note-name]] — [what to avoid/replicate]

## Impact Analysis
- **Files touched**: [list]
- **Behavior changes**: [list]
- **Dependencies**: [list]

## Side Effects
- **Risk 1**: [description] — Severity: [H/M/L] — Mitigation: [how]

## Edge Cases
- [Case]: [what happens, how to handle]

## Integration Risks
- [Risk]: [how this interacts with task X]

## Upgrade & Migration
- **New config values**: [list, with defaults — or "none"]
- **New files**: [list files added — or "none"]
- **Template changes**: [what changed in agent templates — or "none"]
- **Upgrade steps**: [what `/squidsquad-upgrade` must do — or "N/A — no upgrade impact"]
- **Graceful degradation**: [what happens if user doesn't upgrade — or "N/A"]

## Capability Gaps
- **[capability_id]**: [available / missing] — Provider: [type] — Fallback: [yes/no]

## Open Questions
- **Q1**: [question] — **Why**: [consequence of getting wrong]

## Recommendation
[Straightforward / Feasible with caveats / Needs rethinking]
```

**If research reveals significant risks**, present your recommendation to the human: "Based on research, this task would [risk]. Recommend: proceed / adjust scope / reject." If warranted, recommend `Rejected` status with justification. Human can override.

**Open in editor**: After RESEARCH.md is created, offer to open it (see "Open Artifacts in Editor" below).

**Clear planning phase flag**: Remove the `**Phase**:` line from `.squidsquad/pm/working-state.md` (the artifact has been written, so suppression is no longer needed for this phase).

### Phase 2A — Discussion Prep (Subagent)

Write current state: `python references/scripts/cycle.py status-bar [ROLE] discussing "Discussion prep for FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/pm/working-state.md` to include `- **Phase**: discussing FEAT-[ROLE_UPPER]-XXX`.

**Check artifact resume** for `FEAT-[ROLE_UPPER]-XXX-PHASE2-PREP.md`. If skipping, proceed to Phase 2.

For non-trivial tasks, route to the configured model for discussion prep:

```bash
python references/scripts/model_router.py discussion-prep \
  --task-id FEAT-[ROLE_UPPER]-XXX \
  --input-files ".squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md" \
  --output-file ".squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-PHASE2-PREP.md" \
  --context "Prep discussion for FEAT-[ROLE_UPPER]-XXX"
```

If exit code is **non-zero**: fall back to spawning a Claude subagent via the Agent tool. The subagent reads the RESEARCH.md and produces a discussion prep file with categorized questions, 3 options each with pros/cons, recommended option marked, and optimal question order.

The PM reads PHASE2-PREP.md to inform the discussion suggestions. Delete PHASE2-PREP.md after Phase 2 completes — CONTEXT.md captures the final decisions.

Light-mode tasks skip Phase 2A entirely.

**Clear planning phase flag** after PHASE2-PREP.md is written.

### Phase 2 — Discussion (PM + Human)

Write current state: `python references/scripts/cycle.py status-bar [ROLE] discussing "Discussion for FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/pm/working-state.md` to include `- **Phase**: discussing FEAT-[ROLE_UPPER]-XXX`.

**Check artifact resume** for `FEAT-[ROLE_UPPER]-XXX-CONTEXT.md`. If skipping, proceed to Phase 3.

Phase 2 is an interactive discussion. It is fine for it to block the loop — discussion is inherently interactive.

**Part 1 — Overview**: Present the full research summary (Phase 1 output) AND list all open questions so the human sees the full picture:

```
[Research summary]

Open questions:
Q1: [question] — Why it matters: [risk]
Q2: [question] — Why it matters: [risk]
...
QN: [question] — Why it matters: [risk]
```

**Part 2 — Interactive walk-through**: Walk through questions one at a time using the `AskUserQuestion` tool to present each as an interactive choosable dialog. For each question, call `AskUserQuestion` with:
- `question`: The question text + "Why this matters: [consequence]"
- `options`: 3 suggestions (PM's recommendations based on research) + "Let's discuss this more"

Example `AskUserQuestion` call:
```
question: "Should version bumps require zero open issues?\n\nWhy this matters: If issues are allowed, shipped versions may have known issues."
options: ["No — bump unconditionally (recommended)", "Soft gate — warn but allow", "Yes — all issues must be closed first", "Let's discuss this more"]
```

**Handling responses:**
- **Selected option (a/b/c)**: Lock the decision in CONTEXT.md, move to next question.
- **"Let's discuss this more"**: Enter a longer back-and-forth discussion. When resolved, lock the decision and move on.
- **Freeform text**: Capture as a locked decision, move on.

Continue until all questions are resolved. Capture decisions in `.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-CONTEXT.md`:

```markdown
# FEAT-[ROLE_UPPER]-XXX Context — [Title]

## Scope
[What this task delivers — clear boundary]

## Locked Decisions (human decided)
- [Decision]: [what and why]

## Dev Discretion (dev agent can choose)
- [Area]: [what the dev can decide]

## Side Effect Mitigations (required)
- [Mitigation]: [from research, must be implemented]

## Upgrade Path (required)
- [Step]: [what upgrade must do — or "N/A — no upgrade impact"]

## Out of Scope
- [Thing]: [explicitly excluded]
```

**Open in editor**: After CONTEXT.md is created, offer to open it (see "Open Artifacts in Editor" below).

**Design routing**: If a `designer` agent is configured (check `config.md` Dev Agents list for `designer`), ask the human if this task needs design work using `AskUserQuestion`:

```
question: "Does this task need design work before implementation?"
options: ["Yes — route to designer", "No — dev can implement directly"]
```

- **"Yes"**: Add `- **Design**: needed` to the task file. Add a `## Design Brief` section to CONTEXT.md with: user story, target platforms, existing patterns to follow, visual references, constraints, and priority. The designer agent will pick this up.
- **"No"**: Add `- **Design**: not-needed` to the task file. Dev agent will pick it up directly.

If no `designer` agent is configured, skip this question — all tasks default to `not-needed`.

**Phase 2 Approval Gate**: After CONTEXT.md is written, present a summary of all locked decisions and use `AskUserQuestion` to confirm before proceeding:

```
question: "Phase 2 complete. Here are the locked decisions:\n\n[list each locked decision from CONTEXT.md]\n\nReady to proceed to test planning?"
options: ["Approve — proceed to test plan", "More discussion needed", "Reject this task"]
```

- **"Approve"**: Continue to Phase 3.
- **"More discussion needed"**: Ask the human what they want to revisit. Re-open the relevant question(s), update CONTEXT.md with revised decisions, then re-present the gate.
- **"Reject"**: Set task status to `Rejected`. Append Discussion entry with reason. Stop the intake process.

**Clear planning phase flag** after CONTEXT.md is written and Phase 2 approval gate is passed.

### Phase 3 — Planning

Write current state: `python references/scripts/cycle.py status-bar [ROLE] test-planning "Test plan for FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/pm/working-state.md` to include `- **Phase**: test-planning FEAT-[ROLE_UPPER]-XXX`.

**Check artifact resume** for `FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md`. If skipping, the task is ready — update status to `Planned` (NOT `Approved` — human must explicitly approve execution).

Create two artifacts:

**A) GitHub Issue** — create via `python references/scripts/tracker.py create-task` with status `Pending`, referencing planning artifacts:
- Description includes research-informed constraints
- Acceptance criteria include edge case handling and side effect mitigations
- References RESEARCH.md and CONTEXT.md

**B) Test plan** — route to the configured model for test plan drafting:

```bash
python references/scripts/model_router.py test-plan \
  --task-id FEAT-[ROLE_UPPER]-XXX \
  --input-files ".squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md,.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-CONTEXT.md" \
  --output-file ".squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md" \
  --context "Draft test plan for FEAT-[ROLE_UPPER]-XXX"
```

If exit code is **non-zero**: fall back to spawning a Claude subagent via the Agent tool to draft the test plan covering happy paths, edge cases, regressions, upgrade verification, smoke tests, regression risks, and comprehension questions.

PM reviews the subagent's draft, adjusts as needed, and saves the final version. The format should be:

```markdown
# FEAT-[ROLE_UPPER]-XXX Test Plan — [Title]

## Test Cases

### TC-1: [Happy path]
- **Precondition**: [setup]
- **Steps**: [what to do]
- **Expected**: [result]
- **Verification**: [command or file check]

### TC-2: [Edge case]
...

### TC-3: [Side effect regression]
- **Precondition**: [existing state that should NOT change]
- **Steps**: [exercise new task]
- **Expected**: [existing behavior preserved]
- **Verification**: [how to check]

## Smoke Tests
- [ ] [Quick check 1]
- [ ] [Quick check 2]

## Regression Risks
- [Risk]: [what to watch for]

## Comprehension Questions (if task touches LLM-consumed instructions)
### CQ-1: [question a fresh agent should answer from the modified files]
- **Files**: [which files to read]
- **Expected**: [correct answer, derivable only from the files]
```

**Open in editor**: After TEST-PLAN.md is created, offer to open it (see "Open Artifacts in Editor" below).

**Clear planning phase flag** after TEST-PLAN.md is written. Normal PM cycling auto-resumes.

Ask the human if they want to approve the task now or leave as `Pending`. This is the **only** point in the lifecycle where approval should be offered — never at initial filing time.

### Phase 4 — Execution (Dev Agent)

_(Handled by the dev agent — see dev template Step 3)_

### Phase 5 — QA Test Execution (Subagent)

When verifying tasks with status `Pending Test` (in Step 6), if a TEST-PLAN.md exists, spawn a QA subagent (via the Agent tool) to execute the test plan.

Subagent prompt:
```
Read .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md. Execute each test case:
1. Read the relevant files mentioned in preconditions
2. Run any verification commands
3. Check regression risks
4. For each test case, record PASS or FAIL with notes on what was observed

Write results to .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-QA-RESULTS.md with format:
### TC-N: [title]
- **Result**: PASS / FAIL
- **Notes**: [what was observed]
- **Verified at**: [timestamp]
```

PM reviews QA-RESULTS.md and makes the final decision:
- **All pass** → Status → `Shipped`. Delete planning files (`.squidsquad/[ROLE]/planning/FEAT-XXX-*`). Append Discussion entry.
- **Any fail** → Status → `In Progress`. Append Discussion with which test cases failed and what was observed.

The PM decides — the subagent only reports results.

---

## Open Artifacts in Editor

After each planning phase creates an artifact (RESEARCH.md, CONTEXT.md, TEST-PLAN.md), check `config.md` for an `Open Artifacts in Editor` setting. If it is set to `no`, skip silently. Otherwise, use the `AskUserQuestion` tool:

```
question: "Would you like to review [ARTIFACT_NAME] in VS Code?"
options: ["Yes, open in VS Code", "No thanks", "Never ask again"]
```

**Handling responses:**
- **"Yes, open in VS Code"**: Run `code [artifact_path]`. If the `code` command fails (not on PATH), print the full file path instead so the user can open it manually.
- **"No thanks"**: Continue to the next phase.
- **"Never ask again"**: Add `- **Open Artifacts in Editor**: no` under a new `## Editor Integration` section in `config.md`, then continue.
