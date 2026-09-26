---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step — Vault Synthesis (Harness-Scheduled)

Synthesize cross-agent vault knowledge into posture notes. When the same event also queued notes for vault optimize, run optimize first, then synthesis (they serve different purposes).

**Activation (#14137)**: run this step only when a `vault-maintenance` event arrives with `synthesis_due: true` in its payload. The harness sends that at most once a week (config `Vault Optimize > Synthesis Interval Days`, never below 7). You do not count quiet cycles or keep any synthesis counter; the harness schedules, and the gates below still decide whether anything is written. With the harness unreachable (loop mode) there is no window, so synthesis waits until event mode returns.

**Vault write freeze**: if `python references/scripts/config.py get vault-writes-per-cycle` returns `0` (the #13862 M0–M4 freeze), run Steps 1–3 as normal, then in Step 4 make **no vault writes**: skip creating or updating the posture note and the vault checks, and fill the review task's **Drafted note** field (Step 4.2) instead, so it can be written after approval once the freeze lifts. Steps 4.2 (review task) and 5 (sentinel + log line) still run.

**Vault size gate**: Only run when the vault has 10+ galaxy notes. If fewer, skip — not enough data to synthesize.

Print: `[🦑 HH:MM:SS] Running vault synthesis...`

Write status bar: `python references/scripts/cycle.py status-bar [ROLE] "verifying" "vault-synthesis — Cross-agent pattern detection..."`

**Step 1 — Gather recent vault writes from all agents**:

List the notes created or updated since the last synthesis (or in the last 7 days if there was none) — a file listing, not a content search:

```bash
find .squidsquad/vault/galaxy/ .squidsquad/vault/systems/ -name "*.md" -newer .squidsquad/[ROLE]/.last-synthesis 2>/dev/null || find .squidsquad/vault/galaxy/ .squidsquad/vault/systems/ -name "*.md" -mtime -7
```

If none, print: `[🦑 HH:MM:SS] No recent vault writes — skipping synthesis.` and skip.

Read each listed note's frontmatter (type, tags, owner) and body summary. To find related notes for a theme, search through the engine (never grep): `python references/scripts/vault_consume.py search --alias [ROLE] --tags <theme tags>`.

**Step 2 — Detect recurring themes**:

Look for multiple agents writing about the same problem area:
- Same tags appearing in notes from different agents
- Similar topics in notes from different owners
- Wikilinks that create cross-agent clusters

**Step 3 — Detect convergent decisions**:

Look for separate decisions that imply a shared principle. Examples:
- "Hard error over silent fallback" + "never ship with gaps" → "explicit failure over silent degradation"
- "Push back on ambiguous specs" + "zero-gap gate" → "clarity before action"

Only surface convergences supported by 2+ distinct vault notes from different agents or contexts.

**Step 4 — Create posture notes**:

For each detected posture (max **1 per synthesis cycle**):

1. Create the posture note per vault-protocol's vault-create steps:
   - A principle about one subsystem → append it to that subsystem's `systems/` hub note (vault-update), under a `## Postures` section.
   - A principle spanning several subsystems → a new `pattern-<descriptive-name>` note (`vault_entity.py create pattern <descriptive-name>`) tagged `posture` + domain tags, linking every hub it spans.
   - Body: state the principle, cite the source notes via `[[wikilinks]]`, explain why they converge.
   - Never create `pattern-posture-*` notes (retired prefix).

2. File a pending task for human review.

   → run sub-skill: `tracker-protocol` — use the **Feature task** one-liner shape with title `"Review posture: [principle name]"` and body:
   ```
   Vault synthesis detected a convergent principle across agent decisions.

   **Principle**: [description]
   **Source notes**: [list with wikilinks]
   **Evidence**: [why these converge]

   If approved, this becomes active scan criteria for all agents.
   ```
   During the vault write freeze, append this field to the body (omit it otherwise):
   ```
   **Drafted note** (vault frozen; write after approval once the freeze lifts):
   Target: [systems/<hub>.md `## Postures` section | new pattern-<descriptive-name> note]
   Tags: posture, [domain tags]
   [full markdown body, as it would have been written]
   ```
   Set `--role pm`, `--priority low`, `--reporter pm-lead`.
   Then record the source notes as used, attributed to that review task: `python references/scripts/vault_consume.py cite --alias [ROLE] --task <review task number> --slugs <source slugs>`.

3. Run vault-protocol's checks after every write on the new or updated note.

**Step 5 — Record synthesis**:

Touch the sentinel file to mark last synthesis time:
```bash
touch .squidsquad/[ROLE]/.last-synthesis
```

Log in iteration summary: `Vault synthesis: [N] recent notes reviewed, [M] postures detected.`

**Rules**:
- **Max 1 posture per synthesis** — quality over quantity, prevent noise
- **Posture notes need human approval** before becoming active scan criteria — file as pending task
- **Never auto-approve postures** — they shape all future agent behavior
- **Output is a `systems/` hub section or a `pattern-*` note** — no posture-specific type or prefix
- **The `posture` tag** distinguishes synthesis-derived principles from regular patterns
- **Cross-agent only** — a pattern from a single agent is not a posture; it must show convergence across 2+ sources
