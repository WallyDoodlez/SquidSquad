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

### G5 — Step 1c / Step 1d legacy numbering

Audit C2: `### Step 1c — Resume From Working State` appears mid-doc with no Step 1a / Step 1b context (pm, dm, verifier). DM and verifier also carry `### Step 1d — Interval Sync`. These are L2 instruction blocks whose body content does PM/DM/QA-specific resume-time and interval-sync checks.

The "Step 1c" / "Step 1d" naming is NOT orphan-confusion — it's a system-wide convention used in `references/sub-skills/common/resume-working-state.md` and `references/sub-skills/common/interval-sync.md` (the H3s in those sub-skill bodies are titled `### Step 1c —` and `### Step 1d —`) and documented in `references/sub-skills/manifest.md` lines 64-65 + 193-194:

```
4. `common/resume-working-state` — Step 1c: resume from working state
5. `common/interval-sync` — Step 1d: interval sync
```

So Step 1a/1b/1c/1d was the original numbered cycle layout — Step 1a and 1b have since been retired or folded elsewhere, but 1c and 1d survive in both the sub-skill bodies and the L2 instruction files that inline them.

**Need user decision**: rename 1c/1d → modern `step:cycle/<id>` shape (proper anchor IDs, cleaner reading for the agent), or keep as legacy and address only the cosmetic surrounding ("PM's resume-time extension" prose framing). Either way, this is tangled with the Iter 11b step-ID restructure and should be planned together.

For tonight I've left the prose alone.

---

### G6 — PM Soul "When verifying pending-test items" contradicts PM Responsibility

Audit M2 surfaced this. PM SOUL.md line 27-32:

> "When verifying pending-test items, check ALL of the following:
> - All acceptance criteria pass
> - New code has corresponding unit tests — no shipping untested code
> - All tests pass (run the full test suite)
> - Bug fixes include regression tests that would have caught the original bug
> - If any of these fail, back to in-progress with specific gaps listed"

Conflicts directly with `references/roles/pm/responsibility.md` ("Does NOT verify pending-test work. Verification is the verifier's lane") and L1 Boundaries ("PM = docs only. Verifier = testing only.").

Two readings:
- **(a) Stale prose** — pre-#10685 PM ran verification; post-rename verifier owns it. The Soul block is leftover and should be deleted.
- **(b) Spec-compliance check, not test execution** — PM reads QA's test outcomes (not runs them) and decides whether to send pending-test → pending-ship or pending-test → in-progress. The bullet "All tests pass (run the full test suite)" is misleading — should read "verify QA's report shows all tests pass".

I lean (b) per PM's existing `pending-test → pending-ship | in-progress — PM or QA` role in the status transition table, but **need your call**. Logging and not editing tonight.

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
| 22 | 916820106 | Fix C4: promote `check-gh` to a new pre-Step-1 "Step 0" so both event and polling boot paths gate on GitHub access; renumber 4b→4a, 4c→4b across all 4 L2 files | landed |
| 23 | 4c9efc1a9 | C5 fix: Goal text of `step:cycle/exit` rewritten to cover BOTH event-mode (re-enter Monitor / ack-stop) and loop-fallback (exit cleanly). M1: typo cleanup in PM SOUL.md ("swtiched"→"switched", "throrough"→"thorough", "- almost that"→"— almost as if"). | landed |
| 24 | a22550af0 | Iter 7 propagation: strip legacy standalone-doc preamble from dm/verifier/worker L2 instructions.md (parallel to the PM pilot in Iter 7). dm: -79 lines, qa: -84, skill: -78. Also M4: strip `<!-- #10360-cleanup ... -->` author TODO comments (19 occurrences across 4 L2 files). | landed |
| 25 | be8b03e2f | Iter 19 propagation to L4: drop "You are the X for SquidSquad" openers from dm/verifier/worker L4 project files (PM L4 already done in Iter 19). | landed |

---

## Morning summary

Six iterations landed overnight (Iter 20–25):

**User-raised concerns addressed**:
- Concern 2 (`#9588` noise) → **Iter 20** stripped four refs (`#9588`/`#9580`/`CONTEXT-9588`) from the Boot — Mode Detection H2 + Step 1/2/4b prose across all four L2 instruction files.
- Concern 3 (Boot — Mode Detection consolidation question) → **G3** in doc-gap log; not auto-applied. Block sits at line ~444 of PM with the "FIRST instruction" claim still self-contradictory (audit C1). Scope warrants morning alignment.
- Concern 1 (QA vs verifier terminology) → **G1** + **G2** in doc-gap log; verified this install's verifier IS aliased "qa" but most composed `QA` references are pre-#6274 class-name drift. Systematic replace deferred for morning spot-review.

**Audit C-series closed**:
- C3 — `[ROLE]-lead` substitution gave PM-level auth to worker agents → **Iter 21** changed source to literal `<role>-lead`.
- C4 — event mode skipped `tracker.py check-gh` → **Iter 22** promoted check-gh to a universal Step 0.
- C5 — `step:cycle/exit` Goal text was polling-only → **Iter 23** rewrote to cover both modes.

**Audit M-series closed**:
- M1 — Three typos in PM SOUL.md ("swtiched", "throrough", "- almost that") → **Iter 23**.
- M4 — 19 `<!-- #10360-cleanup ... -->` author TODO comments → **Iter 24**.

**Queued propagations applied**:
- Iter 7 preamble strip (PM pilot) → propagated to dm/verifier/worker L2 instructions.md in **Iter 24** (−241 lines total: dm −79, qa −84, skill −78).
- Iter 19 "You are the X" L4 dedupe → propagated to dm/verifier/worker L4 project files in **Iter 25**.

**Doc-gap questions awaiting decision** (G1–G6 above):
- G1 — Systematic `QA` (drift) → `verifier` rename across 40 occurrences in 17 source files
- G2 — File-naming conventions (`qa-log.md`, `QA-RESULTS-<N>.md`, `.squidsquad/qa/planning/`) — alias-tracked or class-named?
- G3 — Boot — Mode Detection consolidation into Agent Functions (closes audit C1 + your concern #3)
- G4 — Document `[ROLE]` vs `<role>` substitution convention in COMPOSE-ARCHITECTURE or sub-skill-guide
- G5 — Step 1c / Step 1d legacy numbering rename (tangled with Iter 11b step-ID restructure)
- G6 — PM Soul "When verifying pending-test items" — stale prose or spec-compliance check (not test execution)?

**Audit C-series still open** (not auto-applied):
- C1 — "FIRST instruction" placement contradiction (tied to G3 consolidation)
- C2 — Orphan Step 1c (tied to G5)
- C6 — Per-step mode self-detection (minor, prose pattern)

**Composed lines after night**:
- dm: 856 → 777 (-79)
- pm: 832 → 826 (-6 from M4 strip + minor)
- qa: 858 → 774 (-84)
- skill: 970 → 892 (-78)

Total: -247 lines across the four roles since Iter 19, mostly from the dm/verifier/worker preamble strip propagation.

Branch HEAD: `be8b03e2f` (Iter 25).
PM CLAUDE.md: https://github.com/WallyDoodlez/SquidSquad/blob/squidsquad/skill/compose-polish-session/.squidsquad/pm/CLAUDE.md
