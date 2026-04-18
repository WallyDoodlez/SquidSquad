# FEAT-PM-1291 Test Plan — Multi-Model Subagents

## Test Cases

### TC-1: Happy path — model_router.py routes research to external model
- **Precondition**: `references/scripts/model_router.py` exists. Config.md has `Research Model: gpt-5.2`. `OPENAI_API_KEY` is set in environment. A task FEAT-PM-9999 with CONTEXT.md exists.
- **Steps**: Run `python references/scripts/model_router.py research --task-id FEAT-PM-9999 --input-files ".squidsquad/pm/planning/FEAT-PM-9999-CONTEXT.md" --output-file ".squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md" --context "Test task"`
- **Expected**: Exit code 0. Output file `.squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md` written with correct RESEARCH.md markdown structure (## Summary, ## Impact Analysis, ## Side Effects, etc.)
- **Verification**: `echo $?` returns 0. `head -20 .squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md` shows expected markdown headers.

### TC-2: Happy path — model_router.py routes discussion prep to external model
- **Precondition**: Same as TC-1. Config.md has `Discussion Prep Model: gpt-5.2`. A RESEARCH.md file exists for the task.
- **Steps**: Run `python references/scripts/model_router.py discussion-prep --task-id FEAT-PM-9999 --input-files ".squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md" --output-file ".squidsquad/pm/planning/FEAT-PM-9999-PHASE2-PREP.md" --context "Prep for discussion"`
- **Expected**: Exit code 0. PHASE2-PREP.md written with categorized questions, 3 options each, recommended option marked.
- **Verification**: `echo $?` returns 0. File exists and contains `## ` headers.

### TC-3: Happy path — model_router.py routes test plan drafting to external model
- **Precondition**: Config.md has `Test Plan Model: gpt-5.2`. RESEARCH.md and CONTEXT.md exist.
- **Steps**: Run `python references/scripts/model_router.py test-plan --task-id FEAT-PM-9999 --input-files ".squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md,.squidsquad/pm/planning/FEAT-PM-9999-CONTEXT.md" --output-file ".squidsquad/pm/planning/FEAT-PM-9999-TEST-PLAN.md" --context "Draft test plan"`
- **Expected**: Exit code 0. TEST-PLAN.md written with correct format (## Test Cases, ## Smoke Tests, ## Regression Risks).
- **Verification**: File exists with expected markdown structure.

### TC-4: Happy path — model_router.py routes improvement scan to external model
- **Precondition**: Config.md has `Improvement Scan Model: gpt-5.2`. Source files available.
- **Steps**: Run model_router.py with `improvement-scan` task type and 3-5 source file paths.
- **Expected**: Exit code 0. Output file with scan findings in expected format.
- **Verification**: Exit code 0, output file exists and contains findings.

### TC-5: Happy path — all-claude config triggers Agent tool fallback
- **Precondition**: Config.md has all model values set to `claude` (the default). No OPENAI_API_KEY needed.
- **Steps**: Run `python references/scripts/model_router.py research --task-id FEAT-PM-9999 --input-files "..." --output-file "..." --context "Test"`
- **Expected**: Exit code 1 (signals parent to use Agent tool instead). No output file written.
- **Verification**: `echo $?` returns 1. Output file does NOT exist.

### TC-6: Fallback — API failure triggers Claude fallback
- **Precondition**: Config.md has `Research Model: gpt-5.2`. `OPENAI_API_KEY` set to an invalid value (e.g., `sk-invalid`).
- **Steps**: Run model_router.py with research task type.
- **Expected**: Exit code 1. No output file written (or partial output cleaned up). Error logged to `.squidsquad/diagnostics/model-routing.log`.
- **Verification**: `echo $?` returns 1. Log file contains error entry.

### TC-7: Fallback — missing API key triggers exit code 2
- **Precondition**: Config.md has `Research Model: gpt-5.2`. `OPENAI_API_KEY` is NOT set (unset from environment).
- **Steps**: Run model_router.py with research task type.
- **Expected**: Exit code 2. Clear error message printed to stderr about missing API key.
- **Verification**: `echo $?` returns 2. Stderr contains "OPENAI_API_KEY" mention.

### TC-8: Read/Grep/Glob tool access — external model can explore repo
- **Precondition**: model_router.py running with external model. Repo has source files.
- **Steps**: Run research task. Monitor model_router.py's tool-use loop — the external model should issue Read, Grep, Glob tool calls which model_router.py fulfills via Python-native implementations.
- **Expected**: External model receives file contents from Read calls, search results from Grep calls, file lists from Glob calls. Tool-use loop iterates until model produces final output.
- **Verification**: Check `.squidsquad/diagnostics/model-routing.log` for tool call entries. Output file references specific file paths and line numbers (evidence the model explored the repo).

### TC-9: Security — path sandboxing prevents escape
- **Precondition**: model_router.py running. External model attempts to Read a file outside repo root (e.g., `../../etc/passwd` or `C:\Windows\System32\config`).
- **Steps**: Craft a prompt that would cause the model to request files outside repo boundary. Alternatively, unit-test the path validation function directly.
- **Expected**: Read tool call is rejected. Error returned to model: path outside sandbox. No file content from outside repo is exposed.
- **Verification**: Unit test for path validation function. Log shows blocked path access attempt.

### TC-10: Security — sensitive file deny-list prevents reading secrets
- **Precondition**: Repo contains `.env`, `*.key`, `*.pem` files, `.git/config`.
- **Steps**: External model (or unit test) attempts to Read `.env`, a `.key` file, `.git/config`.
- **Expected**: All reads blocked. Error returned to model for each.
- **Verification**: Unit test against deny-list. None of these file contents appear in model output or logs.

### TC-11: Security — no shell access
- **Precondition**: model_router.py running with external model.
- **Steps**: External model attempts to call a tool that would execute shell commands (if any such tool is exposed, or attempts to inject shell commands via tool arguments).
- **Expected**: No shell execution occurs. Only Read, Grep, Glob tools available. Any attempt to execute commands is rejected.
- **Verification**: Check tool whitelist enforcement. No subprocess calls with `shell=True` in v1 code.

### TC-12: Provider manifest — YAML manifest loads correctly
- **Precondition**: `references/scripts/providers/openai/manifest.yaml` exists with correct schema (API config, deps, auth env var, tools).
- **Steps**: Run model_router.py. It should load the OpenAI provider manifest.
- **Expected**: API endpoint, model name, auth env var, pip dependencies parsed correctly from YAML.
- **Verification**: `python -c "import yaml; print(yaml.safe_load(open('references/scripts/providers/openai/manifest.yaml')))"` parses without error and contains expected keys.

### TC-13: Auto-install pip deps on first use
- **Precondition**: `openai` pip package is NOT installed. Config.md has an external model configured.
- **Steps**: Run model_router.py for the first time with an external model task type.
- **Expected**: Script detects missing `openai` package, installs it via pip (from manifest deps), then proceeds with API call.
- **Verification**: After run, `python -c "import openai; print(openai.__version__)"` succeeds.

### TC-14: Auto-install does NOT trigger for all-claude config
- **Precondition**: Config.md has all models set to `claude`. `openai` package is NOT installed.
- **Steps**: Run model_router.py (which exits code 1 for claude config).
- **Expected**: No pip install triggered. `openai` package remains uninstalled.
- **Verification**: `python -c "import openai"` still fails with ImportError.

### TC-15: Prompt templates exist and render correctly
- **Precondition**: `references/prompts/` directory exists with template files.
- **Steps**: Check that all 4 v1 templates exist: `research.md.j2`, `discussion-prep.md.j2`, `test-plan.md.j2`, `improvement-scan.md.j2`. Render each with sample input data.
- **Expected**: All templates exist. Each renders to valid prompt text with file contents embedded.
- **Verification**: `ls references/prompts/*.md.j2 | wc -l` returns 4. Python test script renders each template without Jinja2 errors.

### TC-16: Config.md Model Routing section parsed correctly
- **Precondition**: Config.md has `## Model Routing` section with per-task model assignments.
- **Steps**: `python references/scripts/model_router.py` internal config parser reads the section.
- **Expected**: Each task type resolves to the configured model name. Missing entries fall back to `Default Model`. `Comprehension Model` is always `claude` regardless of config.
- **Verification**: Unit test or manual test: set `Research Model: gpt-5.2`, verify `get_model_for_task("research")` returns `"gpt-5.2"`. Set `Default Model: claude`, verify `get_model_for_task("unknown-task")` returns `"claude"`.

### TC-17: Comprehension model is locked to claude
- **Precondition**: Config.md has `Comprehension Model: gpt-5.2` (attempt to override).
- **Steps**: Run model_router.py with task type `comprehension`.
- **Expected**: Despite config saying `gpt-5.2`, script treats comprehension as locked to claude. Exit code 1 (use Agent tool).
- **Verification**: `echo $?` returns 1 regardless of config value.

### TC-18: QA execution model locked to claude
- **Precondition**: Config.md has `QA Execution Model: gpt-5.2` (attempt to override).
- **Steps**: Run model_router.py with task type `qa-execution`.
- **Expected**: Per locked decision, QA execution always uses Claude. Exit code 1.
- **Verification**: `echo $?` returns 1.

### TC-19: Output format matches expected markdown structure
- **Precondition**: Successful external model call for research task type.
- **Steps**: Run model_router.py for research. Examine output file.
- **Expected**: Output contains all required RESEARCH.md sections: `## Summary`, `## Impact Analysis`, `## Side Effects`, `## Edge Cases`, `## Integration Risks`, `## Upgrade & Migration`, `## Open Questions`, `## Recommendation`.
- **Verification**: `grep "^## " .squidsquad/pm/planning/FEAT-PM-9999-RESEARCH.md` shows all expected headers.

### TC-20: Quality gate — output too short triggers fallback
- **Precondition**: External model returns a very short/empty response (simulate via mock or rate-limited response).
- **Steps**: model_router.py receives response below minimum length threshold.
- **Expected**: Treated as failure. Exit code 1. Parent falls back to Claude Agent tool.
- **Verification**: Log shows "output below minimum length threshold" or similar. Exit code 1.

### TC-21: Skill-equivalent tool mapping — web_search availability check
- **Precondition**: Provider manifest declares optional tool `web_search` mapped to MCP server capability.
- **Steps**: Run model_router.py. Script checks if the required MCP server is available.
- **Expected**: If MCP server available, tool is exposed to external model. If not available, tool is omitted (not exposed) — no error, just fewer tools.
- **Verification**: Log shows which optional tools were exposed vs omitted.

### TC-22: Large file handling — truncation strategy
- **Precondition**: Repo contains a file larger than the external model's practical context limit.
- **Steps**: External model requests Read on a very large file.
- **Expected**: model_router.py truncates the file content with a clear truncation marker. Model receives partial content, not an error.
- **Verification**: Tool response to model includes truncation notice. No API error from oversized prompt.

### TC-23: Agent template changes — task-intake.md updated correctly
- **Precondition**: `references/sub-skills/pm-specific/task-intake.md` has been updated with model_router.py calls replacing Agent tool spawn instructions.
- **Steps**: Read the modified task-intake.md. Check Phase 1, Phase 2A, Phase 3 spawn instructions.
- **Expected**: Each spawn point now shows: (1) Bash call to model_router.py with correct task type, (2) fallback logic checking exit code, (3) Agent tool spawn as fallback if exit code non-zero.
- **Verification**: `grep -c "model_router.py" references/sub-skills/pm-specific/task-intake.md` returns >= 3 (one per offloadable phase). `grep "Agent tool" references/sub-skills/pm-specific/task-intake.md` still present in fallback sections.

### TC-24: Agent template changes — verification.md updated correctly
- **Precondition**: `references/sub-skills/qa-specific/verification.md` has been updated.
- **Steps**: Read the modified verification.md. Check QA execution spawn (Step 5).
- **Expected**: QA execution spawn remains Agent tool only (locked to Claude per CONTEXT.md). Comprehension testing (Step 5, item 1b) remains Agent tool only. No model_router.py calls in verification.md for these two spawn types.
- **Verification**: `grep "model_router.py" references/sub-skills/qa-specific/verification.md` returns 0 matches (QA exec and comprehension are both Claude-locked).

### TC-25: Concurrent access — model_router.py handles simultaneous calls
- **Precondition**: Two agents running simultaneously (PM + skill).
- **Steps**: Both invoke model_router.py at the same time with different task IDs and different output file paths.
- **Expected**: Both complete independently. No file corruption, no log interleaving issues. Output files are distinct.
- **Verification**: Both output files exist with correct content. Log entries are distinguishable by task ID.

### TC-26: Network timeout handling
- **Precondition**: Config.md has `API Timeout Seconds: 120`. External API is slow/unreachable.
- **Steps**: Simulate timeout (e.g., set timeout to 1 second with a real API call, or use a mock).
- **Expected**: After timeout, script exits code 1. Partial output cleaned up. Log records timeout.
- **Verification**: Exit code 1. Log contains timeout error. No partial output file left behind.

## Side Effect Regression Tests

### TC-27: Existing all-claude installs have zero behavior change
- **Precondition**: Fresh install or upgrade with all default config (all models = `claude`). No `OPENAI_API_KEY` set.
- **Steps**: Run a full PM Ralph Loop cycle including Phase 1 research spawn.
- **Expected**: Agent tool spawns work exactly as before. No errors about model_router.py, missing API keys, or missing pip packages. Subagent output identical to pre-feature behavior.
- **Verification**: Iteration log shows normal completion. No new errors in qa-log.md. Agent tool spawns produce expected output files.

### TC-28: Existing config.md without Model Routing section
- **Precondition**: A config.md that was created before this feature — has no `## Model Routing` section.
- **Steps**: Run model_router.py (or agent template that calls it).
- **Expected**: model_router.py gracefully handles missing config section. Falls back to all-claude defaults. Exit code 1 for all task types.
- **Verification**: No crash. Exit code 1. Stderr may warn "Model Routing section not found in config.md, using defaults."

### TC-29: Improvement scan inline behavior unchanged
- **Precondition**: Improvement scanning configured. Spawn 6 (improvement scan) runs inline, not as a subagent.
- **Steps**: Trigger an improvement scan during a quiet cycle.
- **Expected**: If config says `Improvement Scan Model: claude`, scan runs inline as before (no model_router.py call). If config says `gpt-5.2`, model_router.py is called for the scan.
- **Verification**: Check iteration log for scan completion. If claude, no model_router.py invocation in the cycle.

### TC-30: Comprehension testing still uses Agent tool exclusively
- **Precondition**: Task touches LLM-consumed files. TEST-PLAN.md has comprehension questions. Config has `Comprehension Model: gpt-5.2` (attempt to override).
- **Steps**: QA runs Step 5, item 1b (comprehension testing).
- **Expected**: Comprehension agent spawned via Agent tool (Claude), NOT via model_router.py. Override ignored.
- **Verification**: QA-RESULTS.md comprehension section exists. No model_router.py call logged for comprehension.

### TC-31: Artifact resume logic still works with model_router.py spawns
- **Precondition**: RESEARCH.md already exists (uncommitted). Phase 1 would normally be skipped.
- **Steps**: PM enters Phase 1 for a task where RESEARCH.md already exists.
- **Expected**: Artifact resume logic fires before model_router.py is called. Phase skipped. No model_router.py invocation.
- **Verification**: Log shows "RESEARCH.md already exists (uncommitted) — skipping Phase 1." No model_router.py process spawned.

## Upgrade Verification Tests

### TC-32: Upgrade adds Model Routing section to config.md
- **Precondition**: Existing install with config.md that has no `## Model Routing` section.
- **Steps**: Run `squidsquad-upgrade`.
- **Expected**: Config.md gains `## Model Routing` section with all values set to `claude`. No other config sections modified.
- **Verification**: `grep "## Model Routing" .squidsquad/config.md` returns a match. All model values are `claude`. Rest of config.md unchanged (diff shows only additions).

### TC-33: Upgrade copies model_router.py and prompt templates
- **Precondition**: Existing install without model_router.py or prompts/.
- **Steps**: Run `squidsquad-upgrade`.
- **Expected**: `references/scripts/model_router.py` exists. `references/prompts/` directory exists with 4 template files. `references/scripts/providers/openai/` exists with manifest.yaml and adapter module.
- **Verification**: `ls references/scripts/model_router.py` succeeds. `ls references/prompts/*.md.j2 | wc -l` returns 4. `ls references/scripts/providers/openai/manifest.yaml` succeeds.

### TC-34: Upgrade recomposes agent templates
- **Precondition**: Existing install with pre-feature agent templates.
- **Steps**: Run `squidsquad-upgrade`. Check that `compose.py deploy-all` ran.
- **Expected**: Agent CLAUDE.md files reflect updated task-intake.md and verification.md content (with model_router.py references in task-intake.md).
- **Verification**: `grep "model_router.py" .squidsquad/pm/CLAUDE.md` returns matches (in task intake section).

### TC-35: Non-upgraded install continues working
- **Precondition**: Install that has NOT been upgraded. No model_router.py, no Model Routing config section, old agent templates.
- **Steps**: Run a full PM cycle with task intake.
- **Expected**: Everything works as before. Agent tool spawns proceed normally. No references to model_router.py in templates. Zero errors.
- **Verification**: Cycle completes normally. No model_router.py errors.

### TC-36: Upgrade idempotency — running upgrade twice is safe
- **Precondition**: Already-upgraded install (has Model Routing section, model_router.py, prompts).
- **Steps**: Run `squidsquad-upgrade` again.
- **Expected**: No duplicate `## Model Routing` section in config.md. Files not corrupted. Templates recomposed cleanly.
- **Verification**: `grep -c "## Model Routing" .squidsquad/config.md` returns exactly 1. model_router.py unchanged (same content).

### TC-37: Upgrade preserves user-modified model config
- **Precondition**: Previously upgraded install. User changed `Research Model: gpt-5.2` in config.md.
- **Steps**: Run `squidsquad-upgrade` again.
- **Expected**: User's `Research Model: gpt-5.2` setting preserved. Not overwritten to `claude`.
- **Verification**: `grep "Research Model" .squidsquad/config.md` still shows `gpt-5.2`.

## Smoke Tests

- [ ] `python references/scripts/model_router.py --help` prints usage without error
- [ ] `python references/scripts/model_router.py research --task-id TEST --input-files "README.md" --output-file "/tmp/test-out.md" --context "test"` exits with code 1 when all models default to claude
- [ ] `ls references/prompts/*.md.j2` lists 4 template files
- [ ] `ls references/scripts/providers/openai/manifest.yaml` exists
- [ ] Config.md `## Model Routing` section has 9 config lines (Default, Research, Discussion Prep, Test Plan, QA Execution, Comprehension, Improvement Scan, Fallback, API Timeout)
- [ ] `grep "model_router.py" references/sub-skills/pm-specific/task-intake.md` returns matches
- [ ] `grep "model_router.py" references/sub-skills/qa-specific/verification.md` returns 0 matches (QA exec + comprehension stay Claude-only)
- [ ] `python -c "import yaml"` works (YAML parsing available in Python stdlib or installed)
- [ ] Provider manifest YAML parses without error
- [ ] model_router.py has no `shell=True` subprocess calls (security check): `grep -n "shell=True" references/scripts/model_router.py` returns 0 matches

## Quality Comparison Tests (requires OPENAI_API_KEY)

### TC-38: Research output — Claude vs GPT 5.2 side-by-side
- **Precondition**: `OPENAI_API_KEY` set. A real task exists with sufficient codebase context (use a recently completed task for realistic input).
- **Steps**: (1) Run model_router.py with `Research Model: gpt-5.2` to produce RESEARCH-external.md. (2) Run the same task via Agent tool (Claude) to produce RESEARCH-claude.md. (3) PM compares both outputs.
- **Expected**: Both outputs have all required sections. External model output references real files and line numbers (evidence of tool-use exploration). Depth of analysis is comparable — both identify the same major risks and side effects.
- **Verification**: PM scores both on: section completeness (all headers present), specificity (file paths, line numbers, concrete recommendations), edge case coverage (number of edge cases identified), accuracy (no hallucinated files or functions). Document scores in QA-RESULTS.md.
- **Pass criteria**: External model scores >= 70% of Claude's score on each dimension. If below, flag as quality concern (does not block — user chose to default research to external).

### TC-39: Test plan output — Claude vs GPT 5.2 side-by-side
- **Precondition**: Same as TC-38. RESEARCH.md and CONTEXT.md exist for the test task.
- **Steps**: (1) Run model_router.py with `Test Plan Model: gpt-5.2` to produce TEST-PLAN-external.md. (2) Run via Agent tool to produce TEST-PLAN-claude.md. (3) PM compares.
- **Expected**: Both produce valid test plans with TC structure. External model covers happy path, edge cases, and regressions.
- **Verification**: PM scores on: number of TCs, edge case diversity, regression risk identification, comprehension question quality. Document in QA-RESULTS.md.
- **Pass criteria**: External model produces >= 60% as many meaningful test cases as Claude.

### TC-40: Discussion prep output — Claude vs GPT 5.2 side-by-side
- **Precondition**: Same as TC-38. RESEARCH.md exists with open questions.
- **Steps**: (1) Run model_router.py with `Discussion Prep Model: gpt-5.2`. (2) Run via Agent tool. (3) PM compares.
- **Expected**: Both categorize questions, suggest 3 options each with pros/cons, recommend an option. External model's recommendations are reasonable and actionable.
- **Verification**: PM scores on: option quality, pros/cons specificity, recommendation justification. Document in QA-RESULTS.md.
- **Pass criteria**: External model's options and recommendations are usable without major revision.

## Regression Risks

- **Config.md corruption during upgrade**: If the upgrade script incorrectly inserts the Model Routing section (wrong position, duplicate, malformed markdown), all agents that parse config.md could break. Watch for: agents failing to read config values, duplicate section headers.
- **Template recompose breakage**: If task-intake.md or verification.md changes introduce syntax errors or broken markdown, compose.py may produce broken CLAUDE.md files. Watch for: agents failing to boot, missing instructions.
- **pip auto-install side effects**: Auto-installing `openai` package could conflict with user's existing Python environment, break virtual envs, or install incompatible dependencies. Watch for: ImportError in other scripts, dependency version conflicts.
- **Prompt template rendering errors**: Jinja2 template syntax errors would crash model_router.py. Watch for: TemplateError exceptions, missing variables in templates.
- **File I/O race conditions**: model_router.py writing output files while agents are reading them could cause partial reads. Watch for: truncated output files, JSON/markdown parse errors in downstream consumers.
- **Logging volume**: model_routing.log could grow unbounded if no rotation is implemented. Watch for: disk space issues on long-running installs.
- **Agent tool spawn count unchanged for claude config**: Verify that the fallback path (exit code 1 -> Agent tool) does not double-spawn (once via model_router.py attempt, once via Agent tool). Watch for: duplicate RESEARCH.md content, doubled token usage.
- **Cross-platform path handling**: model_router.py path sandboxing must work on Windows (backslashes, drive letters) and Unix. Watch for: path traversal bypasses on Windows, sandbox check failures on Unix.

## Comprehension Questions

### CQ-1: When a PM agent reads task-intake.md, what should it do when spawning a research subagent for Phase 1?
- **Files**: `references/sub-skills/pm-specific/task-intake.md`
- **Expected**: The agent should first attempt to route the task to model_router.py via Bash (e.g., `python references/scripts/model_router.py research --task-id ... --input-files ... --output-file ... --context ...`). If the exit code is non-zero, fall back to spawning a Claude subagent via the Agent tool with the same prompt. The output file path and format remain identical regardless of which model produced the output.

### CQ-2: Which subagent task types are locked to Claude and cannot use external models?
- **Files**: `references/sub-skills/pm-specific/task-intake.md`, `references/sub-skills/qa-specific/verification.md`, `.squidsquad/config.md` (Model Routing section)
- **Expected**: Two task types are locked to Claude: (1) Comprehension testing (Step 5, item 1b in verification.md) — because templates are consumed by Claude agents, so testing with a different model is not meaningful. (2) QA test execution (Phase 5) — because external models cannot run Bash verification commands. The Comprehension Model config value is marked as locked/not configurable.

### CQ-3: What happens if an existing SquidSquad install does not upgrade and has no Model Routing section in config.md?
- **Files**: `references/sub-skills/pm-specific/task-intake.md`, `references/scripts/model_router.py`
- **Expected**: Zero impact. Non-upgraded installs continue using Agent tool spawns exactly as before. The old templates do not reference model_router.py, so no calls are made to it. If model_router.py is somehow invoked without the config section, it defaults all models to `claude` and exits with code 1, triggering Agent tool fallback.

### CQ-4: What tools does an external model get access to when spawned via model_router.py?
- **Files**: `references/scripts/model_router.py`, provider manifest YAML
- **Expected**: External models get Read, Grep, and Glob tools implemented as Python-native functions (sandboxed to repo root). These are NOT actual MCP servers — they are internal implementations. Additionally, provider manifests can declare optional skill-equivalent tools (e.g., web_search, web_fetch) that are only exposed if the corresponding MCP server is available. External models do NOT get Bash/shell access, Write access, or Edit access.

### CQ-5: What are the 4 layers of security enforcement in model_router.py?
- **Files**: `references/scripts/model_router.py`, `.squidsquad/pm/planning/FEAT-PM-1291-CONTEXT.md`
- **Expected**: (1) Tool whitelist — only defined tools (Read, Grep, Glob, plus manifest-declared optional tools) are callable. (2) Path sandboxing — all file access is restricted to repo root boundary. (3) No shell access — no subprocess with shell=True in v1, CLI tools deferred to v2. (4) Sensitive file deny-list — .env, *.key, *.pem, .git/config are blocked from reading.

### CQ-6: How does the auto-install of pip dependencies work, and when does it NOT trigger?
- **Files**: `references/scripts/model_router.py`, provider manifest YAML
- **Expected**: model_router.py reads pip dependencies from the provider's YAML manifest and auto-installs them on first use. Auto-install only triggers when the user has configured an external model in config.md AND the required package is not already installed. It does NOT trigger when all models are set to `claude` (the default) — Claude-only setups never run pip install.

### CQ-7: What is the fallback behavior when an external API call fails?
- **Files**: `references/scripts/model_router.py`, `references/sub-skills/pm-specific/task-intake.md`
- **Expected**: model_router.py exits with code 1 on API failure (network error, rate limit, timeout, bad response) or if the response is below a minimum quality/length threshold. The parent agent detects the non-zero exit code and falls back to spawning a Claude subagent via the Agent tool with the same prompt. This ensures zero pipeline blockage — external API failures never stop work.

### CQ-8: What is the default value for every model in the Model Routing config section after a fresh upgrade?
- **Files**: `.squidsquad/config.md`
- **Expected**: Most models default to `claude` (Discussion Prep, Test Plan, QA Execution, Comprehension, Improvement Scan, Fallback). **Research Model defaults to `gpt-5.2`** (per locked decision — biggest cost savings, external models are capable at code analysis with tool access). Default Model is `claude`. API Timeout Seconds defaults to 120. Comprehension Model is locked to `claude` regardless of config value.
