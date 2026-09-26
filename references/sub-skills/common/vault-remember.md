---
slot: instructions
ordinal: 10
---

### Step 4b — Vault Remember (End-of-Cycle Reflection)

Print: `[🦑 HH:MM:SS] Reflecting on cycle...`

**Per-role write lane** (see [[vault-protocol]] for the full lane discipline). Each role writes patterns from its own lane only: PM = coordination/decision patterns; worker = implementation patterns; **verifier = testing/verification patterns ONLY — never debate PM or worker decisions in vault writes**; DM = delivery patterns. If a candidate learning is outside your lane, file it on the owning role's tracker as a `learning` note request instead of writing it yourself.


Vault-remember is **always-on** — there is no enable/disable toggle. Activation is controlled by the quiet-cycle gate and the per-cycle write budget below (#13043).

**BRIEFING.md staleness check** (runs every cycle — not gated by quiet check):

Read `.squidsquad/vault/BRIEFING.md` and `config.md`. Compare key fields:
- **Version**: Does BRIEFING.md match `SquidSquad Version` in config.md?
- **Active agents**: Does BRIEFING.md list the same agents as config.md `Workers` (6274.1 dual-aware shim also accepts the deprecated `Dev Agents:` key)?
- **Current priorities**: Do listed priorities match open high/medium priority items in the tracker?
- **Token budget** (#13563): run `python references/scripts/vault_remember.py briefing-budget`. If it prints `0`, BRIEFING.md is at or over its ~2000-token budget — trimming is a **must-fix this cycle**, same as the fields above (not gated by write budget; staleness fixes don't consume it). The budget check is corrective, not just a gate on new additions: BRIEFING.md's append-only sections (Active Priorities, Recently Shipped) grow every cycle by design, so this check exists to catch overage on contact rather than let it accumulate silently until someone notices the file is bloated (#13563 found it 3.3x over budget with no prior trim). Graduate the oldest dated increments/entries to a `vault/archives/` note (precedent: `archives/shipped-pre-2026-05-19.md`, `archives/briefing-active-priorities-2026-06-15-to-07-17.md`) — move content verbatim, never delete — leaving a one-line pointer in BRIEFING.md. Keep the freshest 1-2 entries inline per section. Target shape: the documented ~50-line summary; operator-facing sections (Active Priorities / Recent Decisions / Constraints / Team State) survive as section headers, condensed — never dropped outright. Re-run `briefing-budget` after trimming to confirm it now reports > 0.

If any field is stale, update BRIEFING.md with current values (or trim, for the token-budget field above). This is a staleness fix, not new content — it does NOT consume write budget. Run vault-protocol's post-write checks after updating.

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

1. **DECISIONS**: architecture, pattern, or trade-off decisions made this cycle? → candidate `decision`
2. **LEARNINGS**: anything fail or succeed unexpectedly? → candidate `learning`
3. **PATTERNS**: reusable approaches discovered or confirmed (incl. coding/writing/process conventions)? → candidate `pattern`
4. **RULES**: did a human or PM establish a binding rule this cycle? → candidate `rule` (linking its parent decision — never your own opinion)
5. **PROJECT CONTEXT**: did project goals, constraints, or architecture change? → update the `projects/` note or BRIEFING.md

For each candidate, apply these **gates IN ORDER**:

**Gate 1 — Write budget**:
```bash
python references/scripts/vault_remember.py write-budget [ROLE]
```
If output is `0`, STOP — no budget remaining this cycle.

**Gate 2 — Engine dedup (prefer update over create)**:
```bash
python references/scripts/vault_consume.py dedup --alias [ROLE] --title "<candidate title>" --tags <tags> --slug <intended-slug>
```
- `"action": "update"` → the candidate becomes an **update** of `target.path` (vault-protocol's vault-update rules): add the new content to that note — never create a near-duplicate.
- `"action": "create"` → no existing note passes the merge-target test; proceed to Gate 3 to create one.
- Exit code 3 (engine unavailable) → dedup cannot run; proceed to Gate 3 and record `dedup skipped: <reason>` in the iteration log.
The decision is the script's, not yours — do not override it by eye.

**Gate 3 — Reusability**: Is this specific to only this cycle with no future value? → SKIP

**Gate 4 — Fresh context test**: Would a fresh agent in a new context benefit from this? → WRITE (create or update per Gate 2)

**Output format** (in iteration log notes):
- `WRITE: <type> <slug> — <one-line description>` (gate 2 said create; gates 3+4 passed)
- `UPDATE: <target slug> — <what was added>` (gate 2 named a merge target)
- `SKIP: <reason>`

**After each write**, increment the counter and run vault-protocol's post-write checks:
```bash
python references/scripts/vault_remember.py inc-writes [ROLE]
```

**Priority when >2 candidates pass the gates** (write the top 2 only):
1. Decisions (architectural choices compound)
2. Learnings (failure lessons prevent repeat mistakes)
3. Rules and patterns
4. Project context (usually a BRIEFING.md update, not a budget-consuming write)

Remaining candidates beyond the write budget are noted in the iteration log's Notes field: `Vault-worthy but deferred (budget): [description]`.

### Capture-at-ship (worker, before handing off a task)

The per-task companion to this sweep (VAULT-ARCH §9.5): before transitioning a task or fix to pending-test, decide whether it produced durable knowledge — a decision, a root cause, a pattern. **Skip** for chores: typo/doc-only edits, dependency bumps, mechanical renames, test-only changes. If it did, run the gates above for that candidate, then write (or update) the note **on the task branch** so it ships in the same PR:

- The note must cite the task — include `#[NUMBER]` in its body — or the branch guard strips it back to main.
- `git add` the note path explicitly and commit it on the task branch (`commit_code` does not stage `.squidsquad/`).
- It counts against this cycle's write budget; the end-of-cycle sweep does not re-capture it.

**BRIEFING.md updates**: Before updating BRIEFING.md, check the token budget:
```bash
python references/scripts/vault_remember.py briefing-budget
```
If remaining is 0, do not add to BRIEFING.md without trimming first (see the corrective token-budget check under BRIEFING.md staleness above). Trimmed content moves to a `vault/archives/` note — never deleted.

**Scope reminder**: The vault stores project and environment facts (conventions, context, decisions, learnings). Human behavioral preferences are captured by soul shepherd (observed) and L4 directives (explicit) — not here.
