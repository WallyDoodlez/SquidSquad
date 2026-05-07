# FEAT-PM-5888 Test Plan — /squidsquad-compose Skill

## Test Cases

### TC-1: Compose skill exists and is invocable
- **Precondition**: Feature branch is pulled, `.claude/commands/squidsquad-compose.md` exists
- **Steps**: Read `.claude/commands/squidsquad-compose.md` and verify it defines the `/squidsquad-compose` slash command with `deploy-all` as the underlying operation
- **Expected**: File exists, is non-empty, and instructs Claude to run `python references/scripts/compose.py deploy-all` plus pre-flight checks and post-compose validation
- **Verification**: `test -f .claude/commands/squidsquad-compose.md && wc -l .claude/commands/squidsquad-compose.md`

### TC-2: Compose skill runs deploy-all and produces all CLAUDE.md files
- **Precondition**: `.squidsquad/` tree is scaffolded (config.md, role directories exist); no CLAUDE.md or SOUL.md files yet
- **Steps**: Run `python references/scripts/compose.py deploy-all` directly (the mechanical engine the skill wraps)
- **Expected**: All agent CLAUDE.md files produced at `.squidsquad/<role>/CLAUDE.md` for every role in config.md Dev Agents field; all SOUL.md files produced at `.squidsquad/<role>/SOUL.md`
- **Verification**: `python -c "import compose; compose.deploy_all()"`; then check each role: `test -s .squidsquad/<role>/CLAUDE.md` for each configured agent

### TC-3: Mechanical validation runs after compose — files exist and are non-empty
- **Precondition**: compose.py deploy-all has run
- **Steps**: Inspect each `.squidsquad/<role>/CLAUDE.md` and `.squidsquad/<role>/SOUL.md`
- **Expected**: All expected files exist, are non-zero bytes, and contain role-specific section headers (not raw placeholder text)
- **Verification**: `python tests/run_tests.py` (test_compose.py suite covers file output validation); also `for f in .squidsquad/*/CLAUDE.md; do [ -s "$f" ] || echo "EMPTY: $f"; done`

### TC-4: Compose skill prints clear success/fail summary
- **Precondition**: `/squidsquad-compose` skill definition written
- **Steps**: Read the slash command file; verify it specifies human-readable output: per-role status lines and a final pass/fail marker
- **Expected**: Skill instructions require printing something like `[compose] OK: <role>` per agent and a final summary of pass/fail count; on partial failure, the failed role list is shown
- **Verification**: Code review of `.claude/commands/squidsquad-compose.md` for output format instructions

### TC-5: wizard.py scaffold_install does NOT call deploy_role, generate_local_config, or boot_role
- **Precondition**: Feature branch is pulled
- **Steps**: Search wizard.py for any remaining imports or calls to `deploy_role`, `generate_local_config`, or `boot_role` inside `scaffold_install()`
- **Expected**: Zero calls found; the function only creates directories, writes config.md, working-state.md, clones repos, and saves install-spec
- **Verification**: `grep -n "deploy_role\|generate_local_config\|boot_role" references/scripts/wizard.py` returns nothing inside `scaffold_install()` body

### TC-6: wizard.py scaffold_install creates directories, config.md, and clones but no CLAUDE.md or SOUL.md
- **Precondition**: Clean test environment with no prior `.squidsquad/` tree; compose NOT yet run
- **Steps**: Run scaffold only (invoke `scaffold_install()` in a test context or via `cmd_setup_yes`)
- **Expected**: `.squidsquad/<role>/` directories exist; `config.md` exists; sibling clones exist; NO `.squidsquad/<role>/CLAUDE.md`; NO `.squidsquad/<role>/SOUL.md`
- **Verification**: `test -d .squidsquad/pm && test ! -f .squidsquad/pm/CLAUDE.md && echo "PASS"` (and equivalent for each role)

### TC-7: add_role.py does NOT call compose.py deploy or compose.py boot
- **Precondition**: Feature branch is pulled
- **Steps**: Search add_role.py for any subprocess calls referencing compose.py
- **Expected**: Zero subprocess calls to `compose.py deploy` or `compose.py boot` found anywhere in add_role.py
- **Verification**: `grep -n "compose" references/scripts/add_role.py` returns nothing related to deploy or boot subprocess invocations

### TC-8: add_role.py has no --boot flag
- **Precondition**: Feature branch is pulled
- **Steps**: Check add_role.py argument parser for `--boot`
- **Expected**: `--boot` argument does not appear in add_role.py's argparse definitions
- **Verification**: `grep -n "\-\-boot" references/scripts/add_role.py` returns nothing

### TC-9: SOUL.md seeded with project context when .install-spec.json exists
- **Precondition**: `.squidsquad/.install-spec.json` exists with valid project context (domain, responsibilities); compose.py deploy_role() is the updated version that owns SOUL.md seeding
- **Steps**: Run `python references/scripts/compose.py deploy-all` against a scaffolded tree that has `.install-spec.json`
- **Expected**: Each `.squidsquad/<role>/SOUL.md` contains the project context from install-spec (not raw `{{PROJECT_CONTEXT}}` placeholder); Project-Specific Responsibilities section is populated
- **Verification**: `grep -L "{{PROJECT_CONTEXT}}" .squidsquad/*/SOUL.md` lists all SOUL.md files (none should contain raw placeholder); `grep "Project Context" .squidsquad/pm/SOUL.md` returns a populated section

### TC-10: SOUL.md seeding gracefully skips when .install-spec.json is missing
- **Precondition**: No `.squidsquad/.install-spec.json` (e.g. first-ever compose before scaffold has written spec); compose.py deploy_role() is the updated version
- **Steps**: Run `python references/scripts/compose.py deploy-all` without `.install-spec.json` present
- **Expected**: Compose completes without error or crash; SOUL.md is written with template placeholders rather than project context (seeding silently skipped); no exception traceback
- **Verification**: `python references/scripts/compose.py deploy-all 2>&1; echo "Exit: $?"`; confirm exit 0 and SOUL.md files exist (even if unseeded)

### TC-11: agent_compose() function removed from compose.py
- **Precondition**: Feature branch is pulled
- **Steps**: Search compose.py for `agent_compose`, `_is_agent_compose_enabled`, `_extract_code_blocks`, `_extract_markers`, `_generate_cqs_from_sources`
- **Expected**: None of these function definitions appear in compose.py
- **Verification**: `grep -n "def agent_compose\|def _is_agent_compose_enabled\|def _extract_code_blocks\|def _extract_markers\|def _generate_cqs_from_sources" references/scripts/compose.py` returns nothing

### TC-12: boot_role() function removed from compose.py
- **Precondition**: Feature branch is pulled
- **Steps**: Search compose.py for `def boot_role`
- **Expected**: `boot_role` function definition does not appear in compose.py
- **Verification**: `grep -n "def boot_role" references/scripts/compose.py` returns nothing

### TC-13: boot and boot-all CLI commands removed from compose.py
- **Precondition**: Feature branch is pulled
- **Steps**: Run `python references/scripts/compose.py --help` or inspect compose.py's `main()` for `boot` and `boot-all` subcommands
- **Expected**: Neither `boot` nor `boot-all` appear as CLI subcommands
- **Verification**: `python references/scripts/compose.py --help 2>&1 | grep -E "boot|boot-all"` returns nothing

### TC-14: agent-compose config field removed or deprecated in compose.py
- **Precondition**: Feature branch is pulled
- **Steps**: Search config.py's FIELD_MAP for `agent-compose`
- **Expected**: Field is either absent from FIELD_MAP or annotated as deprecated/no-op; no runtime code reads it to enable agent_compose logic
- **Verification**: `grep -n "agent-compose\|agent_compose" references/scripts/config.py`; confirm no live code path depends on it

### TC-15: Setup orchestration — wizard scaffold then compose skill
- **Precondition**: SKILL.md Setup Instructions updated; `.claude/commands/squidsquad-compose.md` exists
- **Steps**: Read SKILL.md Setup Instructions section; verify the documented flow is: (1) wizard.py scaffold (directories + config.md + clones), then (2) trigger `/squidsquad-compose` (composition + validation)
- **Expected**: SKILL.md explicitly documents the two-step flow; no single-step `wizard.py setup-yes` that also composes
- **Verification**: `grep -A 20 "Setup Instructions" SKILL.md` shows `/squidsquad-compose` as a distinct step after wizard scaffold

### TC-16: Add-role orchestration — add_role.py then compose skill
- **Precondition**: SKILL.md or add-role sub-skill documentation updated
- **Steps**: Read the add-role skill runbook in SKILL.md or `references/sub-skills/`; verify documented flow is: (1) `add_role.py` (clone + `.active-role`), then (2) trigger `/squidsquad-compose`
- **Expected**: No single-step `add_role.py --compose` or `add_role.py --boot` in the documented flow
- **Verification**: `grep -rn "add_role" SKILL.md | grep -v compose` shows add_role.py calls; confirm compose is a separate documented step

### TC-17: Upgrade skill uses compose skill (not inline compose.py)
- **Precondition**: SKILL.md Upgrade Instructions updated; `.claude/commands/squidsquad-upgrade.md` rewritten
- **Steps**: Read SKILL.md upgrade Step 3 and `.claude/commands/squidsquad-upgrade.md`; verify both reference `/squidsquad-compose` rather than `python references/scripts/compose.py deploy-all` inline
- **Expected**: Neither SKILL.md upgrade section nor squidsquad-upgrade.md contains a raw `python references/scripts/compose.py` call for composition
- **Verification**: `grep -n "python references/scripts/compose.py" SKILL.md` returns nothing in the upgrade section; `grep -n "python references/scripts/compose.py" .claude/commands/squidsquad-upgrade.md` returns nothing

### TC-18: PM post-merge recompose uses compose skill
- **Precondition**: `references/sub-skills/roles/pm/post-merge-recompose.md` updated
- **Steps**: Read `references/sub-skills/roles/pm/post-merge-recompose.md` and check line 25 (or equivalent)
- **Expected**: The sub-skill instructs PM to invoke `/squidsquad-compose` instead of running `python references/scripts/compose.py deploy-all` as inline bash
- **Verification**: `grep -n "compose.py" references/sub-skills/roles/pm/post-merge-recompose.md` returns nothing (or only a comment); `grep -n "squidsquad-compose" references/sub-skills/roles/pm/post-merge-recompose.md` returns the trigger instruction

### TC-19: squidsquad-upgrade.md rewritten — no parallel-subagent flow
- **Precondition**: Feature branch is pulled
- **Steps**: Read `.claude/commands/squidsquad-upgrade.md`; verify the pre-compose.py parallel-subagent template regeneration flow is gone
- **Expected**: File does not contain "Fan Out Agents in Parallel" or equivalent; upgrade flow delegates to `/squidsquad-compose` for template regeneration; no subagent spawning for per-role CLAUDE.md generation
- **Verification**: `grep -n "parallel\|Fan Out\|subagent" .claude/commands/squidsquad-upgrade.md` returns nothing; file references `/squidsquad-compose`

### TC-20: WIZARD.md references updated — no raw compose.py preview calls
- **Precondition**: Feature branch is pulled
- **Steps**: Read `references/wizard/WIZARD.md` lines around 587–591 and 704–705; verify direct `compose.py deploy <role>` preview calls and "always go through compose.py" directives are updated
- **Expected**: WIZARD.md no longer instructs the wizard agent to call `compose.py deploy <role>` for preview; updated to reference `/squidsquad-compose` or to note that composition is a separate post-scaffold step
- **Verification**: `grep -n "compose.py deploy\|always go through compose" references/wizard/WIZARD.md` returns nothing (or only in a historical/context note)

### TC-21: Post-merge recompose sub-skill references skill, not inline bash
- **Precondition**: Feature branch is pulled (covered partially by TC-18; this TC verifies it from composed CLAUDE.md perspective)
- **Steps**: Run `python references/scripts/compose.py deploy pm`; then read `.squidsquad/pm/CLAUDE.md`; find the post-merge recompose section
- **Expected**: The composed PM CLAUDE.md instructs PM to invoke `/squidsquad-compose`, not run inline bash
- **Verification**: `grep -A 5 "post-merge\|recompose" .squidsquad/pm/CLAUDE.md | grep "squidsquad-compose"`

### TC-22: setup-yes (CI path) scaffolds only and does not compose
- **Precondition**: Feature branch is pulled; test environment available
- **Steps**: Run `python references/scripts/wizard.py setup-yes --config <test-config>` (dry-run or in isolated environment)
- **Expected**: Command exits after scaffolding only; no CLAUDE.md or SOUL.md files written; no calls to compose.py
- **Verification**: After `setup-yes`, check `test ! -f .squidsquad/pm/CLAUDE.md && echo "scaffold-only PASS"`

### TC-23: setup-yes prints "Next: run compose" not boot instructions
- **Precondition**: Feature branch is pulled
- **Steps**: Run `python references/scripts/wizard.py setup-yes` (or read `cmd_setup_yes` output logic in wizard.py)
- **Expected**: Post-setup summary says something like "Scaffolding complete. Next: run /squidsquad-compose" — NOT per-agent `claude --resume` boot commands
- **Verification**: `python references/scripts/wizard.py setup-yes 2>&1 | grep -i "compose\|next"` shows compose-related instruction; `grep -i "claude --resume\|boot" output` returns nothing from the summary

### TC-24: compose.py deploy_role still importable as a Python function
- **Precondition**: Feature branch is pulled; dead code removed
- **Steps**: `python -c "from compose import deploy_role; print('importable')"` from the references/scripts directory
- **Expected**: Import succeeds without ImportError; `deploy_role` is callable
- **Verification**: `cd references/scripts && python -c "from compose import deploy_role; print('importable')"` prints "importable" and exits 0

### TC-25: generate_local_config still runs via deploy-all
- **Precondition**: Feature branch is pulled; compose.py deploy-all run on a scaffolded tree
- **Steps**: Run `python references/scripts/compose.py deploy-all`; check for `.local-config` file
- **Expected**: `.squidsquad/.local-config` (or equivalent path) is written with agent→clone path mappings
- **Verification**: `test -f .squidsquad/.local-config && echo "PASS"` after deploy-all

### TC-26: Existing tests pass — no regressions from dead code removal
- **Precondition**: Feature branch is pulled; dead code (agent_compose, boot_role) removed from compose.py; corresponding test classes removed from test_compose.py
- **Steps**: Run full test suite
- **Expected**: All remaining tests pass; removed test classes for agent_compose/boot_role are absent; no new failures introduced by the dead code removal
- **Verification**: `python tests/run_tests.py` exits 0; `python -m pytest tests/test_compose.py -v` shows no `TestAgentCompose*`, `TestExtractCodeBlocks`, `TestExtractMarkers`, `TestGenerateCQs` test classes

### TC-27: All agent CLAUDE.md files produced correctly after compose
- **Precondition**: Scaffolded tree with all configured agents; compose.py deploy-all run
- **Steps**: Run `python references/scripts/compose.py deploy-all`; inspect each `.squidsquad/<role>/CLAUDE.md`
- **Expected**: Each CLAUDE.md contains composed content (sub-skill sections present, no raw include markers, role-specific instructions intact); files are substantively populated (not just a header line)
- **Verification**: `python -m pytest tests/test_compose.py -k "deploy" -v` passes; additionally spot-check `wc -l .squidsquad/*/CLAUDE.md` — each should exceed 50 lines

### TC-28: test_wizard.py updated — TestScaffoldInstall* no longer asserts CLAUDE.md/SOUL.md post-scaffold
- **Precondition**: Feature branch is pulled
- **Steps**: Read `tests/test_wizard.py` classes `TestScaffoldInstallDesignPreset`, `TestScaffoldInstallDevVariants`, `TestScaffoldInstallSafetyAndIdempotency`
- **Expected**: None of these test classes assert that `CLAUDE.md` or `SOUL.md` exist after scaffold; assertions updated to expect scaffold-only outputs (directories, config.md, install-spec)
- **Verification**: `grep -n "CLAUDE.md\|SOUL.md" tests/test_wizard.py` returns nothing in the `TestScaffoldInstall*` test bodies

### TC-29: TestSoulMdSeeding updated or relocated to test_compose.py
- **Precondition**: Feature branch is pulled; SOUL.md seeding moved to compose.py's deploy_role()
- **Steps**: Search tests for soul seeding tests; verify they now test compose.py's behavior (not wizard.py's)
- **Expected**: SOUL.md seeding tests pass; they verify that `deploy_role()` in compose.py seeds Project Context and Project-Specific Responsibilities from `.install-spec.json` when present
- **Verification**: `python -m pytest -k "soul" tests/ -v` — all SOUL.md-related tests pass

### TC-30: test_add_role.py updated — no compose subprocess mock needed
- **Precondition**: Feature branch is pulled; add_role.py has no compose calls
- **Steps**: Read `tests/test_add_role.py` `TestAddRoleFixesRemote` class (lines ~212–240); verify it no longer patches `_run` to mock compose subprocess calls
- **Expected**: Test does not mock any compose.py subprocess; test verifies clone creation, `.active-role` writing, `.local-config` sync only
- **Verification**: `grep -n "compose\|_run.*compose" tests/test_add_role.py` returns nothing in subprocess mock context

---

## Smoke Tests

- [ ] `.claude/commands/squidsquad-compose.md` exists and is non-empty
- [ ] `python references/scripts/compose.py deploy-all` exits 0 on a scaffolded tree
- [ ] All `.squidsquad/<role>/CLAUDE.md` files exist and are non-empty after `deploy-all`
- [ ] All `.squidsquad/<role>/SOUL.md` files exist and are non-empty after `deploy-all`
- [ ] `grep -n "deploy_role\|boot_role\|generate_local_config" references/scripts/wizard.py` — none appear inside `scaffold_install()` body
- [ ] `grep -n "compose.py" references/scripts/add_role.py` — no subprocess calls to compose
- [ ] `grep -n "def agent_compose\|def boot_role" references/scripts/compose.py` — both return nothing
- [ ] `python tests/run_tests.py` exits 0
- [ ] `.claude/commands/squidsquad-upgrade.md` contains no "Fan Out Agents in Parallel" or parallel subagent flow
- [ ] `references/sub-skills/roles/pm/post-merge-recompose.md` references `/squidsquad-compose`, not `python references/scripts/compose.py`
- [ ] `wizard.py setup-yes` output contains "compose" or "Next" instruction, not `claude --resume`
- [ ] `.squidsquad/.local-config` written after `compose.py deploy-all` runs

---

## Regression Risks

- **SOUL.md seeding silently skipped**: If `deploy_role()` in compose.py doesn't read `.install-spec.json`, SOUL.md files are produced with raw `{{PROJECT_CONTEXT}}` placeholders — no error, silent regression. Watch for placeholder strings in produced SOUL.md files.
- **generate_local_config not called**: If compose skill runs per-role deploy instead of deploy-all, `.local-config` is not written. Health check and boot_remote scripts silently break. Always verify `.local-config` exists after compose.
- **WIZARD.md instructing compose.py directly**: If WIZARD.md lines 587–591 still instruct the wizard agent to call `compose.py deploy <role>` for preview, a newly-installed agent following WIZARD.md will bypass the compose skill. Verify all direct compose.py invocation instructions in WIZARD.md are removed or updated.
- **squidsquad-upgrade.md parallel-subagent flow**: If file still has the old parallel-subagent template regeneration, any agent reading it directly will spawn conflicting parallel subagents that race with compose.py's deterministic output. Verify the entire file is rewritten.
- **agent booted before compose**: If setup-yes prints boot instructions (claude --resume) before compose has run, the agent starts with no CLAUDE.md and undefined behavior. Verify setup-yes output contains no boot instructions.
- **add_role.py --boot surviving as a flag**: If `--boot` remains in add_role.py's argparse, an agent could call it and start a role with no CLAUDE.md. Verify the flag is removed.
- **test_wizard.py TestScaffoldInstall* asserting CLAUDE.md existence**: If old assertions remain, the tests will fail (expected) but the CI will be green for the wrong reason — compose tests passing but wizard tests newly failing. Verify all scaffold tests are updated.
- **Partial compose failure silently ignored**: If one role fails during deploy-all and the compose skill only checks exit code (not per-role output), a broken install looks like a success. Verify the compose skill's validation step checks each expected CLAUDE.md individually.
- **config.py agent-compose field remaining active**: If `agent-compose` field stays in config.py's FIELD_MAP with a live code path, an existing install with `agent-compose: yes` in config.md could attempt to invoke Claude recursively from within the compose skill. Verify the field is removed or its handler is deleted.
- **test_compose.py agent_compose test classes not removed**: If `TestAgentComposeDisabled`, `TestExtractCodeBlocks`, etc. remain in test_compose.py, they will fail when the functions are deleted — causing a test suite failure at the wrong level. Verify these classes are removed alongside the functions.

---

## Comprehension Questions

### CQ-1: What is the single entry point for composition after this change ships?
- **Files**: `.claude/commands/squidsquad-compose.md`, `SKILL.md` (Setup Instructions, Upgrade Instructions)
- **Expected**: `/squidsquad-compose` is the only LLM-driven composition entry point. `compose.py` remains callable as a Python API and CLI but is not invoked directly by setup/upgrade/add-role skill runbooks.

### CQ-2: After scaffold_install() runs, which files exist and which do not?
- **Files**: `references/scripts/wizard.py` (scaffold_install function), `SKILL.md` (Setup Instructions)
- **Expected**: Directories (`.squidsquad/<role>/`), `config.md`, `working-state.md`, clone repos, and `.install-spec.json` exist. `CLAUDE.md` and `SOUL.md` do NOT exist until `/squidsquad-compose` runs.

### CQ-3: Where does SOUL.md seeding (project context + responsibilities) happen now?
- **Files**: `references/scripts/compose.py` (deploy_role function), `references/scripts/wizard.py`
- **Expected**: `compose.py`'s `deploy_role()` reads `.install-spec.json` (and optionally `.repo-scan.json`) to seed Project Context and Project-Specific Responsibilities into SOUL.md during composition. wizard.py no longer seeds SOUL.md.

### CQ-4: What does add_role.py do after this change, and what does it NOT do?
- **Files**: `references/scripts/add_role.py`
- **Expected**: add_role.py creates the clone, writes `.active-role`, and syncs `.local-config`. It does NOT call compose.py, does NOT generate CLAUDE.md or SOUL.md, and does NOT have a `--boot` flag. Composition and booting are handled by the invoking skill after add_role.py returns.

### CQ-5: What happens if /squidsquad-compose is run and .install-spec.json does not exist?
- **Files**: `references/scripts/compose.py` (deploy_role seeding logic), `.claude/commands/squidsquad-compose.md`
- **Expected**: Compose completes normally. SOUL.md seeding is skipped gracefully (deploy_role checks for .install-spec.json existence before reading). SOUL.md is written with template placeholders. No error or crash.

### CQ-6: What does the CI setup-yes path produce after this change, and what must CI do next?
- **Files**: `references/scripts/wizard.py` (cmd_setup_yes), `SKILL.md`
- **Expected**: `setup-yes` produces a scaffolded directory tree (no CLAUDE.md or SOUL.md). The post-setup summary says "Scaffolding complete. Next: run /squidsquad-compose" — not boot instructions. CI must invoke composition separately (either via the slash command or directly via `compose.py deploy-all`) before booting agents.

### CQ-7: Which test classes were removed from test_compose.py and why?
- **Files**: `tests/test_compose.py`
- **Expected**: `TestAgentComposeDisabled`, `TestExtractCodeBlocks`, `TestExtractMarkers`, `TestGenerateCQs`, and `TestAgentComposeEnabled` were removed because the functions they tested (`agent_compose()`, `_extract_code_blocks()`, `_extract_markers()`, `_generate_cqs_from_sources()`) were deleted as dead code. These were never enabled in production.

### CQ-8: How does the upgrade flow compose agent templates after this change?
- **Files**: `SKILL.md` (Upgrade Instructions), `.claude/commands/squidsquad-upgrade.md`
- **Expected**: The upgrade agent triggers `/squidsquad-compose` (not inline `python references/scripts/compose.py deploy-all`). The old parallel-subagent approach in squidsquad-upgrade.md is gone. The compose skill runs deploy-all, validates output, and reports pass/fail before the upgrade agent proceeds to config patching and commit.

### CQ-9: What does generate_local_config produce and how is it invoked after this change?
- **Files**: `references/scripts/compose.py` (deploy_all, generate_local_config), `.claude/commands/squidsquad-compose.md`
- **Expected**: `generate_local_config()` writes `.squidsquad/.local-config` mapping agent roles to their clone paths. It is called inside `deploy_all()` in compose.py. Since the compose skill always runs `deploy-all` (not per-role deploy), `.local-config` is always regenerated. wizard.py no longer calls it.
