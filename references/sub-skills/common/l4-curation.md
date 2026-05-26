### L4 Curation — Project-Role Customization Detection + Authoring

#### Purpose

L4 is `.squidsquad/project/*.md` — the install-local layer that **overrides or supplements** L1–L3 with project-specific rules. This sub-skill defines how an agent recognizes when the human is asking for a project-role customization, dialogs to capture the rule clearly, and produces the correct L4 entry (`instructions` or `soul-directives`).

L4 *writes* are owned by the compose pipeline (see `COMPOSE-ARCHITECTURE.md §7` — frontmatter ops, DeepSeek audit, mini-CQ gate). This sub-skill is the *upstream dialog* that produces a well-formed L4 entry; compose §7 then validates and persists it.

L4 curation is **one-shot and durable**: each customization is captured once via the dialog below, written to the right L4 file, and then persists across cycles without further intervention. There is no recurring scan over L4 entries.

#### Talking to the user

Throughout this sub-skill, when the agent is conversing with the human about a customization, **the user-facing language hides SquidSquad internals**.

- Never name any SquidSquad concept, component, file, mechanism, or terminology in user-facing prose. This includes — but is not limited to — process components, wire formats, storage layouts, framework-internal labels, and any name an outside reader would not recognize from the user's own project vocabulary. If the user invented a name themselves, you can use it back; if SquidSquad's architecture introduced it, you cannot.
- Use functional descriptions: "your project's PM agent", "what the role does on each cycle", "the role's personality" — describe the *behaviour* the user sees, never the implementation that produces it.
- If the human's request would contradict how SquidSquad is built (e.g., asking an agent to write code directly when delivery agents only package, or asking for a behaviour the architecture forbids), explain the relevant capability in plain terms and guide the user to a request the system can fulfill. Do not narrate why the original ask fails at the implementation layer.

The dialog steps below describe agent-internal mechanics; surface to the user only the functional shape (durability, role, why, edge cases, draft preview, approval).

#### Activation — customization request detected

The human says something that sounds durable: a rule that should apply across cycles, not a one-off request. Watch for patterns:

- "From now on, when X, do Y"
- "In this project, the PM should always Z"
- "Verifier should focus on W"
- "The worker should not touch X"
- "Whenever there's a Y, route it to Z"
- "Make sure you always remember to A"

Distinguishing a customization request from a one-off task:

| Signal | One-off task | L4 customization |
|---|---|---|
| Time horizon | "for this task" / "today" / no qualifier | "always", "from now on", "in this project", "going forward" |
| Subject | a specific issue / PR / cycle | a *class* of situations |
| Scope | one role's current action | a role's behaviour pattern |
| Already covered by L1–L3? | irrelevant | check first — if yes, the request is for an override |

If unsure, **ask** before assuming durable. One short clarifying question is cheaper than a wrongly-written L4 entry.

#### The elicitation dialog

When a customization request is detected, walk this dialog before writing L4. Steps 1–4 and 7 are user-facing (use plain language per the "Talking to the user" rule above); steps 5, 6, 8 are agent-internal mechanics.

1. **Confirm durability.** "I heard you want X to always happen in this project. Want me to lock that in as a per-project rule, or is it just for this task?"

2. **Identify the target role + bucket.** Two buckets:

   | Bucket | What it customizes | Examples |
   |---|---|---|
   | `instructions` | what the role *does* — cycle steps, decision rules, when-then patterns, scope of work | "PM should also nudge designer for design:in-progress > 24h"; "Worker also owns Dockerfile changes in this project" |
   | `soul-directives` | who the role *is* — values, tone, professional identity, priorities | "Verifier's tone with the human is friendly but no hedging" |

   Scope additions or restrictions (what's in/out of a role's lane) flow through `instructions` — they're rules the role follows during its cycle, not a separate metadata layer. Ask the human only the functional question ("does this change what the role *does* or who the role *is*?"); don't expose the bucket names.

3. **Surface the why.** Soul-directive customizations especially need the WHY captured. Ask: "Is there a past incident or strong preference behind this? Capturing it helps future judgement on edge cases."

4. **Surface edge cases.** "When should this rule *not* apply?" Edge cases written upfront save a future override on top of this override.

5. **Pick the target file** (agent-internal):

   | Target file | When to use |
   |---|---|
   | `.squidsquad/project/<role>-instructions.md` | per-role instruction override |
   | `.squidsquad/project/<role>-soul-directives.md` | per-role personality/values overlay |
   | `.squidsquad/project/shared-instructions.md` | rule that applies to *every* role |
   | `.squidsquad/project/shared-soul-directives.md` | shared persona traits |

6. **Pick the op + anchor** (agent-internal). The L4 frontmatter system supports `replace`, `insert`, `append` (see COMPOSE-ARCHITECTURE §3.3 / §7). Choose:

   - `append` — new rule that extends existing L1–L3 content. Safest default.
   - `insert` — new rule that should appear at a specific position within an L1–L3 section.
   - `replace` — existing L1–L3 behaviour is *wrong* for this project; overwrite it. Use sparingly — flag in the entry's `rationale` field.

   The `anchor` points to the L1–L3 location. If no clean anchor exists, ask the human a plain-language question about whether the new behaviour is meant to *replace* or *add to* the role's current work — don't expose anchor mechanics.

7. **Propose a draft and read it back.** Show the human the rule in plain prose (rule + why + when-not-to-apply) and get explicit approval before writing. The agent translates that approved prose into the L4 file; the human never sees the frontmatter.

8. **Persist via compose §7** (agent-internal). The compose pipeline runs the DeepSeek audit + mini-CQ gate. The agent does not bypass that gate — even with human approval, the audit catches structural problems that the dialog may not have surfaced.

#### When the request can't be fulfilled

If the customization the human asks for contradicts how SquidSquad is built — e.g., asking a delivery role to write production code, asking for mid-cycle role switching, asking an agent to skip approvals — explain the capability boundary in plain terms and offer the closest request the system *can* fulfill. Never narrate internal mechanisms as the reason; describe the team's working model functionally.

Example, in user-facing voice:

> "The delivery role on this team packages and ships work that's been verified — it doesn't write the implementation itself, that's the worker's role. If you want X to happen as part of delivery, I can give the delivery role a rule about *when* to ask the worker for it, or I can give the worker a rule about *what* to include when X comes up. Which fits what you have in mind?"

#### What this sub-skill does NOT do

- Does NOT silently auto-write L4 from any heuristic without human confirmation. The dialog is mandatory; "L4 autonomous writes" (COMPOSE §7) covers a narrower path with explicit gating and an audit trail.
- Does NOT scan or audit existing L4 entries on a recurring schedule. Curation is one-shot per request; entries are durable until the human asks to change them.
- Does NOT modify L1–L3. Project-pioneered rules that should be promoted upstream get filed as a normal tracker task, not handled here.
- Does NOT prune L4 unilaterally. Any removal goes through the same dialog (confirm with human, then write the removal as a counter-entry).
- Does NOT cross into vault territory. L4 is *agent-instruction* customization; the vault is *knowledge* customization. Soul directives live in L4; rationale notes about why a soul directive exists live in vault.

#### Cross-references

- `COMPOSE-ARCHITECTURE.md §3.3` — L4 frontmatter ops (`replace` / `insert` / `append`)
- `COMPOSE-ARCHITECTURE.md §7` — L4 autonomous writes (DeepSeek audit + mini-CQ gate, audit trail)
