# CQ Pass 2 — PR #10356 Comprehension Test

**Subagent**: general-purpose / Sonnet
**Docs**: COMPOSE-ARCHITECTURE.md, AGENT-RUNTIME.md, l4-curation.md (PR-branch versions, post-`4321f0ea`)
**Mode**: First-pass only per author directive ("pause the CQ test after first pass")

## Summary

25 questions covering the L1–L4 model, slot grammar, manifest selection, L4 op grammar, file naming, elicitation dialog, safety gates, team-awareness routing, mode flip, cursor ownership, and source-output sync. 24/25 answered confidently. 1 partial gap + 3 new gaps + 5 friction points.

## Resolved from prior CQ pass

All 8 prior `l4-curation.md` findings confirmed resolved:

1. ✅ `soul-directives` bucket → `slot: soul`
2. ✅ File naming → `<slot>-<short-kebab-description>.md`
3. ✅ Bare `insert` op → `append` / `insert-before` / `insert-after` / `replace`
4. ✅ `anchor` field → `target`
5. ✅ Gate sequence — DS audit → mini-CQ → dry-run, consistent across both docs
6. ✅ `shared-*.md` files removed
7. ✅ `vault-optimize.md` cross-ref dropped
8. ✅ Cross-role L4 ambiguity → both docs consistent (l4-curation says not supported, COMPOSE §11.1 Q3 flags as open)

## New gaps

- **GAP 1 — Soul slot L4 replace semantics** (COMPOSE §11.1 Q1, unresolved). The sub-skill assumes any slot accepts any op; the parent doc flags this as open. Implementer doesn't know whether to use `replace` or `append` for soul.
- **GAP 2 — Ordinal collision/tiebreak rule** (COMPOSE §3.3). `append` ops "sorted by their own `ordinal`" but no rule for missing/duplicate ordinals.
- **GAP 3 — Loop-mode improvement subloop coverage** (AGENT-RUNTIME §7.6). Single-sentence mention; no dedicated section like event-mode.

## Friction points

- **F1** — Cycle wrapper "same in both modes" prominent at §2; per-event-not-per-nudge qualifier buried in pseudocode. Most likely first-pass misread.
- **F2** — COMPOSE §6.5 silent per-role manifest fallback ("falls back to polling manifest if absent") could be conflated with operator-level fallback.
- **F3** — COMPOSE §4.2 insert ordering "in the current base" ambiguous: pre-replace or post-replace base?
- **F4** — Gate sequence is consistent (no friction; positive note).
- **F5** — `ordinal` field appears in both L1-L3 frontmatter (slot sort) and L4 frontmatter (append sort); same name, different semantics; not flagged.

## Strengths

- AGENT-RUNTIME §7.1 nudge contract (pseudocode + sequence diagram)
- §7.4 + l4-curation step 8 gate alignment
- COMPOSE §6.5 two-manifest rationale
- l4-curation "Talking to the user" labeling
- AGENT-RUNTIME §7.3 routing table
- COMPOSE §5.6 worked examples + diff table
