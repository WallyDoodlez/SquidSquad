# FEAT-PM-2487 Test Plan — Wire Cycle Runner Into Templates

## Test Cases

### TC-1: [ROLE] substitution in deployed CLAUDE.md files
- **Precondition**: cycle-runner sub-skill source (`references/sub-skills/common/cycle-runner.md`) uses `[ROLE]` placeholders in commands and paths. compose.py has composition-time substitution implemented.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. For each role (pm, skill, qa, dm, designer), read `.squidsquad/<role>/CLAUDE.md`.
  3. Search for literal `[ROLE]` in the cycle-runner section of each deployed file.
- **Expected**: Zero occurrences of literal `[ROLE]` in any deployed CLAUDE.md. Every instance replaced with the correct role name (e.g., `cycle_pre.py pm`, `.squidsquad/pm/cycle-input.json`).
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  for role in pm skill qa dm designer; do grep -c "\[ROLE\]" .squidsquad/$role/CLAUDE.md && echo "FAIL: $role has literal [ROLE]"; done
  ```

### TC-2: Cycle-runner section present in all role templates
- **Precondition**: compose.py deploy-all has been run.
- **Steps**:
  1. For each role (pm, skill, qa, dm, designer), read `.squidsquad/<role>/CLAUDE.md`.
  2. Search for the cycle-runner section markers (`## Cycle Runner (Transport Layer)` or `<!-- sub-skill: cycle-runner -->`).
- **Expected**: Every deployed CLAUDE.md contains the cycle-runner section with the 3-phase flow (Phase 1 Pre-Cycle, Phase 2 Creative Work, Phase 3 Post-Cycle).
- **Verification**:
  ```bash
  for role in pm skill qa dm designer; do
    grep -q "Cycle Runner" .squidsquad/$role/CLAUDE.md && echo "PASS: $role" || echo "FAIL: $role missing cycle-runner"
  done
  ```

### TC-3: cycle_pre.py produces valid cycle-input.json for each role
- **Precondition**: Scripts exist at `references/scripts/cycle_pre.py`. Config and working-state files present for each role.
- **Steps**:
  1. For each role, run `python references/scripts/cycle_pre.py <role>`.
  2. Read `.squidsquad/<role>/cycle-input.json`.
  3. Validate JSON structure: must contain `role`, `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`.
- **Expected**: Valid JSON written for each role. `role` field matches the argument. No crash, exit code 0.
- **Verification**:
  ```bash
  for role in pm skill qa dm designer; do
    python references/scripts/cycle_pre.py $role
    python -c "import json; d=json.load(open('.squidsquad/$role/cycle-input.json')); assert d['role']=='$role', f'role mismatch'; print(f'PASS: {role}')"
  done
  ```

### TC-4: cycle_post.py processes cycle-output.json for each role
- **Precondition**: A valid `cycle-output.json` exists in `.squidsquad/<role>/` with at minimum `role`, `cycle_number`, `cycle_type`, and `iteration_summary`.
- **Steps**:
  1. For each role, write a minimal cycle-output.json:
     ```json
     {"role": "<role>", "cycle_number": 1, "cycle_type": "quiet", "iteration_summary": "test run", "commit_message": "<role>: cycle 1 — test"}
     ```
  2. Run `python references/scripts/cycle_post.py <role>`.
- **Expected**: Exit code 0. Iteration log written. No crash. Status transitions and tracker comments only processed if present in the output.
- **Verification**:
  ```bash
  python references/scripts/cycle_post.py pm
  echo "Exit code: $?"
  ```

### TC-5: Feature flag off skips cycle-runner instructions
- **Precondition**: `config.md` has `Cycle Runner: no` (default).
- **Steps**:
  1. Deploy templates with `python references/scripts/compose.py deploy-all`.
  2. Read a deployed CLAUDE.md (e.g., `.squidsquad/skill/CLAUDE.md`).
  3. Locate the cycle-runner section.
  4. Verify the feature flag gate text is present: "If set to `no` (default), skip this section entirely and use the existing Ralph Loop steps."
- **Expected**: The deployed template contains the feature flag check. When the flag is `no`, an agent following the instructions would skip the cycle-runner section and fall back to existing manual Ralph Loop steps.
- **Verification**: Read the deployed file and confirm the gate text is present. Manually verify that no cycle-runner scripts are invoked when an agent follows the `Cycle Runner: no` path.

### TC-6: PM suppressed cycles via cycle-input.json
- **Precondition**: PM working-state.md contains `**Phase**: researching FEAT-PM-2487`. cycle_pre.py parses `**Phase**:` lines.
- **Steps**:
  1. Write a working-state.md with an active planning phase.
  2. Run `python references/scripts/cycle_pre.py pm`.
  3. Read `.squidsquad/pm/cycle-input.json`.
  4. Check for `working_state.suppressed` field.
- **Expected**: `cycle-input.json` contains `"suppressed": true` in `working_state`. Agent reads this and writes a minimal cycle-output.json with `"cycle_type": "suppressed"`.
- **Verification**:
  ```bash
  python references/scripts/cycle_pre.py pm
  python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); print('suppressed:', d.get('working_state',{}).get('suppressed', False))"
  ```

### TC-7: QA branch switching handled by cycle_pre, normalized by cycle_post
- **Precondition**: Branch workflow enabled in config. A pending-test item exists with a feature branch.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py qa`.
  2. Check current git branch (should be feature branch if pending-test item exists).
  3. Write a cycle-output.json with verification results.
  4. Run `python references/scripts/cycle_post.py qa`.
  5. Check current git branch after post-cycle.
- **Expected**: cycle_pre checks out the feature branch for QA work. cycle_post normalizes back to main before committing. Agent instructions do not duplicate branch switching.
- **Verification**:
  ```bash
  python references/scripts/cycle_pre.py qa
  git branch --show-current  # should be feature branch or main
  python references/scripts/cycle_post.py qa
  git branch --show-current  # should be main
  ```

### TC-8: Permissive schema — cycle_post warns on missing optional fields, does not crash
- **Precondition**: cycle_post.py exists and handles optional fields gracefully.
- **Steps**:
  1. Write a cycle-output.json with only required fields (`role`, `cycle_number`, `cycle_type`) and omit all role-specific optional fields (e.g., no `improvement_scan`, no `e2e_log`, no `version_bump`).
  2. Run `python references/scripts/cycle_post.py <role>`.
  3. Write a cycle-output.json with extra unexpected fields (e.g., `"foo": "bar"`).
  4. Run cycle_post again.
- **Expected**: Both runs exit 0. Missing optional fields produce warnings (stderr or log), not crashes. Extra fields are ignored silently.
- **Verification**:
  ```bash
  echo '{"role":"skill","cycle_number":1,"cycle_type":"quiet","iteration_summary":"test","commit_message":"skill: cycle 1 — test"}' > .squidsquad/skill/cycle-output.json
  python references/scripts/cycle_post.py skill
  echo "Exit code: $?"
  ```

### TC-9: Missing cycle-output.json graceful handling
- **Precondition**: No cycle-output.json exists for the role.
- **Steps**:
  1. Ensure `.squidsquad/<role>/cycle-output.json` does not exist.
  2. Run `python references/scripts/cycle_post.py <role>`.
- **Expected**: Exit code 0. Warning printed. Status bar set to idle. No tracker transitions, no commits, no crashes.
- **Verification**:
  ```bash
  rm -f .squidsquad/skill/cycle-output.json
  python references/scripts/cycle_post.py skill
  echo "Exit code: $?"
  ```

### TC-10: Existing manual sub-skills not in cycle flow
- **Precondition**: Sub-skills `common/pull-latest`, `common/git-commit`, `common/iteration-log` exist in `references/sub-skills/common/`.
- **Steps**:
  1. Read each deployed CLAUDE.md.
  2. Check that when Cycle Runner is enabled, the instructions do NOT direct the agent to use pull-latest, git-commit, or iteration-log sub-skills for mechanical operations.
  3. Verify these sub-skill files still exist in the codebase as reference documentation.
- **Expected**: Manual sub-skills remain in the repo. They are NOT included in the cycle flow. The cycle-runner section explicitly handles their responsibilities (pull, commit, push, iteration logging) via scripts. No duplication of mechanical steps.
- **Verification**:
  ```bash
  # Sub-skills still exist as reference
  ls references/sub-skills/common/pull-latest.md references/sub-skills/common/git-commit.md references/sub-skills/common/iteration-log.md
  # Not composed into cycle flow (check that cycle-runner replaces, not duplicates)
  grep -c "pull-latest" .squidsquad/skill/CLAUDE.md  # should be 0 or only in non-cycle-runner sections
  ```

### TC-11: compose.py deploy-all still works end-to-end
- **Precondition**: All role entry templates updated with cycle-runner include. compose.py has [ROLE] substitution logic.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Verify exit code 0.
  3. For each role, verify the deployed CLAUDE.md is non-empty and well-formed.
  4. Run `python tests/run_tests.py` to verify all existing tests pass.
- **Expected**: deploy-all succeeds. All deployed files are valid. No existing tests broken.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  echo "deploy-all exit: $?"
  python tests/run_tests.py
  echo "tests exit: $?"
  ```

### TC-12: Rollout — recompose and reboot produces working agents
- **Precondition**: Agents are idle. Templates have been updated with cycle-runner.
- **Steps**:
  1. Wait for all agents to go idle (check `current-state` files).
  2. Run `python references/scripts/compose.py deploy-all`.
  3. Reboot all agents: `python references/scripts/reboot_agent.py --all`.
  4. Monitor agent health for 2 cycles.
- **Expected**: All agents boot successfully, read the new cycle-runner instructions, and execute cycles using the 3-phase flow (when Cycle Runner is enabled) or the existing Ralph Loop steps (when disabled).
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  python references/scripts/reboot_agent.py --all
  # Wait ~60s then check health
  python references/scripts/health_check.py
  ```

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` exits 0
- [ ] No literal `[ROLE]` in any `.squidsquad/*/CLAUDE.md` file
- [ ] `python references/scripts/cycle_pre.py pm` exits 0 and writes valid JSON
- [ ] `python references/scripts/cycle_post.py pm` exits 0 with minimal cycle-output.json
- [ ] `python tests/run_tests.py` — all existing tests pass after template changes
- [ ] `grep "Cycle Runner" .squidsquad/skill/CLAUDE.md` returns matches (section present)
- [ ] Config `Cycle Runner: no` causes agents to skip the cycle-runner section

---

## Regression Risks

- **Dual-instruction confusion**: If cycle-runner is composed but the template still includes manual pull-latest/git-commit/iteration-log steps in the main Ralph Loop, agents may run both. Watch for duplicated pulls, commits, or iteration log entries.
- **PM suppression regression**: PM planning phase suppression currently works via working-state.md parsing. The cycle-runner path must preserve this behavior through cycle-input.json's `suppressed` flag. If broken, PM will run full cycles during planning phases.
- **Branch workflow conflicts**: cycle_post.py has special handling for skill branch workflow (split commits). If the skill template still instructs manual git-commit sub-skill actions alongside cycle_post, commits may conflict or duplicate.
- **compose.py breaking on new include**: Adding `{{include: common/cycle-runner}}` to role entry templates may break compose.py if the include path resolution or [ROLE] substitution has edge cases (e.g., nested substitution, escaping).
- **Windows path issues**: cycle_pre.py and cycle_post.py write to `.squidsquad/<role>/` paths. Verify forward-slash paths work on Windows (project runs on Windows 11).
- **Missing config key**: The sub-skill checks `Cycle Runner` in config.md. If `config.py` does not support that key name/casing, the feature flag check will fail silently or crash.

---

## Comprehension Questions

### CQ-1: What are the three phases of the cycle-runner flow?
- **Files**: `.squidsquad/skill/CLAUDE.md` (deployed, cycle-runner section)
- **Expected**: Phase 1 is Pre-Cycle (run `cycle_pre.py skill`), Phase 2 is Creative Work (agent's core work using cycle-input.json), Phase 3 is Post-Cycle (write cycle-output.json and run `cycle_post.py skill`).

### CQ-2: When Cycle Runner is set to `no`, what should an agent do with the cycle-runner section?
- **Files**: `.squidsquad/skill/CLAUDE.md` (deployed, cycle-runner section)
- **Expected**: Skip the cycle-runner section entirely and use the existing Ralph Loop steps (manual pull, commit, iteration logging).

### CQ-3: What mechanical operations should an agent NOT perform manually when cycle-runner is enabled?
- **Files**: `.squidsquad/skill/CLAUDE.md` (deployed, cycle-runner section)
- **Expected**: git pull, git push, status bar writes, tracker transitions, iteration logging, git commit. These are handled by cycle_pre.py and cycle_post.py. The agent should only do creative work (reasoning, code analysis, code writing, verification, tests, spawning subagents).

### CQ-4: Where does a PM agent write its cycle output, and what command runs afterward?
- **Files**: `.squidsquad/pm/CLAUDE.md` (deployed, cycle-runner section)
- **Expected**: Write results to `.squidsquad/pm/cycle-output.json`, then run `python references/scripts/cycle_post.py pm`.

### CQ-5: If cycle-input.json contains `"suppressed": true` in working_state, what should the PM agent do?
- **Files**: `.squidsquad/pm/CLAUDE.md` (deployed, cycle-runner section + PM-specific instructions)
- **Expected**: Write a minimal cycle-output.json with `"cycle_type": "suppressed"` and a brief summary, then run cycle_post.py pm. Do not perform full creative work — the cycle is suppressed due to an active planning phase.
