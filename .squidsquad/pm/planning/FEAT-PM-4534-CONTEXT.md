# FEAT-PM-4534 Context — PM L2: Acceptance Criteria Quality

## Scope

Strengthen PM's acceptance criteria creation process across all layers. PM's ACs directly shape what the entire team builds — weak ACs cascade into incomplete implementations, dead outputs, and missed regressions.

## Locked Decisions (human decided)

### Layer placement (human clarified)

**L2 — Universal PM trait (all PMs, all projects):**
- ACs must identify the CONSUMER of the output and verify delivery reaches that consumer
- ACs must verify the change doesn't regress existing behavior
- ACs must be deterministically testable — if QA can't run a command to verify it, it's not an AC
- ACs must consider the full lifecycle: create → integrate → deploy → consume
- ACs must check alignment with established decisions and architecture (consult vault/decisions)
- Never assume "file exists" = "file is used" — verify the consumption path
- Every AC must answer: "Who reads this? How do they get it? What breaks if it's wrong?"
- **PM must read and internalize L3 and L4 instructions for all roles on the project** — PM cannot write correct ACs for dev/QA/DM without understanding what each agent's L3 (domain) and L4 (project) instructions tell them to do. PM's ACs must align with and leverage the specific instructions each agent operates under. If PM doesn't know what dev's L4 says about setup/upgrade checks, PM can't write ACs that verify dev did them.

**L3 — PM for skill dev (probabilistic/LLM skill projects):**
- ACs must verify the composition/build pipeline produces correct output
- ACs must verify QA can run deterministic pytest against each criterion
- ACs must consider that LLM-consumed instructions need comprehension testing (not just file existence)

**L4 — This project (SquidSquad):**
- ACs must verify deliverable is composed into deployed CLAUDE.md/SOUL.md via compose.py
- ACs must verify agents read the content at boot (includes.yml or auto-include path)
- ACs must verify installer-files.txt is updated if references/ files change

### AC Integration Check (added to PM Phase 3 task-intake)

Before writing any task's acceptance criteria, PM runs this mental checklist:

1. **Consumer**: Who reads/uses the output? Can they reach it? How?
2. **Integration**: Does the output traverse a build/deploy/compose step? Does the AC verify it passes through?
3. **Regression**: What existing behavior could this break? Is there an AC that checks it doesn't?
4. **Testability**: Can QA execute a single command per AC and get a deterministic PASS/FAIL?
5. **Architecture**: Does this align with vault decisions, established patterns, and project philosophy?

If any answer is unclear, the AC is incomplete.

## Dev Discretion

- Exact wording of the L2 instructions
- Whether the integration check is a section in CLAUDE.md or a separate sub-skill
- How to phrase it so it's actionable without being a rote checklist that gets ignored

## Side Effect Mitigations (required)

- Must not slow down Phase 3 significantly — the check should be fast (mental checklist, not a script)
- Must not make ACs so rigid that edge cases can't be handled
- Must not duplicate what's already in PM SOUL.md quality bar

## Out of Scope

- Changing the task-intake phase structure
- Adding new tools or scripts for AC generation
- Changing QA's verification process
