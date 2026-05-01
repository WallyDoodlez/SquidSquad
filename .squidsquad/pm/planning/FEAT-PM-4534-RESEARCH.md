# FEAT-PM-4534 Research — PM L2 Acceptance Criteria Must Consider Project Workflows, Philosophy, and Prevent Regression

## Summary

PM's acceptance criteria process has a structural blind spot: it validates that implementation *exists* but not that it *integrates and reaches its consumer*. The motivating case (#4455-#4459) is a series of L4 content tasks where the AC verified "files created" but not "files composed into deployed templates" and "agents can read the content at boot." The content shipped as dead files nobody reads.

This is not an isolated incident pattern — it is a predictable failure mode of the current AC creation guidance. The task-intake sub-skill specifies that ACs should include "edge case handling and side effect mitigations" and be "research-informed," but provides no systematic prompt for the PM to think about: (a) the build/composition pipeline the output must traverse, (b) the end consumer that must receive the output, and (c) regression against existing workflows and philosophy.

The root cause is a missing mental checklist at AC-writing time, not a deficiency in PM's general quality posture. SOUL.md and task-intake together form a strong process, but they leave the "integration gap" question implicit rather than explicit. The fix is a small, mandatory AC validation checklist embedded in the task-intake Phase 3 instructions — applied at the moment the GitHub Issue body is authored.

---

## Vault Context

- **BRIEFING.md priorities**: Going-public focus (v1.0.0 launch); any PM process fix should be L2 (universal, project-agnostic).
- **Related decisions**: [[decision-deterministic-testing]] — TCs must be executable, not subjective. ACs must be testable by a QA agent without judgment. This decision already exists and directly applies.
- **Related decisions**: [[decision-sub-skill-architecture]] — Composition is build-time concatenation; content in source files does not reach agents until `compose.py deploy` runs. This is the exact mechanism the L4 tasks failed to verify.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — Verification must be script-runnable, not prose assertions.
- **Human preferences**: "A loose acceptance criterion is not a judgment call left to dev — it is an unfinished spec." (SOUL.md, Quality Bar section). The human has high standards here — they want PM to catch this class of failure.
- **Related learnings**: None directly, but the #1291 QA incident (deferred TCs shipped as "zero gaps") parallels this failure. Both are cases where process allowed a gap to be normalized rather than caught.

---

## Impact Analysis

### Current AC Creation Process

ACs are created during **Phase 3 (Planning)** of the task-intake lifecycle. The specific instruction in `task-intake.md` is:

> **A) GitHub Issue** — create via tracker.py create-task with status Pending, referencing planning artifacts:
> - Description includes research-informed constraints
> - **Acceptance criteria include edge case handling and side effect mitigations**
> - References RESEARCH.md and CONTEXT.md

This is the only normative guidance on what ACs must contain. The PM is expected to derive ACs from research and context. There is no checklist or systematic prompt for integration verification.

### Files Touched

- `references/sub-skills/roles/pm/task-intake.md` — Phase 3 section, GitHub Issue creation block
- `references/roles/pm/L2/instructions.md` (if L2 architecture is being used) or equivalent PM L2 source
- Deployed `.squidsquad/pm/CLAUDE.md` (after compose)

### Behavior Changes

Adding a mandatory 4-point AC validation checklist that PM must explicitly apply before writing the AC list. No behavioral change to dev, QA, or DM workflows.

---

## Failure Modes — Categorized

### Type 1: Output Existence ≠ Output Delivered
The most common failure. PM verifies the file/content was created but does not verify it traverses the pipeline to its consumer.

- **Example**: L4 files created ✓, but `compose.py deploy` not in AC → agents never see the content.
- **Example**: Sub-skill source file added ✓, but not added to `includes.yml` → never composed.
- **Pattern trigger**: Any task where the output is an *intermediate artifact* (source file, template, config) rather than a *runtime behavior*.

### Type 2: Consumer Not Identified
PM writes ACs from the producer's perspective (file written, script updated) without asking "who reads this, and how do they get it?"

- **Example**: L4 SOUL.md updated, but AC doesn't verify `soul_adaptation.py` write target or that compose regenerates deployed SOUL.
- **Pattern trigger**: Any task that produces content meant to be read by an agent, user, or downstream script.

### Type 3: Regression to Existing Workflows Not Verified
AC checks that new behavior works, but doesn't verify existing behavior is preserved.

- **Example**: New compose layer added without verifying `git diff .squidsquad/` shows no unintended changes to existing agents.
- **Example**: New sub-skill inserted without verifying existing sub-skills are still present in deployed output.
- **Pattern trigger**: Any task that touches composition, template structure, or shared infrastructure.

### Type 4: Philosophy/Convention Conflict Not Checked
AC doesn't verify the implementation aligns with established decisions and patterns in the vault.

- **Example**: A new config mechanism that works correctly but bypasses the deterministic-scripts pattern established in [[pattern-deterministic-scripts-over-prose]].
- **Example**: A process change that contradicts a locked vault decision without flagging it.
- **Pattern trigger**: Tasks that add new patterns, mechanisms, or conventions.

### Type 5: AC Is Structurally Untestable
ACs written as prose quality goals that QA cannot execute deterministically.

- **Example**: "Content must be correct and comprehensive" — no script, no grep, no assertion.
- **Pattern trigger**: Whenever PM writes an AC without thinking "what command does QA run to verify this?"
- **Note**: [[decision-deterministic-testing]] already prohibits this — but the AC-creation step doesn't enforce it at write-time.

---

## Root Causes

**Primary**: No integration-awareness checklist at AC-writing time. PM is expected to derive integration requirements from research, but research focuses on risks/side effects — not on explicitly tracing the "write → pipeline → consumer" path for each deliverable.

**Secondary**: The Phase 3 instruction says "acceptance criteria include edge case handling and side effect mitigations" — but edge cases are about failure modes, not about pipeline integration. A PM can write a fully edge-case-aware AC that still misses the integration gap.

**Tertiary**: The task-intake sub-skill has no explicit prompt like "for each file this task creates, who reads it and how?" This question is obvious in retrospect but is not part of the current Phase 3 scaffolding.

**Not the root cause**: PM's general quality posture is strong. SOUL.md has the right values ("a loose acceptance criterion is not a judgment call left to dev"). The failure is mechanical — a missing checklist — not a values problem.

---

## Side Effects

- **Risk 1**: Checklist adds friction to trivial/cosmetic tasks — Severity: L — Mitigation: task-intake already has "light mode" for trivial tasks; checklist can be abbreviated or skipped in light mode with justification.
- **Risk 2**: PM applies checklist mechanically without understanding — Severity: M — Mitigation: frame each checklist item with a concrete question, not a box to tick.
- **Risk 3**: Checklist becomes stale as architecture evolves — Severity: L — Mitigation: keep the checklist generic (pipeline, consumer, regression) rather than referencing specific scripts. Project-specific details (compose.py, CLAUDE.md) belong in L4, not L2.

---

## Edge Cases

- **Task with no file output** (e.g., pure behavior change in a script): Type 1 and Type 2 don't apply. Checklist must be applied selectively — "does this task produce any artifact that must be consumed by another system?"
- **Light-mode task** (typo fix, config tweak): Full checklist overkill. PM should explicitly note which checklist items are N/A and why.
- **Task with multiple output types** (files + behavior + config): Each output type needs its own pipeline trace. PM must enumerate all outputs before writing ACs.
- **Bug fixes vs features**: Bug fixes that patch behavior in place (no new files) primarily need regression ACs. Bug fixes that change templates/configs still need integration ACs.

---

## Open Questions

- **Q1**: Should the AC checklist live in task-intake.md (Phase 3 block) or as a standalone AC-writing guide? — **Why it matters**: If in task-intake, it's guaranteed to fire at the right moment. If standalone, it can be referenced from multiple places (task-intake + SOUL.md) but adds one more file PM must remember to consult.
  - **Recommendation**: task-intake.md Phase 3, as a mandatory pre-writing block titled "AC Integration Check."

- **Q2**: Should the checklist be enforced at QA verification time, not just at PM writing time? — **Why it matters**: If QA has the same checklist, it can catch ACs that PM wrote incorrectly.
  - **Recommendation**: Yes — add a parallel note to QA's domain-context (skill domain) that integration ACs are expected and QA should flag if they're absent. But the primary fix is PM-side (write better ACs); QA-side is defense-in-depth.

- **Q3**: How prescriptive should the checklist be about SquidSquad-specific pipeline steps (compose.py, CLAUDE.md)? — **Why it matters**: This is L2 (universal PM), so it should not reference project-specific scripts. But the human wants PM to catch exactly the compose.py failure mode.
  - **Recommendation**: L2 checklist uses generic language ("build/composition pipeline," "deployed output"). The SquidSquad project's L4 instructions can add project-specific examples (compose.py, CLAUDE.md, boot sequence). This keeps L2 portable.

---

## What Good ACs Look Like For This Project

Given the 4-layer compose architecture, sub-skill system, and agent boot sequence, every AC on this project should be evaluated against this template:

```
For each deliverable this task produces:
  1. PIPELINE: Does the deliverable flow through a build/composition step before reaching its consumer?
     → If yes, AC must verify that step runs and succeeds (e.g., compose.py exit 0, includes.yml updated).
  2. CONSUMER: Who reads/uses the deliverable at runtime? Can the consumer actually see it?
     → AC must verify the consumer (agent, script, user) can reach the output (e.g., grep in deployed CLAUDE.md).
  3. REGRESSION: Does this change affect any existing behavior, template, or configured workflow?
     → AC must include a regression check (e.g., git diff shows no unexpected changes; test suite passes).
  4. TESTABILITY: Can QA run a deterministic command to verify each AC?
     → Every AC must map to a grep, script run, file check, or pytest assertion. No prose-only ACs.
```

### Industry Context

This maps to established patterns:

- **Definition of Done** (Scrum/Kanban): DoD includes "integrated into the system" and "all existing tests pass" — not just "code written." The L4 failure is a DoD gap.
- **Given/When/Then** (BDD): "When the task ships, THEN the agent reads the new content" — the "then" must close the loop, not stop at "THEN the file exists."
- **INVEST criteria**: ACs that only verify file existence are not "Testable" in the INVEST sense because the testable outcome is "agent behavior changes" not "file present."
- **Shift-left integration testing**: The integration gap should be caught at spec-writing (AC authoring), not at QA time. This is the key shift: PM owns the integration spec, QA verifies it.

---

## Recommendation

**Feasible with a small, targeted fix.** Add a mandatory "AC Integration Check" block to the Phase 3 section of `task-intake.md`, applied before writing the GitHub Issue body. The block consists of 4 questions PM must answer for each deliverable. If any answer is "yes," a corresponding AC is required. This fix is:

- Mechanical and low-ambiguity (4 questions, not open-ended)
- Applied at the right moment (Phase 3, just before Issue creation)
- Generic enough for L2 (no project-specific scripts)
- Consistent with SOUL.md's quality posture and [[decision-deterministic-testing]]
- Additive to the existing process (no phases removed or reordered)

**Secondary fix**: Add a parallel note in PM SOUL.md's Quality Bar section reinforcing that ACs must verify integration, not just existence. This is belt-and-suspenders — the Phase 3 checklist is the mechanical gate, SOUL.md reinforces the mindset.

**Do not fix**: Do not rewrite the entire task-intake Phase 3. The existing structure is sound. The gap is narrow and surgical.

---

## Vault Candidates

- **Type**: learning — "AC existence ≠ AC delivery: for any task producing an intermediate artifact, ACs must verify the full pipeline to the consumer, not just the artifact's creation." — **Why**: This is a reusable pattern that will apply to any future content/template task. Worth preserving so future PM cycles don't rediscover it.
- **Type**: pattern — "4-question AC integration checklist: pipeline? consumer? regression? testable?" — **Why**: Concise enough to put in vault as a reference pattern for AC writing.
