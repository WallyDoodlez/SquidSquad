---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step — Vault Synthesis (Quiet Cycle)

During quiet cycles, synthesize cross-agent vault knowledge into posture notes. This step runs AFTER vault optimize — if vault optimize ran this cycle, synthesis still runs (they serve different purposes).

**Activation**: Maintain a **synthesis cycle counter** in working state (separate from the improvement scan counter). Increment each quiet cycle. **After 5 consecutive quiet cycles**, trigger synthesis. Reset the counter when:
- Real work occurs (issue fix, task progress, verification)
- A synthesis completes (reset to 0, must accumulate 5 more quiet cycles)

**Vault size gate**: Only run when the vault has 10+ galaxy notes. If fewer, skip — not enough data to synthesize.

Print: `[🦑 HH:MM:SS] Running vault synthesis...`

Write status bar: `python references/scripts/cycle.py status-bar [ROLE] "verifying" "vault-synthesis — Cross-agent pattern detection..."`

**Step 1 — Gather recent vault writes from all agents**:

Find galaxy notes created or updated since the last synthesis (or in the last 7 days if no prior synthesis):

```bash
# Find recently modified galaxy notes
find .squidsquad/vault/galaxy/ -name "*.md" -newer .squidsquad/[ROLE]/.last-synthesis 2>/dev/null || \
find .squidsquad/vault/galaxy/ -name "*.md" -mtime -7
```

If no recent notes found, print: `[🦑 HH:MM:SS] No recent vault writes — skipping synthesis.` and skip.

Read each recent note's frontmatter (type, tags, owner) and body summary.

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

1. Create a vault galaxy note using vault-create protocol:
   - **Type**: `pattern`
   - **Tags**: include `posture` tag + relevant domain tags
   - **Confidence**: `medium` (agent-observed convergence, not human-confirmed)
   - **Body**: describe the principle, cite the source notes via `[[wikilinks]]`, explain why these converge
   - **Name**: `pattern-posture-<descriptive-name>.md`

2. File a pending task for human review.

   → run sub-skill: `tracker-protocol` — use the **Feature task** one-liner shape with title `"Review posture: [principle name]"` and body:
   ```
   Vault synthesis detected a convergent principle across agent decisions.

   **Principle**: [description]
   **Source notes**: [list with wikilinks]
   **Evidence**: [why these converge]

   If approved, this becomes active scan criteria for all agents.
   ```
   Set `--role pm`, `--priority low`, `--reporter pm-lead`.

3. Run vault-check Level 1 on the new note.

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
- **Use existing `pattern` type** — no new vault entity type needed
- **The `posture` tag** distinguishes synthesis-derived principles from regular patterns
- **Cross-agent only** — a pattern from a single agent is not a posture; it must show convergence across 2+ sources
