### L4 Curation — Project-Role Customization Detection + Authoring

#### Purpose

L4 is `.squidsquad/project/*.md` — the install-local layer that **overrides or supplements** L1–L3 with project-specific rules. This sub-skill defines how an agent recognizes when the human is asking for a project-role customization, dialogs to capture the rule clearly, and produces a well-formed L4 file that the compose pipeline can persist.

L4 *writes* are owned by the compose pipeline. The L4 file structure (one file per agent class, H2 slot sections, H3 op blocks), the op grammar, and the three safety gates (DeepSeek audit → mini-CQ → compose dry-run) are all defined in `COMPOSE-ARCHITECTURE.md` §3.3, §7.3, and §7.4. This sub-skill is the *upstream dialog* that produces an L4 H3 block before those gates run.

L4 curation is **one-shot and durable** (see `COMPOSE-ARCHITECTURE.md` §7.7): each customization is captured once via the dialog below, written to the right L4 file, and persists across cycles without further intervention. There is no recurring scan over L4 entries; drift between L4 and L1–L3 is caught at recompose time by the existing dry-run gate, not by a separate curation pass.

#### Talking to the user

Throughout this sub-skill, when the agent is conversing with the human about a customization, **the user-facing language hides SquidSquad internals**.

**Scope of "user-facing prose"**: the agent's *output addressed to the human* — chat messages, status updates, mini-CQ confirmations, capability explanations. It does NOT include the agent's own composed CLAUDE.md instructions (which freely name sub-skills, slots, ops, file paths), nor agent-internal reasoning, nor the frontmatter in files the agent writes. The rule constrains the speech act, not the agent's cognition.

- Never name any SquidSquad concept, component, file, mechanism, or terminology in user-facing prose. This includes — but is not limited to — process components, wire formats, storage layouts, framework-internal labels, and any name an outside reader would not recognize from the user's own project vocabulary. If the user invented a name themselves, you can use it back; if SquidSquad's architecture introduced it, you cannot.
- Use functional descriptions: "your project's PM agent", "what the role does on each cycle", "the role's personality" — describe the *behaviour* the user sees, never the implementation that produces it.
- If the human's request would contradict how SquidSquad is built (e.g., asking an agent to write code directly when delivery agents only package, or asking for a behaviour the architecture forbids), explain the relevant capability in plain terms and guide the user to a request the system can fulfill. Do not narrate why the original ask fails at the implementation layer.

The dialog steps below distinguish user-facing turns from agent-internal mechanics; the human sees only the functional shape (durability, role, why, edge cases, draft preview, approval).

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

1. **Confirm durability** (user-facing). "I heard you want X to always happen in this project. Want me to lock that in as a per-project rule, or is it just for this task?"

2. **Identify the target role and the shape of the customization** (user-facing).

   Ask the human only the functional question: "does this change what the role *does* on each cycle, or who the role *is*?" Don't expose slot names or any of the structural detail below to the user.

   **Agent-internal mapping** (never shown to the user):

   | What the user describes | Which slot the agent will write | Op constraints |
   |---|---|---|
   | What the role *does* — cycle behaviour, decision rules, when-then patterns, scope of work | `## Instructions` H2 | all four ops legal per §3.3 (`### append`, `### insert-before step:cycle/<id>`, `### insert-after step:cycle/<id>`, `### replace step:cycle/<id>`) |
   | Who the role *is* — values, tone, professional identity, priorities | `## Soul` H2 | **append-only** per §3.3 + §3.4; no targeted ops. Composed soul carries shipped content + L4 append in order; on conflict the agent follows L4. |

   If a customization concerns both (e.g., "be more conservative when filing bugs") split it into two L4 entries — one per slot — and walk the human through each.

   Step-specific *prohibitions* ("during step X, do not do Y") do NOT belong in L4. Per `COMPOSE-ARCHITECTURE.md` §6.3, those live in the relevant L1–L3 sub-skill source — they are built into SquidSquad's shipped behaviour and cannot be overridden per-project. If the human asks for one, explain that this kind of rule is part of SquidSquad's core (in plain language, never naming the layer) and offer to file an upstream feature request against the SquidSquad repo if the change would be broadly useful.

3. **Surface the why** (user-facing). Soul customizations especially need the WHY captured. Ask: "Is there a past incident or strong preference behind this? Capturing it helps future judgement on edge cases."

4. **Surface edge cases** (user-facing). "When should this rule *not* apply?" Edge cases written upfront save a future override on top of this override.

5. **Pick the op + target** (agent-internal). The op set is `append`, `insert-before <step-id>`, `insert-after <step-id>`, `replace <step-id>` (`COMPOSE-ARCHITECTURE.md` §3.3). The op surface is **per-slot**:

   - `## Identity`, `## Soul`, `## Project Context`, `## Vault` slots are **append-only** — no targeted ops are legal. Skip the rest of this step and go to step 6.
   - `## Instructions` slot accepts all four ops. Pick by intent:
     - `append` — new rule that doesn't relate to a specific existing step. Safest default.
     - `insert-before` / `insert-after` — new rule that should run adjacent to a specific existing step. The user-facing question is "should this happen before or after [existing behaviour]?", not "which op?". Resolve to a real `step:cycle/<step-id>`.
     - `replace` — the existing step's behaviour is wrong for this project. Use sparingly; the step ID is preserved so later inserts targeting it still resolve.

   Every non-append op requires a `step:cycle/<step-id>` target that resolves to a real L1–L3 step. If no clean target exists, ask the human a plain-language question about whether the new behaviour is meant to *replace* or *add to* the role's current work; don't expose target mechanics.

6. **Pick the file** (agent-internal). There is exactly **one L4 file per agent class** — `.squidsquad/project/<role>.md` (e.g., `pm.md`, `verifier.md`, `worker.md`, `dm.md`, or variant-specific files like `worker-frontend.md` for installs with worker variants). The file is appended to in place; existing slot sections are kept and new H3 op-blocks are added under the appropriate `## <Slot>` H2.

   If the customization applies to more than one agent class (e.g., "all roles should also check incidents/"), the dialog repeats per class — one H3 block written to each class's L4 file. The wording can be reused verbatim; the placement is per-file.

7. **Propose a draft and read it back** (user-facing). Show the human the rule in plain prose (rule + why + when-not-to-apply) and get explicit approval before writing. The agent translates that approved prose into the L4 file; the human never sees the frontmatter.

8. **Run the safety gates** (agent-internal). Before persisting, the agent runs the three §7.4 gates in order:

   1. **DeepSeek decision-tree audit**: a deepseek-class model reviews the agent's slot + op + target classification (which H2 the H3 block goes under, which op type, which step-id target if any) and rejects if the call is wrong.
   2. **Mini-CQ**: the agent gives the human a one-sentence confirmation of the change in functional terms (e.g., "Adding a project rule that you want PM to check incidents before filing any bug — OK?") and gets explicit yes/no. The detailed prose draft was already shown in step 7; this is the final go/no-go in one line. Rejection aborts; no file changed.
   3. **Compose dry-run**: `compose.py deploy-all --check` validates the updated L4 file resolves cleanly (step-id targets exist, op type is legal for the enclosing slot, no validation errors).

   Only after all three gates pass does the agent append the H3 block to the L4 file and commit. The gates are agent-side, not part of the compose pipeline itself — the file does not change until all three are green.

#### When the request can't be fulfilled

If the customization the human asks for contradicts how SquidSquad is built — e.g., asking a delivery role to write production code, asking for mid-cycle role switching, asking an agent to skip approvals — explain the capability boundary in plain terms and offer the closest request the system *can* fulfill. Never narrate internal mechanisms as the reason; describe the team's working model functionally.

Example, in user-facing voice:

> "The delivery role on this team packages and ships work that's been verified — it doesn't write the implementation itself, that's the worker's role. If you want X to happen as part of delivery, I can give the delivery role a rule about *when* to ask the worker for it, or I can give the worker a rule about *what* to include when X comes up. Which fits what you have in mind?"

#### What this sub-skill does NOT do

- Does NOT silently auto-write L4 from any heuristic without human confirmation. The dialog is mandatory; the §7.4 gates run on every write.
- Does NOT scan or audit existing L4 entries on a recurring schedule. Curation is one-shot per request; entries are durable until the human asks to change them (`COMPOSE-ARCHITECTURE.md` §7.7).
- Does NOT modify L1–L3. Project-pioneered rules that should be promoted upstream get filed as a normal tracker task, not handled here.
- Does NOT author step-specific prohibitions as L4. Those are built into SquidSquad's shipped L1–L3 sources (`COMPOSE-ARCHITECTURE.md` §6.3) and cannot be overridden per-project. Route such requests upstream as feature requests against the SquidSquad repo, not into L4.
- Does NOT prune L4 unilaterally. Any removal goes through the same dialog (confirm with human, then write the removal as a counter-entry per §7.5).
- Does NOT cross into vault territory. L4 is *agent-instruction* customization; the vault is *knowledge* customization. Soul customizations live in L4; rationale notes about why a soul customization exists live in vault.

#### Cross-references

- `COMPOSE-ARCHITECTURE.md` §3.3 — L4 file structure (one file per agent class, H2 slot sections, H3 op blocks), op grammar, per-slot op constraints (only Instructions accepts targeted ops; Soul/Identity/Project Context/Vault are append-only)
- `COMPOSE-ARCHITECTURE.md` §3.4 — soul slot semantic-merge precedence (L4 wins on conflict at the agent's reading layer)
- `COMPOSE-ARCHITECTURE.md` §6.3 — step-specific prohibitions live in sub-skills, not L4
- `COMPOSE-ARCHITECTURE.md` §7.3 — concrete L4 file format with worked example
- `COMPOSE-ARCHITECTURE.md` §7.4 — the three safety gates (DeepSeek audit → mini-CQ → compose dry-run)
- `COMPOSE-ARCHITECTURE.md` §7.7 — one-shot + durable model; drift caught at recompose time
