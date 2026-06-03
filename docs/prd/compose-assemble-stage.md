# PRD B — Compose Assemble Stage

> **Status**: shipped, 2026-06-02 (E6 V2 CUTOVER, #10685). Derived from TRD [[COMPOSE-ARCHITECTURE]] §4.6 (assemble pass). Part of the COMPOSE-ARCH PRD slice family: A (link) / B (this) / C (L4 + l4-curation) / D (catalog + wake-mode) / E (harness-owned freshness).
>
> **Scope:** the LLM-driven coherence rewrite that runs **after** the link stage produces a per-slot linked composite. Excludes link-stage mechanics (PRD A), runtime L4 writes (PRD C), sub-skill catalog enforcement (PRD D), and harness-owned freshness (PRD E).

---

## 1. Goal

After PRD A's link stage produces a per-slot linked composite — which can look like "original step → insert-before patch → original body → insert-after patch → append override" — a runtime agent reading that has to mentally reconcile "what does this slot *actually* tell me to do?" on every cycle. The assemble pass does that reconciliation **once at compose time** and writes the resolved prose to disk. Operators get a single coherent `CLAUDE.md` per agent that reads as one voice instead of as layered patches.

## 2. User-facing outcomes

| Persona | Outcome |
|---|---|
| **Runtime agent reading its own `CLAUDE.md`** | Each slot reads as a single coherent voice; no mental "but actually, the L4 override says…" reconciliation at every cycle |
| **Operator running `compose.py deploy-all`** | A complete audit triple lands per alias on success: `CLAUDE.md` (assembled), `CLAUDE.linked.md` (pre-assemble linked output), `CLAUDE.conflicts.md` (every L1/L2/L3/L4 contradiction the assembler resolved) |
| **Operator inspecting an L4 override** | Can read `CLAUDE.conflicts.md` to confirm the override landed as intended — every conflict cites the source files + verbatim quotes from both sides + the higher-L resolution |
| **Reviewer of a PR that changes L4 ops** | Can diff `CLAUDE.conflicts.md` between pre-PR and post-PR to see exactly which conflicts were introduced/resolved by the L4 change |
| **Operator on a fresh install** | First-deploy prose is stochastic (LLM rewrite); cache commits to git; subsequent re-deploys with unchanged inputs reuse the cache (deterministic from that point) |

## 3. Success criteria

The assemble stage is "done" for PRD-B purposes when ALL of the following hold:

1. The assemble pass runs **unconditionally** after the link stage on every `compose.py deploy <alias>` and `deploy-all` — there is no `Assemble:` config opt-out (per [[project_assemble_unconditional]]).
2. Per-slot scope: `identity`, `responsibility`, `soul`, `instructions` get the LLM rewrite; `project-context` and `vault` emit linked body verbatim (per TRD §4.6 per-slot table).
3. **Hard preservation guarantees** verified after every LLM call, abort on any failure:
   - Every `→ run sub-skill: <name>` reference in linked input is in assembled output (multiset equality)
   - Every `step:cycle/<id>` reference preserved (multiset equality)
   - All fenced code blocks and bash/python invocations preserved verbatim (count + content)
   - All file paths preserved verbatim
4. **Length floor**: `len(assembled) >= 0.8 * len(linked)` per slot. Below floor → abort (compose-time constant; no config field).
5. **Code-block parity**: count of fenced code blocks and inline backticks match within ±10%. Below threshold → abort.
6. **Conflict resolution** follows higher-L-wins (L4 > L3 > L2 > L1). When L2 says X and L4 says NOT-X, the assembled output aligns with L4. Lower-layer prose is NOT silently dropped; it is recorded in `CLAUDE.conflicts.md`.
7. `CLAUDE.conflicts.md` is emitted per role-class on every successful run with the canonical format from TRD §4.6: header (timestamp + commit SHA + model-id + total conflicts), one `## CONFLICT-NNN` section per resolved conflict (slot, precedence, both source quotes ≤200 chars, why, resolution).
8. **Cache** keyed on `SHA256(linked_body || slot_name || slot_purpose || model_id || prompt_version)`:
   - Cache store at `.squidsquad/<alias>/.assemble-cache/` (git-tracked)
   - First uncached run is stochastic; cached re-runs are deterministic
   - Cache hit logged to stderr (`[cache hit] slot=X`); miss triggers LLM call
9. **Atomic emit**: on success, the triple (`CLAUDE.md` + `CLAUDE.linked.md` + `CLAUDE.conflicts.md`) lands atomically; on any failure mode (LLM error, preservation check fail, length floor fail, code-block parity fail, conflict report write fail), compose aborts with diagnostic and the previously-written triple (if any) is left untouched.
10. **Model**: `sonnet` (compose-time constant; not config) at temperature ≤ 0.3.

## 4. Non-goals

- Link-stage mechanics (slot grammar, L4 ops, per-slot ordering) — [[compose-link-stage]] (PRD A).
- Runtime L4 writes / `l4-curation` sub-skill — PRD C.
- Sub-skill catalog enforcement — PRD D.
- Harness-driven recompose-on-source-change — PRD E.
- An `Assemble: no` config opt-out — explicitly out, per [[project_assemble_unconditional]].
- A "fallback to linked body on assemble failure" path — explicitly out per TRD §4.6 ("shipping inconsistent prose to the agent on every cycle would be worse than failing the deploy").

## 5. Architectural anchors

These are the TRD sections this PRD draws on; no architectural decisions in this PRD — only delivery shaping.

- **TRD §4.6** — Assemble pass full spec: motivation, per-slot scope, hard preservation guarantees, conflict resolution, conflict report format, length floor, code-block parity, cache, model, failure modes, atomic emit contract, first-run determinism trade-off.
- **TRD §4.4** — End-to-end pipeline diagram showing link → assemble → atomic emit.
- **TRD §5** — Composed-output structure (assembled output must conform to the six-slot grammar).
- **TRD §6.1** — Step-ID grammar (preserved through assemble).

## 6. Dependencies

| Dependency | From | Why |
|---|---|---|
| Link stage produces a per-slot linked composite | [[compose-link-stage]] (PRD A) | Assemble operates on link-stage output; can't start until PRD A's slot grammar lands |
| LLM gateway reachable via `references/scripts/model_router.py` | Existing infrastructure | Assemble calls the LLM via `model_router code-review` or new task type |
| `references/scripts/providers/` adapters present | Existing | `model_router` uses these to dispatch to the configured provider |
| Six-slot output emitter (PRD A) | PRD A | Assemble is invoked per slot; needs link to emit slot-tagged composite |

**No new dependencies** outside the link-stage prerequisites.

## 7. Story breakdown (proposed)

Each story = one deliverable PR or coherent commit set.

| # | Story | TRD anchor | Effort | Notes |
|---|---|---|---|---|
| **B1** | Assemble pass: LLM call scaffolding per slot — invoke `model_router` for `identity`/`responsibility`/`soul`/`instructions`; pass-through for `project-context`/`vault` | §4.6 per-slot table | M | First end-to-end skeleton; uses naive prompts; no cache yet |
| **B2** | Hard preservation verifier — multiset checks for sub-skill refs, step IDs, code-block count, file paths | §4.6 preservation list | M | Pure function; unit-testable independently of LLM |
| **B3** | Length-floor + code-block parity checks | §4.6 floor + parity | S | Two more checks added to B2's verifier |
| **B4** | Conflict detection + `CLAUDE.conflicts.md` emitter | §4.6 conflict resolution + report format | M | Detect: assembler examines per-slot linked input for materially-contradicting prose between layers; emit: structured markdown per CONFLICT-NNN |
| **B5** | Higher-L-wins resolver — when conflict detected, align assembled output with higher-layer prose; verify after rewrite | §4.6 precedence rule | M | Couples with B4 — both ship together or B5 hard-depends on B4 |
| **B6** | Cache layer — `SHA256` key, `.squidsquad/<alias>/.assemble-cache/` store, hit/miss logging | §4.6 caching | S | Pure I/O work on top of B1's call site |
| **B7** | Atomic emit + abort semantics — on success write triple atomically; on any failure abort and leave prior triple untouched | §4.6 atomic-write contract + failure-mode table | M | Wraps the whole pipeline; needs all of B1–B6 in place |
| **B8** | Golden-file regression tests against fixtures from PRD A's A3 | success-criterion 7 + 9 | M | Re-use A3 fixtures; goldens are assembled outputs + conflict reports |

Effort scale: S = 1–2 days, M = 3–5 days, L = 1+ week.

**Recommended pickup order** (lowest risk first):

1. B2 (preservation verifier — pure function, no LLM)
2. B3 (floor + parity — extends B2)
3. B6 (cache layer — pure I/O, can be smoke-tested against synthetic inputs)
4. B1 (LLM scaffolding — depends on PRD A's slot grammar)
5. B4 (conflict detection)
6. B5 (resolver — couples with B4)
7. B7 (atomic emit — wraps all)
8. B8 (golden-file tests — verifies the whole stack)

## 8. Open questions for this PRD

| # | Question | Resolution path |
|---|---|---|
| Q-B1 | Should assemble use `model_router code-review` task type, or a new `assemble` task type? | Decide in B1 — `code-review` is overloaded; recommend adding a dedicated `assemble` task type with its own prompt template |
| Q-B2 | What's the prompt template for the assemble call? Should it live at `references/prompts/assemble.md.j2` alongside the others? | Decide in B1 — yes, `references/prompts/assemble.md.j2`; per-slot variants can use Jinja conditionals |
| Q-B3 | How does the assembler **detect** materially-contradicting prose between layers (for B4)? Pure-LLM judgment? Diff-based heuristics? Two-pass LLM? | Decide in B4 — recommend single-pass LLM with explicit "list any contradictions you reconciled" output section, parsed back into the structured conflict report |
| Q-B4 | Cache key includes `prompt_version` — how is `prompt_version` derived? File hash? Manual version constant? | Decide in B6 — recommend hash of the prompt template file (auto-invalidates on prompt edits) |

## 9. Out of scope — explicit list

For clarity, these items belong to other PRDs and should NOT slip into PRD B:

- Six-slot output emitter ([[compose-link-stage]] / TRD §5)
- Link-stage validation rules R1-R6 ([[compose-link-stage]] / TRD §3.3 + §4.5)
- `## Aliases` parser ([[compose-link-stage]] / TRD §3.0)
- `l4-curation` sub-skill, runtime L4 write flow, three-gate model (PRD C / TRD §7)
- Sub-skill catalog enforcement (PRD D / TRD §4.5 full)
- Wake-mode selection, mode-agnostic manifest (PRD D / TRD §6.5)
- Boot-time freshness check, L4-write trigger, operator `squidsquad_cli.py check` (PRD E / TRD §8)
- An `Assemble:` config field of any kind (per [[project_assemble_unconditional]])

## 9a. Coexistence with v1 — no broken installs during the transition

**Family-wide constraint** (applies to all PRDs A–E): the existing v1 `.squidsquad/<alias>/CLAUDE.md` MUST remain the runtime contract until the family-wide **v2 switch PR** ships at the end of the slice family. No PRD-B PR is allowed to:

1. Modify the v1 output path or its bytes
2. Break the v1 compose pipeline (`compose.py deploy <role>` must keep producing byte-identical v1 output)
3. Land assemble-pass code on the default path — v2 is opt-in (`--v2` flag or equivalent) until the switch

**PRD-B-specific application**:
- B1–B7 implement the assemble pipeline against the v2 link-stage output (PRD-A's output paths). Output goes to a v2 path (e.g. `.squidsquad/<alias>/CLAUDE.v2.md` + sibling `CLAUDE.linked.v2.md` + `CLAUDE.conflicts.v2.md`) — NOT to the v1 `CLAUDE.md`.
- B8 golden-file tests assert (a) v2 outputs match expected goldens AND (b) a parallel run of v1 compose continues to produce byte-identical v1 `CLAUDE.md` content.
- Loop-mode fallback during the switch is automatic per [[AGENT-RUNTIME]] §8.3 boot probe — no new mechanism needed.

The switch PR (ships after A/B/C/D/E story-PRs all land) renames v2 paths to canonical v1 paths, removes v1 compose code, and drops the `--v2` opt-in flag in one atomic change.

## 10. Acceptance

This PRD is "done" when:

- All 8 stories (B1–B8) have shipped or been explicitly deferred (with rationale + target PRD).
- The 10 success criteria above are demonstrably met (preservation tests pass; conflict report format matches TRD §4.6; cache hit/miss observable; abort-on-failure verified end-to-end).
- A reviewer can read this PRD top-to-bottom and identify what the assemble pass does, what it does NOT do, and where the boundaries to PRDs A / C / D / E sit.
- At least one fixture exercises a real L4 contradiction (e.g., L2 says "verify pending-test items" and L4 says "verifier handles all verification") and the resulting `CLAUDE.conflicts.md` correctly cites both sides + the L4-wins resolution.

## 11. References

- TRD: [[COMPOSE-ARCHITECTURE]] (canonical spec)
- Sibling architecture: [[AGENT-RUNTIME]], [[HARNESS-ARCH]], [[INSTALLER-ARCH]], [[VAULT-ARCH]]
- Companion PRDs: [[compose-link-stage]] (A), [[compose-l4-customization]] (C, forthcoming), [[compose-catalog-and-wake-mode]] (D, forthcoming), [[compose-freshness]] (E, forthcoming)
- Memory rules: [[project_trd_prd_delivery_model]], [[project_assemble_unconditional]], [[project_compose_freshness_harness_owned]]
