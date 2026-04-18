# FEAT-PM-1291 Context — Multi-Model Subagents

## Scope

Build a universal subagent runner (`model_router.py`) that can spawn any model as a subagent with read-only tool access and per-task instructions, replacing Claude Agent tool spawns for cost savings. Ships with multi-provider plugin architecture and YAML manifests.

**In scope (v1)**:
- model_router.py as universal subagent runner with agentic tool-use loop
- Multi-provider plugin architecture with YAML manifests
- Read-only tools: Read, Grep, Glob (Python-native implementations, sandboxed)
- Skill-equivalent tool mappings (web_search, web_fetch if MCP available)
- 4-layer security enforcement (tool whitelist, path sandbox, no shell, sensitive file deny-list)
- OpenAI provider adapter (GPT 5.2 as initial external model)
- Per-task prompt templates for: Research, Discussion Prep, Test Plan, Improvement Scan
- Auto-install pip deps from provider manifest on first use
- Config.md Model Routing section with per-task-type model selection
- Fallback to Claude Agent tool on external API failure

**v2 follow-up** (separate ticket):
- CLI tools via manifest whitelist with argument validation (design established in Phase 2)

## Locked Decisions (human decided)

- **Auto-install deps**: model_router.py auto-installs pip dependencies from provider manifest on first use. SquidSquad is NOT marketed as dependency-free. Why: reduces friction for users enabling external models.
- **Multi-provider from day 1**: Plugin architecture with per-provider YAML manifests and adapter modules. Why: human wants extensibility from the start, each provider is self-contained.
- **YAML manifest format**: Manifests live alongside adapter code in provider directories. Why: human prefers YAML readability, self-contained provider packages.
- **MCP from day 1, read-only**: External models get Read/Grep/Glob tool access via Python-native implementations (not actual MCP servers). Why: solves file pre-selection gap — external models can dynamically explore the repo like Claude subagents.
- **Skill-equivalent tools in manifest**: Manifests can declare optional tools mapped to SquidSquad capabilities (e.g., web_search requires MCP server). model_router.py checks capability availability before exposing to external model. Why: enables richer subagent behavior on fully-equipped setups.
- **CLI tools deferred to v2**: Whitelist + argument validation design established but not built in v1. Why: reduces v1 scope while preserving the design direction.
- **QA execution always Claude**: QA test execution (Phase 5) locked to Claude — external models cannot run Bash verification commands. Why: QA verification is safety-critical, tool access gap is real.
- **Research defaults to external model**: Research (Phase 1) defaults to GPT 5.2 with tool access. With MCP Read/Grep/Glob, the file pre-selection gap is solved. Why: biggest cost savings opportunity, external models are capable at code analysis.
- **No quality scoring in v1**: Rely on existing PM/QA review as quality gate. Why: avoids speculative design, real usage will inform what quality means.

## Dev Discretion (dev agent can choose)

- Internal module structure of model_router.py
- Error message wording and logging format
- Exact tool-calling loop implementation details
- How to handle very large file reads (truncation strategy)
- Grep implementation details (ripgrep subprocess vs Python regex)
- Provider manifest YAML schema details (as long as it covers: API config, deps, auth, tools)

## Side Effect Mitigations (required)

- **Security**: 4-layer enforcement — tool whitelist (only defined tools callable), path sandboxing (repo root boundary), no shell access (subprocess with shell=False only in v2), sensitive file deny-list (.env, *.key, *.pem, .git/config)
- **API key exposure**: Keys in env vars only, never in config.md or committed files. model_router.py reads from os.environ.
- **Fallback reliability**: If external API fails (network, auth, rate limit, timeout), model_router.py exits code 1 and parent agent falls back to Claude Agent tool. Zero pipeline blockage.
- **Output format consistency**: Per-task prompt templates specify exact markdown structure. External model output must match expected format (RESEARCH.md, TEST-PLAN.md, etc.)
- **Auto-install safety**: pip install runs only when the user has configured an external model in config.md. Claude-only setups never trigger pip.

## Upgrade Path (required)

- Add `## Model Routing` section to config.md (all defaults = claude, zero behavior change)
- Copy model_router.py, prompt templates, and provider directories
- Recompose agent templates (compose.py deploy-all)
- Users opt in by changing model values in config.md and setting API key env vars
- Graceful degradation: non-upgraded installs continue using Agent tool spawns unchanged

## Out of Scope

- CLI tool execution by external models (v2)
- Quality scoring / automated quality gates
- Token cost tracking / budgeting
- Anthropic API direct provider (users who want Claude use Agent tool, not API)
- Streaming responses from external models
- Multiple concurrent subagent spawns
