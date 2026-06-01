---
slot: instructions
ordinal: 10
---

### Step 4b — Vault Remember (End-of-Cycle Reflection)

Print: `[🦑 HH:MM:SS] Reflecting on cycle...`

**Config gate**: Check vault-remember setting:
```bash
python references/scripts/config.py get vault-remember
```
If `no`, skip this step entirely.

**BRIEFING.md staleness check** (runs every cycle — not gated by quiet check):

Read `.squidsquad/vault/BRIEFING.md` and `config.md`. Compare key fields:
- **Version**: Does BRIEFING.md match `SquidSquad Version` in config.md?
- **Active agents**: Does BRIEFING.md list the same agents as config.md `Workers` (6274.1 dual-aware shim also accepts the deprecated `Dev Agents:` key)?
- **Current priorities**: Do listed priorities match open high/medium priority items in the tracker?

If any field is stale, update BRIEFING.md with current values. This is a staleness fix, not new content — it does NOT consume write budget. Run vault-check Level 1 after updating.

**Quiet-cycle gate**: Check if this cycle did real work:
```bash
python references/scripts/vault_remember.py is-quiet [ROLE]
```
If exit code 0 (quiet), skip the reflection below — nothing to reflect on.

**Reset write counter** at the start of each reflection:
```bash
python references/scripts/vault_remember.py reset-writes [ROLE]
```

**Reflection prompt**: Review this cycle's iteration log and evaluate each category. Do NOT capture human preferences or behavioral directives here — those belong in soul shepherd (observed signals) or L4 (explicit directives).

1. **DECISIONS**: Any architecture, pattern, or trade-off decisions made this cycle?
   → If yes: vault-create `galaxy/decision-*.md`
2. **PATTERNS**: Any reusable patterns discovered or confirmed?
   → If yes: vault-create `galaxy/pattern-*.md`
3. **LEARNINGS**: Anything fail or succeed unexpectedly?
   → If yes: vault-create `galaxy/learning-*.md`
4. **PROJECT CONTEXT**: Did project goals, constraints, or architecture change?
   → If yes: vault-update `projects/<name>.md` or `BRIEFING.md`

For each candidate, apply these **deterministic gates IN ORDER**:

**Gate 1 — Write budget**:
```bash
python references/scripts/vault_remember.py write-budget [ROLE]
```
If output is `0`, STOP — no budget remaining this cycle.

**Gate 2 — Dedup check**:
```bash
python references/scripts/vault_check.py dedup-check --title "<candidate-name>" --tags "<tags>"
```
- If exact match found → SKIP (already in vault)
- If near-match found → decide: UPDATE existing note or CREATE new
- If no match → proceed to Gate 3

**Gate 3 — Reusability**: Is this specific to only this cycle with no future value? → SKIP

**Gate 4 — Fresh context test**: Would a fresh agent in a new context benefit from this? → WRITE

**Output format** (in iteration log notes):
- `WRITE: <type> — <one-line description>` (gates 3+4 passed)
- `UPDATE: <existing-note> — <what to add>` (dedup found near-match)
- `SKIP: <reason>`

**After each write**, increment the counter and run vault-check:
```bash
python references/scripts/vault_remember.py inc-writes [ROLE]
# vault-check Level 1 runs automatically per vault-protocol
```

**Priority when >2 candidates pass gates** (write the top 2 only):
1. Decisions (architectural choices compound)
2. Learnings (failure lessons prevent repeat mistakes)
3. Patterns (useful but can wait a cycle)

Remaining candidates beyond the write budget are noted in the iteration log's Notes field: `Vault-worthy but deferred (budget): [description]`.

**BRIEFING.md updates**: Before updating BRIEFING.md, check the token budget:
```bash
python references/scripts/vault_remember.py briefing-budget
```
If remaining is 0, do not add to BRIEFING.md without trimming. Trimmed content moves to a galaxy note — never deleted.

**Scope reminder**: The vault stores project and environment facts (conventions, context, decisions, learnings). Human behavioral preferences are captured by soul shepherd (observed) and L4 directives (explicit) — not here.
