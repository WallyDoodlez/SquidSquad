# FEAT-SKILL-1778 Test Plan — Project-Specific Role Responsibilities + Setup Flow Overhaul

## Test Cases

### TC-1: repo_scan.py detects Node.js/TypeScript project (happy path)
- **Precondition**: Repo contains `package.json` (with `next` dependency), `tsconfig.json`, `pnpm-lock.yaml`, `jest.config.ts`, `.github/workflows/ci.yml`, `Dockerfile`, `vercel.json`, `.eslintrc.js`, `.prettierrc`.
- **Steps**: Run `python references/scripts/repo_scan.py` from the repo root.
- **Expected**: JSON output includes `languages: ["typescript"]`, `frameworks: ["next.js"]`, `package_managers: ["pnpm"]`, `test_runners: ["jest"]`, `ci: ["github-actions"]`, `deploy_targets: ["vercel", "docker"]`, `linting: ["eslint", "prettier"]`. Exit code 0.
- **Verification**: `python references/scripts/repo_scan.py | python -m json.tool` — validate JSON is well-formed, keys match the documented schema, values match the fixture files.

### TC-2: repo_scan.py detects Python project (happy path)
- **Precondition**: Repo contains `pyproject.toml` (with `[tool.pytest]` section), `requirements.txt`, `conftest.py`, `.github/workflows/test.yml`, no `package.json`.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: JSON output includes `languages: ["python"]`, `test_runners: ["pytest"]`, `ci: ["github-actions"]`. No JavaScript/TypeScript detections.
- **Verification**: Parse JSON output, assert `"typescript" not in languages`, `"pytest" in test_runners`.

### TC-3: repo_scan.py detects Go project (happy path)
- **Precondition**: Repo contains `go.mod`, `Dockerfile`, no CI files.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: JSON output includes `languages: ["go"]`, `deploy_targets: ["docker"]`, `ci: []`, `test_runners: []`.
- **Verification**: Parse JSON, confirm `ci` and `test_runners` are empty lists.

### TC-4: repo_scan.py detects Rust project (happy path)
- **Precondition**: Repo contains `Cargo.toml`, `.github/workflows/rust.yml`.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: JSON output includes `languages: ["rust"]`, `ci: ["github-actions"]`.
- **Verification**: Parse JSON, confirm expected keys present.

### TC-5: repo_scan.py handles empty repo (edge case)
- **Precondition**: Repo contains only `.git/` and a `README.md`. No language, CI, test, or deploy markers.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: JSON output with all detection arrays empty: `languages: []`, `frameworks: []`, `package_managers: []`, `test_runners: []`, `ci: []`, `deploy_targets: []`. Exit code 0 (not an error).
- **Verification**: Parse JSON, assert every list field has length 0. Script does not crash or print errors to stderr.

### TC-6: repo_scan.py handles monorepo (edge case)
- **Precondition**: Repo root contains no `package.json`. Subdirectories: `packages/web/package.json` (with `react`), `packages/api/pyproject.toml` (with `[tool.pytest]`), `packages/shared/package.json` (with `typescript`).
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: Scan detects the union of technologies: `languages` includes both `typescript` and `python`, `frameworks` includes `react`, `test_runners` includes `pytest`. `monorepo: true`.
- **Verification**: Parse JSON, confirm multi-language detection and `monorepo` flag is true.

### TC-7: repo_scan.py excludes vendor/build directories (edge case)
- **Precondition**: Repo has `node_modules/leftpad/package.json`, `dist/bundle.js`, `vendor/lib/Cargo.toml`, and a real `src/` with `package.json`.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: Only `src/`-level and root-level markers are detected. `node_modules/`, `dist/`, `vendor/` contents are ignored. No Rust detection from `vendor/lib/Cargo.toml`.
- **Verification**: Parse JSON, confirm `"rust" not in languages` (only vendored), confirm detections match only the real project files.

### TC-8: repo_scan.py — no CI detected (edge case)
- **Precondition**: Repo has `package.json` and `jest.config.js` but no `.github/`, no `Jenkinsfile`, no `.gitlab-ci.yml`, no other CI markers.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: `ci: []`. Other detections (languages, test runners) still populated.
- **Verification**: Parse JSON, confirm `ci` is empty, `test_runners` is not empty.

### TC-9: repo_scan.py — no tests detected (edge case)
- **Precondition**: Repo has `package.json` (Express app) and `Dockerfile` but no test config files, no `*.test.*` patterns, no `conftest.py`.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: `test_runners: []`. Language and deploy detections still work.
- **Verification**: Parse JSON, confirm `test_runners` is empty.

### TC-10: repo_scan.py — no package manager detected (edge case)
- **Precondition**: Repo has only `*.go` files and `go.mod`. No `package.json`, `requirements.txt`, `Cargo.toml`, etc.
- **Steps**: Run `python references/scripts/repo_scan.py`.
- **Expected**: `package_managers: []` (Go modules are not a package manager in the traditional sense — dev discretion on whether `go.mod` counts). Languages includes `go`.
- **Verification**: Parse JSON, confirm `languages` is populated, `package_managers` handling is consistent with the mapping.

### TC-11: repo_scan.py outputs valid JSON to stdout (happy path)
- **Precondition**: Any repo with at least one detectable marker.
- **Steps**: Run `python references/scripts/repo_scan.py` and capture stdout.
- **Expected**: Output is valid JSON parseable by `json.loads()`. All documented top-level keys are present (`languages`, `frameworks`, `package_managers`, `test_runners`, `ci`, `deploy_targets`, `monorepo`, `project_type`). No extraneous output on stdout (warnings go to stderr only).
- **Verification**: `python -c "import json, sys; d=json.load(sys.stdin); assert 'languages' in d" < <(python references/scripts/repo_scan.py)`

### TC-12: CLI flow — prerequisites pass and scan runs (happy path)
- **Precondition**: Node 18+, Python 3.8+, `gh` CLI authenticated, Claude CLI installed. Fresh repo with no `.squidsquad/` directory. Repo contains `package.json` and `tsconfig.json`.
- **Steps**: Run `npx @anthropic/squidsquad` (or equivalent CLI entry point). Observe the 10 mechanical steps.
- **Expected**: CLI checks prerequisites (Node, Python, gh, Claude), fetches files, runs `repo_scan.py`, displays scan results, prompts for model routing (y/n), prompts for loop interval, commits scan results to `.squidsquad/.repo-scan.json`, then launches Claude with `/squidsquad-setup`.
- **Verification**: After CLI completes the mechanical steps: `.squidsquad/.repo-scan.json` exists with valid JSON matching repo contents. Model routing config stored (or skipped). Loop interval value stored.

### TC-13: CLI flow — model routing prompt (happy path)
- **Precondition**: CLI has completed prerequisites and scan. `~/.squidsquad/secrets/` directory exists (or will be created).
- **Steps**: CLI prompts "Configure external model routing? (y/n)". User enters "y". CLI opens secrets file in default editor.
- **Expected**: Secrets file opens in `$EDITOR` (or platform default). After editor closes, CLI continues to loop interval prompt.
- **Verification**: Secrets file exists at expected path. CLI does not crash if editor env var is unset (falls back to platform default or prints path).

### TC-14: CLI flow — loop interval prompt (happy path)
- **Precondition**: CLI has completed scan and model routing steps.
- **Steps**: CLI prompts for loop interval in minutes. User enters "30".
- **Expected**: Value "30" is stored and passed to the wizard. CLI accepts numeric input, rejects non-numeric with re-prompt.
- **Verification**: Stored value matches user input. Entering "abc" produces a re-prompt, not a crash.

### TC-15: CLI flow — scan results persisted as .repo-scan.json (happy path)
- **Precondition**: CLI has run `repo_scan.py` successfully.
- **Steps**: Check `.squidsquad/.repo-scan.json` after CLI mechanical steps complete.
- **Expected**: File exists, contains valid JSON matching the scan output, is committed to git.
- **Verification**: `cat .squidsquad/.repo-scan.json | python -m json.tool` succeeds. `git log --oneline -1 -- .squidsquad/.repo-scan.json` shows a commit.

### TC-16: Wizard flow — merged Step 1 presents scan results for review (happy path)
- **Precondition**: `.squidsquad/.repo-scan.json` exists with detected tech: `languages: ["typescript"]`, `frameworks: ["next.js"]`, `test_runners: ["jest"]`.
- **Steps**: Wizard launches. Step 1 displays project identity (name, description) alongside scan findings: "I detected: TypeScript, Next.js, Jest. Is this correct?"
- **Expected**: Wizard presents combined view of project identity + scan results in a single step. User can confirm or correct detections. Corrected results are used for responsibility seeding.
- **Verification**: If user corrects (e.g., removes "Jest"), the corrected detections propagate to responsibility seeding — SOUL.md should not contain Jest-related responsibilities.

### TC-17: Wizard flow — responsibilities seeded per role (happy path)
- **Precondition**: Scan detected TypeScript, Next.js, Jest, GitHub Actions, Vercel, ESLint. Wizard completed Step 1 with confirmed detections. Roles selected: PM, Dev, QA.
- **Steps**: Wizard proceeds through steps 2-6, scaffolds install.
- **Expected**: Each role's SOUL.md contains a `### Project-Specific Responsibilities` section with role-appropriate entries. Dev SOUL.md includes "All new code must be TypeScript", "Write unit tests for all new functions" (Jest), "Run lint+format before committing" (ESLint), "Follow app router conventions" (Next.js). PM SOUL.md includes "Monitor CI status in PRs" (GitHub Actions). QA SOUL.md includes "Run unit test suite and verify no regressions" (Jest), "Verify zero lint warnings" (ESLint).
- **Verification**: `grep "### Project-Specific Responsibilities" .squidsquad/dev/SOUL.md` finds the section. `grep "TypeScript" .squidsquad/dev/SOUL.md` finds the responsibility. Cross-check each role's SOUL.md against the responsibility mapping for the detected tech.

### TC-18: Wizard flow — empty repo gets graceful fallback (edge case)
- **Precondition**: `.squidsquad/.repo-scan.json` exists with all empty arrays (empty repo scan).
- **Steps**: Wizard launches. Step 1 displays project identity. Scan review is skipped or shows "No tech stack detected yet."
- **Expected**: Wizard does not crash. Responsibilities section in SOUL.md contains a fallback message like "No tech stack detected yet. Re-run setup after adding code." or is left with a minimal placeholder.
- **Verification**: `grep "### Project-Specific Responsibilities" .squidsquad/dev/SOUL.md` finds the section. Content is a graceful fallback, not empty or errored.

### TC-19: Wizard flow — reduced adaptive questions (happy path)
- **Precondition**: Scan detected the full tech stack. `.repo-scan.json` populated.
- **Steps**: Wizard runs Step 1 (merged). Observe how many adaptive questions are asked.
- **Expected**: Wizard asks 1-2 questions about domain/purpose and conventions only. Does NOT ask "What languages do you use?" or "What test framework?" since the scan already detected these.
- **Verification**: Count the adaptive questions. Should be <= 2 for a well-scanned repo. Tech stack questions should not appear.

### TC-20: Wizard flow — 6 wizard steps total (happy path)
- **Precondition**: CLI has completed all 10 mechanical steps. Wizard launched.
- **Steps**: Walk through the entire wizard from start to finish.
- **Expected**: Wizard has exactly 6 steps (Steps 0/0a/0b/5/5b/7-commit moved to CLI). Remaining: (1) Project identity + scan review, (2) Intent + roster, (3) Preset confirm, (4) Setup requirements, (5) Review screen, (6) Scaffold + write.
- **Verification**: Count the wizard steps by observing the flow. No prerequisites check, no shared FS init, no loop interval prompt, no model routing prompt within the wizard.

### TC-21: Responsibility mapping — static dict covers top 15 detections (happy path)
- **Precondition**: `repo_scan.py` (or companion `responsibility_map.py`) contains the mapping dict.
- **Steps**: Read the mapping dict. Verify coverage of the locked top 15: JS/TS, Python, Go, Rust, Docker, GitHub Actions, Vercel, Jest, pytest, Playwright, ESLint, Prettier, Next.js, FastAPI, Tailwind.
- **Expected**: Each of the 15 detections has at least one responsibility entry for at least one role. Every role (PM, Dev, QA, Designer, DM) has at least one detection mapped.
- **Verification**: `python -c "from repo_scan import RESPONSIBILITY_MAP; ..."` (or equivalent import) — iterate keys and assert coverage. Count unique detection keys >= 15.

### TC-22: wizard.py seed_responsibilities helper (happy path)
- **Precondition**: `wizard.py` has a `seed_responsibilities(spec, scan_results)` function. `scan_results` is a dict matching repo_scan.py output schema.
- **Steps**: Call `seed_responsibilities(spec, {"languages": ["typescript"], "test_runners": ["jest"], "ci": ["github-actions"]})` for a 3-role install (PM, Dev, QA).
- **Expected**: Returns a dict mapping role_id to a markdown string. Dev entry contains TypeScript and Jest responsibilities. PM entry contains GitHub Actions responsibility. QA entry contains Jest responsibility. Markdown is well-formed (bullet list).
- **Verification**: Assert return type is dict. Assert each role key maps to a non-empty string. Assert specific responsibility strings are present per the mapping.

### TC-23: wizard.py seed_responsibilities with unknown detections (edge case)
- **Precondition**: Scan results include a detection not in the mapping, e.g., `languages: ["elixir"]`.
- **Steps**: Call `seed_responsibilities(spec, {"languages": ["elixir"], "ci": []})`.
- **Expected**: Unknown detections are gracefully skipped. No crash, no KeyError. Responsibilities section may be empty or contain only mapped detections. Function returns successfully.
- **Verification**: Assert no exception raised. Assert return dict has entries for all roles (even if some are empty strings or minimal).

### TC-24: SOUL.md templates have new placeholder section (happy path)
- **Precondition**: All 5 SOUL.md templates updated: `references/roles/pm/SOUL.md`, `references/roles/dev/SOUL.md`, `references/roles/qa/SOUL.md`, `references/roles/designer/SOUL.md`, `references/roles/dm/SOUL.md`.
- **Steps**: Read each template file.
- **Expected**: Each contains `### Project-Specific Responsibilities` section with a placeholder stub (similar to `### Project Context` pattern). Section appears after `### Project Context` (or between `### Improvement Scan` and `### Project Context` per research recommendation).
- **Verification**: `grep -l "### Project-Specific Responsibilities" references/roles/*/SOUL.md` returns all 5 files.

### TC-25: WIZARD.md has 6 steps (happy path)
- **Precondition**: `references/wizard/WIZARD.md` has been rewritten.
- **Steps**: Read the wizard file. Count the steps.
- **Expected**: 6 steps total. Step 1 is merged (project identity + scan review). Steps 0/0a/0b/5/5b/7-commit are absent (moved to CLI). Remaining steps cover: project identity+scan, intent+roster, preset confirm, setup requirements, review screen, scaffold.
- **Verification**: `grep -c "^## Step" references/wizard/WIZARD.md` returns 6 (or equivalent step header count).

### TC-26: Existing SOUL.md preserved on upgrade — empty section added (upgrade)
- **Precondition**: Existing install with `.squidsquad/dev/SOUL.md` that has custom content in `### Project Context` and other sections. No `### Project-Specific Responsibilities` section exists.
- **Steps**: Run `/squidsquad-upgrade` (or equivalent upgrade path).
- **Expected**: Existing SOUL.md content is fully preserved. A new `### Project-Specific Responsibilities` section is appended with an empty or placeholder stub. No existing sections are modified or deleted.
- **Verification**: `diff` the SOUL.md before and after upgrade. Only addition should be the new section. All prior content byte-identical.

### TC-27: Existing SOUL.md with custom responsibilities preserved on regenerate (upgrade)
- **Precondition**: Existing install where human has manually edited the `### Project-Specific Responsibilities` section with custom content.
- **Steps**: Run `/squidsquad-upgrade` or any template regeneration.
- **Expected**: Custom content in `### Project-Specific Responsibilities` is preserved. Scaffolder does NOT overwrite user-customized SOUL.md sections.
- **Verification**: `diff` before/after. Custom content still present and unchanged.

### TC-28: scan-results.json enables refresh on upgrade (upgrade)
- **Precondition**: Existing install with `.squidsquad/scan-results.json` from initial setup. Project has since added a new framework (e.g., added Playwright).
- **Steps**: User manually runs `python references/scripts/repo_scan.py > .squidsquad/scan-results.json` (or upgrade flow triggers re-scan).
- **Expected**: New scan results include the newly added framework. Re-seeding responsibilities would pick up Playwright-related responsibilities for QA and Dev.
- **Verification**: Parse new `scan-results.json`, confirm new detection present. (Full re-seed is out of scope for initial implementation but the data path works.)

### TC-29: Existing wizard steps still work — intent + roster (regression)
- **Precondition**: Wizard launched after CLI mechanical steps. Step 1 (merged) completed.
- **Steps**: Proceed to Step 2 (intent + roster). Select a team shape (e.g., PM + Dev + QA).
- **Expected**: Intent classification and role selection work identically to pre-change behavior. No regressions from step merge or renumbering.
- **Verification**: Wizard produces a valid install spec with selected roles. Compare against known-good wizard output from a pre-change install.

### TC-30: Existing wizard steps still work — setup requirements (regression)
- **Precondition**: Wizard at Step 4 (setup requirements). Roles selected include Dev.
- **Steps**: Wizard walks through manifest-driven requirements for each selected role.
- **Expected**: Setup requirements flow is unchanged. Per-role questions still asked. Manifest walker still invokes `manifest.py` calls correctly.
- **Verification**: Compare the questions asked and values collected against a pre-change wizard run. No missing questions, no extra questions (beyond the removed tech-stack ones).

### TC-31: CLI does not re-ask model routing if already configured (regression)
- **Precondition**: CLI has completed model routing step. Wizard launches.
- **Steps**: Wizard runs through all steps.
- **Expected**: Wizard does NOT ask about model routing (Step 5b has been moved to CLI). No duplicate prompt for API keys or provider selection.
- **Verification**: Search wizard conversation for model/provider/API-key prompts. None should appear.

### TC-32: CLI does not re-ask loop interval if already configured (regression)
- **Precondition**: CLI has collected loop interval (e.g., 30 minutes). Wizard launches.
- **Steps**: Wizard runs through all steps.
- **Expected**: Wizard does NOT ask about loop interval (Step 5 has been moved to CLI). Interval value from CLI is used in the install spec.
- **Verification**: Check the generated `config.md` for `Iteration Interval`. Value should match what was entered in the CLI, not re-prompted in the wizard.

### TC-33: No breakage without scan-results.json — wizard fallback (regression)
- **Precondition**: Old CLI version (does not produce `.repo-scan.json`). New wizard version.
- **Steps**: Launch the new wizard without `.repo-scan.json` present.
- **Expected**: Wizard detects missing scan file and falls back gracefully. Either skips scan review in Step 1 or runs the scan inline. Does NOT crash with FileNotFoundError.
- **Verification**: Wizard completes successfully. SOUL.md is generated (possibly without project-specific responsibilities or with a fallback message).

## Comprehension Questions (Template Changes)

### CQ-1: WIZARD.md — merged Step 1 comprehension
- **Question**: A fresh agent reads the new WIZARD.md. When it reaches Step 1, does it understand that it should present scan results alongside project identity? Does it know where to read scan results from (`.squidsquad/.repo-scan.json`)?
- **Method**: Spawn a fresh agent with only WIZARD.md in context. Ask: "What does Step 1 require you to do?" and "Where do you read scan results from?"
- **Pass criteria**: Agent mentions both project identity questions AND scan result review. Agent names the correct file path for scan results.

### CQ-2: WIZARD.md — step count comprehension
- **Question**: Does a fresh agent correctly identify that there are 6 wizard steps, not 7 or 9?
- **Method**: Spawn a fresh agent with only WIZARD.md. Ask: "How many steps are in the wizard?"
- **Pass criteria**: Agent answers 6. Agent does not mention prerequisites, shared FS, loop interval, or model routing as wizard steps.

### CQ-3: SOUL.md — responsibility section comprehension
- **Question**: Does a fresh agent reading a seeded SOUL.md understand that the `### Project-Specific Responsibilities` section contains project-tailored duties, not generic role duties?
- **Method**: Spawn a fresh agent with a seeded Dev SOUL.md (containing TypeScript + Jest responsibilities). Ask: "What are your project-specific responsibilities?"
- **Pass criteria**: Agent lists the seeded responsibilities (TypeScript, Jest). Agent does not confuse them with generic role duties from other sections.

### CQ-4: SOUL.md — empty responsibilities comprehension
- **Question**: Does a fresh agent handle an empty `### Project-Specific Responsibilities` section correctly (e.g., from an upgrade with no re-scan)?
- **Method**: Spawn a fresh agent with a SOUL.md where the responsibilities section contains only the placeholder stub.
- **Pass criteria**: Agent acknowledges the section exists but is not yet populated. Agent does not hallucinate responsibilities or crash.

## Smoke Tests

- [ ] `python references/scripts/repo_scan.py` exits 0 and outputs valid JSON on the SquidSquad repo itself
- [ ] `python references/scripts/repo_scan.py --help` (or equivalent) does not crash
- [ ] `.squidsquad/.repo-scan.json` is created during a fresh CLI install
- [ ] All 5 SOUL.md templates contain `### Project-Specific Responsibilities`
- [ ] WIZARD.md is parseable and contains no broken step references
- [ ] `wizard.py seed-responsibilities` (or equivalent CLI) does not crash with empty scan results
- [ ] Existing `config.md` values are not modified by the new CLI steps
- [ ] `packages/cli/index.js` still passes any existing lint/test checks

## Regression Risks

- **Wizard step renumbering**: If steps were referenced by number elsewhere (iteration logs, CLAUDE.md, error messages), the renumbering could cause confusion. Search for hardcoded step numbers.
- **scaffold_install ordering**: The new `### Project-Specific Responsibilities` section must be inserted at the correct position in SOUL.md. If `scaffold_install` uses simple string replacement, the new placeholder must not collide with the existing `### Project Context` placeholder.
- **CLI exit codes**: New CLI steps (scan, model routing, loop interval) must not change the exit code behavior. A scan failure should warn but not abort the entire install (the wizard can still function without scan results).
- **Windows path handling**: `repo_scan.py` must use `os.path` or `pathlib` for file detection, not hardcoded `/` separators. The CLI runs on Windows (this project runs on Windows 11).
- **Large repos**: `repo_scan.py` scanning one level of subdirectories in a monorepo with 100+ packages could be slow. Ensure a timeout or depth limit.
- **Git state**: The CLI commits scan results before launching the wizard. If the commit fails (dirty working tree, merge conflict), the wizard must still launch (scan results can be uncommitted).
