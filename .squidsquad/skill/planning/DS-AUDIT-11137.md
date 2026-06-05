Now I have a complete picture. Let me inventory all Goal statements across the four files and assess them against each criterion.

## Systematic Inventory

**Goal statements that exist** (identical `cycle-runner`, `context-pressure`, `agent-lifecycle` across all 4 files; worker-only Goals for `resume-working-state`, `git-commit`, `working-state`):

| Goal | Files | Lines |
|------|-------|-------|
| `cycle-runner` | pm, dm, verifier, worker | 182, 182, 183, 176 |
| `context-pressure` | pm, dm, verifier, worker | 200, 200, 201, 194 |
| `agent-lifecycle` | pm, dm, verifier, worker | 249, 236, 231, 228 |
| `resume-working-state` | worker | 200 |
| `git-commit` | worker | 220 |
| `working-state` | worker | 256 |

**`→ run sub-skill:` directives without Goal statements** fall into two categories: (a) runtime-loaded fragments (event-driven-workflow, l1-base, etc.) — never inlined, correct to lack Goals; (b) H3 compose-model directives (checkin, task-intake, pipeline-sentinel, etc.) — these have imperative inline descriptions but are compose-model operations, not replaced inlines. Neither category is a finding for criterion 1.

**Criterion 5 (boot-bootstrap inline)**: ✓ Confirmed inline in all 4 files (pm:72-166, dm:67-161, verifier:73-167, worker:64-158).

**Criterion 3 (tightness)**: ✓ All Goal statements are ≤3 sentences.

Now let me examine the `cycle-runner` Goal against criteria 2 and 4:

---

```
### Finding 1

- **File**: references/roles/pm/instructions.md (line 182), references/roles/dm/instructions.md (line 182), references/roles/verifier/instructions.md (line 183), references/roles/worker/instructions.md (line 176)
- **Severity**: FLAG
- **Issue**: The `cycle-runner` Goal statement describes tool-level mechanics — naming specific scripts and their actions — rather than only the end state the agent must reach.
- **Evidence**: The Goal reads: "`cycle_pre.py` has populated `cycle-input.json` with pull result, context pressure, working-state snapshot, and queue state; the agent's creative work has been read against that input; `cycle_post.py` will durably commit results and propagate status transitions." This violates criterion 2 ("no statement describes mechanics or 'how' — only what state the agent must reach") per TRD §4.6. Naming `cycle_pre.py` and `cycle_post.py` and describing what they do/have-done/will-do is a "how" description of tool orchestration, not a "what end state exists" description. A contract-compliant version would describe the state — e.g., "the cycle's input state (pull result, context pressure, working-state snapshot, queue state) has been captured; the agent's creative work is aligned against that input; the cycle's outputs are staged for durable commit" — without naming scripts.
- **Suggested fix**: Rewrite to describe only the end state without referencing `cycle_pre.py` or `cycle_post.py` by name. The Goal belongs to the orchestrator — it should say what is true at step completion, not which tool produced which artifact.
```

---

```
### Finding 2

- **File**: references/roles/pm/instructions.md (line 182), references/roles/dm/instructions.md (line 182), references/roles/verifier/instructions.md (line 183), references/roles/worker/instructions.md (line 176)
- **Severity**: NIT
- **Issue**: The `cycle-runner` Goal ends with "Hard precondition for any per-step work this cycle" — a meta-instruction about step ordering/dependencies, not a description of agent end state.
- **Evidence**: Criterion 4 requires Goals to summarize "what the agent has done by the end of this step." This closing clause describes a scheduling constraint (when other steps may run), not what state has been achieved. It reads as an implementation note that belongs in the sub-skill body, not in the orchestrator-facing Goal contract.
- **Suggested fix**: Drop the "Hard precondition for any per-step work this cycle" sentence from the Goal statement. If the dependency ordering needs documentation, place it in the `cycle-runner` sub-skill file body.
```

---

```
### Finding 3

- **File**: references/roles/pm/instructions.md (line 182), references/roles/dm/instructions.md (line 182), references/roles/verifier/instructions.md (line 183), references/roles/worker/instructions.md (line 176)
- **Severity**: NIT
- **Issue**: The `cycle-runner` Goal mixes past and future tense — "`cycle_pre.py` *has populated*" (past/completed) vs. "`cycle_post.py` *will durably commit*" (future/not-yet-done) — which undermines the "by the end of this step" framing.
- **Evidence**: Criterion 4: the Goal should summarize "what the agent has done by the end of this step." The future-tense clause about `cycle_post.py` describes something that hasn't happened yet at step completion, creating ambiguity about whether the Goal describes preconditions, postconditions, or both. Compare with the well-formed `context-pressure` Goal which consistently uses present-perfect: "the agent *has read*... *has compared*... *has checkpointed*."
- **Suggested fix**: Unify to present-perfect tense describing the end state — e.g., "the cycle's outputs have been staged for durable commit" rather than "`cycle_post.py` will durably commit."
```

---

## Summary

- **Criterion 1** (marker-first Goal on every replaced inline): ✅ PASS — all 6 de-inlined L1 step sub-skills have `Goal:` markers. The H3 compose-model directives with inline imperative text are a different mechanism (compose-model slot ops, not replaced inlines).
- **Criterion 2** (no mechanics/how): ❌ FINDING 1 — `cycle-runner` Goal names scripts and describes their actions.
- **Criterion 3** (tightness <5 sentences): ✅ PASS — all Goal statements are 2–3 sentences.
- **Criterion 4** (correct "end of step" contract): ⚠ FINDING 2, FINDING 3 — `cycle-runner` Goal includes a meta-instruction about ordering and uses future tense.
- **Criterion 5** (boot-bootstrap inline): ✅ PASS — confirmed inline in all 4 files.