Now I have a comprehensive picture of the document structure and all the issues. Let me compile the audit report.

---

# 10003-ds-audit-r1 Research — VAULT-ARCH.md v2 Internal-Consistency Audit

## Summary

I audited `docs/VAULT-ARCH.md` (599 lines, §1–§13, all sections v2) for internal contradictions only — cross-section claims, cross-reference integrity, undefined terms, lifecycle inconsistencies, and table-vs-prose mismatches. The document is structurally sound at the architectural level: the PARAG-kept profile, the consumption pipeline, the per-writer shard design, and the M0–M4 migration sequence are internally coherent. However, the v2 rewrite introduced **8 cross-reference errors** from section renumbering — references that point to non-existent subsections (§9.5.1, §9.3.2, §9.5 M1) or the wrong section (§6.3→§10.5). There is one **genuine contradiction** between §6.3 and §8.5/§12.2 on the `.gitattributes` mechanism for telemetry merge strategy, and one **undefined scoring input** (`recency`) that appears in the ranking formula but has no computation defined anywhere in the document. Overall: **3 blockers, 6 minor/nit issues**.

## Vault Context
- **BRIEFING.md priorities**: The active priorities mention "4 umbrella PRDs from DS TRD audits (#10836 INSTALLER-ARCH / #10837 HARNESS-ARCH / #10838 VAULT-ARCH / #10839 cross-TRD role→alias rename) — operator-paced post-cutover, #10837/#10839 need DS re-audit before pickup." This audit addresses #10838. The briefing also notes "Audit refresh strategy: HARD GATE for #10836/#10838; DS re-audit needed for #10837/#10839 before PM pickup."
- **Related decisions**: [[vault-v2-telemetry-storage-locked]] — the §6.3 per-writer shard design is operator-locked; this audit must not propose redesigns, only flag internal contradictions.
- **Related patterns**: None directly applicable — this is a document audit, not an implementation task.
- **Human preferences**: "Documents live on forge, not chat. Git = audit trail." — this document is the prescriptive target design; consistency errors in it would propagate to implementation.
- **Related learnings**: None directly applicable.

## Impact Analysis
- **Files touched**: `docs/VAULT-ARCH.md` only (audit target)
- **Behavior changes**: None — this is a consistency audit, not a redesign
- **Dependencies**: None — standalone document audit

## Findings

### BLOCKER 1: Broken cross-references to non-existent subsections (§9.5.1, §9.3.2, §9.5 M1)

The v2 rewrite collapsed v1's subsection hierarchy but three cross-references still point at the old numbering:

| Location | Says | Problem |
|---|---|---|
| §4.3 (line 226) | "swept during migration (§9.5 M1)" | M1 is §10.2, not §9.5. §9.5 is "Ship — capture-at-ship + end-of-cycle sweep." Should read **§10.2 M1**. |
| §7.2 (line 367) | "capture-at-ship (§9.5.1)" | §9.5 has no numbered subsections; it uses a flat numbered-list (1. and 2.) within the section body. Should read **§9.5 item 1**. |
| §9.8 (line 483) | "capture-at-ship (§9.5.1)" | Same as above — §9.5.1 does not exist. Should read **§9.5 item 1**. |
| §11 #3 (line 565) | "Rules-lane registry placement … (§9.3.2's receipt contract is independent of this)" | §9.3 has no subsection 9.3.2. The receipt contract is described in §9.3's body (items 1 and 2). Should read **§9.3** or **§9.3 item 2**. |

**Severity**: **BLOCKER** — four cross-references are dead; an implementer following them arrives at the wrong content or nothing.

---

### BLOCKER 2: `.gitattributes` mechanism contradicts between §6.3 and §8.5/§12.2

**§6.3 (line 323)** says:

> "`merge=union` in `.gitattributes` on `.telemetry/*.jsonl` — git's built-in union strategy, no per-clone registration, works for every clone on day one."

This describes the **repo-root `.gitattributes`** file with a path pattern (`.telemetry/*.jsonl merge=union`).

**§8.5 (line 425)** says:

> "the installer seeds `.telemetry/.gitattributes` (`merge=union`)"

**§12.2 (line 592)** says:

> "install scaffold seeds `vault-schema.json` (default profile) + `.telemetry/.gitattributes` (`merge=union`)"

These describe a **nested `.gitattributes` file inside the `.telemetry/` directory**, not the root file. These are two different git configurations with different semantics:

- **Root `.gitattributes` with pattern**: `*.jsonl merge=union` applied to files matching `.telemetry/*.jsonl` — one location, centrally managed.
- **`.telemetry/.gitattributes`**: a directory-local `.gitattributes` — would need its own `*.jsonl merge=union` pattern scoped to that directory.

The document endorses both without acknowledging the discrepancy. §6.3 is the LOCKED design section; §8.5 and §12.2 are derivative references that should agree with it.

**Severity**: **BLOCKER** — the installer/seeding instruction (§8.5, §12.2) would produce a different file layout than the locked design spec (§6.3) describes. An implementer following both would be confused about which file to create.

---

### BLOCKER 3: Cross-reference §6.3 → §10.5 points at wrong section for supersession rationale

**§6.3 (line 315)** says:

> "Supersedes `VAULT-COMPARISON-DMPWEB.md` §9.4 point 1 (2026-07-12: harness-owned gitignored store) — **see §10.5 for the full supersession rationale.**"

But **§10.5 (lines 551–555)** is "M4 — cutover & unfreeze" and describes:

- Atomic PR flipping the compose default
- `references/migrations/` documentation
- Unfreezing writes
- Telemetry starting cold

None of this is the *rationale* for why the harness-local store was superseded. The actual rationale is in **§6.3 itself** (lines 317–319: "Why §9.4's harness-local store had to change: a SquidSquad install can run multiple independent harness instances…").

**Severity**: **BLOCKER** — the cross-reference is misleading; an implementer seeking the design justification goes to the wrong section. Should reference **§6.3 itself** (or remove the "see §10.5" clause since the rationale is inline).

---

### MINOR 1: "recency" scoring factor is referenced but never defined

The ranking formula (§6.2, line 307) includes `recency×0.25` as a tiebreak term, and graceful degradation (§6.2 line 309, §7.5 line 386, §9.9 line 493, §10.5 line 555) repeatedly says "tier + recency + type weight" as the fallback. The weight is specified in `vault-schema.json`'s `tieBreakWeights.recency` (0.25, §3.1 line 86, §3.2 line 111). But **nowhere in the document is the recency value itself defined**: is it days-since-`updated:`? Days-since-`created:`? Days-since-last-`used`-event? A normalized 0–1 decay curve? The term is used as if it has an obvious meaning, but the computation is unspecified.

**Severity**: **MINOR** — the formula works structurally without this definition, but an implementer has to guess what "recency" means.

---

### MINOR 2: Undefined term "sonnet subagents" in §10.3

**§10.3 (line 538)** says:

> "Modeled on dmp-web's optimize analyze phase: **sonnet subagents** per topical cluster, proposing, never applying"

"Sonnet" is Anthropic's Claude model name — it is never defined or explained anywhere in this document. A reader unfamiliar with Anthropic's model naming would not understand what "sonnet subagents" means.

**Severity**: **MINOR** — implementation detail leaking into an architecture spec without definition.

---

### MINOR 3: Ambiguous shorthand "planning doc" used without definition

The term "planning doc" appears 5 times (§7.5 lines 383, 386; §10.2 line 525; §11 line 563) as a reference to `VAULT-COMPARISON-DMPWEB.md`. The preamble (line 5) gives the full path `.squidsquad/pm/planning/VAULT-COMPARISON-DMPWEB.md` but never establishes "planning doc" as its canonical shorthand. The word "planning" comes from the directory name `.squidsquad/pm/planning/`, which is incidental to the file's identity.

**Severity**: **NIT** — contextually clear, but a defined abbreviation would prevent ambiguity.

---

### MINOR 4: §3.4 references "§4.5-equivalent" — v1 section ref in a v2 doc

**§3.4 (line 159)** says:

> "a note's identity (its path) never changes on status transitions, only on explicit rename (§4.5-equivalent, still a distinct operation)"

v2's §4.5 is "Wikilinks" — it discusses link graphs and redirect maps, not rename operations. The "§4.5-equivalent" appears to reference v1's §4.5 (which, per the revision log, was about something else in the v1 structure). Within the v2 document, this reference is disorienting.

**Severity**: **NIT** — the meaning is recoverable ("renames are a distinct operation"), but the cross-reference is vestigial.

---

### MINOR 5: Circular cross-reference between §4.4 and §6.4

**§4.4 (lines 242–247)** defines Cold / Surfaced-but-never-used / Stale buckets and says "The impressions report (§6.4, port of dmp-web's `vault-impressions-report`) classifies every note as: [buckets]."

**§6.4 (lines 333–341)** says "buckets every note (per §4.4): [same three buckets]."

Both sections redundantly define the same three buckets and point to each other as the authority. The definitions agree verbatim, so there is no contradiction — but the circular self-reference is structurally odd: neither section is the canonical definition; both are.

**Severity**: **NIT** — not a contradiction, but a maintenance risk (changing one definition requires updating both).

---

### MINOR 6: Hub exemplar list varies between §3.2 and §10.3

- **§3.2 tree diagram (lines 133–136)** lists 7 systems: "harness, event bus, compose pipeline, tracker, pr_merge, launcher, vault itself"
- **§10.3 M2 (line 541)** lists 8 systems: "harness, event bus, compose pipeline, tracker, pr_merge, launcher, **QA gates**, vault itself"

Both are within the stated "~7–10" range and the difference is additive (QA gates added in §10.3), but the inconsistency in what the "initial hub set" contains is noticeable.

**Severity**: **NIT** — both say ~7–10; the exemplar list drift doesn't change the design.

---

## Table-vs-Prose Mismatches

No substantive table-vs-prose mismatches found. The key tables (§2 vault terminology, §4.1 by-folder, §4.2 by-prefix, §6.1 event model, §8.5 engine boundary, §9.9 failure modes, §11 open decisions, §12.1 cross-references) are consistent with surrounding prose. The `archives/` row in §4.1 says "retired as a folder (§3.4)" and §3.4 prose confirms — aligned.

---

## Lifecycle Inconsistencies

No lifecycle inconsistencies found. The M0→M4 migration sequence (§10.1–§10.5) is internally coherent: freeze → transform → distill → human-gate → cutover. The consumption pipeline (§9.2→§9.3→§9.4→§9.5) forms a clean linear flow. Telemetry shards are created at runtime (§6.3), compacted in quiet cycles (§6.5/§9.6), and survive migration (§10.2 deletes `.relevance-index.json` but preserves the vault tree). No entity is deleted in one section and relied on in another.

---

## Recommendation

**Feasible with caveats** — the 3 blockers are all cross-reference fixups (wrong section numbers, wrong file path), not structural redesigns. They can be resolved with targeted edits:

1. Fix §4.3: `§9.5 M1` → `§10.2 M1`
2. Fix §7.2 and §9.8: `§9.5.1` → `§9.5 item 1`
3. Fix §11 #3: `§9.3.2` → `§9.3`
4. Resolve `.gitattributes` contradiction: align §8.5 and §12.2 with §6.3's root-`.gitattributes` design (or vice versa, but pick one)
5. Fix §6.3: remove "see §10.5 for the full supersession rationale" or point to §6.3 itself
6. Define the `recency` computation (or note it as an open decision in §11)
7. Define "sonnet" or replace with model-agnostic language
8. Define "planning doc" shorthand

---

## Vault Candidates

- **Type**: learning — **Cross-reference drift from section renumbering is the #1 defect class in v2 rewrites of v1 architecture docs** — **Why**: This audit found 8 cross-reference errors, all from section renumbering during the v2 rewrite. If the same pattern occurred in #10836 (INSTALLER-ARCH) and #10837 (HARNESS-ARCH), those docs likely have the same defect class. Worth checking proactively.
- **Type**: pattern — **Architecture docs should use stable anchor-based cross-references (e.g., `[section-name](#heading)`) rather than brittle §-notation during rewrites** — **Why**: The §-notation is inherently fragile when sections are renumbered; markdown anchors survive reordering.
- **Type**: learning — **"recency" as a scoring term is a dmp-web concept that was ported without its definition** — **Why**: When porting concepts from a reference system, ensure every term in formulas has a defined computation in the target doc, not just in the source.

## Verdict

**3 blockers** — cross-reference drift from v2 section renumbering (§9.5.1, §9.3.2, §9.5 M1), `.gitattributes` location contradiction (§6.3 vs §8.5/§12.2), and wrong target for supersession rationale (§6.3→§10.5).