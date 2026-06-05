# V2-AGENT-ASSEMBLE-DESIGN — Phase 1

PM Phase 1 deliverable for [#11053](https://github.com/WallyDoodlez/SquidSquad/issues/11053). Designs the **substrate** for `docs/COMPOSE-ARCHITECTURE.md` §4.6's assemble pass — replacing the retired PRD-B implementation (`model_router` → provider adapter → claude/sonnet API → preservation gates) with a Claude Code Agent-tool spawn pattern.

**Not a new architecture.** §4.6's vision is unchanged: per-H2-slot LLM rewrite, L4 > L3 > L2 > L1 precedence, verbatim conflict report, sub-skill-ref + step-ID + length-floor + code-block preservation. This document picks the substrate; the design lives in `docs/COMPOSE-ARCHITECTURE.md`.

Companion: [#11053 issue body](https://github.com/WallyDoodlez/SquidSquad/issues/11053).

## TL;DR

- **Substrate**: Agent-tool spawn from inside `atomic_emit.assemble_and_emit` (the same call site the retired API substrate used). One spawn per non-verbatim slot.
- **Default**: verbatim. Operator opts a slot IN via new `.squidsquad/config.md` `assemble-slots:` field, default empty.
- **First opt-in candidate**: `identity` (7-9 lines/role — smallest prompt budget, lowest preservation surface).
- **Audit substrate (AC7)**: hybrid — deterministic Python script as cheap fast-fail, second Agent spawn as semantic check (only runs if script passes).
- **Hard rule (AC6)**: subagent must justify every override against §4.6's precedence rule verbatim; unjustifiable conflicts emit unresolved (degrade to verbatim for that fragment) + log.

## Per-slot size budget (measured 2026-06-05 post-#11069)

| slot | dm | pm | qa | skill | avg | recommendation |
|---|---|---|---|---|---|---|
| Identity | 9 | 9 | 9 | 7 | 8 | **first opt-in** — tiny, prose-heavy, low preservation surface |
| Responsibility | 21 | 24 | 23 | 22 | 23 | second opt-in after identity proves out |
| Soul | 157 | 194 | 168 | 206 | 181 | third opt-in; per-H3 sub-spawns within slot if needed |
| Instructions | 770 | 795 | 760 | 985 | 828 | high preservation surface (step IDs + sub-skill refs); stays verbatim indefinitely |
| Project Context | 20 | 15 | 19 | 19 | 18 | stays verbatim (operator-authored L4) |
| Vault | 29 | 29 | 29 | 29 | 29 | stays verbatim (boilerplate-shaped) |

**Hard verbatim slots** (`_VERBATIM_SLOTS`-forced regardless of config opt-in): `project-context`, `vault`. Operator can never opt these in — see §1.3 below.

---

## 1. Substrate

### 1.1 Call site

`references/scripts/atomic_emit.assemble_and_emit()` — the same function that was the PRD-B dispatch site. Current behavior (post-#11050 prune): every slot routes through `_VERBATIM_SLOTS` (all 6), no LLM dispatch occurs. Post-this-design, `_VERBATIM_SLOTS` shrinks to forced-verbatim slots only (`project-context`, `vault`); the rest route through:

```python
if slot in _FORCED_VERBATIM_SLOTS:
    assembled_per_slot[slot] = linked_slot_body
elif slot not in opted_in_slots:           # operator config
    assembled_per_slot[slot] = linked_slot_body
else:
    assembled_per_slot[slot] = _agent_spawn_assemble(slot, linked_slot_body, ...)
```

`_agent_spawn_assemble` does the Agent-tool call and returns the rewritten body + conflict records.

### 1.2 Why this call site (not `compose.py` orchestration)

`compose.py:deploy_alias_v2` already calls `atomic_emit.assemble_and_emit(linked_composite, ...)`. Putting the spawn logic INSIDE `atomic_emit` means:

- Existing callers (test suite, wizard scaffolder path via `deploy_role_v2`) get the new behavior with zero call-site changes.
- The link stage and the catalog gate (compose.py:1140-1174) stay completely unchanged.
- Test injection seams that the PRD-B atomic_emit had can be re-introduced surgically (one parameter per assembler-callable) without re-touching `compose.py`.

The alternative (spawn from `compose.py` after `assemble_and_emit` returns) would require splitting the atomic-write contract — the §4.6 triple has to land in one operation or zero. Splitting is wrong.

### 1.3 Forced-verbatim slots

Two slots will NEVER be opted into LLM rewrite:

- **`project-context`**: this is operator-authored L4 content. The operator wrote it as the override of record; LLM rewrite would defeat the L4 contract.
- **`vault`**: boilerplate-shaped composed-state pointer (~29 lines, identical across roles). Nothing to dedupe; no contradictions possible.

These are enforced in code (not just config) as `_FORCED_VERBATIM_SLOTS`. Operator's `assemble-slots:` config entry for `project-context` or `vault` is a compose-time error.

### 1.4 Agent-tool invocation

```python
from anthropic_subagent import Agent  # pseudo-import; actual API per Claude Code

result = Agent({
    "description": f"assemble-{slot}",
    "subagent_type": "general-purpose",  # or a new "assemble" type if we register one
    "prompt": _build_prompt(slot, linked_slot_body, repo_root),
    "model": _model_for_slot(slot),  # default sonnet; pm config override
})
```

Returns a structured response (§4 below). On any tool error / timeout / refusal, fall back to verbatim for this slot and log under §6's failure-mode table.

---

## 2. Prompt template

### 2.1 Static structure

Each per-slot prompt is the concatenation of:

1. **Task header** (~10 lines, identical across slots): "You are an assemble subagent for SquidSquad's compose pipeline. You will receive a single H2 slot's linked-composite body. Rewrite it into a single coherent voice while preserving every architectural invariant. Output a structured JSON response (schema below). Do not introduce new content, new sub-skill references, new step IDs, or new file paths."

2. **Precedence rule, verbatim from §4.6** (~15 lines, identical across slots):
   > Layer precedence: L4 > L3 > L2 > L1. When two prose blocks materially contradict each other, the higher layer's prose prevails. The link stage placed higher-layer content later in the linked body via (slot_index, ordinal) sort. Collapse "do X / actually don't do X" into a single coherent statement aligned with the higher-layer position. Lower-layer prose is not silently erased — record the conflict in the JSON response.
   >
   > **Hard rule**: every override you apply MUST be justifiable using ONLY this precedence rule and the prose itself. If you cannot justify, emit the conflict as `unresolved` — keep both prose blocks verbatim in the assembled output for that fragment, and let the operator decide.

3. **Preservation contract** (~10 lines, identical across slots):
   > These tokens must survive verbatim in your output:
   > - Every `→ run sub-skill: <name>` reference
   > - Every step ID (`step:cycle/<phase>`)
   > - Every fenced code block content + language tag
   > - Every file path that appears outside HTML comments
   >
   > HTML comments (`<!-- ... -->`) may be trimmed.

4. **Slot-specific guidance** (~5-15 lines, per slot):
   - `identity`: "This slot establishes who the agent IS. Keep voice unified, second-person."
   - `responsibility`: "This slot enumerates duties. Preserve every bullet's intent; merge near-duplicates."
   - `soul`: "This slot is the agent's character. The §3.4 soul-merge precedence applies: shipped soul (L1-L3) first, project-local L4 append second; L4 wins on contradiction."
   - (etc.)

5. **The linked slot body** (the actual content to rewrite, variable size 7-985 lines).

### 2.2 Per-slot prompt budget

For sonnet, conservative budget: 64K tokens prompt + ~16K tokens response. With 4 chars/token average:

- Static prompt portion: ~40 lines × 80 chars = ~3.2KB = ~800 tokens
- Linked slot body: per measurements above, max ~985 lines × ~80 chars = ~79KB = ~20K tokens (skill instructions)
- Total: ~21K tokens prompt → comfortably under budget for every slot.

Identity at 7-9 lines fits in ~2.5KB. No budget concern for the first opt-in.

### 2.3 What the prompt does NOT include

- The full composed CLAUDE.md (only this one slot)
- Other slots' bodies (slot independence is by design)
- The architecture doc (§4.6 rules are inlined verbatim above; no `docs/COMPOSE-ARCHITECTURE.md` Read needed)
- Sub-skill bodies (they live elsewhere, agent doesn't need them to rewrite the slot)
- The conflicts report from prior runs (each invocation is stateless)

---

## 3. Opt-in config surface

### 3.1 Config field

New field in `.squidsquad/config.md`:

```markdown
## Assemble Slots
- **identity**: yes
- **responsibility**: no
- **soul**: no
- **instructions**: no
- **project-context**: forced-verbatim
- **vault**: forced-verbatim
```

Default state (no field present): all slots verbatim. Operator adds the section to opt in.

### 3.2 Per-slot model override

For future flexibility, allow per-slot model selection:

```markdown
## Assemble Slots
- **identity**: yes
- **identity-model**: sonnet
- **soul**: yes
- **soul-model**: opus
```

Default model: sonnet. Per-slot `-model` field overrides.

### 3.3 Validation at compose time

`config.py:parse_assemble_slots()` validates:
- Slot name is in `_CANONICAL_SLOTS` — unknown slot is a compose-time error
- `project-context` and `vault` cannot be `yes` — compose-time error
- Value must be `yes` / `no` / `forced-verbatim` — anything else is a compose-time error

---

## 4. Output schema

Subagent must return JSON with this shape:

```json
{
  "assembled_body": "<rewritten slot body as markdown>",
  "conflicts": [
    {
      "conflict_id": "C001",
      "winner_layer": "L4",
      "loser_layer": "L2",
      "winner_source": "references/sub-skills/project/pm-soul-directives.md",
      "winner_ordinal": 40,
      "loser_source": "references/sub-skills/common/agent-boundaries.md",
      "loser_ordinal": 10,
      "winner_quote": "<verbatim, ≤200 chars>",
      "loser_quote": "<verbatim, ≤200 chars>",
      "why_conflict": "<one-sentence explanation>",
      "resolution": "<one-sentence description of what assembled prose says>",
      "justification_citation": "§4.6 precedence rule: L4 > L3 > L2 > L1; winner is L4."
    }
  ],
  "unresolvable_fragments": [
    {
      "fragment_id": "U001",
      "fragments": ["<verbatim L_X quote>", "<verbatim L_Y quote>"],
      "why_unresolvable": "<one-sentence explanation>"
    }
  ]
}
```

### 4.1 Parsing

`atomic_emit._parse_assemble_response(json_text)`:
- Raise `LLMError` if JSON doesn't parse or required keys missing
- Validate every conflict has all 11 fields
- Validate every unresolvable fragment has its fragments preserved verbatim somewhere in `assembled_body`

### 4.2 AC6 enforcement at parse time

Per #11053 AC6: if any conflict's `justification_citation` does NOT cite §4.6's precedence rule literally, that conflict is REJECTED. The subagent gets one retry (cheap — same prompt). If retry also fails AC6, fall back to verbatim for the slot and log.

---

## 5. Conflict-report integration

`atomic_emit._build_conflicts_md(conflicts, unresolvable_fragments, role_class, model_id, commit_sha, generated_at)`:

Emits `CLAUDE.conflicts.md` per `docs/COMPOSE-ARCHITECTURE.md` §4.6 format:

```markdown
# Compose Conflict Report — <role-class>
Generated: <ISO-8601 timestamp>
Compose run: <commit SHA>
Assemble model: <model-id>
Total conflicts resolved: <N>
Total unresolvable fragments: <M>

## CONFLICT-C001 — slot: identity — precedence: L4 > L2
- **L2 source**: `references/sub-skills/common/agent-boundaries.md` (ordinal 10)
  > <loser_quote>
- **L4 source**: `references/sub-skills/project/pm-soul-directives.md` (ordinal 40)
  > <winner_quote>
- **Why this is a conflict**: <why_conflict>
- **Resolution in assembled output**: <resolution>
- **Justification citation**: <justification_citation>

## UNRESOLVABLE-U001 — slot: identity
- **Fragment A**: > <fragment A verbatim>
- **Fragment B**: > <fragment B verbatim>
- **Why unresolvable**: <why_unresolvable>
- **Resolution in assembled output**: both fragments preserved verbatim
```

Zero-conflict + zero-unresolvable runs still emit the file with the header and `Total: 0` lines.

---

## 6. Failure modes

| Mode | Detection | Response |
|---|---|---|
| Agent timeout (>120s) | `subprocess` timeout / Agent-tool error | Fall back to verbatim for this slot; log timeout in conflicts.md |
| Agent refuses | Empty / refusal response | Same as timeout |
| JSON parse fails | `json.loads` raises | One retry; if retry fails, fall back to verbatim |
| AC6 violation (no §4.6 citation) | `_parse_assemble_response` rejects conflict | One retry; if retry fails, fall back to verbatim |
| Preservation token dropped | Post-parse check: every `→ run sub-skill:`, step ID, file path, code block in input MUST appear in `assembled_body` | Fall back to verbatim; log preservation diff |
| `unresolvable_fragments` over-budget (>3 per slot) | Post-parse count check | Fall back to verbatim entire slot — too many unresolvables means the subagent didn't internalize the precedence rule |
| AC7 audit fails | §7 below | Fall back to verbatim; log audit failure |

Fall-back to verbatim for one slot does NOT abort the deploy. The other slots' assemble results stand. Logged failure surface is `CLAUDE.conflicts.md` plus a new `CLAUDE.assemble-log.md` (TBD — Phase 2).

---

## 7. Post-compose architecture audit (AC7)

Per #11053 cycle 2135 constraint: every non-verbatim slot's assembled body must pass an architecture audit before landing.

### 7.1 Two-tier audit

**Tier A — deterministic script (cheap fast-fail)** runs FIRST:

```python
def audit_assembled_slot(slot, assembled_body, linked_slot_body):
    # Same checks as the retired preservation pass plus structural ones:
    assert _sub_skill_refs(assembled_body) >= _sub_skill_refs(linked_slot_body)
    assert _step_ids(assembled_body) >= _step_ids(linked_slot_body)
    assert _file_paths(assembled_body, exclude_comments=True) >= _file_paths(linked_slot_body, exclude_comments=True)
    assert _code_blocks(assembled_body) == _code_blocks(linked_slot_body)
    # Workflow contracts:
    assert _status_transition_refs(assembled_body) == _status_transition_refs(linked_slot_body)
    assert _tracker_grammar_examples(assembled_body) >= _tracker_grammar_examples(linked_slot_body)
```

If Tier A fails → revert to verbatim immediately, log under §6.

**Tier B — subagent audit (semantic check)** runs only if Tier A passes:

A second Agent spawn (`subagent_type: "general-purpose"`) gets a prompt:

> You are auditing a rewritten H2 slot of a SquidSquad composed CLAUDE.md. Compare the rewritten body to the original linked body. Answer two questions:
>
> 1. Does the rewrite disable any functionality? Specifically: does it weaken or drop any sub-skill reference, step ID, fenced procedure block, configuration directive, or workflow contract present in the original?
>
> 2. Does the rewrite break agent-to-agent workflow? Check: status transition table integrity, role-routing rules, tracker comment grammar, file-conventions agents rely on for hand-off, vault/BRIEFING.md write protocols.
>
> Output JSON: `{"functionality_disabled": "<finding or 'none'>", "workflow_broken": "<finding or 'none'>", "audit_verdict": "PASS" | "FAIL"}`.

If Tier B verdict = FAIL → revert to verbatim, log Tier B's specific findings as a new conflict entry of type `AUDIT-FAILURE`.

### 7.2 Audit cost

Per-deploy cost: N spawns for assemble + N spawns for Tier B audit = 2N total, where N = opted-in slots. For the recommended first-opt-in (`identity` only), that's 2 spawns per `deploy <alias>`, 8 spawns per `deploy-all` (4 aliases). Acceptable.

---

## 8. Phased rollout

1. **Phase 2.1 (skill task)**: implement `_FORCED_VERBATIM_SLOTS` + `parse_assemble_slots` config + `_agent_spawn_assemble` stub that just returns verbatim. Ship. Validates the plumbing.
2. **Phase 2.2 (skill task)**: implement full `_agent_spawn_assemble` for `identity` slot only. Implement Tier A audit. Ship. Operator can now opt `identity` in via config.
3. **Phase 2.3 (skill task)**: implement Tier B subagent audit. Ship. Closes AC7.
4. **Phase 2.4 (operator)**: opt `identity` in for one role, eyeball the result, iterate on the prompt template.
5. **Phase 2.5+**: opt subsequent slots in (responsibility, then soul) once identity proves stable.

`instructions` slot stays verbatim indefinitely (highest preservation surface; lowest ROI).

---

## 9. Open questions for operator decision

1. **Subagent type**: use `general-purpose`, or register a new `subagent_type: "assemble"` with constrained tool access (Read only — no Write/Edit needed since the subagent's output IS the result)? Lean: register a new type to enforce the contract.

2. **Model default**: sonnet across the board, or per-slot defaults (opus for soul because it's harder; haiku for vault because it's small)? Lean: sonnet for all, per-slot override available in config.

3. **AC6 retry count**: one retry on AC6 violation, or zero (fail fast)? Lean: one retry — subagents sometimes self-correct.

4. **Audit timeout**: Tier B's audit subagent timeout — same 120s as assemble, or tighter (60s)? Lean: 120s same (audit task is similar complexity).

5. **`CLAUDE.assemble-log.md`**: do we add a sixth artifact alongside CLAUDE.md / CLAUDE.linked.md / CLAUDE.conflicts.md to log per-slot assemble outcomes (verbatim / assembled / failed-fellback / audit-failed)? Lean: yes, but defer to Phase 2 implementation.

---

## 10. What Phase 2 implementation scopes (handoff to skill)

When operator confirms this design, file as one umbrella task (or three, per the phasing above) to skill. Skill writes the code. PM stays in coordination — answers config-validation questions, picks the first opt-in slot, signs off on Phase 2.2 ship.

Phase 1 deliverable (this document) does NOT include:
- Code changes (skill's lane)
- Prompt template iteration (Phase 2.4, operator-driven)
- The exact JSON parser implementation (skill's lane during Phase 2.1)

---

## Status (cycle 2143 ext, 2026-06-05)

- Phase 1 deliverable v1 committed
- #11053 transitioned approved → in-progress
- **Awaiting operator review of §9 open questions** before any Phase 2 work files

Next PM cycle: refine §2 prompt template based on §9 answers; possibly file Phase 2.1 task to skill.
