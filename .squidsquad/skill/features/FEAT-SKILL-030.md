## FEAT-SKILL-030 — Sub-skill architecture: roles as independent skills with layered plugin system

- **Priority**: High
- **Owner**: TBD
- **Status**: Approved
- **Description**: Foundational architectural redesign — break the monolithic SKILL.md into a main skill + layered sub-skills. **All phases must ship atomically** in a single dev cycle to avoid breaking running agents mid-migration.

  **Skill hierarchy (human-confirmed):**
  ```
  squidsquad (main skill)
  ├── setup, config, philosophy, orchestration
  ├── role sub-skills (hardcoded, one per role)
  │   ├── pm/qa
  │   ├── skill-lead
  │   └── dm
  ├── common sub-skills (auto-included by every role)
  │   ├── tracker protocol, discussion protocol
  │   ├── Ralph Loop core, context pressure, working state
  │   └── health checks, git protocol
  └── role-specific sub-skills (shipped, not user-configurable yet)
      ├── pm: feature intake, QA test execution, delivery fallback
      ├── skill: bug triage, implementation workflow
      └── dm: delivery packaging, version bumps
  ```

  **Phase A — Sub-skill architecture:**
  - Main skill = orchestrator (setup, config, philosophy)
  - Each hardcoded role = its own sub-skill with manifest
  - Common sub-skills auto-included by all roles
  - Role-specific sub-skills bundled with each role
  - Discovery & registration: how PM finds and manages sub-skills

  **Phase B — Hardened phase execution:**
  - Non-interactive mode (`--print` / headless) for phase execution
  - Structured output, no conversational drift
  - Orchestrator chains phase outputs
  - Prompt injection prevention

  **Phase C — Interaction layer:**
  - External interface for human interaction (discussions, approvals)
  - Explore: web UI (FEAT-SKILL-020), VS Code (FEAT-SKILL-028), GitHub Issues, hybrid breakpoints

  **Phase D — API/SDK migration:**
  - Claude API direct usage vs CLI spawning
  - Agent SDK as foundation
  - Rate limits, cost, architecture implications

  **Atomicity requirement (human-confirmed):** Phases A-B-C must execute in the same dev cycle. We cannot ship half the sub-skill migration and leave agents running on the old structure — that breaks everything. Phase D can follow separately.

  **Future (out of scope):** Workflow editor for configuring steps between roles (see FEAT-SKILL-054).

- **Acceptance Criteria**:
  - [ ] Main skill contains only setup, config, philosophy, orchestration
  - [ ] Each role (PM, skill, DM) is an independent sub-skill with a manifest
  - [ ] Common sub-skills (tracker, discussion, Ralph Loop, etc.) auto-included by all roles
  - [ ] Role-specific sub-skills bundled with their role
  - [ ] Sub-skill discovery and registration mechanism
  - [ ] Hardened non-interactive phase execution for deterministic pipelines
  - [ ] External interaction surface for human-in-the-loop phases
  - [ ] All phases ship atomically — no partial migration
  - [ ] Existing installs upgrade cleanly via `/squidsquad-upgrade`
  - [ ] Running agents don't break during migration

### Discussion

> [2026-03-29 03:10] **pm/qa**: Filed from human request. Foundational platform initiative — plugin system, hardened non-interactive phase execution, external interaction surfaces, and Claude API considerations. Human specifically called out: (1) preventing conversational override of phase behavior, (2) exploring non-interactive mode + structured output, (3) interaction outside Claude CLI, (4) navigating Claude API agreements. Ties into FEAT-SKILL-020 (web UI), FEAT-SKILL-028 (VS Code extension). Large scope, parked for planning. Status: Pending — awaiting human approval.
> [2026-03-31 02:30] **pm/qa**: Human clarified the core vision: SquidSquad should be a set of cooperating skills, not one monolith. The main skill (`squidsquad`) is the orchestrator — setup, general workflow, philosophy. Each role (PM, dev, DM) becomes its own sub-skill that depends on the main skill's concepts. Current state: everything crammed into one SKILL.md. **Planning note: this requires significantly more thought than a normal feature. Extended research, architectural discussion, and possibly multiple phases of implementation. Do not rush planning.**
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
> [2026-04-02 00:25] **pm/qa**: Major scope refinement from human discussion.
> [2026-04-02 00:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process (Phase 1: Research). Split into layered sub-skill hierarchy: main skill → role sub-skills (hardcoded) → common sub-skills (auto-included) → role-specific sub-skills (shipped). Common sub-skills get auto-included by every role. Role-specific are shipped only (no user-configurable yet — future FEAT-SKILL-054 covers workflow editing). Human confirmed: all phases must ship atomically in one dev cycle to avoid breaking running agents. Phase D (API/SDK) can follow separately.
> [2026-04-02 06:15] **pm/qa**: Phase 2 Discussion complete — all 8 open questions resolved. Locked decisions: build-time composition, concatenation with section markers, sources in references/sub-skills/, agent-instructions.md as generated artifact, separate Architecture Version field, keep Agent tool (no --print), diff-verified composition testing. Phase C (interaction layer) removed from scope — GitHub integration deferred to separate feature. CONTEXT.md written. Human approved Phase 2 gate.
> [2026-04-02 06:20] **pm/qa**: Phase 3 complete — TEST-PLAN.md generated (40 TCs, 12 smoke tests, 8 regression risks). Planning phases complete. Status → Approved. Ready for skill-lead pickup.
