# FEAT-SKILL-462 Test Plan — Adaptive Setup Questions

## Test Cases

### TC-1: Q1 seeded from gh repo description
- **Precondition**: Repo has a description set on GitHub (e.g., "A CLI tool for processing CSV files"). `gh repo view` returns that description successfully.
- **Steps**: Run the setup wizard through Step 1 (project detection) into Step 1b.
- **Expected**: Q1 is presented as a seeded prompt — e.g., "I see this repo is described as 'A CLI tool for processing CSV files'. Can you tell me more about what it does?" — not as a blank "What does your project do?" Q1 is never a purely empty ask when gh description is available.
- **Verification**: Wizard output includes the repo description text in the Q1 prompt. The wizard does not ask a generic uncontextualized question.

### TC-2: Graceful degradation when gh repo view fails
- **Precondition**: `gh repo view` is unavailable or returns no description (network failure or blank description).
- **Steps**: Run the setup wizard through Step 1b with gh unavailable.
- **Expected**: Wizard falls back to asking Q1 without a seed: "What does your project do?" — no crash, no partial output, no empty prompt. Wizard continues normally from Q1 onward.
- **Verification**: Wizard does not error out. Q1 is presented as a clean open-ended question. Subsequent questions proceed normally.

### TC-3: Q2 inferred from Q1 answer (not hardcoded)
- **Precondition**: Q1 answered with "It's a React web app with a Node.js backend."
- **Steps**: Observe Q2 content.
- **Expected**: Q2 asks about something relevant to a React+Node project that wasn't already answered — e.g., test framework, CI setup, or deployment target. Q2 does NOT ask "Do you have a frontend?" (already answered). Q2 does NOT ask about design tools if the user mentioned no design tools. Q2 is not a fixed hardcoded question.
- **Verification**: Q2 topic is coherent with Q1 answer. No redundant coverage of information already given. If Q1 mentioned "we use Jest," Q2 does not ask about testing.

### TC-4: Q3 asks about remaining blind spots after Q1+Q2
- **Precondition**: Q1 = "React + Node.js app." Q2 = "We use Jest and Cypress, CI on GitHub Actions." Q3 = ?
- **Steps**: Observe Q3 content.
- **Expected**: Q3 targets the largest remaining unknown given what Q1+Q2 already established. E.g., asks about conventions/branching, deployment targets, or external tools not yet mentioned. Q3 does NOT re-ask about stack (Q1), tests (Q2), or CI (Q2).
- **Verification**: Q3 is on a different topic than Q1 and Q2. Q3 is specific — "What external tools or services does your project integrate with?" rather than another generic open question.

### TC-5: Multi-part questions work
- **Precondition**: Wizard has identified that both stack AND test commands are unknown after Q1.
- **Steps**: Observe whether wizard bundles related topics into one question.
- **Expected**: Wizard may ask a multi-part question: "What's your tech stack and how do you run your tests?" — covering two info categories in a single exchange. The wizard does not split these into two separate questions unnecessarily.
- **Verification**: A single wizard message covers multiple info categories when they are closely related. The answer to a multi-part question populates multiple config/SOUL fields.

### TC-6: 3 question target — stops when config.md + SOUL.md can be populated
- **Precondition**: After 3 questions, the wizard has enough information to populate all core config.md project fields and seed SOUL.md.
- **Steps**: Complete the 3-question block and observe whether the wizard moves on to Step 2.
- **Expected**: Wizard stops at Q3 and proceeds to Step 2 (intent classification). Does not ask Q4 or Q5 when information gathered is sufficient.
- **Verification**: Wizard output shows Step 2 beginning after Q3 when answers were informative. No Q4 question is presented.

### TC-7: 5 question max cap enforced
- **Precondition**: User gives vague one-word answers to Q1, Q2, and Q3 (e.g., "software", "not sure", "none").
- **Steps**: Observe whether wizard asks Q4 and Q5, and whether it stops after Q5 regardless.
- **Expected**: Wizard escalates to Q4 and Q5 to fill gaps. After Q5, wizard moves on to Step 2 regardless of how incomplete the answers are. No Q6 is asked. SOUL.md is seeded with whatever was gathered.
- **Verification**: Wizard asks at most 5 questions in Step 1b. After Q5, Step 2 begins. Install spec JSON contains whatever partial answers were collected.

### TC-8: Answers populate config.md project fields
- **Precondition**: Wizard completed Step 1b with rich answers (project description, stack, test commands, conventions).
- **Steps**: Complete full wizard run. Inspect the generated `config.md`.
- **Expected**: `config.md` contains `project.description` populated from Q1 answer (processed summary). New fields `project.domain_context` and `project.conventions` are present with values derived from the answers. `E2E Tests` / test command fields are populated if test commands were mentioned.
- **Verification**: `grep -A5 "## Project" .squidsquad/config.md` shows populated description. Relevant fields are non-empty.

### TC-9: Answers seed SOUL.md ### Project Context section
- **Precondition**: Wizard completed Step 1b. Fresh install (SOUL.md does not yet exist for any role).
- **Steps**: Complete full wizard run including Step 7 (scaffold). Inspect `.squidsquad/pm/SOUL.md`, `.squidsquad/skill/SOUL.md`, etc.
- **Expected**: Each scaffolded agent's SOUL.md contains a `### Project Context` section. The section is populated with a narrative summary derived from the adaptive question answers (domain, tech stack, conventions, key tools). The section is distinct from the static role identity sections above it.
- **Verification**: `grep -A20 "### Project Context" .squidsquad/pm/SOUL.md` shows project-specific content, not a blank stub.

### TC-10: Raw answers stored in install spec JSON
- **Precondition**: Wizard completed Step 1b.
- **Steps**: After wizard completes, inspect the install spec JSON file (the intermediate artifact before scaffold_install runs).
- **Expected**: Install spec contains a field for raw adaptive question answers (exact user text). Processed summaries appear in config.md/SOUL.md; raw answers are traceable in the spec for audit purposes.
- **Verification**: Install spec JSON has a field (e.g., `adaptive_answers` or similar) containing the raw Q&A exchange. The processed `project.description` in config.md may differ from the raw answer but both exist.

### TC-11: Designer detection from UI/design keywords
- **Precondition**: User answers Q1: "It's a web app. We design everything in Figma before building."
- **Steps**: Observe whether wizard suggests designer agent and/or pre-selects Figma capability.
- **Expected**: Wizard detects "Figma" keyword. Pre-selects `tools.designer.tool = "figma"` in install spec. Suggests adding a designer agent to the roster during Step 2 or Step 4. The Figma pre-selection appears in the Step 6 review screen for human confirmation — not silently applied.
- **Verification**: Step 6 review screen lists "Designer tool: Figma (auto-detected)" or equivalent. Install spec contains Figma assignment. User can edit or confirm.

### TC-12: Capability sub-skill suggestion when design tools mentioned
- **Precondition**: User mentions "Google Stitch" in answers.
- **Steps**: Observe Step 6 review screen content.
- **Expected**: Wizard detects "Google Stitch" or "Stitch" keyword, matches against capability manifest (`google_stitch`), pre-selects it for the designer role. Review screen shows the pre-selection.
- **Verification**: Step 6 review screen mentions Google Stitch auto-detection. Install spec has the capability assignment.

### TC-13: No capability auto-assignment for unrecognized tools
- **Precondition**: User mentions "AWS Amplify" — a tool not in the current capability registry.
- **Steps**: Observe whether wizard tries to assign a capability for it.
- **Expected**: Wizard notes that AWS Amplify is not in the registry (or simply ignores it without error). No false-positive capability assignment. No crash. Wizard continues normally.
- **Verification**: Review screen does not show an AWS Amplify capability pre-selection. No error in wizard output.

### TC-14: Skip-if-answered logic — no duplicate questions in Step 4
- **Precondition**: Q1 answer stated "We use TypeScript and React." Q2 stated "We use Jest for unit tests."
- **Steps**: Observe Step 4 (setup_requirements walker) for the dev agent.
- **Expected**: Step 4 does not ask about tech stack or test framework again. Wizard pre-fills `dev.stack = TypeScript/React` and confirms rather than asking from scratch. Test command field is pre-filled from Q2 answer.
- **Verification**: Step 4 for the dev agent shows confirmation of pre-filled values, not fresh questions for already-answered info. Wizard output says "Based on your earlier answer, I've noted your stack as TypeScript/React — confirm?" or similar.

### TC-15: SOUL.md never overwritten on upgrade
- **Precondition**: Existing install with a manually customized `.squidsquad/pm/SOUL.md` that has a `### Project Context` section with custom content.
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade does NOT overwrite the existing SOUL.md. Custom `### Project Context` content is preserved. Only CLAUDE.md is recomposed. The existing project context seeding is never clobbered.
- **Verification**: After upgrade, `.squidsquad/pm/SOUL.md` content matches pre-upgrade state exactly. Git diff shows no changes to SOUL.md.

### TC-16: SOUL.md template stub added on upgrade (empty section)
- **Precondition**: Existing install with a SOUL.md that has NO `### Project Context` section (pre-462 install).
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade adds an empty `### Project Context` stub to each agent's SOUL.md (does not attempt to re-ask the setup questions or populate content). The stub is an empty placeholder the user can fill manually.
- **Verification**: After upgrade, `grep "Project Context" .squidsquad/pm/SOUL.md` returns a match. The section body is empty or contains a placeholder comment.

### TC-17: Adaptive questions inform Step 2 intent classification
- **Precondition**: User's Q1 answer clearly indicates software development ("It's a Python CLI tool for data ETL").
- **Steps**: Observe Step 2 (intent + preset classification) behavior.
- **Expected**: Step 2 classifier uses the Q1 answer context. It does NOT ask "what are you building?" again as if Step 1b never happened. The preset classification (software-dev) is informed by the adaptive answers and can be reached with less ambiguity.
- **Verification**: Step 2 does not re-ask for project description. The classifier output references or is consistent with Step 1b answers.

### TC-18: Re-run (regenerate) skips adaptive questions
- **Precondition**: An existing install with config.md already present. User runs wizard in `regenerate` mode (Step 0b re-run detection).
- **Steps**: Run wizard in regenerate mode.
- **Expected**: Step 1b adaptive questions are skipped. The regenerate flow (which skips Steps 1-6) does not re-ask project context questions. Existing config.md project fields are preserved.
- **Verification**: Wizard output in regenerate mode does not show Q1, Q2, or Q3. Wizard proceeds directly to Step 7 (commit and write) or equivalent regenerate behavior.

### TC-19: Full-rebuild runs adaptive questions
- **Precondition**: Existing install. User runs wizard in `full-rebuild` mode.
- **Steps**: Run wizard in full-rebuild mode.
- **Expected**: Step 1b runs as normal — adaptive questions are asked fresh. Full-rebuild goes through the complete flow including the new Step 1b.
- **Verification**: Wizard output shows Q1, Q2, Q3 in the full-rebuild flow.

---

## Smoke Tests

- [ ] Wizard Step 1b runs without error when `gh repo view` succeeds
- [ ] Wizard Step 1b runs without error when `gh repo view` fails
- [ ] After wizard completes, `config.md` has non-empty `project.description`
- [ ] After wizard completes, at least one agent SOUL.md has `### Project Context` section
- [ ] Wizard never asks more than 5 questions in Step 1b
- [ ] Install spec JSON is valid JSON and contains adaptive answers field
- [ ] Step 6 review screen shows any auto-detected capabilities
- [ ] Step 4 setup_requirements does not repeat questions answered in Step 1b
- [ ] `grep "Project Context" .squidsquad/*/SOUL.md` returns matches after fresh install

---

## Regression Risks

- **Existing wizard flow broken**: The new Step 1b inserts between Steps 1 and 2. Verify the original wizard flow (project name → intent → preset → roles → interval → review → scaffold) still works correctly end-to-end with Step 1b present.
- **Q1 prompt duplication**: Step 1 already uses `gh repo view` to get project name. Step 1b also uses it for description seeding. Verify no duplicate `gh repo view` calls, and that both steps use the same cached data.
- **SOUL.md size growth**: Adding `### Project Context` sections to every agent SOUL.md increases token cost for all agents. Verify the section is concise (no verbose dumps) and fits within acceptable SOUL.md size limits.
- **wizard.py schema changes**: New `project.domain_context` and `project.conventions` fields in the install spec schema. Verify that existing wizards reading the old spec format do not crash on missing fields (both must be optional with empty defaults).
- **build_config_md renders new fields correctly**: If `project.domain_context` or `project.conventions` is empty (user gave vague answers), `build_config_md` must render these as empty or omit them — no "None" or null strings in config.md.
- **Capability pre-selection not silently applied**: All auto-detected capabilities must appear in the Step 6 review screen. No capability is assigned without the user seeing it in review.
- **Step 1b added ~50 lines to WIZARD.md**: Verify WIZARD.md total size remains readable and within the agent's practical context budget for a single setup session.
