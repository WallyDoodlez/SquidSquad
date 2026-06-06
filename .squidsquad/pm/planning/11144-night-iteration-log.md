# #11144 Compose-polish overnight iteration log — for morning review

Branch: `squidsquad/skill/compose-polish-session`
Started: 2026-06-06 (autonomous session — user sleeping, will review in morning)

## Operating mandate

- Keep iterating per established compose-polish pattern (compose → review → iterate).
- Audit the composed CLAUDE.md against `docs/AGENT-RUNTIME.md`.
- If a gap in AGENT-RUNTIME.md is identified, **record here** for morning solution.
- Address user's three explicit concerns:
  1. **QA vs verifier terminology** — verify this install's verifier role IS aliased "qa" and whether composed references using "QA" are correct alias usage or legacy drift.
  2. **`#9588` in section titles** — drop issue-reference noise from agent-facing headings.
  3. **Boot — Mode Detection consolidation** — should this whole block fold into Agent Functions?
- Continue C-series audit findings from Iter 16 audit.

---

## Doc-gap questions (need user decision)

### G1 — `QA` vs `verifier` terminology drift (needs systematic decision)

**Verdict**: This install's verifier role IS aliased `qa` (per `.squidsquad/config.md` line 14 `**qa**: qa`), so paths like `.squidsquad/qa/planning/` are correct alias usage. However, **most `QA` references in the composed CLAUDE.md are legacy class-name drift** from the pre-#6274 rename (`qa` → `verifier`).

`docs/AGENT-RUNTIME.md` §1 is explicit on canonical class names:

> **Role classes** (4 categorical, post-#6274 rename — `dev` → `worker`, `qa` → `verifier`):
> | `pm` | `verifier` | `worker` | `dm` |

So in the composed PM CLAUDE.md (20 `QA` occurrences):
- **Drift (should be `verifier`)** — when used as a role-class noun: "You hold QA accountable… verification is QA's job" (Soul line 111), "if QA says it fails, it fails" (line 205), "QA produces TEST-PLAN-…" (line 433), 14 more like these.
- **Drift (should be `worker`)** — when "dev" is used: "dev/QA/DM" (line 128), "dev agents" / "dev-style transitions" in Tracker Protocol.
- **Correct alias usage** — `.squidsquad/qa/planning/` (line 433), `qa-log.md` filename references (lines 664, 700) — though those file names are themselves alias-derived and would change on installs that alias verifier differently.
- **Mixed** — "QA uses `--role verifier-lead`" (line 397): `QA` is the alias-flavored noun, `verifier-lead` is the role-class flag. Per convention but confusing to a fresh reader.

**Scope**: The drift is in 17 source files under `references/roles/` (40 `QA` occurrences) and likely a similar number of `dev`/`developer`/`dev agent` occurrences. A systematic sweep would replace:
- `QA` (as role-class noun) → `verifier` or `Verifier`
- `QA's` → `the verifier's`
- `dev agent` / `dev agents` → `worker agent(s)`

**Why not auto-apply overnight**: this is a >100-file replacement touching agent-facing language across all roles; risk of mis-applying to alias-correct uses (e.g., `.squidsquad/qa/`) is real. **Recommendation: bulk-replace pass during your morning session with my draft + your spot review.** Until then, I've fixed only specific instances flagged by the audit (C3 below).

---

### G2 — File-naming conventions (`qa-log.md`, `QA-RESULTS-<N>.md`)

Related to G1. Some file conventions in the composed CLAUDE.md are alias-flavored:
- `.squidsquad/pm/qa-log.md` (PM's tracking file for verifier findings)
- `QA-RESULTS-<NUMBER>.md` produced by verifier under `.squidsquad/qa/planning/`
- `TEST-PLAN-<NUMBER>.md`, `TEST-<NUMBER>-tests.py`

On installs that alias verifier differently (say `qe`), are these names supposed to track the alias (`qe-log.md`, `QE-RESULTS-…`), or were they always meant to be class-named (`verifier-log.md`, `VERIFIER-RESULTS-…`)? AGENT-RUNTIME doesn't specify. **Needs your call.**

---

### G3 — Boot — Mode Detection consolidation question (your raised concern #3)

You asked: > "Should this be consolidated into agent function?"

**My assessment**: yes, this is the right move, and it would also close audit finding C1 (the "FIRST instruction" placement contradiction — the block sits ~line 444 of an 830-line doc despite claiming primacy). But the change is substantial:

- Boot — Mode Detection is currently a peer H2 to Agent Functions, appearing AFTER Tracker Protocol. Its 70 lines (4 steps, port discovery, fragment Reads) are the concrete procedure for what Agent Functions describes abstractly via the session-boot mermaid + `step:cycle/boot`.
- Consolidating means either:
  - **(a)** Moving the whole block into Agent Functions as a sub-section under "Session-boot steps" (would re-nest Mode Detection's H3 Step 1-4 hierarchy under H2 Session-boot steps).
  - **(b)** Hoisting Mode Detection content into L1 base `references/roles/instructions.md` (currently L2 per-role; the content is essentially identical across pm/dm/verifier/worker).
- Risk: changes the slot structure and step ID anchors; may affect L4 ops targeting boot-bootstrap step IDs.

**Recommendation**: do this AFTER you wake up so we can scope together. The intermediate value (audit C1 closes, structural cleanup) is high but the blast radius warrants alignment.

In the meantime I've stripped the issue-ref noise (`#9588`/`#9580`/`CONTEXT-9588`) from the H2 title and Step 1/2/4b prose (Iter 20).

---

### G4 — AGENT-RUNTIME doc gap: `[ROLE]` substitution semantics for advice prose

The C3 fix (Iter 21) exposed a structural gap: when a sentence in L1 instructions.md gives advice **about other agents** (e.g., "dev agents use `--role <role>-lead`") and contains `[ROLE]`, the `_substitute_placeholders` machinery rewrites `[ROLE]` to the **reading agent's** role — turning generic advice into self-targeted nonsense ("dev agents use `--role pm-lead`" appearing in PM's deployed CLAUDE.md).

`docs/AGENT-RUNTIME.md` doesn't address this — the substitution machinery is documented in `COMPOSE-ARCHITECTURE.md` but the convention "use literal `<role>` (angle brackets) when referring to another agent's role" isn't written down anywhere. **Recommendation: add a convention note to COMPOSE-ARCHITECTURE.md or sub-skill-guide.md** clarifying:
- `[ROLE]` / `[ROLE_UPPER]` → substituted to the composing role at deploy time (use for self-references and per-role paths).
- `<role>` / `<your-role>` / `<their-role>` → literal angle-bracket placeholders that survive composition (use when describing what another agent might do).

I've applied this convention in the C3 fix but the doc gap remains.

---

## Iteration ledger

| Iter | Hash | Scope | Status |
| --- | --- | --- | --- |
| 20 | fe592806f | Strip `#9588`/`#9580`/`CONTEXT-9588` from Boot — Mode Detection H2 + Step 1/2/4b prose, all four L2 files | landed |
| 21 | 451ed7f7a | Fix C3: `[ROLE]-lead` → `<role>-lead` (worker-flavored advice survives composition) + log G1/G2/G3/G4 | landed |
| 22 | _committing_ | Fix C4: promote `check-gh` to a new pre-Step-1 "Step 0" so both event and polling boot paths gate on GitHub access; renumber 4b→4a, 4c→4b across all 4 L2 files | composing |
