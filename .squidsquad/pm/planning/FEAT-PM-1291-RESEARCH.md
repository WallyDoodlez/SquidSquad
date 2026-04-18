# FEAT-PM-1291 Research — Multi-Model Subagents for SquidSquad

## Summary

SquidSquad agents spawn Claude subagents via the Agent tool at 6 distinct points in the task lifecycle. These spawns are the most token-expensive operations in the system: research, discussion prep, test plan drafting, QA test execution, comprehension testing, and improvement scanning. The Agent tool is a Claude Code built-in that exclusively spawns Claude instances — it cannot invoke external models. To route work to cheaper models (GPT 5.2 initially), we need a Python-based abstraction layer that calls external APIs via Bash, using the same file-based input/output contract the Agent tool uses today.

**Recommendation**: Feasible with caveats. The approach should be: (1) new `references/scripts/model_router.py` script, (2) new config.md section for model-per-task-type, (3) subagent prompts refactored into template files that can be adapted per model. Comprehension testing must stay Claude-only. Fallback logic is critical — external API failures must not block the pipeline.

---

## 1. Current Subagent Usage — Complete Inventory

### Spawn 1: Research Agent (PM, Phase 1)

- **Where**: `references/sub-skills/pm-specific/task-intake.md`, Phase 1
- **Spawned by**: PM agent
- **What it does**: Analyzes codebase impact, side effects, edge cases, integration risks, upgrade/migration, prior art, capability gaps for a proposed feature
- **Input**: The full codebase (reads files freely), the task description from the GitHub Issue
- **Output**: `.squidsquad/pm/planning/FEAT-PM-XXX-RESEARCH.md` (structured markdown with Summary, Impact Analysis, Side Effects, Edge Cases, Integration Risks, Upgrade & Migration, Capability Gaps, Open Questions, Recommendation)
- **Estimated tokens**: 50k-150k per spawn (reads many files, produces 200-500 lines of analysis)
- **Frequency**: Once per non-trivial task intake

### Spawn 2: Discussion Prep Agent (PM, Phase 2A)

- **Where**: `references/sub-skills/pm-specific/task-intake.md`, Phase 2A
- **Spawned by**: PM agent
- **What it does**: Reads RESEARCH.md, categorizes open questions, suggests 3 options with pros/cons for each, recommends optimal question order
- **Input**: RESEARCH.md file (single file read)
- **Output**: `.squidsquad/pm/planning/FEAT-PM-XXX-PHASE2-PREP.md`
- **Estimated tokens**: 10k-30k per spawn (reads one file, produces structured options)
- **Frequency**: Once per non-trivial task intake (skipped in light mode)

### Spawn 3: Test Plan Agent (PM, Phase 3)

- **Where**: `references/sub-skills/pm-specific/task-intake.md`, Phase 3
- **Spawned by**: PM agent
- **What it does**: Reads RESEARCH.md and CONTEXT.md, drafts test plan with happy path, edge cases, side effect regressions, upgrade verification, smoke tests, comprehension questions
- **Input**: RESEARCH.md + CONTEXT.md (two files)
- **Output**: `.squidsquad/pm/planning/FEAT-PM-XXX-TEST-PLAN.md`
- **Estimated tokens**: 15k-40k per spawn
- **Frequency**: Once per task intake (even light mode runs this)

### Spawn 4: QA Test Execution Agent (PM Phase 5 / QA Step 5)

- **Where**: `references/sub-skills/pm-specific/task-intake.md` Phase 5 AND `references/sub-skills/qa-specific/verification.md` Step 5
- **Spawned by**: PM agent (when QA absent) OR QA agent (when present)
- **What it does**: Reads TEST-PLAN.md, executes each test case by reading files and running verification commands, records PASS/FAIL per TC
- **Input**: TEST-PLAN.md + referenced source files + bash commands for verification
- **Output**: `.squidsquad/[role]/planning/FEAT-XXX-QA-RESULTS.md`
- **Estimated tokens**: 30k-100k per spawn (reads many files, runs commands, produces detailed results)
- **Frequency**: Once per task verification (can repeat if rework occurs)

### Spawn 5: Comprehension Test Agent (QA Step 5, item 1b)

- **Where**: `references/sub-skills/qa-specific/verification.md`, Step 5 item 1b
- **Spawned by**: QA agent
- **What it does**: Reads modified LLM-consumed files (CLAUDE.md, sub-skills, SOUL.md) and answers comprehension questions from TEST-PLAN.md, quoting file content
- **Input**: Modified files + comprehension questions from TEST-PLAN.md
- **Output**: Results appended to QA-RESULTS.md under `## Comprehension Tests`
- **Estimated tokens**: 20k-60k per spawn (reads large template files, answers questions)
- **Frequency**: Once per task that touches LLM-consumed instructions; adaptive spawning (1 per sub-skill group if 4+ affected)
- **MUST STAY CLAUDE-ONLY** (see Section 8)

### Spawn 6: Improvement Scan (PM + Skill, quiet cycles)

- **Where**: `references/sub-skills/common/improvement-scan.md`
- **Spawned by**: PM and skill agents during quiet cycles
- **What it does**: NOT a subagent spawn — the agent itself does the scanning inline. However, the scanning step reads 3-5 source files and analyzes them, consuming significant tokens.
- **Input**: 3-5 source files selected by scan_index.py + SOUL.md scan criteria
- **Output**: GitHub Issues filed via tracker.py (max 2 per scan) + scan-history.md entry
- **Estimated tokens**: 10k-30k per scan cycle (inline, not a separate spawn)
- **Note**: This is NOT an Agent tool spawn — it runs inline. Listed for completeness since it is token-heavy. Could be moved to a subagent for cost savings.

### Summary Table

| Spawn | Role | Phase | Input Files | Output File | Est. Tokens | Frequency | Offloadable? |
|-------|------|-------|-------------|-------------|-------------|-----------|-------------|
| Research | PM | Phase 1 | Many (codebase scan) | RESEARCH.md | 50-150k | Per task | Yes |
| Discussion Prep | PM | Phase 2A | RESEARCH.md | PHASE2-PREP.md | 10-30k | Per non-trivial task | Yes |
| Test Plan | PM | Phase 3 | RESEARCH.md + CONTEXT.md | TEST-PLAN.md | 15-40k | Per task | Yes |
| QA Execution | PM/QA | Phase 5 | TEST-PLAN.md + source files | QA-RESULTS.md | 30-100k | Per verification | Yes |
| Comprehension | QA | Step 5.1b | Modified files + CQs | QA-RESULTS.md section | 20-60k | Per template-touching task | NO — Claude only |
| Improvement Scan | PM/Skill | Quiet cycle | 3-5 source files | GitHub Issues | 10-30k | Every ~4 quiet cycles | Yes (if moved to subagent) |

**Total estimated per full task lifecycle**: 125k-380k tokens across spawns 1-5 (excluding comprehension repeat runs and QA rework cycles).

---

## 2. Agent Tool Limitations

The Agent tool is a Claude Code built-in capability. Based on analysis of the codebase and Claude Code documentation:

- **It spawns Claude subagents only** — there is no parameter to specify a different model
- **It inherits the parent session's tool access** — subagents can use Read, Write, Edit, Bash, Grep, Glob
- **It passes a prompt string** and the subagent runs autonomously
- **Communication is via files** — subagents write markdown files that the parent reads after completion
- **No streaming** — parent blocks until subagent completes
- **Token usage is additive** — subagent tokens count against the same billing

**Conclusion**: The Agent tool cannot spawn non-Claude models. Any multi-model strategy must bypass the Agent tool entirely for non-Claude work.

---

## 3. Alternative Approach — Python Script via Bash

Since the Agent tool only spawns Claude, external models must be called through a different mechanism. The recommended approach:

### Architecture

```
Parent Agent (Claude)
  │
  ├── Agent tool → Claude subagent (for comprehension testing, fallback)
  │
  └── Bash tool → python references/scripts/model_router.py
                     │
                     ├── reads prompt template + input files
                     ├── calls external API (OpenAI, etc.)
                     ├── writes output to expected file path
                     └── returns exit code (0=success, 1=fail → trigger fallback)
```

### How it works

1. **Prompt templates**: Each subagent task type gets a prompt template file in `references/prompts/`:
   - `research.md.j2` — Research agent prompt
   - `discussion-prep.md.j2` — Discussion prep prompt
   - `test-plan.md.j2` — Test plan drafting prompt
   - `qa-execution.md.j2` — QA test execution prompt
   - `improvement-scan.md.j2` — Improvement scan prompt

2. **Context assembly**: The script reads the input files, injects them into the prompt template, and assembles the full prompt with all file contents inline (since external models cannot read local files).

3. **API call**: The script calls the configured external model API with the assembled prompt.

4. **Output handling**: The script writes the model's response to the expected output file path (same as what the Agent tool subagent would write).

5. **Fallback**: If the API call fails (network error, rate limit, bad response), the script exits with code 1. The parent agent detects this and falls back to spawning a Claude Agent tool subagent instead.

### Usage from agent templates

Replace:
```
Spawn a research agent (via the Agent tool) that analyzes: [...]
```

With:
```
Route to model:
```bash
python references/scripts/model_router.py research \
  --task-id FEAT-PM-XXX \
  --input-files ".squidsquad/pm/planning/FEAT-PM-XXX-CONTEXT.md,references/sub-skills/pm-specific/task-intake.md" \
  --output-file ".squidsquad/pm/planning/FEAT-PM-XXX-RESEARCH.md" \
  --context "Task title: [title]. Task body: [body]"
```

If exit code is non-zero, fall back to Agent tool spawn.
```

### Advantages

- Same file I/O contract — parent agent reads the same output files regardless of which model produced them
- Fallback is automatic — network failures, API errors, or quality issues trigger Claude fallback
- No changes to the output format — downstream consumers (PM reviewing RESEARCH.md, QA reviewing QA-RESULTS.md) see identical artifacts
- Model selection is centralized in config.md and model_router.py

### Challenges

- **File context**: The Agent tool subagent can freely read any file in the repo. An external model API call must have all relevant file contents passed inline in the prompt. This means model_router.py must pre-read all input files and embed them.
- **Tool access**: Agent tool subagents can run Bash commands (e.g., for QA test execution). External models cannot. QA execution via external model would be limited to file reading — it cannot run verification commands.
- **Prompt size**: Embedding multiple file contents in a single prompt may exceed token limits for some models.

---

## 4. GPT 5.2 API

### API Access

- **Endpoint**: `https://api.openai.com/v1/chat/completions` (or `/v1/responses` for the newer Responses API)
- **Authentication**: Bearer token via `OPENAI_API_KEY` environment variable
- **Model identifier**: `gpt-5.2` (or similar — exact identifier TBD at launch)

### Request Format

```json
{
  "model": "gpt-5.2",
  "messages": [
    {"role": "system", "content": "You are a research analyst..."},
    {"role": "user", "content": "Analyze the following codebase files and produce a research document..."}
  ],
  "max_tokens": 16384,
  "temperature": 0.2
}
```

### Token Limits & Pricing (estimated, based on GPT-4.1 trajectory)

- **Context window**: Likely 128k-1M tokens (GPT-4.1 already supports 1M)
- **Output tokens**: Up to 32k-64k per response
- **Pricing**: Estimated 50-70% cheaper than Claude Opus for equivalent tasks. GPT-4.1 is ~$2/M input, $8/M output vs Claude Opus at ~$15/M input, $75/M output. GPT 5.2 pricing unknown but expected to follow similar ratios.
- **Rate limits**: Tier-dependent, typically 10k-100k tokens/min for paid accounts

### Capability Differences Relevant to Our Use Cases

| Capability | Claude (Agent tool) | GPT 5.2 (API) |
|-----------|-------------------|---------------|
| File reading | Native (Read tool) | Must embed in prompt |
| Command execution | Native (Bash tool) | Cannot — must pre-run commands and embed output |
| Structured output | Good at markdown | Good at markdown, also supports JSON mode |
| Long context reasoning | Strong | Strong (GPT-4.1 shows excellent long-context) |
| Instruction following | Excellent (XML tags, tool use) | Excellent (system/user messages) |
| Code analysis | Excellent | Excellent |

**Key gap**: GPT 5.2 cannot execute commands or read files. For QA test execution (Spawn 4), the model_router.py script would need to pre-run verification commands and embed their output, or the QA execution task stays Claude-only.

---

## 5. Abstraction Layer Design

### Config.md Addition

```markdown
## Model Routing

- **Default Model**: claude
- **Research Model**: gpt-5.2
- **Discussion Prep Model**: gpt-5.2
- **Test Plan Model**: gpt-5.2
- **QA Execution Model**: claude
- **Comprehension Model**: claude (locked — not configurable)
- **Improvement Scan Model**: gpt-5.2
- **Fallback Model**: claude
- **API Timeout Seconds**: 120
```

### model_router.py Interface

```python
# Usage:
# python references/scripts/model_router.py <task-type> \
#   --task-id <ID> \
#   --input-files <comma-separated paths> \
#   --output-file <path> \
#   --context <additional context string>
#
# Exit codes:
#   0 = success (output file written)
#   1 = API failure (parent should fall back to Agent tool)
#   2 = configuration error (missing API key, invalid config)

def route(task_type, task_id, input_files, output_file, context):
    model = get_model_for_task(task_type)  # reads config.md
    if model == "claude":
        sys.exit(1)  # signal parent to use Agent tool

    prompt = assemble_prompt(task_type, input_files, context)
    response = call_api(model, prompt)
    write_output(output_file, response, task_type)
    sys.exit(0)
```

### Prompt Template System

```
references/prompts/
├── research.md.j2          # Research agent prompt template
├── discussion-prep.md.j2   # Discussion prep template
├── test-plan.md.j2         # Test plan template
├── qa-execution.md.j2      # QA execution template
├── improvement-scan.md.j2  # Improvement scan template
└── adapters/
    ├── claude.py            # Claude-specific prompt formatting
    └── openai.py            # OpenAI-specific prompt formatting
```

Each template contains the task instructions with `{{ file_contents }}` placeholders. The adapter layer handles model-specific formatting (XML tags for Claude, system/user messages for OpenAI).

### Flow

1. Agent template says "route to model for research"
2. Agent runs `python references/scripts/model_router.py research --task-id ... --input-files ... --output-file ...`
3. Script reads config.md → `Research Model: gpt-5.2`
4. Script reads input files, assembles prompt using `research.md.j2` template
5. Script calls OpenAI API with the assembled prompt
6. Script parses response, writes to output file in expected markdown format
7. Script exits 0
8. Agent reads output file and continues

**Fallback flow**: If step 5 or 6 fails → script exits 1 → agent detects non-zero exit → spawns Claude Agent tool subagent with the same prompt (original behavior).

---

## 6. Prompt Adaptation

### The Problem

Claude prompts use XML tags, tool descriptions, and Claude-specific conventions. GPT uses system/user message roles and different instruction patterns. Maintaining two copies of every prompt is fragile.

### Solution: Single Template + Model Adapters

```
Template (model-agnostic):
  "Analyze these files for codebase impact, side effects, edge cases..."
  "Files: {{ file_contents }}"
  "Write output in this format: {{ output_format }}"

Claude adapter:
  - Wraps in <instructions>...</instructions> XML tags
  - Adds tool-use context if needed
  - Uses Claude's preferred instruction style

OpenAI adapter:
  - Splits into system message (role/instructions) and user message (files/task)
  - Uses function calling for structured output if needed
  - Adjusts temperature and max_tokens
```

### Approach

- **One canonical prompt template per task type** (in `references/prompts/`)
- **Thin adapter layer** that reformats for each model's API
- **Output format stays identical** — the template specifies the markdown structure (RESEARCH.md format, TEST-PLAN.md format, etc.), and both models produce the same format
- **No model-specific logic in the agent templates** — the agent just calls model_router.py and reads the output file

### Minimal changes to existing prompts

The existing subagent prompts in `task-intake.md` and `verification.md` are already well-structured:
- Clear task description
- Specific file paths to read
- Exact output format with markdown structure

These can be extracted into template files with minimal changes. The main addition is embedding file contents inline (since external models cannot read files).

---

## 7. Side Effects

### API Key Management

- **OPENAI_API_KEY** stored as environment variable (standard practice)
- `.env` file in repo root, gitignored (already in `.gitignore` pattern)
- `model_router.py` reads from `os.environ` with clear error message if missing
- Setup wizard (`references/scripts/wizard.py`) updated to prompt for API keys during install
- **Risk**: Users who only want Claude can skip this entirely — model routing defaults to `claude` which triggers Agent tool fallback

### Network Dependency

- External API calls may fail (timeout, rate limit, outage)
- **Mitigation**: Fallback to Claude Agent tool is automatic (exit code 1)
- **Latency**: External API calls add network round-trip (~1-5 seconds). Claude Agent tool has similar latency.
- **Timeout**: Configurable per config.md (`API Timeout Seconds: 120`)
- **Offline mode**: If no internet, all tasks fall back to Claude (which runs locally via Claude Code)

### Response Format Differences

- Different models may format markdown slightly differently (header levels, list styles, whitespace)
- **Mitigation**: model_router.py includes a normalization step — validates output against expected markdown structure and reformats if needed
- **Risk**: Low — both Claude and GPT produce clean markdown. The output format is specified in the prompt template.

### Quality Variance

- External models may produce lower-quality research, less thorough test plans, or miss edge cases
- **Mitigation**: PM/QA always reviews subagent output — this is already the case with Claude subagents
- **Monitoring**: model_router.py logs model used, response length, and any formatting issues to `.squidsquad/diagnostics/model-routing.log`
- **Quality gate**: If output is too short (below a configurable threshold), treat as failure and fall back to Claude

### Latency Differences

- GPT API: typically 10-60 seconds for large responses
- Claude Agent tool: typically 30-120 seconds (spawns a full subagent)
- **Net effect**: External API calls may be faster than Agent tool spawns for simple tasks, slower for complex multi-file tasks

---

## 8. What Stays Claude-Only

### Comprehension Testing (LOCKED — not configurable)

Comprehension testing spawns a fresh agent to read modified LLM-consumed files (CLAUDE.md, sub-skills, SOUL.md) and answer questions about them. This MUST stay Claude-only because:

1. **Same-model fidelity**: The templates are consumed by Claude agents. Testing with a different model tells you whether GPT understands the instructions, not whether Claude does. The whole point is to verify that a Claude agent reading these files will behave correctly.
2. **Tool access**: Comprehension agents need to read files via the Read tool. External API calls cannot read local files.
3. **Context matching**: A Claude comprehension agent has the same context window behavior, tokenization, and instruction-following patterns as the production agents. Testing with GPT would have different failure modes.

### QA Test Execution (default Claude, but partially offloadable)

QA test execution needs to run verification commands (Bash tool). For tasks where verification is file-reading-only (checking that a file contains expected content), an external model could work if model_router.py pre-reads the files and embeds them. For tasks with command-based verification, Claude is required.

**Recommendation**: Default to Claude for QA execution. Allow override to external model only for file-inspection-only test plans (no `**Verification**: [command]` entries).

### Other tasks that should consider staying Claude

- **Research agent (Phase 1)**: This is the highest-value spawn — it shapes all downstream decisions. Consider keeping this Claude-only for quality, even though it is the most expensive spawn. Make it configurable so users can choose cost vs quality.
- **Improvement scanning**: Low stakes — external model is fine. Quality issues just mean fewer/weaker findings, not broken pipeline.

---

## 9. Upgrade & Migration

### New Files

- `references/scripts/model_router.py` — the routing script (~200 lines)
- `references/prompts/` — directory with 5 prompt template files
- `references/prompts/adapters/` — model-specific formatters (claude.py, openai.py)

### New Config Values

```markdown
## Model Routing

- **Default Model**: claude
- **Research Model**: claude
- **Discussion Prep Model**: claude
- **Test Plan Model**: claude
- **QA Execution Model**: claude
- **Comprehension Model**: claude
- **Improvement Scan Model**: claude
- **Fallback Model**: claude
- **API Timeout Seconds**: 120
```

All defaults are `claude` — zero behavior change on upgrade. Users opt in by changing individual model values.

### New Dependencies

- `openai` Python package (for GPT API calls)
- **Not required if all models set to `claude`** — model_router.py only imports openai when needed (lazy import)

### API Key Setup

- `OPENAI_API_KEY` environment variable (only needed if any model is set to a GPT variant)
- Wizard (`references/scripts/wizard.py`) adds optional step: "Would you like to configure external model routing? (requires OpenAI API key)"
- If user declines, config stays all-Claude, no API key needed

### Template Changes

- `references/sub-skills/pm-specific/task-intake.md`: Replace Agent tool spawn instructions with model_router.py calls + fallback logic
- `references/sub-skills/qa-specific/verification.md`: Replace QA Agent tool spawn with model_router.py call + fallback (except comprehension)
- Both files gain ~10 lines each (the Bash call + fallback check)

### Upgrade Steps (for `/squidsquad-upgrade`)

1. Add `## Model Routing` section to config.md (with all-claude defaults)
2. Copy `references/scripts/model_router.py` to target
3. Copy `references/prompts/` directory to target
4. Recompose all agent templates (`compose.py deploy-all`)
5. Print: "Model routing installed. All tasks default to Claude. To use external models, set model names in config.md and provide API keys."

### Graceful Degradation

- If user does not upgrade: no impact. Agent tool spawns continue to work exactly as before.
- If user upgrades but does not set API keys: all tasks use Claude (config defaults). Zero behavior change.
- If user sets external model but API key is missing: model_router.py exits with code 2 and clear error message. Agent falls back to Claude.

---

## Open Questions

- **Q1**: Should Research (Phase 1) default to Claude or external model? — **Why**: It is both the most expensive and highest-value spawn. Cost savings are largest here, but quality risk is also highest.
- **Q2**: Should model_router.py support multiple external providers (OpenAI, Anthropic API direct, Google Gemini) from day 1, or start with OpenAI only? — **Why**: Over-engineering risk vs future flexibility. OpenAI-only is simpler to build and test.
- **Q3**: How to handle the QA execution gap (external models cannot run commands)? — **Why**: Options are: (a) always use Claude for QA execution, (b) pre-run commands in model_router.py and embed output, (c) hybrid approach where model_router.py runs commands and external model analyzes results.
- **Q4**: Should there be a quality scoring mechanism to auto-detect when an external model produces inferior output? — **Why**: Without it, quality degradation is only caught during PM/QA review, which may be too late.
- **Q5**: What is the pip install experience for the `openai` package? — **Why**: SquidSquad currently has zero Python package dependencies (all scripts use stdlib). Adding `openai` changes the install story.

## Recommendation

Feasible with caveats. Start with OpenAI-only, default everything to Claude, let users opt in per task type. The file-based I/O contract makes the abstraction clean. Main risks are (1) quality variance in research/test-plan outputs and (2) the QA execution gap where external models cannot run commands.
