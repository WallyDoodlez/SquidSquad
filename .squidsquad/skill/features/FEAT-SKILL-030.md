## FEAT-SKILL-030 — Sub-skill plugin system with hardened phase execution

- **Priority**: High
- **Owner**: TBD
- **Status**: Pending
- **Description**: Foundational architectural redesign enabling SquidSquad to be extended via sub-skills (plugins) while maintaining execution integrity. This is a large, multi-faceted initiative covering several interconnected concerns:

  **1. Plugin system / Sub-skills:**
  Define extension points in SquidSquad where sub-skills can hook in and modify behavior — e.g., custom agent templates (designer, devops), custom Ralph Loop steps, custom QA checks, custom tracker fields, custom intake phases. Sub-skills register via a manifest and are discovered at setup/runtime. Core SquidSquad remains lean; capabilities are added through plugins.

  **2. Hardened phase execution:**
  Current phases run as conversational prompts — an agent (or user) can override instructions just by talking to it. This is fragile. Explore running phases in Claude's **non-interactive mode** (`--print` / headless) where the agent executes a fixed prompt and produces structured output, with no opportunity for conversational drift. The orchestrator (PM or a runner script) chains phase outputs together. This makes the pipeline deterministic and tamper-resistant.

  **3. Interaction layer outside Claude CLI:**
  If phases run non-interactively, human interaction (Phase 2 discussions, approvals, bug triage) needs to happen through an external interface. Explore:
  - Standalone web interface (ties into FEAT-SKILL-020)
  - VS Code extension (ties into FEAT-SKILL-028)
  - GitHub Issues / PR comments as interaction surface
  - A hybrid: non-interactive execution with interactive breakpoints that pause and wait for external input

  **4. Claude API/SDK considerations:**
  Running agents non-interactively at scale may require using the Claude API directly (via Anthropic SDK or Agent SDK) rather than spawning CLI instances. Need to explore: API usage agreements, rate limits, cost implications, how sub-skills would work in an API-driven architecture vs CLI-driven, and whether the Claude Code Agent SDK is the right foundation.

  **Key design questions to explore:**
  - What are the natural extension points in SquidSquad today?
  - How do we prevent prompt injection from overriding phase behavior?
  - Can we mix interactive and non-interactive phases in one pipeline?
  - What's the right boundary between "core" and "plugin"?
  - How do sub-skills declare dependencies on each other?

- **Acceptance Criteria**: TBD — requires deep architectural research and scoping. This is a platform-level change that affects everything.

### Discussion

> [2026-03-29 03:10] **pm/qa**: Filed from human request. Foundational platform initiative — plugin system, hardened non-interactive phase execution, external interaction surfaces, and Claude API considerations. Human specifically called out: (1) preventing conversational override of phase behavior, (2) exploring non-interactive mode + structured output, (3) interaction outside Claude CLI, (4) navigating Claude API agreements. Ties into FEAT-SKILL-020 (web UI), FEAT-SKILL-028 (VS Code extension). Large scope, parked for planning. Status: Pending — awaiting human approval.
> [2026-03-31 02:30] **pm/qa**: Human clarified the core vision: SquidSquad should be a set of cooperating skills, not one monolith. The main skill (`squidsquad`) is the orchestrator — setup, general workflow, philosophy. Each role (PM, dev, DM) becomes its own sub-skill that depends on the main skill's concepts. Current state: everything crammed into one SKILL.md. **Planning note: this requires significantly more thought than a normal feature. Extended research, architectural discussion, and possibly multiple phases of implementation. Do not rush planning.**
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
