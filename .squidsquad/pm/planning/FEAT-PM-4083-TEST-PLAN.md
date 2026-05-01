# FEAT-PM-4083 Test Plan — L4 Project Customization & Layer Lifecycle

## Scope

Covers Phase A (setup wizard: pre-flight + 7 steps), Phase B (L4 propagation: PM writes → compose → reboot), Phase C (upgrade: pre-layer → post-layer migration), and the hard gate checklist.

---

## Test Cases

### TC-1: Pre-flight — gh auth missing stops setup
- **Precondition**: `gh` CLI is not authenticated (run `gh auth logout` or point `GH_TOKEN` to an invalid value in test environment).
- **Steps**: Invoke `wizard.py` (or `/squidsquad-setup`).
- **Expected**: Setup halts immediately before Step 1. Clear error printed to stdout, e.g. "Pre-flight failed: gh CLI not authenticated." No files written, no wizard questions asked.
- **Verification**: Exit code is non-zero. No `.squidsquad/` config, L1, L2, L3, or L4 files created.

---

### TC-2: Pre-flight — git repo missing stops setup
- **Precondition**: Run wizard from a directory that is not a git repo (no `.git/` directory).
- **Steps**: Invoke `wizard.py` (or `/squidsquad-setup`).
- **Expected**: Setup halts immediately before Step 1 with error, e.g. "Pre-flight failed: not a git repository." No files written.
- **Verification**: Exit code is non-zero. Confirm no `.squidsquad/` directory was created.

---

### TC-3: Pre-flight — no git remote detected stops setup
- **Precondition**: Git repo exists (`git init`) but has no remote (`git remote -v` returns empty).
- **Steps**: Invoke `wizard.py` (or `/squadsquad-setup`).
- **Expected**: Setup halts with error, e.g. "Pre-flight failed: no git remote detected." No files written.
- **Verification**: Exit code is non-zero. No install artifacts present.

---

### TC-4: Setup Step 1 — repo scan detects languages and frameworks
- **Precondition**: Valid pre-flight environment. Project directory contains representative files (e.g. `Package.swift` for iOS, `pubspec.yaml` for Flutter, `package.json` + `angular.json` for web, `requirements.txt` for Python backend).
- **Steps**: Start wizard. Complete pre-flight (passes). Observe Step 1 output.
- **Expected**: Wizard Step 1 reports detected languages/frameworks in summary. Output must include at least one correct detection (e.g. "Detected: Swift/iOS" for a Swift project). Detection results are displayed to the user before the preset question.
- **Verification**: Read Step 1 console output or written scan artifact. At least one framework/language correctly identified. No crash on projects with no recognised files (graceful unknown).

---

### TC-5: Setup Step 3 — iOS preset installs correct L3 for all roles
- **Precondition**: Valid pre-flight. Wizard reaches project type question.
- **Steps**: Select `ios` preset.
- **Expected**: L3 files installed for dev, pm, qa, dm — all using the iOS variant (`dev-ios`, `pm-ios`, `qa-ios`, `dm-ios`). No L3 files for unrelated presets (e.g. no `dev-web` L3 present).
- **Verification**: Check that L3 source files (under `references/roles/l3/` or equivalent) for `dev-ios`, `pm-ios`, `qa-ios`, `dm-ios` are referenced or written. Confirm no cross-preset contamination.

---

### TC-6: Setup Step 3 — Android preset installs correct L3 for all roles
- **Precondition**: Same as TC-5. Select `android`.
- **Expected**: `dev-android`, `pm-android`, `qa-android`, `dm-android` L3 installed. No iOS L3 files.
- **Verification**: Same check pattern as TC-5.

---

### TC-7: Setup Step 3 — Multi-platform preset installs correct L3 for all roles
- **Precondition**: Same as TC-5. Select `multi-platform`.
- **Expected**: L3 for all roles is multi-platform aware (cross-platform concerns, shared codebase, React Native/Flutter/KMP awareness). All 4 roles covered.
- **Verification**: L3 files for each role present and named/tagged as multi-platform. No single-platform L3 installed.

---

### TC-8: Setup Step 3 — Web preset installs correct L3 for all roles
- **Precondition**: Select `web`.
- **Expected**: `dev-web`, `pm-web`, `qa-web`, `dm-web` L3 installed.
- **Verification**: Correct L3 files present, no non-web L3 files.

---

### TC-9: Setup Step 3 — PWA preset installs correct L3 for all roles
- **Precondition**: Select `pwa`.
- **Expected**: L3 for all roles reflects PWA focus (service workers, offline-first, installability, lighthouse, web manifest, push notifications).
- **Verification**: L3 files present and contain PWA-specific content or reference PWA L3 definitions.

---

### TC-10: Setup Step 3 — Backend preset installs correct L3 for all roles
- **Precondition**: Select `backend`.
- **Expected**: L3 for all roles reflects backend focus (API design, database, auth, scalability, server-side architecture).
- **Verification**: Correct backend L3 files present.

---

### TC-11: Setup Step 3 — Fullstack preset installs correct L3 for all roles
- **Precondition**: Select `fullstack`.
- **Expected**: `dev-fullstack`, `pm-fullstack`, `qa-fullstack`, `dm-fullstack` L3 installed.
- **Verification**: Correct L3 files present.

---

### TC-12: Setup Step 3 — Skill preset installs correct L3 for all roles
- **Precondition**: Select `skill`.
- **Expected**: L3 for all roles reflects probabilistic/deterministic code development (Claude Code skills focus).
- **Verification**: Skill-specific L3 files present for all 4 roles.

---

### TC-13: Setup Step 3 — Custom (no preset) installs L1+L2 only
- **Precondition**: Select `custom` (or no preset / skip preset selection).
- **Expected**: Only L1 (base) and L2 (role) layers installed. No L3 files written. Agents are functional with L1+L2 only.
- **Verification**: No `l3` files in composed output. L1 and L2 files present. Compose produces valid CLAUDE.md for each role.

---

### TC-14: Setup Step 4 — config values written to config.md correctly
- **Precondition**: Wizard reaches Step 4 (configuration). Provide test values: project name "TestProj", E2E command "pytest e2e/", branch workflow "yes".
- **Steps**: Complete Step 4 with provided values.
- **Expected**: `config.md` contains all provided values under the correct fields. No values omitted. Values match exactly what was entered.
- **Verification**: Read `.squidsquad/config.md`. Assert "TestProj" under project name, "pytest e2e/" under E2E Tests, "yes" under Branch Workflow.

---

### TC-15: Setup Step 4 — external model configuration written correctly
- **Precondition**: Wizard reaches Step 5 (external models). Provide a model name, e.g. "claude-opus-4-5".
- **Steps**: Complete Step 5 with a model selection.
- **Expected**: External model config written to config.md or the appropriate model config file. The value matches what was entered.
- **Verification**: Read config. Assert external model field contains entered value.

---

### TC-16: Setup Step 6 — L4 customization step is informational only (no data collected)
- **Precondition**: Wizard reaches Step 6 (L4 customization info step).
- **Steps**: Observe output. Do not enter any data (step should not ask for any).
- **Expected**: Step displays informational text about instructions.md and SOUL.md customization examples. No questions asked, no data written to L4 files. L4 source files start empty.
- **Verification**: After setup completes, check L4 source files for each role. All should be empty or contain only placeholder/template content. No user-supplied content present.

---

### TC-17: Setup Step 7 — compose produces valid L1+L2+L3+L4 for iOS preset
- **Precondition**: Complete setup with `ios` preset. Reach Step 7 (compose & deploy).
- **Steps**: Allow Step 7 to run compose.
- **Expected**: Each role's composed CLAUDE.md contains content from all four layers (L1 base, L2 role, L3 iOS-specific, L4 project — empty at this stage). Composed output is syntactically valid (no truncation, no merge artifacts, no duplicate sections). All 4 roles composed.
- **Verification**: Read each agent's CLAUDE.md (or composed output path). Confirm L1 base content present, L2 role content present, L3 iOS content present. L4 section exists (empty or with placeholder). No raw template tags or unresolved includes.

---

### TC-18: Setup Step 7 — compose produces valid L1+L2+L3+L4 for web preset
- **Precondition**: Same as TC-17 with `web` preset.
- **Expected**: Same layer integrity check for web L3 content.
- **Verification**: Same method, assert web-specific L3 content in output.

---

### TC-19: Propagation — PM writes L4 file and compose updates deployed CLAUDE.md
- **Precondition**: Post-setup install with ios preset. L4 source for dev is initially empty. PM edits `.squidsquad/skill/l4/instructions.md` (or equivalent L4 source path) to add "Enforce linting for dev."
- **Steps**: PM runs `python references/scripts/compose.py deploy-all`.
- **Expected**: Deployed CLAUDE.md for the dev agent now contains the L4 content "Enforce linting for dev." Content from L1, L2, L3 is preserved — not clobbered. Other roles' CLAUDE.md files are also recomposed (all roles updated).
- **Verification**: Read deployed CLAUDE.md for dev. Assert L4 content present. Assert L1/L2/L3 content still present (spot-check one known L1 line and one L3 line). Read another role's CLAUDE.md and verify it was also recomposed (timestamp newer, content intact).

---

### TC-20: Propagation — reboot after compose picks up new CLAUDE.md content
- **Precondition**: TC-19 completed. Deployed CLAUDE.md for dev contains new L4 content. Dev agent is not running (or in idle state).
- **Steps**: PM runs `reboot_agent.py` for the dev agent (or equivalent reboot command).
- **Expected**: Dev agent reboots and loads the updated CLAUDE.md. The new L4 content ("Enforce linting for dev") is active in the agent's instructions. Reboot waits for the agent to be idle before rebooting (no mid-cycle interrupt).
- **Verification**: After reboot, check agent startup logs or query agent state. New content present in loaded context. Agent reaches healthy state after reboot (health file updated within 10s).

---

### TC-21: Propagation — compose handles agents mid-cycle (waits for idle)
- **Precondition**: An agent is actively running a cycle (in-progress state). PM triggers `compose.py deploy-all` and then `reboot_agent.py`.
- **Steps**: Initiate compose and reboot while agent is mid-cycle.
- **Expected**: Reboot does not interrupt the mid-cycle agent. Wait contract is respected — reboot occurs only after current cycle completes. No data loss, no partial cycle output.
- **Verification**: Agent completes its current cycle, then reboots. Post-reboot health file updated. No zombie processes or duplicate agents.

---

### TC-22: Upgrade — pre-layer install detected correctly
- **Precondition**: Set up a pre-layer install: create `.squidsquad/` structure WITHOUT a `references/roles/base/` directory (or equivalent marker used by upgrade detection).
- **Steps**: Invoke `/squidsquad-upgrade`.
- **Expected**: Upgrade script detects the pre-layer state. Prints a clear message: "Pre-layer install detected. Beginning upgrade." Does NOT treat a post-layer install as pre-layer.
- **Verification**: Upgrade proceeds to extraction step. No false positive on a post-layer install (run on post-layer — should be a no-op, see TC-24).

---

### TC-23: Upgrade — Project Adaptation extracted to L4 SOUL without content loss
- **Precondition**: Pre-layer install where each role's SOUL.md contains a populated `## Project Adaptation` section with known content (e.g. "Dev enforces 80% code coverage", "QA is strict about accessibility").
- **Steps**: Invoke `/squidsquad-upgrade`. Allow it to run through the extraction phase.
- **Expected**: Content from each role's `## Project Adaptation` section is extracted and written to the corresponding L4 SOUL source file verbatim. No content truncated, no content lost, no content mixed between roles. Original SOUL.md content not clobbered before extraction completes.
- **Verification**: Read L4 SOUL source for each role. Assert all known adaptation content is present. Diff extracted content against original `## Project Adaptation` — zero diff. Original SOUL.md still readable (not deleted) until recompose.

---

### TC-24: Upgrade — post-upgrade compose produces valid layered output
- **Precondition**: TC-23 completed. L4 files populated from extraction. L1-L3 set up from new templates.
- **Steps**: Upgrade completes recompose phase (`compose.py deploy-all` or equivalent).
- **Expected**: All role CLAUDE.md files are layered (L1+L2+L3+L4). L4 content matches what was extracted in TC-23. L1/L2/L3 content from new templates is present. No duplicate sections, no raw template tags.
- **Verification**: Read each composed CLAUDE.md. Spot-check for L1 base content, L2 role content, L3 content (preset selected during upgrade or skill default), L4 extracted adaptation content. All present.

---

### TC-25: Upgrade — idempotent (running upgrade twice on post-layer install is a no-op)
- **Precondition**: Post-layer install (already upgraded or fresh post-layer setup).
- **Steps**: Run `/squidsquad-upgrade` again.
- **Expected**: Upgrade detects post-layer state. Prints or silently skips: no extraction attempted, no recompose triggered, no files modified. Existing L4 content preserved.
- **Verification**: Check that no L4 source files were modified (git diff clean). No duplication in SOUL.md files.

---

### TC-26: Upgrade — preset selection during upgrade
- **Precondition**: Pre-layer install with no detectable project type from existing config.
- **Steps**: Invoke `/squidsquad-upgrade`. When asked "What type of project?", select `web`.
- **Expected**: Web L3 is applied during upgrade recompose. All roles get web L3.
- **Verification**: Post-upgrade composed CLAUDE.md files contain web L3 content.

---

### TC-27: Upgrade — preset defaults to "skill" when auto-detectable
- **Precondition**: Pre-layer install where the project is clearly a skill project (e.g. has `SKILL.md`, `references/sub-skills/` present).
- **Steps**: Invoke `/squidsquad-upgrade`. Observe preset selection behavior.
- **Expected**: Upgrade auto-detects skill type and defaults to `skill` preset without asking, OR asks and defaults to `skill` as the pre-selected option.
- **Verification**: Post-upgrade L3 content matches skill preset.

---

### TC-28: Gate — agent posts structured checklist comment on issue before pending-test
- **Precondition**: Any dev agent (dev, QA, DM) is about to transition a setup/upgrade-related task to `pending-test`.
- **Steps**: Agent runs gate check. Observe issue comment posted before or concurrent with pending-test transition.
- **Expected**: A structured checklist comment is posted to the GitHub Issue. Comment covers setup/upgrade mechanics only (wizard.py, compose.py, /squidsquad-upgrade, includes.yml, manifest). Comment is formatted (markdown table or bullet list — dev discretion). Comment is visible as evidence for QA before transition occurs.
- **Verification**: `gh issue view [NUMBER] --json comments` shows a comment from the agent with a checklist. Comment predates or is concurrent with the `pending-test` label transition. Checklist items are checkable (markdown checkboxes or equivalent structure).

---

## Smoke Tests

- [ ] Running `/squidsquad-setup` from a valid repo with gh auth produces a complete `.squidsquad/` directory structure.
- [ ] After setup, `python references/scripts/compose.py deploy-all` completes with exit code 0.
- [ ] After setup, each role's CLAUDE.md file is non-empty and contains recognisable layer content.
- [ ] After upgrade, `git diff` shows no unintended changes outside `.squidsquad/` and `references/`.
- [ ] `reboot_agent.py` invocation on a healthy agent completes without error.
- [ ] Pre-flight gate at agent boot time (not just during setup) also enforces gh/git/remote checks.

---

## Regression Risks

- **Compose overwrites custom edits**: If a user manually edited a composed CLAUDE.md (not via L4), compose will overwrite those edits. Mitigation: L4 is the correct customization path; ensure compose is idempotent on source-driven content only.
- **Upgrade clobbers Project Adaptation before extraction**: If the extraction step and recompose step are ordered incorrectly, accumulated signals could be lost. This is the highest-severity regression risk in Phase C.
- **Cross-preset L3 contamination**: If preset selection logic has a bug, a web project might accidentally include iOS L3 content. Verify TC-5 through TC-12 across at least two presets in sequence.
- **Reboot race condition mid-cycle**: If reboot does not respect the idle wait contract, an agent mid-write could produce corrupt state files. TC-21 covers this.
- **L4 empty section in compose**: If compose does not gracefully handle an empty L4 source file (fresh install), it may inject a malformed section into CLAUDE.md. TC-17 and TC-18 should verify compose handles empty L4 cleanly.
- **Gate checklist bypass**: An agent could transition to pending-test without posting the checklist. The gate must be enforced as a pre-condition to the transition, not a post-condition.
- **Upgrade on partially-migrated install**: If a previous upgrade attempt failed midway, the state is neither fully pre-layer nor fully post-layer. Upgrade must handle this gracefully (resume or error clearly) without silently skipping extraction.

---

## Comprehension Questions

These questions must be answerable by a fresh agent reading only the modified files (wizard.py, compose.py, upgrade script, L4 source templates, and their compose includes). Run against a comprehension-testing subagent.

### CQ-1: What triggers setup to stop before any questions are asked?
- **Files**: `wizard.py` (or equivalent setup entry point), pre-flight check module.
- **Expected answer**: Three conditions each independently halt setup: (1) `gh` CLI not authenticated, (2) not in a git repository, (3) no git remote detected. All three are checked before Step 1. The check also runs at agent boot time.

### CQ-2: When a user selects the "multi-platform" preset, which L3 files are applied and to which roles?
- **Files**: Preset definition config (e.g. `includes.yml`, preset manifest, or wizard.py preset map).
- **Expected answer**: All four roles (dev, pm, qa, dm) receive the multi-platform L3 variant. The multi-platform L3 covers shared codebase concerns for React Native, Flutter, and KMP, plus platform-specific build/test/deploy awareness. A single preset selection sets L3 for all roles simultaneously.

### CQ-3: In the upgrade flow, what is the exact order of operations to ensure zero content loss?
- **Files**: Upgrade script (`squidsquad-upgrade` or `upgrade.py`), compose.py.
- **Expected answer**: (1) Detect pre-layer install (no `references/roles/base/` or equivalent marker). (2) Extract `## Project Adaptation` from each role's existing SOUL.md into L4 SOUL source files — before any templates are overwritten. (3) Set up L1-L3 from new templates. (4) Recompose all agents using `compose.py deploy-all`. Running upgrade on a post-layer install is a no-op at step 1 — no extraction or recompose occurs.

### CQ-4: What does L4 contain immediately after fresh setup (before the user customizes anything)?
- **Files**: Wizard setup output, L4 source template files.
- **Expected answer**: L4 source files are empty (or contain only an empty placeholder). The setup wizard Step 6 is informational only — no data is collected from the user. The user configures L4 later by editing instructions.md files directly or by telling PM what to change.

### CQ-5: Who owns the full propagation flow when L4 content changes, and what are the exact steps?
- **Files**: Phase B description in CONTEXT.md, compose.py, reboot_agent.py.
- **Expected answer**: PM owns the full flow. Steps: (1) PM writes to L4 project sub-skill files directly. (2) PM runs `compose.py deploy-all` to rebuild all agent templates. (3) PM runs `reboot_agent.py` for affected agents. There are no file watchers, no auto-detect, no daemon — propagation is explicit and PM-initiated only.
