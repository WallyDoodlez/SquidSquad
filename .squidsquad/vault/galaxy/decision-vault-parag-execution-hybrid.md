---
type: decision
tags: [vault, architecture, redesign, parag, dmp-web, execution-model, knowledge-management]
created: 2026-05-24
updated: 2026-05-24
owner: pm
status: active
confidence: medium
source: research
links: []
---

# Decision: vault redesign — PARAG storage paired with workflow-triggered execution

## Decision

Redesign SquidSquad's vault subsystem to keep the PARAG storage model (selectively) and replace the cycle-triggered execution layer with the workflow-triggered, subagent-dispatched model observed in [[dmp-web2-vault-skills]] (lotusflare/dmp-web fork at naahtec, `.claude/skills/vault-*`).

Captured during interactive work on [[task-10003]] (massage `docs/VAULT-ARCH.md`) after surfacing that BRIEFING.md was 147 cycles stale and the current PM cycle stretch had zero vault writes — the cadence rule "every cycle, vault-remember" is not being followed in practice.

## Why

Two observations forced the rethink:

1. **Storage richness without execution discipline = elaborate types over stale data.** SquidSquad has confidence decay, a BRIEFING hot tier, archives auto-population, multi-role write authority, galaxy with prefix typing — but the writes feeding those structures are not actually happening on the cadence the spec assumes.
2. **Execution discipline without storage richness = clean cadence but a taxonomy ceiling.** dmp-web2's vault has a simpler 4-folder layout (people/systems/projects/knowledge) but reliably accumulates value because every write is tied to a concrete workflow event (PR creation).

The right design space is the union: keep the richer storage primitives from PARAG where they earn their keep, lift the trigger and integration discipline from dmp-web2 wholesale.

## What to keep from PARAG

- **Galaxy** layer with prefix typing (`decision-*`, `pattern-*`, `learning-*`, `style-*`) — atomic, cross-linked knowledge nodes are the right primitive for durable institutional memory; dmp-web2's flat `knowledge/` folder loses the affordance of "I want all the decisions".
- **Confidence levels with decay** (high → medium → low; 60d / 120d defaults) — institutional memory should age out of "ground truth" automatically. dmp-web2 has no equivalent.
- **Archives tier with link-rewrite** — supersession that preserves the link graph beats deletion.
- **BRIEFING.md as hot tier** — a small always-loaded summary is the right pattern; the failure was the trigger to keep it fresh, not the concept.
- **Multi-role write authority** — SquidSquad is a multi-agent system; ownership labels in frontmatter matter in a way they don't in a single-user vault.

## What to drop from PARAG

- **Areas/Resources distinction** — in practice, "areas" notes (human-profile, code-conventions) are just knowledge notes that happen to live in a separate folder. Fold both into a single `knowledge/` (or keep `galaxy/`) tier; promote tag-based grouping over folder-based.
- **Projects folder** — `.squidsquad/<role>/working-state.md` and tracker issues already hold per-project context; a parallel vault `projects/` folder duplicates state and goes stale.

Result: vault becomes `BRIEFING.md` + `galaxy/` + `archives/` plus the optional `people/` / `systems/` noun folders if multi-team coordination grows enough to need them.

## What to lift from dmp-web2 execution

- **Workflow-triggered writes, not cycle-triggered.** Vault writes are bound to concrete events: PR creation (Step 7.5 — capture knowledge), PR URL existence (Step 9.5 — backfill reference), dev-decided moments via slash command. No "every cycle, do staleness check".
- **Thin-dispatcher subagent pattern.** Each vault write skill (`vault-remember`, `vault-create`, `vault-update`, `vault-check`, `vault-optimize`) is a SKILL.md that dispatches to a subagent under `.claude/agents/<name>.md` with `run_in_background: true`. Main thread never blocks on vault I/O.
- **Signal-gated writes.** Explicit list of what *not* to vault (chores, lint fixes, dep bumps, tests-only). Ambiguity protocol: ask the user. "The vault should be signal, not a PR archive."
- **Atomic with code commit.** Vault writes land on the feature branch *before* `gh pr create`. Reviewers see vault and code as one diff. No drift between what shipped and what's documented.
- **Plan-deviation as first-class content.** When intent and execution diverged, capture the delta — those are the highest-signal vault entries.
- **ASK-USER protocol.** Subagent returns `ASK-USER: <question>` on ambiguity; main thread surfaces verbatim. No silent guesses, no hangs.

## What to lift from dmp-web2 utilization

- **Knowledge-budget graph traversal in search.** Along any traversal path, at most 2 knowledge nodes; people/systems/projects are free connectors. Stops semantic drift in long traversals.
- **"Vault as compass, code as truth" rule.** For code/implementation questions, vault content tells you *where* to look — read the actual code for the answer. Vault content is the final answer only for domain/history questions.
- **Foreground vs background by purpose.** Search is foreground (user waiting); writes are background subagent (user doesn't need to watch).

## Why this matters for SquidSquad

Without this rethink, the vault remains "static decision log, not living institutional memory" — the gap [[issue-5855]] names. Adding more sub-skills to the cycle (the previous approach) does not solve it; the failure is upstream of the storage model. With workflow-triggered writes, every meaningful event in the dev lifecycle (PR, ship, merge-conflict resolution, design decision) becomes a vault prompt — and the rich PARAG primitives finally have a steady supply of content to organize.

## Open questions

- **Where does the multi-agent system trigger vault writes?** dmp-web2 has one trigger (`/pr`); SquidSquad has pm/qa/skill/dm cycles, ship gates, design hand-offs. Each role needs its own concrete event(s) to bind to.
- **What replaces "every cycle, refresh BRIEFING"?** Likely: a BRIEFING-refresh subagent triggered on (a) any vault write, (b) version bump, (c) explicit `/squidsquad-briefing-refresh`. Not on cycle counter.
- **Migration of the current vault content.** ~98 commits' worth of existing vault data in `projects/`, `areas/`, `galaxy/`, `archives/`. Mostly OK to leave in place during transition; areas/projects content can be reclassified lazily.
- **DM lane vault writes for shipped work.** dmp-web2's signal-gate is "did this PR produce durable knowledge?"; SquidSquad's equivalent is "did this shipped item teach the squad something?" — likely captured during DM ship cycle.

## Links

- See [[task-10003]] for the doc-polish work that surfaced this.
- See [[issue-5855]] for the existing "vault as living memory" gap.
- See [[decision-event-bus-architecture-redesign]] for analogous "trigger over polling" rethink in the event/harness layer — same direction.
- Implementation will be filed as a separate task (TBD this cycle).
