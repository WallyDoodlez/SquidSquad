## Background

Operator ran `python references/scripts/compose.py deploy-all` post-E6 cutover (#10999, merged ~2 hours before this issue). Every alias failed before producing any output. Multi-hour interactive debugging session uncovered four bugs in the cutover and three structural issues in the compose architecture. All four bugs were patched locally to confirm the pipeline could be unblocked; patches were then reverted so main is clean. **This issue is the formal investigation request — DO NOT pick this up as straight implementation. PM runs Phase 1.**

## Symptom

`compose.py deploy-all` from a plain shell (not from inside an Agent-tool-equipped parent) fails for every alias:

```
[model_router] No provider found for model 'sonnet'. Falling back to Claude.
ERROR: assemble_and_emit failed for alias 'dm': assemble_slot raised on slot `identity`: model_router.route returned exit code 1 for assemble task_id=assemble-identity slot=identity.
```

## Bugs found and confirmed (all four reproduced + patched + reverted)

### Bug 1: `sonnet` model lock has no provider

`references/scripts/model_router.py:135-136` hardcodes `return "sonnet"` for task_type `"assemble"` (PRD-B B9 / #10763 AC5, locked per PRD-B SC10). But `references/scripts/providers/` only ships `openai` and `deepseek` manifests — no Anthropic provider. `_load_provider_manifest("sonnet")` returns `(None, None)`, route() prints "No provider found" and returns exit 1, `assemble_slot` raises `AssembleSlotError`, deploy aborts.

Git history confirms no Anthropic provider was ever committed. PR #10999's "end-to-end deploy_alias_v2 verified clean" claim (PM audit cycle 2121) must have run under `SQUIDSQUAD_MODEL_OVERRIDE=gpt-5.2` (live-integration test mode) or inside an agent that satisfied the `delegate-to-agent-tool` contract — not raw operator-invoked CLI.

### Bug 2: `model == "claude"` path is unwired for shell callers

When `model_router.route()` resolves to `"claude"`, it logs `{"action": "delegate-to-agent-tool"}` and returns exit 1 with NO file written (`references/scripts/model_router.py:662-670`). That contract assumes an Agent-tool-equipped parent wraps the call. True from inside an agent session; FALSE from `python compose.py deploy-all` at a plain shell. `assemble_slot` treats non-zero as fatal, raises. The pattern that DOES work (and exists in the codebase) is `references/scripts/run_comprehension_test.py:158-215` which shells out to `claude -p <prompt> --output-format json --allowedTools Read`. The route() claude branch never adopts it.

### Bug 3: `_split_linked_into_slots` regex breaks on role-suffixed H2 in soul

`references/scripts/atomic_emit.py:_split_linked_into_slots` matches every `## <heading>` as a section boundary, then keys by lowercased display name. Every source SOUL.md (`references/roles/{pm,dm,verifier,worker}/SOUL.md`) opens with a role-suffixed H2 — `## Soul — PM`, `## Soul — DM (Delivery Manager)`, etc. The link stage wraps each slot with a bare canonical H2 (`## Soul\n\n`). Net result in the composite:

```
## Soul          ← canonical (empty body)
## Soul — Base Agent
<base body>
## Soul — PM
<PM body>
## Instructions  ← next slot starts
```

The splitter regex matches the bare canonical `## Soul` → empty body wins the lookup. The role-suffixed H2s aren't canonical names → their bodies are silently discarded. `assemble_slot` then sends an empty linked body to the LLM, which responds conversationally ("Ready. Paste the slot content...") instead of rewriting. Captured prompt/response artifacts were under `.squidsquad/diagnostics/assemble-debug/` during the debug session (deleted on revert).

### Bug 4: Preservation verifier counts tokens inside HTML comments

`references/scripts/assemble_verifier.py:verify_preservation` extracts sub-skill refs, step IDs, file paths from the FULL linked body, including inside `<!-- ... -->` blocks. Source files contain meta-comments like:

```
<!-- L2 DM instructions — H3 ops target L1 base step IDs defined in references/roles/instructions.md -->
```

The LLM reasonably trims these meta-comments during rewrite. The verifier counts the path tokens inside the comment and flags them as "the LLM dropped this path." False positive that blocks deploy. Affected paths observed during debug: `references/roles/instructions.md`, `tests/test_compose_9588.py`, `.squidsquad/vault/BRIEFING.md`, `references/scripts/config.py`.

## Structural issues uncovered during debugging (the real cost)

These are NOT bugs in the cutover. They are architectural choices the cutover surfaced. **These are the actual investigation scope.**

### Finding A: Sub-skills are double-included, violating `feedback_compose_dry`

Operator memory `feedback_compose_dry` explicitly states: *"Within L1-L4 each creative-work concept must have exactly one authoring location; extract-and-reference, never duplicate inline."*

Measurement on the post-cutover PM composite (`.squidsquad/pm/CLAUDE.linked.md`, 2227 lines, captured during debug session):
- **28 sub-skill bodies inlined in full**, each wrapped between `<!-- sub-skill: <name> -->` / `<!-- /sub-skill: <name> -->` boundary markers
- **16 sub-skill references** in `→ run sub-skill: <name>` form
- **65% of the linked composite (1453 of 2227 lines) is inlined sub-skill bodies**
- Substantial overlap: `pipeline-sentinel` appears at line 836 (130-line inline body) AND at line 2129 as `→ run sub-skill: pipeline-sentinel`. Same pattern for `vault-remember`, `health-check`, `agent-lifecycle`, etc.

The link stage's inlining is deliberate (`v2_link_stage.py` emits the boundary markers explicitly). The design decision violates the saved operator preference.

### Finding B: Procedural sub-skills are runbooks in prose, not Python

`references/sub-skills/roles/pm/pipeline-sentinel.md` is 135 lines containing ~10 inline bash code blocks. The shape is uniform: `gh issue list --json ...` query → filter by status/label → conditional `tracker.py transition` + `tracker.py comment`. Six sub-procedures (4a Orphaned PR, 4b Shipped without merge, 4c Approved no pickup, 4d Planned no approval, 4e Pending no planning, 4f In-progress on dead agent) each have the same query+filter+act shape. None of this requires LLM reasoning — the only "judgment" is parameters like "max 2 nudges per cycle" which are function arguments.

Comparable runbooks in prose (size, % bash, complexity):
- `pipeline-sentinel` — 135 lines, 10 bash blocks, 6 sub-procedures
- `vault-remember` — 88 lines in composite, explicit 4-gate logic with bash gates between each
- `vault-synthesis` — 82 lines in composite, 5 numbered steps with bash queries
- `health-check` — bash query + conditional tier-1/tier-2 actions
- `soul-shepherd` — 5-category checklist with conditional vault writes
- `improvement-scan` — file selection + scan execution + finding triage

Operator memory `project_improvement_loop_philosophy` and broader `feedback_trust_script_output` point at this: deterministic scripts over prose. When behavior can be encoded in a Python script, do that instead of writing prose instructions that an LLM must interpret. The existing `cycle_pre.py` / `cycle_post.py` split is the proven pattern.

### Finding C: Instructions slot is too large for any LLM rewrite to be deterministic

PM's instructions slot is 1924 lines (86% of the composite). 85 H3 sub-sections. Largest single section is pipeline-sentinel at 130 lines.

The assemble pass asks the LLM to rewrite this while preserving every sub-skill ref, step ID, fenced code block, and file path verbatim — multiset-exact. Even at 99.5% per-token compliance, hundreds of preservation tokens means ~5 expected misses per run. The B2/B3/B5 preservation gates are deliberately zero-tolerance. **Stochastic LLM compliance cannot satisfy deterministic gates at this slot size.** This was confirmed across 7+ retry runs during the debug session, each producing different drift: dropped `step:cycle/resume`, dropped `step:cycle/implement`, extra duplicated step IDs, lower-layer prose left in alongside higher-layer (B5 PrecedenceViolation), missing file paths. Prompt strengthening shifts the rate but cannot make stochastic deterministic.

For context: the PM assemble actually saved 50 lines (2227 → 2177, 2% compression). The assemble pass is doing trivial work at huge cost and infinite failure risk on the instructions slot.

## Why these are linked

Finding A is the cause of Finding C. The link stage inlines 1453 lines of sub-skill body THEN the assemble pass tries to rewrite them. If sub-skills stayed as references (per `feedback_compose_dry`), the instructions slot would be ~470 lines — possibly tractable for assemble, or possibly assemble becomes unnecessary because the prose was never bloated in the first place.

Finding B compounds A: even those ~470 remaining lines of "real" instructions contain procedural runbooks (e.g. "Step 1b — Context Pressure Check" with its 4-step bash sequence) that should be `python references/scripts/<runbook>.py` calls.

## Recommended Phase 1 research scope

This investigation likely re-shapes as a **PRD** (per `project_trd_prd_delivery_model`), not a single task. Phase 1 should determine:

1. **Cutover bug ownership**: are bugs 1-4 a single "cutover stabilization" issue with 4 ACs, or four separate issues? Operator preference: combined, since they were all introduced together and the fix touches overlapping files.
2. **Inlining decision**: was sub-skill body inlining intentional in PR #10999, or an emergent property of the v2 link-stage rewrite? Read `v2_link_stage.py` history + the v2 design TRD if one exists. If intentional, what problem was it solving? (If runtime sub-skill resolution is unreliable, that's the underlying problem to fix, not "inline everything.")
3. **Reference-only feasibility**: if the link stage stops inlining and only emits `→ run sub-skill:` references, can the agent reliably Read the sub-skill file at runtime? `boot-bootstrap.md` runtime-loads several fragments; the pattern exists. Quantify which sub-skills are run-once-per-cycle vs run-only-on-event.
4. **Procedural extraction candidate list**: which sub-skills are pure runbooks that should become `.py` files? Each candidate: input args, output contract, current size in prose, estimated Python size.
5. **Assemble pass scope after inlining is fixed**: does it still have a job? If instructions becomes ~470 lines of non-procedural coordination prose, is the layered-voice rewrite worth the cost + fragility? If not, retire the assemble stage entirely and revert to v1 single-stage compose.

## Acceptance criteria (proposed — PM finalizes after Phase 1)

- AC1: `compose.py deploy-all` succeeds from a plain shell with no environment overrides, no `SQUIDSQUAD_MODEL_OVERRIDE` env var, no Agent-tool parent.
- AC2: No sub-skill body appears more than once in any composed CLAUDE.md. Sub-skills are referenced via `→ run sub-skill: <name>` only (per `feedback_compose_dry`).
- AC3: `pipeline-sentinel`, `vault-remember`, `vault-synthesis`, `health-check` are deterministic Python scripts the agent invokes; the sub-skill markdown contains only the run instruction + argument schema.
- AC4: Comprehension test: a fresh agent given the new composed PM CLAUDE.md can correctly answer (a) when to run pipeline-sentinel, (b) what tier-2 stuck-state detection does, (c) where to find sub-skill bodies — without seeing the prior version of any file.
- AC5: `tests/test_compose_*.py` cover the load-bearing invariants (no double-include, instructions slot under N lines, all sub-skill references resolve to a runtime-readable file).

## Operator-session evidence (not part of the formal record, but useful context)

During the debug session the operator added `instructions` to `_VERBATIM_SLOTS` as a one-line unblock; with that flag plus the four bug patches, all 4 aliases deployed successfully in ~10 seconds (dm 1549, pm 2189, qa 1778, skill 1941 lines). The unblock returns instructions slot to pre-cutover behavior (raw layered prose, no LLM rewrite). This is NOT the recommended fix — it papers over Findings A+B without addressing them — but proves the slot doesn't need the assemble pass to produce a working CLAUDE.md.

All operator patches have been reverted; main is clean as of this filing.
