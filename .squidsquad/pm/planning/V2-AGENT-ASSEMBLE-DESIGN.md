# V2-AGENT-ASSEMBLE-DESIGN — Phase 1

PM Phase 1 deliverable for [#11053](https://github.com/WallyDoodlez/SquidSquad/issues/11053). Designs the **substrate** for `docs/COMPOSE-ARCHITECTURE.md` §4.6's assemble pass — replacing the retired PRD-B implementation (`model_router` → provider adapter → claude/sonnet API → preservation gates) with a Claude Code Agent-tool spawn pattern.

**Not a new architecture.** §4.6's vision is unchanged: per-H2-slot LLM rewrite, L4 > L3 > L2 > L1 precedence, verbatim conflict report, sub-skill-ref + step-ID + length-floor + code-block preservation. This document picks the substrate; the design lives in `docs/COMPOSE-ARCHITECTURE.md`.

Companion: [#11053 issue body](https://github.com/WallyDoodlez/SquidSquad/issues/11053).

## TL;DR

- **Substrate**: Agent-tool spawn from inside `atomic_emit.assemble_and_emit` (the same call site the retired API substrate used). One spawn per non-forced-verbatim slot.
- **Operating mode**: **unconditional** per TRD §3.0 / §4.6. Every non-forced-verbatim slot is rewritten on every compose run. The opt-in/opt-out framing from this doc's first draft is superseded — the TRD-locked decision is unconditional assemble, made tractable by the orchestrator-content rule keeping slots small and goal-shaped (TRD §4.6 "Orchestrator-content rule").
- **`assemble-slots:` config**: per-slot **model overrides only** (per TRD §4.6 Model paragraph) — not a slot-level on/off switch. Forced-verbatim slots cannot be named in `assemble-slots:` (compose-time error per TRD §4.6 "Forced-verbatim behaviour").
- **Audit substrate (AC7)**: hybrid — deterministic Python script as cheap fast-fail, second Agent spawn as semantic check (only runs if script passes).
- **Hard rule (AC6)**: subagent must justify every override against §4.6's precedence rule verbatim; unjustifiable conflicts emit unresolved (degrade to verbatim for that fragment) + log.

## Per-slot size budget (measured 2026-06-05 post-#11069)

| slot | dm | pm | qa | skill | avg | recommendation |
|---|---|---|---|---|---|---|
| Identity | 9 | 9 | 9 | 7 | 8 | unconditional spawn — tiny, prose-heavy, low preservation surface |
| Responsibility | 21 | 24 | 23 | 22 | 23 | unconditional spawn |
| Soul | 157 | 194 | 168 | 206 | 181 | unconditional spawn; per-H3 sub-spawns within slot may be useful at the upper end |
| Instructions | 770 | 795 | 760 | 985 | 828 | unconditional spawn under the orchestrator-content rule — sizes shown are pre-Task B (Path A over-inline reversal); post-Task B the instructions slot is expected to drop substantially as the 9 misplaced mandatory inlines move back to marker references |
| Project Context | 20 | 15 | 19 | 19 | 18 | **forced verbatim** (`_FORCED_VERBATIM_SLOTS`) — never spawns |
| Vault | 29 | 29 | 29 | 29 | 29 | **forced verbatim** (`_FORCED_VERBATIM_SLOTS`) — never spawns |

**Forced-verbatim slots** (`_FORCED_VERBATIM_SLOTS`): `project-context`, `vault`. Enforced in code; operator's `assemble-slots:` config cannot opt them in (compose-time error per TRD §4.6) — see §1.3 below.

---

## 1. Substrate

### 1.1 Call site

`references/scripts/atomic_emit.assemble_and_emit()` — the same function that was the PRD-B dispatch site. Current behavior (post-#11050 prune): every slot routes through `_VERBATIM_SLOTS` (all 6), no LLM dispatch occurs. Post-this-design, `_VERBATIM_SLOTS` shrinks to **`_FORCED_VERBATIM_SLOTS`** (only `project-context`, `vault`); every other slot dispatches unconditionally via Agent-tool spawn per TRD §3.0 / §4.6:

```python
if slot in _FORCED_VERBATIM_SLOTS:
    assembled_per_slot[slot] = linked_slot_body
else:
    # Unconditional Agent-tool spawn per TRD §3.0 / §4.6. The assemble-slots:
    # config may carry a per-slot model override; it does NOT gate on/off.
    model = _model_for_slot(slot)  # default sonnet; per-slot override from config
    assembled_per_slot[slot] = _agent_spawn_assemble(slot, linked_slot_body, model=model, ...)
```

`_agent_spawn_assemble` does the Agent-tool call and returns the rewritten body + conflict records.

### 1.2 Why this call site (not `compose.py` orchestration)

`compose.py:deploy_alias_v2` already calls `atomic_emit.assemble_and_emit(linked_composite, ...)`. Putting the spawn logic INSIDE `atomic_emit` means:

- Existing callers (test suite, wizard scaffolder path via `deploy_role_v2`) get the new behavior with zero call-site changes.
- The link stage and the catalog gate (compose.py:1140-1174) stay completely unchanged.
- Test injection seams that the PRD-B atomic_emit had can be re-introduced surgically (one parameter per assembler-callable) without re-touching `compose.py`.

The alternative (spawn from `compose.py` after `assemble_and_emit` returns) would require splitting the atomic-write contract — the §4.6 triple has to land in one operation or zero. Splitting is wrong.

### 1.3 Forced-verbatim slots

Two slots will NEVER receive LLM rewrite:

- **`project-context`**: this is operator-authored L4 content. The operator wrote it as the override of record; LLM rewrite would defeat the L4 contract.
- **`vault`**: boilerplate-shaped composed-state pointer (~29 lines, identical across roles). Nothing to dedupe; no contradictions possible.

These are enforced in code (not just config) as `_FORCED_VERBATIM_SLOTS`. Operator's `assemble-slots:` config entry for `project-context` or `vault` is a compose-time error.

### 1.4 Agent-tool invocation

```python
from anthropic_subagent import Agent  # pseudo-import; actual API per Claude Code

result = Agent({
    "description": f"assemble-{slot}",
    "subagent_type": "assemble",  # LOCKED per §9 Q1; .claude/agents/assemble.md with tools: Read
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

Identity at 7-9 lines fits in ~2.5KB. No budget concern.

### 2.3 What the prompt does NOT include

- The full composed CLAUDE.md (only this one slot)
- Other slots' bodies (slot independence is by design)
- The architecture doc (§4.6 rules are inlined verbatim above; no `docs/COMPOSE-ARCHITECTURE.md` Read needed)
- Sub-skill bodies (they live elsewhere, agent doesn't need them to rewrite the slot)
- The conflicts report from prior runs (each invocation is stateless)

### 2.4 Worked example — PM identity slot (smallest spawning slot — used as the worked-example anchor throughout this document)

Concrete input the subagent sees for `compose.py deploy pm` at the `identity` slot. This is what the freshly-deployed PM composite produces at slot=identity (cycle 2143 measurement):

```
### append

You are the PM on the SquidSquad autonomous dev team. You are the bridge between the human and the dev agents. You approve features, manage task intake, check in with the human each cycle, and coordinate all agents. You have a technical background — almost as if you were a highly skilled developer who switched career. You think in scope, priorities, and dependencies. You protect the human from noise and protect agents from ambiguity.

The active dev agents on this project are listed in `.squidsquad/config.md` (Workers field). Read it at boot.

You are PM on SquidSquad — the framework that builds itself. Every process decision you make affects your own next cycle. The team you coordinate develops the system you run on; treat this as a load-bearing constraint on every choice, not [...]
```

This input has FOUR distinct prose pieces:
1. The L4 op header (`### append`) — preserve verbatim per §4.6 step-ID preservation
2. L4 project-pm-identity body — "You are the PM..." (high ordinal, project layer)
3. L1 base config pointer — "The active dev agents..." (low ordinal, applies to every role)
4. L4 project-soul-style body — "You are PM on SquidSquad..." (highest ordinal)

Pieces 2 and 4 both establish "who PM is" with overlapping but not identical prose. The assemble subagent's job: collapse into one coherent identity statement. Piece 3 is a procedural pointer, not character prose — it stays inline as-is (or merges into the first paragraph).

**Expected output** (sketch — actual prose is the subagent's call):

```
### append

You are the PM on the SquidSquad autonomous dev team — the framework that builds itself. You bridge the human and the dev agents: approving features, managing task intake, checking in with the human each cycle, and coordinating all agents. You have a technical background, the kind of highly skilled developer who switched into coordination. You think in scope, priorities, and dependencies. You protect the human from noise and protect agents from ambiguity.

Every process decision you make affects your own next cycle. The team you coordinate develops the system you run on; treat this as a load-bearing constraint on every choice.

The active dev agents on this project are listed in `.squidsquad/config.md` (Workers field). Read it at boot.
```

**Conflicts identified** (subagent JSON response):
- None in this example. Pieces 2 and 4 don't materially contradict — they reinforce. The subagent merges them under the §4.6 rule "later/more-specific layers refine earlier/more-general ones" without invoking a precedence override.

**If a conflict WERE present** (hypothetical): say a future L4 op replaced "highly skilled developer who switched career" with "career project manager with no engineering background." Then:
- `winner_layer: "L4"`, `loser_layer: "L4"` (same layer, later ordinal wins via stable sort)
- `justification_citation`: "§4.6 precedence rule: same layer → later ordinal wins via link stage's (slot_index, ordinal) sort"
- `resolution`: "Identity describes PM as career project manager; engineering-background phrasing dropped."

This worked example is what Phase 2.4 operator-driven prompt tuning iterates on. The prompt template in §2.1 should produce something close to the sketch on the first run.

### 2.5 Worked example — PM responsibility slot (the boring case)

Counter-example: a slot where the assemble subagent should produce output that is nearly identical to the input. This documents that "no rewrite needed" is a legal output state.

PM responsibility slot has two source files:
- L4 `references/sub-skills/project/pm-responsibility.md` ordinal 10 — currently a stub ("No install-specific responsibility additions for pm at this time.")
- L2 `references/roles/pm/responsibility.md` ordinal 20 — the full role-specific content (3 H3 sections, ~24 lines)

The linked input the subagent sees:

```
# pm — Install-specific responsibility additions (L4)

No install-specific responsibility additions for pm at this time.

To add: replace this stub with directives in the same shape as L2 ...

## Responsibility

### What this role does

- Coordinates the squad: investigates the pipeline state every cycle, ...
- Interfaces with the human each cycle: captures new requirements, ...
[...continues with full role content...]
```

**Expected output**: drop the L4 stub (it's literally "no additions"), keep the L2 content verbatim. The subagent should recognize the L4 stub as non-content and emit:

```
## Responsibility

### What this role does

- Coordinates the squad: investigates the pipeline state every cycle, ...
- Interfaces with the human each cycle: captures new requirements, ...
[...continues with full role content verbatim...]
```

**Conflicts**: zero. The L4 stub doesn't contradict L2; it's an empty placeholder.

**Justification cited**: none needed. No overrides applied. The conflicts.md entry for this slot is: `Total conflicts resolved: 0`.

**What this example teaches**: the subagent's value is in conflict resolution, not unconditional rewriting. Most slot rewrites with default L4 content (stubs everywhere) should be near-verbatim. Phase 2.4 tuning includes a "don't rewrite unnecessarily" instruction so the subagent doesn't paraphrase coherent prose just because it can.

This pattern (L4 stub + L2 full) is the COMMON case for responsibility / instructions / soul slots in a fresh install. Identity is the exception — its L4 typically has real content because project naming is install-specific.

---

## 3. `assemble-slots:` config surface (model-override only)

Per TRD §3.0 / §4.6, the assemble pass is **unconditional**: every non-forced-verbatim slot dispatches via Agent-tool spawn on every compose run. There is no slot-level on/off switch. The `assemble-slots:` config field exists for **per-slot model overrides only**.

### 3.1 Config field

New field in `.squidsquad/config.md` (optional — installs without this field use the sonnet default for every spawning slot):

```markdown
## Assemble Slots
- **identity-model**: sonnet
- **soul-model**: opus
- **instructions-model**: sonnet
```

Default state (field absent or no per-slot `-model` entry): sonnet for every spawning slot. Operator adds entries only to override the default for specific slots.

### 3.2 Per-slot model override

The `<slot>-model:` entries pick the model the per-slot Agent spawn uses. The forced-verbatim slots (`project-context`, `vault`) accept no `-model` entry — listing one is a compose-time error per §3.3.

Valid model identifiers track the Anthropic tier names current at compose time (`sonnet`, `opus`, `haiku`). Compose treats unknown identifiers as a compose-time error rather than passing them through to the Agent tool.

### 3.3 Validation at compose time

`config.py:parse_assemble_slots()` validates:

- Slot name in `<slot>-model:` is in `_CANONICAL_SLOTS` — unknown slot is a compose-time error
- Slot must NOT be in `_FORCED_VERBATIM_SLOTS` (`project-context`, `vault`) — naming a forced-verbatim slot is a compose-time error, regardless of value
- Model identifier must be a known tier name — anything else is a compose-time error
- Legacy on/off entries from this doc's first draft (`identity: yes`, `responsibility: no`, etc.) are **rejected** as a compose-time error with a migration hint pointing at the TRD §4.6 "unconditional" decision and this section's model-override format

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

A second Agent spawn (`subagent_type: "assemble"` — same custom type as the primary spawn; the Read-only tool constraint applies equally to the audit pass, since the audit subagent should not introduce external context either) gets a prompt:

> You are auditing a rewritten H2 slot of a SquidSquad composed CLAUDE.md. Compare the rewritten body to the original linked body. Answer two questions:
>
> 1. Does the rewrite disable any functionality? Specifically: does it weaken or drop any sub-skill reference, step ID, fenced procedure block, configuration directive, or workflow contract present in the original?
>
> 2. Does the rewrite break agent-to-agent workflow? Check: status transition table integrity, role-routing rules, tracker comment grammar, file-conventions agents rely on for hand-off, vault/BRIEFING.md write protocols.
>
> Output JSON: `{"functionality_disabled": "<finding or 'none'>", "workflow_broken": "<finding or 'none'>", "audit_verdict": "PASS" | "FAIL"}`.

If Tier B verdict = FAIL → revert to verbatim, log Tier B's specific findings as a new conflict entry of type `AUDIT-FAILURE`.

### 7.2 Audit cost

Per-deploy cost: N spawns for assemble + N spawns for Tier B audit = 2N total, where N = non-forced-verbatim slots (today: 4 — identity, responsibility, soul, instructions). That's 8 spawns per `deploy <alias>`, 32 spawns per `deploy-all` (4 aliases). Tier B is cache-eligible per §1.1 caching contract, so steady-state cost drops substantially after the first compose run on a given source tree.

---

## 8. Phased rollout

1. **Phase 2.1 (skill task)**: implement `_FORCED_VERBATIM_SLOTS` + `parse_assemble_slots` config + `_agent_spawn_assemble` stub that just returns verbatim. Ship. Validates the plumbing.
2. **Phase 2.2 (skill task)**: implement full `_agent_spawn_assemble` covering all four non-forced-verbatim slots (identity, responsibility, soul, instructions). Implement Tier A audit. Ship. Identity is the smallest slot and the natural first opt-in for any ad-hoc operator testing during this phase, but the implementation covers all four because the assemble pass is unconditional per the TRD.
3. **Phase 2.3 (skill task)**: implement Tier B subagent audit. Ship. Closes AC7.
4. **Phase 2.4 (operator)**: run `compose.py deploy <alias>` on one role, eyeball the `identity` slot first (smallest, easiest to read end-to-end), iterate on the prompt template if findings emerge.
5. **Phase 2.5+**: review the larger slots (responsibility, then soul, then instructions) once identity reads cleanly; iterate prompt template per slot if needed. All four slots ship in 2.2; this phase is observation + prompt refinement, not gated activation.

`instructions` slot stays verbatim indefinitely (highest preservation surface; lowest ROI).

---

## 9. Open questions — LOCKED 2026-06-05 (operator decision)

1. **Subagent type**: **LOCKED — register new `subagent_type: "assemble"`** with Read-only tool access. Implementation: add `.claude/agents/assemble.md` with frontmatter `tools: Read` + model default per Q2 + description naming this design as the contract. Replaces line 76's `"general-purpose"` placeholder with `"assemble"` once the agent definition lands.

2. **Model default**: **LOCKED — sonnet across the board**, per-slot override available via `assemble-slots:` config (see §3.2). Opus/haiku tuning deferred to Phase 2 observed-data review.

3. **AC6 retry count**: **LOCKED — 1 retry.** Retry prompt structure: short, names the violating conflict IDs, demands `justification_citation` quote §4.6 verbatim, keeps `assembled_body` identical. If retry also fails AC6, fall back to verbatim for the slot and log per §6.

4. **Audit timeout**: **LOCKED — 120s** (symmetric with assemble). Revisit after 100 production audits if observed P99 is well under 60s.

5. **`CLAUDE.assemble-log.md`**: **LOCKED — yes on the data, file vs. section format deferred to Phase 2.1 implementation.** Skill chooses whether to extend `CLAUDE.conflicts.md` with a per-slot status header table OR emit a separate sixth artifact — both produce the same operator signal. Default toward the sixth file if `conflicts.md` would balloon past ~50 lines on zero-conflict runs.

---

## 10. What Phase 2 implementation scopes (handoff to skill)

When operator confirms this design, file as one umbrella task (or three, per the phasing above) to skill. Skill writes the code. PM stays in coordination — answers config-validation questions, signs off on Phase 2.2 ship, drives prompt-template refinement in Phase 2.4+.

Phase 1 deliverable (this document) does NOT include:
- Code changes (skill's lane)
- Prompt template iteration (Phase 2.4, operator-driven)
- The exact JSON parser implementation (skill's lane during Phase 2.1)

---

## Status (cycle 2158, 2026-06-05)

- Phase 1 deliverable v1 committed (cycle 2143 ext)
- §9 LOCKED 2026-06-05 by operator (this cycle): assemble subagent type, sonnet default, 1 retry on AC6, 120s audit timeout, sixth-artifact-or-section TBD by skill
- #11053 status: in-progress

Next PM cycle: file Phase 2 task breakdown to skill (one umbrella OR three sub-phases per §7 phasing). Skill writes the code starting from §1–§8 of this document as the contract.
