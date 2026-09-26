---
slot: instructions
ordinal: 10
---

## Vault — Shared Memory Layer

All agents have read/write access to the shared knowledge vault at `.squidsquad/vault/`: decisions, patterns, learnings, binding rules, subsystem hubs, and human preferences that outlive any single cycle. The note types and their folders are defined by the type registry `.squidsquad/vault/vault-schema.json` — it is authoritative; nothing below overrides it.

**Per-role write lanes**. Every role contributes patterns from its own lane:
- **PM**: coordination / decision patterns; team-process learnings; vault-synthesis on quiet cycles (cross-agent posture notes).
- **Worker**: implementation patterns; debugging recipes; architecture-decision rationale for code-side calls.
- **Verifier**: testing-and-verification patterns (TEST-PLAN approaches that catch a recurring root-cause class, comprehension-test fixtures that surface a class of LLM drift, verification techniques that generalize). **Do NOT** use vault writes to revisit, second-guess, or rebut decisions PM or worker agents have already made — their decisions are theirs to own. The verifier's vault contribution is the *testing craft*, not the design call.
- **DM**: delivery patterns; release-process learnings; CHANGELOG framing that generalized; version-bump heuristics.

The universal write budget (max 2 writes per cycle) and the 4-gate logic apply to every role — see [[vault-remember]].

```
.squidsquad/vault/
├── BRIEFING.md         # hot summary — read directly, outside the engine
├── vault-schema.json   # the type registry
├── projects/  areas/  resources/   # hubs + reference material
├── systems/            # one hub note per subsystem; galaxy notes link INTO these
├── archives/           # legacy location only — retire notes by status, not by moving them
└── galaxy/             # atomic notes: decision-*, pattern-*, learning-*, rule-*
```

### Reading the vault — engine only

Every vault search goes through the engine. **Never grep, glob, or Read-scan the vault folders to search**: a grep that finds the right note leaves no telemetry trail, so the note reads as unused and gets proposed for pruning.

```bash
python references/scripts/vault_consume.py search --alias [ROLE] [--task N] --tags <keywords> --terms "<subject>" [--types rule]
```

- Output is ranked metadata, never note bodies: each result carries `slug`, `path`, `title`, `type`, `status`, `tags`, `tier` and usage counts, among other fields. Read the note bodies you need; reading a note the engine surfaced is the intended follow-up.
- Pass `--task N` whenever you are working an issue — telemetry attributes to it. Pass `--no-write` only for diagnostics.
- Exit code 3 = engine unavailable. Say so honestly wherever a result was expected; never substitute a grep, never claim "none relevant".
- `BRIEFING.md` and `areas/human-profile.md` are read directly (no search needed).

### Consumption steps and receipts

These steps are mandatory and their output is committed:

| When | Who | Step |
|---|---|---|
| Task filing | PM | `vault_consume.py inject-context <n> --alias [ROLE] --tags <keywords> --terms "<subject>"` appends `## Vault context` to the issue body (task-intake Phase 3) |
| Pickup | worker | Context consultation + rules matching; receipts `## Vault context consumed` and `## Applicable rules` go in the issue's single lineage file (`vault_consume.py lineage-path <n>`) — procedure in implement-tasks step 2c |
| Verification | verifier | `vault_consume.py check-receipts <n> --diff-base origin/main` + rule compliance |

Receipt lines, per section (the gate checks them section by section):
- `## Vault context consumed`: `- [[slug]] -- one-line relevance` lines, or the single line `- None relevant (searched: …)`.
- `## Applicable rules`: `- [[rule-slug]] -- how it applies` lines, or the single line `- None matched (searched rules lane: …)`.
- Either section: the single line `- Engine unavailable: <reason>` when the search could not run.

**Citation duty**: whenever a note shapes a committed artifact (a receipt, a research doc, a plan), record it — the engine cannot:

```bash
python references/scripts/vault_consume.py cite --alias [ROLE] --task N --slugs a,b
```

### Creating notes (vault-create)

1. Pick the type from the registry. Galaxy types carry a filename prefix (`decision-`, `pattern-`, `learning-`, `rule-`); `system` hubs live in `systems/`.
2. Materialize from the type's template — never hand-roll frontmatter:
   ```bash
   python references/scripts/vault_entity.py create <type> <slug>
   ```
3. Fill the frontmatter: `type`, `tags` (at least one domain tag — the word a teammate would search for; `tags: []` is invalid), `created`, `updated`, `status: active`, `owner` (`pm` | `worker` | `verifier` | `dm` | `shared`). Do not add `confidence`, `source`, `links`, or any usage counter — usage is telemetry, never frontmatter.
4. Body: bare wikilinks `[[note-name]]`, no aliases. Every galaxy note links to the `systems/` hub it is about.
5. **Rule notes** (`rule-*`) are the binding lane that pickup matches and the verifier enforces: one imperative sentence under `## Rule`, where it applies under `## Scope`, and `## Why` linking the parent decision. Write one only when a human or PM established the rule — never promote your own opinion to a rule.
6. Creation threshold: only if reusable across contexts. Transient observations belong in iteration logs.

### Updating notes (vault-update)

1. Read the full note first.
2. Surgical edit — change only the targeted section.
3. Never delete content; correct it, or retire the note with `status: superseded` (link its replacement) or `status: archived`. Do not move files to `archives/`.
4. Set `updated` to today.
5. If the note has a `## Changelog`, append `- YYYY-MM-DD — [ROLE]: what changed and why`.

### Checks after every write

```bash
python references/scripts/vault_check.py check-frontmatter
python references/scripts/vault_check.py check-wikilinks
python references/scripts/vault_check.py check-structure
```

Fix every flag that names the note you wrote before committing. Flags on other notes are pre-existing legacy debt owned by the vault migration (#13862) — leave them. Advisory: `vault_check.py check-size` (galaxy notes over 500 lines — split them) and `vault_check.py check-hub-links` (notes linked to no hub).

### BRIEFING.md

`.squidsquad/vault/BRIEFING.md` is a ~50-line summary of active context (priorities, recent decisions, key preferences via `[[human-profile]]`, blockers). Read it at boot and re-read when more than a cycle old. Its staleness check runs every cycle — see [[vault-remember]].

### Concurrent access and git

- One note per topic; prefer updating an existing note over creating a near-duplicate ([[vault-remember]] gate 2).
- Vault notes are committed on main with normal cycle commits. The one exception is capture-at-ship: a note written on a task branch rides that PR.
- Telemetry shards under `.telemetry/` are written only by the engine and ride main commits only — never hand-edit them, never commit them on a task branch.
- On a merge conflict in a note: keep both versions, never discard vault content; PM reconciles.
