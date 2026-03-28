# FEAT-SKILL-016 — Deep Research-Driven Feature Lifecycle

## Design Document — Draft for Human Review

---

## Problem

The current Feature Intake Process is shallow. The PM acts as a stenographer — it takes the human's request, does a quick duplicate check, asks a couple of questions, and files the feature. This leads to:

- Impulse requirements that don't consider side effects (e.g., statusLine feature wiped user configs → BUG-SKILL-009)
- Acceptance criteria that miss edge cases
- Dev agents implementing without full context
- PM verification that's just "did the code change?" instead of real QA

## Vision

Map GSD's proven workflow onto SquidSquad's multi-agent architecture. GSD runs everything in one agent; SquidSquad distributes the work across specialized roles:

| GSD Phase | SquidSquad Owner | Output |
|-----------|-----------------|--------|
| Research | PM/QA | RESEARCH.md |
| Discussion | PM/QA + Human | CONTEXT.md |
| Planning | PM/QA | Feature entry + TEST-PLAN.md |
| Execution | Dev Agent | Implementation + self-verification |
| QA | PM/QA | Test case run against TEST-PLAN.md |
| Ship | PM/QA | Status → Shipped |

The key difference from today: **PM does the thinking, dev does the building, PM verifies the result.** Today PM barely thinks and barely verifies.

---

## The New Feature Lifecycle

### Phase 1 — Research (PM)

**Trigger:** Human requests a feature.

**Before writing anything**, PM spawns a research agent that:

1. **Codebase impact analysis** — What files, templates, and systems does this feature touch? What existing behavior changes?
2. **Side effect mapping** — What could break? Consider:
   - Users with existing custom configs (settings.json, CLAUDE.md)
   - Different team shapes (1 agent, 5 agents, mixed roles)
   - Different OS/shells (bash, zsh, PowerShell, cmd)
   - Different project types (monorepo, multi-repo, skill repo, app repo)
3. **Edge case identification** — Unusual inputs, failure modes, race conditions, empty states
4. **Integration risk** — How does this interact with other features? (e.g., does PR flow + GitHub Issues ingestion create circular behavior?)
5. **Prior art** — Has something similar been attempted? What can we learn from GSD or other skills?

**Output:** `.squidsquad/[role]/planning/FEAT-XXX-RESEARCH.md`

```markdown
# FEAT-SKILL-XXX Research — [Title]

## Summary
[2-3 paragraphs: what was researched, recommendation, primary risks]

## Impact Analysis
- **Files touched**: [list with brief explanation of each change]
- **Behavior changes**: [what works differently after this feature]
- **Dependencies**: [other features/systems this relies on]

## Side Effects
- **Risk 1**: [description] — Severity: [High/Medium/Low] — Mitigation: [how to handle]
- **Risk 2**: ...

## Edge Cases
- [Case 1]: [what happens, how to handle]
- [Case 2]: ...

## Integration Risks
- [Risk 1]: [how this interacts with feature X]
- ...

## Open Questions
[Things that need human input — each with WHY it matters]
- **Q1**: [question] — **Why**: [consequence of getting this wrong]
- **Q2**: ...

## Recommendation
[Straightforward / Feasible with caveats / Needs significant rethinking]
```

### Phase 2 — Discussion (PM + Human)

**Purpose:** Resolve all open questions from research. PM presents findings and asks targeted questions.

**Process:**

1. PM presents the research summary to the human
2. For each open question, PM explains:
   - What the question is
   - WHY it matters (what breaks if we get it wrong)
   - The options available
   - PM's recommendation (if any)
3. Human answers. PM may follow up with deeper questions based on answers.
4. PM captures decisions as **locked** (human decided, non-negotiable) vs **discretion** (dev agent can choose)
5. PM continues asking until all questions are resolved — no rushing to file

**Key principle:** PM should push back on impulse requirements. If research reveals significant risks, PM says so. "Based on my research, this feature would break X for users who have Y. Do you want to proceed, adjust scope, or shelve it?"

**Output:** `.squidsquad/[role]/planning/FEAT-XXX-CONTEXT.md`

```markdown
# FEAT-SKILL-XXX Context — [Title]

## Scope
[What this feature delivers — clear boundary]

## Locked Decisions (human decided)
- [Decision 1]: [what was decided and why]
- [Decision 2]: ...

## Dev Discretion (dev agent can choose)
- [Area 1]: [what the dev agent can decide on their own]
- [Area 2]: ...

## Side Effect Mitigations (required)
- [Mitigation 1]: [from research, must be implemented]
- [Mitigation 2]: ...

## Out of Scope
- [Thing 1]: [explicitly excluded]
- [Thing 2]: ...
```

### Phase 3 — Planning (PM)

**Purpose:** Write the feature entry with full context, AND plan the test cases.

PM creates two artifacts:

**A) Feature entry** in `features.md` — informed by research and discussion:
- Description references RESEARCH.md and CONTEXT.md
- Acceptance criteria include edge case handling from research
- Side effect mitigations are explicit acceptance criteria
- Implementation constraints from research are noted

**B) Test plan** — `.squidsquad/[role]/planning/FEAT-XXX-TEST-PLAN.md`

```markdown
# FEAT-SKILL-XXX Test Plan — [Title]

## Test Cases

### TC-1: [Happy path test name]
- **Precondition**: [setup needed]
- **Steps**: [what to do]
- **Expected**: [what should happen]
- **Verification**: [how to check — command, file read, grep]

### TC-2: [Edge case test name]
- **Precondition**: [setup needed]
- **Steps**: [what to do]
- **Expected**: [what should happen]
- **Verification**: [how to check]

### TC-3: [Side effect regression test]
- **Precondition**: [existing config/state that should NOT change]
- **Steps**: [exercise the new feature]
- **Expected**: [existing behavior preserved]
- **Verification**: [how to check existing config is intact]

## Smoke Tests
[Quick checks that the feature doesn't break basic functionality]
- [ ] [Check 1]
- [ ] [Check 2]

## Regression Risks
[Things to watch for that might break silently]
- [Risk 1]: [what to check]
- [Risk 2]: [what to check]
```

### Phase 4 — Execution (Dev Agent)

**What changes for the dev agent:**

1. Dev agent reads the feature entry as today
2. **NEW:** Dev agent also reads RESEARCH.md, CONTEXT.md, and TEST-PLAN.md from the planning directory
3. Dev implements the feature, respecting:
   - Locked decisions from CONTEXT.md (non-negotiable)
   - Side effect mitigations (required acceptance criteria)
   - Edge case handling identified in research
4. **Self-verification:** Dev agent runs the smoke tests from TEST-PLAN.md before marking as `Pending Test`
5. Dev updates working-state.md as today
6. Status → `Pending Test`

### Phase 5 — QA (PM/QA)

**This is new.** Today PM just reads the files and checks acceptance criteria loosely. The new flow:

1. PM picks up the feature at `Pending Test`
2. PM reads TEST-PLAN.md
3. PM executes each test case:
   - Reads the relevant files
   - Runs verification commands where specified
   - Checks that side effect regressions didn't occur
   - Records pass/fail per test case
4. PM updates TEST-PLAN.md with results:

```markdown
### TC-1: [Test name]
- **Result**: PASS / FAIL
- **Notes**: [what was observed]
- **Verified at**: [timestamp]
```

5. **If all test cases pass:** Status → `Shipped`
6. **If any test case fails:** Status → `In Progress`, PM appends Discussion entry with:
   - Which test cases failed
   - What was observed vs expected
   - Reference to the specific test case in TEST-PLAN.md

---

## File Structure

```
.squidsquad/
├── [role]/
│   ├── planning/                    ← NEW: per-feature planning artifacts
│   │   ├── FEAT-XXX-RESEARCH.md    ← Research findings
│   │   ├── FEAT-XXX-CONTEXT.md     ← Discussion decisions
│   │   └── FEAT-XXX-TEST-PLAN.md   ← Test cases for QA
│   ├── bugs.md
│   ├── features.md
│   ├── iterations/
│   └── working-state.md
```

Planning files are created per-feature and auto-deleted after the feature ships (they're preserved in git history).

Bugs do NOT go through this flow — they use the current lightweight process (fix, verify, close). Only features get the full research → discussion → planning → QA lifecycle.

---

## What Changes in the Codebase

### 1. `references/agent-instructions.md` — PM/QA Template

**Feature Intake Process** section rewritten with the 5-phase flow:
- Phase 1: Spawn research agent with structured prompt
- Phase 2: Interactive discussion protocol (present research, ask questions, capture decisions)
- Phase 3: Write feature + test plan
- Phase 4: (no change to dev template needed here)
- Phase 5: QA test execution protocol added to "Verify Pending Test Features" step

**New section:** "QA Test Execution Protocol" — how to run test cases from TEST-PLAN.md

### 2. `references/agent-instructions.md` — Dev Agent Template

**Implement Features** step updated:
- Read planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) before implementing
- Respect locked decisions
- Run smoke tests before marking Pending Test

### 3. `SKILL.md`

- Feature lifecycle documentation updated
- Planning directory structure documented
- New file formats documented (RESEARCH.md, CONTEXT.md, TEST-PLAN.md)
- QA process documented

### 4. Generated CLAUDE.md files

- PM and dev CLAUDE.md files regenerated with new templates

---

## Migration

Existing features in the tracker don't need planning artifacts. The new flow applies to features filed after this ships. In-progress features continue as-is.

---

## Decisions (Human Approved)

1. **Light mode for trivial changes** — YES. PM can skip research for trivial features (typo fixes, config tweaks, documentation). PM uses judgment to classify: if the feature touches behavior or user-facing systems, full flow. If it's cosmetic or documentation-only, light mode (skip Phase 1, abbreviated Phase 2).

2. **Research agent token cost** — YES, acceptable. Deep research upfront prevents costly rework and bug-filing later. Better to spend tokens on thinking than on fixing.

3. **Planning file cleanup** — YES, auto-delete after ship. Planning files are auto-deleted from `.squidsquad/[role]/planning/` when PM marks a feature as `Shipped`. Git history preserves them if ever needed.

4. **Bug flow** — NO. Bugs do NOT go through the full research/planning flow. Bugs use the current lightweight process: fix → verify → close. Only features get the 5-phase lifecycle.

5. **Feature rejection** — YES. If research reveals the feature is a bad idea (high risk, low value, breaks existing behavior), PM should explicitly recommend against it. New status: `Rejected` with a Discussion entry explaining why. Human can override and approve anyway.

---

## Inspiration Credit

This design is heavily inspired by GSD's (Get Stuff Done) workflow:
- Research phase → GSD's `gsd:research-phase` (RESEARCH.md)
- Discussion phase → GSD's `gsd:discuss-phase` (CONTEXT.md with locked decisions vs discretion)
- Planning phase → GSD's `gsd:plan-phase` (goal-backward verification, must-haves)
- QA phase → GSD's `gsd:verify-work` (conversational UAT with persistent test state)
- File chain → GSD's consumption pattern: each artifact references and builds on the previous
