---
name: learning-targetable-step-anchors-must-be-bare-h3
description: an L3/L4-targetable step anchor in a composed role spine must be authored as bare H3 "### step:cycle/<id>" (no "Step N —" / "N." numbering prefix) — link_stage_validator._SOURCE_STEP_HEADING_RE matches ONLY bare H3, so it is what makes an anchor a known step-id for R5 op-target validation; the op PROCESSOR is more lenient (H3-H6 + optional numbering prefix) which masks the mismatch until an L4 op aborts compose with R5
metadata:
  type: learning
type: learning
tags: [learning, compose, link-stage, op-grammar, step-anchors, dm-arch, 12749, 11227]
created: 2026-06-18
owner: skill
status: active
confidence: high
source: observation
links: [learning-audit-scope-and-source-of-truth]
---

# A targetable step anchor must be bare H3 `### step:cycle/<id>`

**Observed (#12749 DM-ARCH — authoring the generic DM delivery spine as L3/L4-overridable steps).** Two regexes govern `step:cycle/<id>` anchors and they DISAGREE on heading level — getting this wrong silently degrades an L3/L4 op to inline or aborts compose:

- **Op PROCESSOR** (`l4_op_processor._STEP_HEADING_RE`) matches **H3–H6** *with* an optional `Step N —` / `N.` numbering prefix (#11227 multi-level support). It finds the target of an `insert-after`/`replace` op at any nesting depth.
- **Link-stage VALIDATOR** (`link_stage_validator._SOURCE_STEP_HEADING_RE`) matches **bare `### step:cycle/<id>` ONLY** — H3 exactly, *no* numbering prefix. `_collect_source_step_ids` uses it to build the set of "known step ids," and **R5** (`_check_r5_l4_step_ids_resolve`) aborts compose if an L4 op targets an id not in that set.

**Consequence.** The cardinal cycle steps are authored `### Step N — step:cycle/<id>` (so `_L1_PARENT_STEP_RE` numbers them + renders the hydrated diagram) — but that `Step N —` prefix makes them **invisible to R5**. So an L4 op targeting `step:cycle/work` would abort with R5 even though the processor could find it. Conversely a role's domain sub-steps authored at H4 (`#### step:cycle/<id>`) are processor-findable (inline L3 ops work) but **not** R5-targetable by L4 ops.

**The rule for an L3/L4-overridable spine** (e.g. the DM's 8-step delivery lifecycle): author each step as **bare `### step:cycle/<id>`** — H3, no numbering prefix. Bare-H3 is simultaneously R5-targetable (validator) and processor-findable, and it is NOT picked up by `_L1_PARENT_STEP_RE`, so it stays a flat addressable anchor rather than a numbered cardinal-cycle parent. Graft the whole block via one `### insert-after step:cycle/<universal-step>` op (the DM spine grafts after `step:cycle/work`). R5 only validates L4 file ops, not inline L1-L3 ops — so an inline L3 op targeting a bare-H3 L2 anchor relies on the processor (apply order: lower ordinal first, so the L2 anchor exists before the L3 op runs), while an L4 op against the same anchor is what actually exercises R5.

DM-ARCH §4 ("one H3 `### step:cycle/<id>` anchor per step ... promoting from the existing H4") is exactly this requirement; the *why* is the validator/processor split above.
