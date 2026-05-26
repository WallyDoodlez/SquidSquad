### L4 Curation — Project-Role Customization Detection + Authoring

#### Purpose

L4 is `.squidsquad/project/*.md` — the install-local layer that overrides L1–L3 with project-specific rules. This sub-skill defines how an agent recognizes when the human is asking for a project-role customization, dialogs to capture the rule clearly, and produces the correct L4 entry (`instructions`, `soul-directives`, or `responsibility`).

L4 *writes* are owned by the compose pipeline (see `COMPOSE-ARCHITECTURE.md §7` — frontmatter ops, DeepSeek audit, mini-CQ gate). This sub-skill is the *upstream dialog* that produces a well-formed L4 entry; compose §7 then validates and persists it.

L4 *curation* (drift detection, conflict detection, promotion review) is the second half of this sub-skill.

#### Activation

Three trigger paths — the first is reactive to the human; the other two run on quiet cycles.

**Trigger 1 — Customization request detected (reactive)**

The human says something that sounds durable: a rule that should apply across cycles, not a one-off request. Watch for patterns:

- "From now on, when X, do Y"
- "In this project, the PM should always Z"
- "QA should focus on W"
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

**Trigger 2 — Drift scan (quiet cycle, PM)**

PM runs this on quiet cycles when its work queue is empty (subject to the same issue gate as `improvement-scan`). The scan compares every `.squidsquad/project/*.md` entry's `anchor` frontmatter against current L1–L3 content:

- **Anchor missing** — the L1–L3 section the entry referenced has been renamed or deleted. The override now applies to nothing.
- **Anchor moved** — exact text match exists but at a different file/section.
- **Op redundant** — the override's `replace`/`insert`/`append` content is now identical to (or subsumed by) the upstream L1–L3 it overrides.

Findings get queued for the human as plain-language questions (see `vault-optimize.md` style), never auto-resolved.

**Trigger 3 — Conflict scan (quiet cycle, PM)**

Detect L4 entries that step on each other:

- Two entries with overlapping `anchor` + incompatible ops (e.g., `replace` and `append` to the same anchor with contradictory body).
- An entry whose `op: replace` removes content another entry's `op: append` extends.
- Per-role entry contradicting a `shared-*` entry without explicit precedence.

Resolution is a human call; surface as a queued question.

#### The elicitation dialog (Trigger 1)

When a customization request is detected, walk this dialog before writing L4:

1. **Confirm durability.** "I heard you want X to always happen in this project. Want me to lock that in as a per-project rule (L4), or is it just for this task?"

2. **Identify the target role + bucket.** Pick from:

   | Bucket | What it overrides | Examples |
   |---|---|---|
   | `instructions` | what the role *does* — cycle steps, decision rules, when-then patterns | "PM should also nudge designer for design:in-progress > 24h" |
   | `soul-directives` | who the role *is* — values, tone, professional identity | "QA's tone with the human is friendly but no hedging" |
   | `responsibility` | what's in/out of the role's lane | "Worker also owns Dockerfile changes in this project" |

   Ask the human if the target is ambiguous. Don't guess between buckets — the bucket choice changes who reads the rule at compose time.

3. **Surface the why.** Soul-directives especially need the WHY captured — same reason `feedback` memories carry a `Why:` line. Ask: "Is there a past incident or strong preference behind this? Capturing it helps future agents judge edge cases."

4. **Surface edge cases.** "When should this rule *not* apply?" Edge cases written upfront save a future override on top of this override.

5. **Pick the target file.**

   | Target file | When to use |
   |---|---|
   | `.squidsquad/project/<role>-instructions.md` | per-role instruction override |
   | `.squidsquad/project/<role>-soul-directives.md` | per-role personality/values overlay |
   | `.squidsquad/project/<role>-responsibility.md` | per-role scope addition or restriction |
   | `.squidsquad/project/shared-instructions.md` | rule that applies to *every* role |
   | `.squidsquad/project/shared-soul-directives.md` | shared persona traits |
   | `.squidsquad/project/shared-responsibility.md` | cross-role lane rules |

6. **Pick the op + anchor.** The L4 frontmatter system supports `replace`, `insert`, `append` (see COMPOSE-ARCHITECTURE §3.3 / §7). Choose:

   - `append` — new rule that extends existing L1–L3 content. Safest default.
   - `insert` — new rule that should appear at a specific position within an L1–L3 section.
   - `replace` — existing L1–L3 behaviour is *wrong* for this project; overwrite it. Use sparingly — flag in the entry's `rationale` field.

   The `anchor` points to the L1–L3 location. If no clean anchor exists, the dialog should pause and ask the human whether to refactor L1–L3 instead.

7. **Propose a draft entry and read it back.** Show the human the exact L4 entry you'll write — frontmatter + body — and get explicit approval before writing. Mirror the `feedback` memory pattern: rule + Why + How-to-apply.

8. **Persist via compose §7.** The compose pipeline runs the DeepSeek audit + mini-CQ gate. The agent does not bypass that gate — even with human approval, the audit catches structural problems (anchor mis-targeted, conflicting op, prose ambiguity) that the human dialog may not have surfaced.

#### Promotion check (when L4 is no longer project-specific)

If an L4 entry's content has been added to L1–L3 in a later release (e.g., a rule the project pioneered became a SquidSquad default), the entry should be retired. The drift scan flags `op redundant` findings; PM surfaces them as "this rule is now part of the default — remove the project override?" questions.

#### What this sub-skill does NOT do

- Does NOT silently auto-write L4 from any heuristic without human confirmation. The dialog is mandatory; "L4 autonomous writes" (COMPOSE §7) covers a narrower path with explicit gating and an audit trail.
- Does NOT modify L1–L3. Project-pioneered rules that should be promoted upstream get filed as a normal tracker task, not handled here.
- Does NOT prune L4 unilaterally. All prunes surface as questions; the human approves.
- Does NOT cross the line into `vault` territory. L4 is *agent-instruction* customization; the vault is *knowledge* customization. Soul directives live in L4; rationale notes about why a soul directive exists live in vault.

#### Cross-references

- `COMPOSE-ARCHITECTURE.md §3.3` — L4 frontmatter ops (`replace` / `insert` / `append`)
- `COMPOSE-ARCHITECTURE.md §7` — L4 autonomous writes (DeepSeek audit + mini-CQ gate, audit trail)
- `vault-optimize.md` — sibling curation sub-skill for the vault; same question-queue pattern
- `improvement-scan.md` — quiet-cycle scan pattern this sub-skill mirrors for drift/conflict scans
