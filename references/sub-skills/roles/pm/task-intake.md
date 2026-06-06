---
slot: instructions
ordinal: 20
roles: [pm]
---

## Task Lifecycle (5-Phase)

When the human suggests a new task, do NOT immediately file it. Run the full 5-phase lifecycle. Issues are excluded — they use the current lightweight fix → verify → close flow.

**PM produces no test artifacts** (#9184). PM defines acceptance criteria only — the AC list lives in the GitHub issue body + CONTEXT.md. Worker writes their own unit tests as part of the implementation PR. Verifier writes the test plan in `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` (derived independently from the AC list) and executes it against a real live instance. CQ specs for any task touching LLM-consumed instructions are owned by the verifier, not PM.

**Light mode**: For trivial/cosmetic tasks (typo fixes, config tweaks, doc-only changes), skip Phase 1 (Research) and Phase 2A (prep), abbreviate Phase 2. Phase 3 (AC + issue body) still runs. Verification is handled by the verifier per `qa/verification.md` (install-coupled path — wizard D4 renames to verifier/verification.md) regardless of mode. Use your judgment: if the task touches behavior or user-facing systems, use the full flow.

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

Apply this logic to: `RESEARCH.md` (Phase 1), `PHASE2-PREP.md` (Phase 2A), `CONTEXT.md` (Phase 2). PM no longer produces `TEST-PLAN.md` — that artifact is owned by the verifier under `.squidsquad/[VERIFIER_ALIAS]/planning/` (#9184).

### Phase 1 — Research

Write current state: `python references/scripts/cycle.py status-bar [ROLE] researching "Researching FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/[PM_ALIAS]/working-state.md` to include `- **Phase**: researching FEAT-[ROLE_UPPER]-XXX` so that cron-triggered cycles are suppressed during this phase.

**Check artifact resume** (see above) for `FEAT-[ROLE_UPPER]-XXX-RESEARCH.md`. If skipping, proceed to Phase 2A.

**Vault consultation** (MANDATORY — do not skip, do not spawn research without this) (#5571):

1. Read `.squidsquad/vault/BRIEFING.md` for active priorities, recent decisions, and constraints.
2. Read `.squidsquad/vault/areas/human-profile.md` for human preferences and quality expectations.
3. Search vault for notes related to the task:
   ```bash
   grep -rl "<keywords from task title>" .squidsquad/vault/ --include="*.md" | head -10
   ```
4. Read matching notes — especially `galaxy/decision-*` (architectural constraints), `galaxy/pattern-*` (validated approaches), and `galaxy/learning-*` (past mistakes to avoid).
5. Include a summary of ALL relevant vault context in the `--context` argument below so the research agent can incorporate it. If no vault context is relevant, note "Vault consulted — no relevant prior context found."

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
8. **Vault candidates**: flag any discoveries worth preserving in the vault — architectural patterns, reusable decisions, or learnings about the codebase. These are candidates only — PM decides whether to vault them. Max 5 candidates.

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

## Vault Candidates
- **Type**: [decision/pattern/learning] — [one-line description] — **Why**: [why this is vault-worthy]
- _(max 5 candidates — flag only, PM decides whether to vault)_
```

**If research reveals significant risks**, present your recommendation to the human: "Based on research, this task would [risk]. Recommend: proceed / adjust scope / reject." If warranted, recommend `Rejected` status with justification. Human can override.

**Open in editor**: After RESEARCH.md is created, offer to open it (see "Open Artifacts in Editor" below).

**Clear planning phase flag**: Remove the `**Phase**:` line from `.squidsquad/[PM_ALIAS]/working-state.md` (the artifact has been written, so suppression is no longer needed for this phase).

### Phase 2A — Discussion Prep (Subagent)

Write current state: `python references/scripts/cycle.py status-bar [ROLE] discussing "Discussion prep for FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/[PM_ALIAS]/working-state.md` to include `- **Phase**: discussing FEAT-[ROLE_UPPER]-XXX`.

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

**Set planning phase flag**: Update `.squidsquad/[PM_ALIAS]/working-state.md` to include `- **Phase**: discussing FEAT-[ROLE_UPPER]-XXX`.

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

## Worker Discretion (worker agent can choose)
- [Area]: [what the worker can decide]

## Side Effect Mitigations (required)
- [Mitigation]: [from research, must be implemented]

## Upgrade Path (required)
- [Step]: [what upgrade must do — or "N/A — no upgrade impact"]

## Out of Scope
- [Thing]: [explicitly excluded]
```

**Open in editor**: After CONTEXT.md is created, offer to open it (see "Open Artifacts in Editor" below).

**Sync issue body when CONTEXT scope is (re)written** (#8917 Change 1): When Phase 2 (deepseek review, discussion locks, scope discussion) rewrites scope on `CONTEXT.md` (or per-task `CONTEXT-<NUMBER>.md`), the corresponding GitHub Issue body MUST be updated in the same PM step. Use `gh issue edit <N> --body-file <new-body>`. The issue body and CONTEXT.md must always agree at the time of the `planned → approved` transition.

Every issue body that has a planning artifact MUST lead with an **AUTHORITATIVE SCOPE banner** pointing at the locked planning file:

```
> **AUTHORITATIVE SCOPE: `.squidsquad/[PM_ALIAS]/planning/CONTEXT.md §5.X` (or `CONTEXT-<NUMBER>.md`). Read that artifact in full. The bullets below are a summary; the planning artifact is the contract.**
```

The banner is required on every issue with a CONTEXT file — at issue creation time (Phase 3 §A below), and on every Phase 2 scope rewrite thereafter.

**Design routing**: If a `designer` agent is configured (check `config.md` Workers list for `designer` (6274.1 shim also accepts deprecated `Dev Agents:` key)), ask the human if this task needs design work using `AskUserQuestion`:

```
question: "Does this task need design work before implementation?"
options: ["Yes — route to designer", "No — worker can implement directly"]
```

- **"Yes"**: Add `- **Design**: needed` to the task file. Add a `## Design Brief` section to CONTEXT.md with: user story, target platforms, existing patterns to follow, visual references, constraints, and priority. The designer agent will pick this up.
- **"No"**: Add `- **Design**: not-needed` to the task file. Worker agent will pick it up directly.

If no `designer` agent is configured, skip this question — all tasks default to `not-needed`.

**Phase 2 Approval Gate**: After CONTEXT.md is written, present a summary of all locked decisions and use `AskUserQuestion` to confirm before proceeding:

```
question: "Phase 2 complete. Here are the locked decisions:\n\n[list each locked decision from CONTEXT.md]\n\nReady to proceed to file the task?"
options: ["Approve — proceed to Planned", "More discussion needed", "Reject this task"]
```

- **"Approve"**: Continue to Phase 3 (AC drafting + issue filing). PM does NOT produce a test plan — Verifier will write `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` from the AC list when picking up verification (#9184).
- **"More discussion needed"**: Ask the human what they want to revisit. Re-open the relevant question(s), update CONTEXT.md with revised decisions, then re-present the gate.
- **"Reject"**: Set task status to `Rejected`. Append Discussion entry with reason. Stop the intake process.

**Clear planning phase flag** after CONTEXT.md is written and Phase 2 approval gate is passed.

### Phase 2B — Re-Research Gate

**Light-mode exemption**: Light-mode tasks skip this gate entirely (their research is already abbreviated or skipped).

After Phase 2 approval and before Phase 3, compare CONTEXT.md locked decisions against RESEARCH.md assumptions to detect heavy scope deviation:

1. **Read both artifacts**:
   - `.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md` — specifically the Impact Analysis, Side Effects, and Edge Cases sections
   - `.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-CONTEXT.md` — specifically the Scope and Locked Decisions sections

2. **Evaluate deviation** against these criteria (any ONE triggers re-research):
   - **New files touched**: CONTEXT.md scope includes files not listed in RESEARCH.md Impact Analysis
   - **Different behavior**: locked decisions change the expected behavior described in research (e.g., research assumed opt-in but discussion decided opt-out)
   - **Features added or removed**: scope expanded or contracted beyond what research analyzed
   - **Fundamentally different approach**: locked decisions chose an implementation strategy research didn't consider (e.g., research assumed config change, discussion decided new script)

   Minor wording changes, cosmetic preferences, or naming choices do NOT trigger re-research.

3. **If deviation detected**:
   - Print: `[🦑 HH:MM:SS] Scope deviation detected — re-running Phase 1 research with updated scope.`
   - Re-run Phase 1 research, but pass the CONTEXT.md locked decisions as additional context so the research agent analyzes the *actual* decided scope, not the original proposal
   - The updated RESEARCH.md replaces the original (CONTEXT.md remains unchanged — it captures the human's decisions)
   - After re-research completes, proceed to Phase 3

4. **If no deviation**: Proceed silently to Phase 3.

### Phase 3 — AC Drafting + Issue Filing

Write current state: `python references/scripts/cycle.py status-bar [ROLE] planning "Filing FEAT-[ROLE_UPPER]-XXX..."`

**Set planning phase flag**: Update `.squidsquad/[PM_ALIAS]/working-state.md` to include `- **Phase**: planning FEAT-[ROLE_UPPER]-XXX`.

PM produces **acceptance criteria only** in Phase 3 (#9184). No test plan, no test cases, no comprehension questions. The AC list lives in the GitHub issue body and is the contract for both worker and verifier. Worker writes their own unit tests against the AC list. Verifier writes its own `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` derived independently from the AC list and executes it against a real live instance.

**AC Integration Check** — before writing acceptance criteria, run this mental checklist:

1. **Consumer**: Who reads/uses the output of this task? Can they reach it? How?
2. **Integration**: Does the output traverse a build/deploy/compose step? Does the AC verify it passes through?
3. **Regression**: What existing behavior could this break? Is there an AC that checks it doesn't?
4. **Testability**: Can the verifier execute a single command per AC and get a deterministic PASS/FAIL **from the AC alone, without reading the diff**?
5. **Architecture**: Does this align with vault decisions, established patterns, and project philosophy?
6. **Observability**: Each AC must be observable, deterministic, and derivable without reading code. If an AC requires inspecting the implementation to know what "pass" means, the AC is incomplete.
7. **CQ coverage signal**: If the task adds or changes LLM-consumed instructions (CLAUDE.md content, sub-skill fragments, SOUL.md, prompts), include an AC such as `AC-N (comprehension): a fresh agent given only the modified files can correctly answer [observable question(s)] about the new behavior`. PM does NOT write the CQ spec itself — verifier produces it. PM's job is to make the comprehension requirement an explicit AC so the verifier knows to cover it.

If any answer is unclear, the AC is incomplete — refine before filing.

**File the GitHub Issue** — create via `python references/scripts/tracker.py create-task` with status `Pending`. The body is the single source of truth for the AC list:

- AUTHORITATIVE SCOPE banner at the start of the body (#8917 Change 3): when the task has a `CONTEXT.md` (bundle `§5.X #<NUMBER>`) or `CONTEXT-<NUMBER>.md`, the body passed to `create-task` MUST start with the banner pointing at that locked planning file. Format:
  ```
  > **AUTHORITATIVE SCOPE: `.squidsquad/[PM_ALIAS]/planning/CONTEXT-<NUMBER>.md` (or `CONTEXT.md §5.X`). Read that artifact in full. The bullets below are a summary; the planning artifact is the contract.**
  ```
  Phase 2 (above) keeps the banner + body bullets in sync on every later scope rewrite; this rule places the banner from the start.
- Description includes research-informed constraints.
- A numbered **Acceptance Criteria** section. Each AC is observable, deterministic, and verifiable from the AC alone — worker implements against it, verifier derives its test plan from it, and they must not need to compare diff-derived guesses to agree.
- ACs include edge-case handling and side-effect mitigations from RESEARCH.md / CONTEXT.md.
- Links to RESEARCH.md and CONTEXT.md.

**No PM-side TEST-PLAN.md** — Phase 3 ends when the issue is filed. Verifier will produce `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` when picking up verification (see `qa/verification.md`).

**Clear planning phase flag** after the issue is filed. Normal PM cycling auto-resumes.

### Phase 3B — Draft PR for Planning Review (#4979)

After Phase 3 (AC drafting + issue filing) completes:

1. **Create feature branch**: `python references/scripts/git_ops.py task-begin [ROLE] [ISSUE_NUMBER]` — capture the branch name from stdout.
2. **Commit planning artifacts** to the branch:
   ```bash
   git add .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-*
   git commit -m "[ROLE]: #[NUMBER] — planning artifacts for [title]"
   ```
3. **Push and create draft PR** (use the branch name from task-begin):
   ```bash
   git push -u origin [BRANCH]
   python references/scripts/git_ops.py pr-create "[ROLE]: #[NUMBER] — [title] (planning review)" \
     "## Planning Artifacts for Review\n\nPlanning artifacts for #[NUMBER].\n\n### Artifacts\n- RESEARCH.md\n- CONTEXT.md\n\nVerifier will produce \`.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-[NUMBER].md\` independently from the AC list at verification time (#9184).\n\n### Status\nPending human review — approve via PR comments."
   ```
4. **Comment PR link on the issue**: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Planning artifacts committed. PR [URL] ready for review."`
5. **Return to working branch**: `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]`

The human reviews planning artifacts via PR comments (inline feedback on specific sections). When the human approves:
- PM converts the draft PR to ready
- PM transitions the task status to `Approved`

Ask the human if they want to approve the task now or leave as `Pending`. This is the **only** point in the lifecycle where approval should be offered — never at initial filing time.

### Phase 4 — Execution (Worker Agent)

_(Handled by the worker agent — see worker template Step 2b. Worker implements against the AC list in the issue body + CONTEXT.md and writes unit tests covering the implementation as part of the same PR.)_

### Phase 5 — Verification (Verifier)

_(Handled by the verifier — see `qa/verification.md`. Verifier derives `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` from the AC list in the issue body, then executes it against a real live instance. PM does NOT spawn verifier subagents from this template (#9184).)_

PM's only role in verification is **holding the verifier accountable**: if a task stalls at `pending-test` past the stall window, nudge the verifier via the pipeline sentinel. PM does not run test cases, does not produce QA-RESULTS.md, and does not perform the AC walk.

---

## Open Artifacts in Editor

After each planning phase creates an artifact (RESEARCH.md, CONTEXT.md), check `config.md` for an `Open Artifacts in Editor` setting. If it is set to `no`, skip silently. Otherwise, use the `AskUserQuestion` tool:

```
question: "Would you like to review [ARTIFACT_NAME] in VS Code?"
options: ["Yes, open in VS Code", "No thanks", "Never ask again"]
```

**Handling responses:**
- **"Yes, open in VS Code"**: Run `code [artifact_path]`. If the `code` command fails (not on PATH), print the full file path instead so the user can open it manually.
- **"No thanks"**: Continue to the next phase.
- **"Never ask again"**: Add `- **Open Artifacts in Editor**: no` under a new `## Editor Integration` section in `config.md`, then continue.
