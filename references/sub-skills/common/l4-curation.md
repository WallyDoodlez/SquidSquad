### L4 Curation — Project-Role Customization Detection + Authoring

#### Purpose

L4 is `.squidsquad/project/*.md` — the install-local layer that **overrides or supplements** L1–L3 with project-specific rules. This sub-skill defines how an agent recognizes when the human is asking for a project-role customization, dialogs to capture the rule clearly, and produces a well-formed L4 file that the compose pipeline can persist.

L4 *writes* are owned by the compose pipeline. The frontmatter grammar (`slot`, `op`, `target`), the file naming convention, and the three safety gates (DeepSeek audit → mini-CQ → compose dry-run) are all defined in `COMPOSE-ARCHITECTURE.md` §3.3, §7.3, and §7.4. This sub-skill is the *upstream dialog* that produces the L4 entry before those gates run.

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
   | What the role *does* — cycle behaviour, decision rules, when-then patterns, scope of work | `slot: instructions` | all four ops legal per §3.3 |
   | Who the role *is* — values, tone, professional identity, priorities | `slot: soul` | **`append`-only** per §3.3 + §3.4; no `target`, no `ordinal`. Composed soul carries shipped content + L4 append in order; on conflict the agent follows L4. |

   If a customization concerns both (e.g., "be more conservative when filing bugs") split it into two L4 entries — one per slot — and walk the human through each.

   Step-specific *prohibitions* ("during step X, do not do Y") do NOT belong in L4. Per `COMPOSE-ARCHITECTURE.md` §6.3, those live in the relevant L1–L3 sub-skill source — they are built into SquidSquad's shipped behaviour and cannot be overridden per-project. If the human asks for one, explain that this kind of rule is part of SquidSquad's core (in plain language, never naming the layer) and offer to file an upstream feature request against the SquidSquad repo if the change would be broadly useful.

3. **Surface the why** (user-facing). Soul customizations especially need the WHY captured. Ask: "Is there a past incident or strong preference behind this? Capturing it helps future judgement on edge cases."

4. **Surface edge cases** (user-facing). "When should this rule *not* apply?" Edge cases written upfront save a future override on top of this override.

5. **Pick the op + target** (agent-internal). The op set is `append`, `insert-before`, `insert-after`, `replace` (`COMPOSE-ARCHITECTURE.md` §3.3). When `slot: soul`, only `append` is legal — skip the rest of this step and go to step 6. Otherwise:

   - `append` — new rule that extends existing content of the chosen slot. Safest default; no `target` required.
   - `insert-before <target>` / `insert-after <target>` — the rule should appear at a specific position relative to an existing L1–L3 step. The `target` is a stable step ID declared in L1–L3 (see §6.1). Pick the variant based on whether the new rule runs before or after the anchor step — the user-facing question is "should this happen before or after [existing behaviour]?", not "which op?".
   - `replace <target>` — existing L1–L3 behaviour is *wrong* for this project; overwrite the step's content entirely. Use sparingly; the step ID is preserved so later L4 inserts targeting it still resolve.

   Every non-`append` op requires a `target` that resolves to a real L1–L3 step ID. If no clean target exists, ask the human a plain-language question about whether the new behaviour is meant to *replace* or *add to* the role's current work; don't expose target mechanics.

6. **Pick the file** (agent-internal). One file per L4 customization, named `<slot>-<short-kebab-description>.md` (`COMPOSE-ARCHITECTURE.md` §7.3), e.g. `instructions-pre-check-incidents.md`. Files live in `.squidsquad/project/`. Role-scoping is implicit — `compose.py deploy-all` (or `compose.py deploy <role>` for single-role) walks `.squidsquad/project/*.md` for each role and applies them.

   **Provisional**: cross-role L4 (a single file that customizes multiple roles) is an open question (`COMPOSE-ARCHITECTURE.md` §11.1 Q3). Until that question is closed, write one file per role for any customization that applies to multiple roles. This guidance may change if multi-role frontmatter (e.g. `roles: [pm, verifier]`) is added.

7. **Propose a draft and read it back** (user-facing). Show the human the rule in plain prose (rule + why + when-not-to-apply) and get explicit approval before writing. The agent translates that approved prose into the L4 file; the human never sees the frontmatter.

8. **Run the safety gates** (agent-internal). Before persisting, the agent runs the three §7.4 gates in order:

   1. **DeepSeek decision-tree audit**: a deepseek-class model reviews the agent's `slot` + `op` + `target` classification and rejects if the call is wrong.
   2. **Mini-CQ**: the agent gives the human a one-sentence confirmation of the change in functional terms (e.g., "Adding a project rule that you want PM to check incidents before filing any bug — OK?") and gets explicit yes/no. The detailed prose draft was already shown in step 7; this is the final go/no-go in one line. Rejection aborts; no file written.
   3. **Compose dry-run**: `compose.py deploy-all --check` validates the new file resolves cleanly (target exists, slot+op combination legal, no DRY violation, no orphan).

   Only after all three gates pass does the agent write the file and commit. The gates are agent-side, not part of the compose pipeline itself — the file does not hit disk until all three are green.

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

- `COMPOSE-ARCHITECTURE.md` §3.3 — L4 op grammar (`append` / `insert-before` / `insert-after` / `replace`), per-slot op constraints (soul = append-only), and the `target` field
- `COMPOSE-ARCHITECTURE.md` §3.4 — soul slot semantic-merge precedence (L4 wins on conflict at the agent's reading layer)
- `COMPOSE-ARCHITECTURE.md` §6.3 — step-specific prohibitions live in sub-skills, not L4
- `COMPOSE-ARCHITECTURE.md` §7.3 — L4 file naming (`<slot>-<short-kebab-description>.md`) and frontmatter shape
- `COMPOSE-ARCHITECTURE.md` §7.4 — the three safety gates (DeepSeek audit → mini-CQ → compose dry-run)
- `COMPOSE-ARCHITECTURE.md` §7.7 — one-shot + durable model; drift caught at recompose time
- `COMPOSE-ARCHITECTURE.md` §11.1 Q3 — cross-role L4 (open question, provisional one-file-per-role)
