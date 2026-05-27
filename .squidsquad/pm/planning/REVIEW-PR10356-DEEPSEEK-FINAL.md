# Audit Report

## Executive summary
- **8 findings**: 2 HIGH, 3 MED, 3 LOW.
- **Single biggest theme**: The `l4-curation.md` sub-skill contains multiple contradictions with `COMPOSE-ARCHITECTURE.md` regarding which slots accept targeted ops, and the dialog-hiding rule conflicts with the agent's need to explain capability boundaries.

---

## HIGH findings

### H1 — `l4-curation.md` contradicts `COMPOSE-ARCHITECTURE.md` on slot op constraints

- **Where**: `l4-curation.md` / "Pick the op + target" / step 5
- **Quote**: "`## Identity`, `## Soul`, `## Project Context`, `## Vault` slots are **append-only** — no targeted ops are legal."
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §3.3 per-slot op constraints table explicitly lists `identity` as "append only", `soul` as "append only", `project-context` as "append only", and `vault` as "append only". However, `COMPOSE-ARCHITECTURE.md` §4.3 "Multi-domain L4" states: "The same op grammar (`replace` / `insert-after` / etc.) applies to any slot." These two statements are directly contradictory — one says all slots accept all ops, the other says most slots are append-only.
- **Fix**: Resolve the contradiction by choosing one model. Either §4.3 is wrong (remove "applies to any slot" and replace with per-slot table), or the per-slot constraints table in §3.3 is wrong (remove the op constraints and make all slots accept all ops). The `l4-curation.md` text is consistent with §3.3 but contradicts §4.3.

### H2 — `l4-curation.md` dialog-hiding rule conflicts with capability-boundary explanations

- **Where**: `l4-curation.md` / "Talking to the user" / bullet 3
- **Quote**: "If the human's request would contradict how SquidSquad is built ... explain the relevant capability in plain terms and guide the user to a request the system can fulfill. Do not narrate why the original ask fails at the implementation layer."
- **Why it's a problem**: The "When the request can't be fulfilled" section provides an example that *does* narrate implementation-layer role distinctions ("delivery role ... doesn't write the implementation itself, that's the worker's role"). This is a direct contradiction — the rule forbids what the example does. An implementer cannot tell whether the rule or the example is authoritative.
- **Fix**: Either remove the example and replace with one that uses purely functional language (e.g., "The person who ships work doesn't write code — that's a different person's job"), or remove the "Do not narrate" restriction from the rule. The two must agree.

---

## MED findings

### M1 — `COMPOSE-ARCHITECTURE.md` §3.2 emit-rule for `instructions` slot is underspecified

- **Where**: `COMPOSE-ARCHITECTURE.md` / §3.2 / "Slot + ordinal contract"
- **Quote**: "the `instructions` slot is emitted as **sub-skill references**, not inlined sub-skill bodies, per §4.1 step 4"
- **Why it's a problem**: §4.1 step 4 says "emit each file's orchestration content verbatim" but then says "Inside the `instructions` slot, step bodies are **references to sub-skills by name**." The implementer needs to know: does the source file contain the reference text directly (e.g., `→ run sub-skill: pipeline-sentinel`), or does compose *transform* the source content into a reference? The phrase "body-extracted reference" in §4.1 step 1 suggests the reference is extracted from the file body, but the mechanism is never specified.
- **Fix**: Add a concrete example showing what a source file's `instructions`-slot content looks like (the raw text with `→ run sub-skill:` directives) and confirm that compose emits that text verbatim without transformation.

### M2 — `AGENT-RUNTIME.md` §7.3 routing table has a gap for `pending → planning` transition

- **Where**: `AGENT-RUNTIME.md` / §7.3 / "tracker.py auto-routing table"
- **Quote**: "`pending → planning` — `pm` — `"planning-needed"`"
- **Why it's a problem**: The table shows `pending → planning` routes to PM, but the table also shows `planned → approved` routes to the assigned role. There is no entry for `planning → planned` — the table says "(no assign — self-routing)". This means the PM receives the planning request, plans it, then self-transitions to `planned` without routing. But the `planned → approved` entry routes to the assigned role. The gap: who transitions `planned → approved`? The table implies it's the PM (since PM owns planning), but the routing says "assigned role from `role:*` label." If PM planned it, PM should approve it — but the table routes to a different role.
- **Fix**: Add a `planning → approved` entry (or clarify that PM both plans and approves, making the `planned → approved` routing entry dead code for PM-planned items). Alternatively, add a note explaining that `planned → approved` is only triggered when a human approves via forge, not by an agent.

### M3 — `COMPOSE-ARCHITECTURE.md` §6.5 event-mode fallback contradicts `AGENT-RUNTIME.md` §8.4

- **Where**: `COMPOSE-ARCHITECTURE.md` / §6.5 / "Why polling is kept"
- **Quote**: "The boot bootstrap (`references/sub-skills/common/boot-bootstrap.md`) treats polling as the fallback when harness reachability fails at boot in event-mode (#9588) — and that fallback is a separate restart, not a mid-session pivot."
- **Why it's a problem**: `AGENT-RUNTIME.md` §8.4 explicitly states: "There is no automatic runtime fall-back; falling back is an explicit operator action." The COMPOSE doc describes an automatic fallback (boot bootstrap falls back to polling when harness unreachable), while the AGENT-RUNTIME doc says no automatic fallback exists. These are contradictory — an implementer cannot know which behavior to build.
- **Fix**: Either remove the fallback mention from COMPOSE §6.5 (aligning with AGENT-RUNTIME's "no automatic fallback" rule), or add the fallback to AGENT-RUNTIME §8.4 as an explicit exception for boot-time harness unreachability.

---

## LOW findings

### L1 — `COMPOSE-ARCHITECTURE.md` §11.1 open question 4 is answered elsewhere but not cross-referenced

- **Where**: `COMPOSE-ARCHITECTURE.md` / §11.1 / Open question 4
- **Quote**: "L4 versioning — when the SquidSquad upgrade changes an L1-L3 step ID that L4 H3 blocks target, how does the upgrade handle the orphaned blocks?"
- **Why it's a problem**: §6.1 "Renaming a step ID" already answers this: "Be paired with a compose-time migration (compose.py prints a warning when it sees an L4 file targeting the old ID; offers an auto-rewrite or aborts)." The open question should be marked CLOSED with a cross-ref to §6.1, not left as an open question.
- **Fix**: Mark Q4 as CLOSED with cross-reference to §6.1 renaming protocol.

### L2 — `AGENT-RUNTIME.md` §4.4 EAD cadence math is inconsistent with the prose

- **Where**: `AGENT-RUNTIME.md` / §4.4 / "Polling cadence — adaptive backoff"
- **Quote**: "3 consecutive empty polls at 10s? → step up to 30s. 3 more consecutive empty polls at 30s? → step up to 60s (ceiling)"
- **Why it's a problem**: The prose says "3 consecutive empty polls" triggers each step-up, but the math in the revision log (rev 8) says "6 polls × 10/20/30/60/90/120s = 120s = 2 min" — which implies 6 polls, not 3+3. The prose says 3+3=6 polls total to reach ceiling, but the math example uses 6 polls with different intervals (10, 20, 30, 60, 90, 120). These describe different backoff algorithms.
- **Fix**: Align the prose with the math. Either change the prose to describe the 6-interval sequence (10→20→30→60→90→120) or change the math to match 3+3 (10→10→10→30→30→30 = 120s).

### L3 — `l4-curation.md` "When the request can't be fulfilled" example uses a role name that doesn't exist

- **Where**: `l4-curation.md` / "When the request can't be fulfilled" / example
- **Quote**: "The delivery role on this team packages and ships work that's been verified — it doesn't write the implementation itself, that's the worker's role."
- **Why it's a problem**: The canonical role names from `AGENT-RUNTIME.md` Terminology are `pm`, `verifier`, `worker`, `dm`. "Delivery role" is not a canonical name — the canonical name is `dm`. While the dialog-hiding rule says to use functional descriptions, "delivery role" is ambiguous (could mean the delivery manager or the delivery process). The example should use the functional description that maps to `dm` without ambiguity.
- **Fix**: Replace "delivery role" with "the person who packages and ships completed work" or similar unambiguous functional description.

---

## What's working well

1. **The L1-L4 composition model is clearly specified** — the slot/ordinal system, frontmatter grammar, and deterministic sort order give implementers a concrete algorithm to follow. The worked examples in §5.6 are particularly valuable for understanding the two-mode output.

2. **The three-layer source-output sync mechanism** (§8 in COMPOSE-ARCHITECTURE.md) is well-designed with clear failure modes and escalation paths. The PR check → auto-recompose → pre-ship gate sequence provides defense in depth without over-engineering any single layer.

3. **The event-driven mode's nudge contract** (§7.1 in AGENT-RUNTIME.md) is precisely specified with sequence diagrams, cursor semantics, and crash-safety analysis. The "context-only, no state mutation" rule for nudges while busy (§7.5) is a clean design choice that avoids race conditions.

4. **The `l4-curation.md` sub-skill's elicitation dialog** (steps 1-8) provides a complete, implementable protocol for human-in-the-loop customization. The three safety gates (DeepSeek audit → mini-CQ → compose dry-run) are well-ordered and appropriately scoped.

5. **The step ID grammar** (§6.1 in COMPOSE-ARCHITECTURE.md) with BNF, character set restrictions, nesting limits, and global uniqueness rules is precisely specified — an implementer can write a parser from this alone.