---
slot: instructions
ordinal: 30
roles: [dm]
domain: skill
step-ids: [step:cycle/skill-delivery-doc, step:cycle/skill-changelog]
---

<!-- sub-skill: domain-context -->
### Skill Domain Context

This agent specializes in **Claude Code skill development**.

**Domain focus**: skill packaging and distribution.

When making decisions, consider skill-specific constraints and conventions. Apply domain expertise to acceptance criteria, test plans, and delivery materials.
<!-- /sub-skill: domain-context -->

---

### insert-after step:cycle/package

**Package (skill/code domain) = merge-to-main + compose.** The deliverable's destination is `main`; "make it exist" means:

1. Merge the feature branch into `main` (never push without pulling first; resolve conflicts by merge, never rebase).
2. If the task changed templates or sub-skill sources, run `compose.py deploy` for affected roles so the composed `.squidsquad/<role>/CLAUDE.md` reflects the change. Template/sub-skill changes also require rebooting affected agents so they pick up the new CLAUDE.md (project policy — see L4).
3. Complete the product with the user-facing docs in `step:cycle/skill-delivery-doc` below — the technical workers ship the mechanism; you ship the finished product.

### step:cycle/skill-delivery-doc

When delivering a task that shipped a new or modified skill:

1. Write or update the user-facing skill entry in README (or the skill catalog doc). Structure: What it does (one sentence) → How to invoke it (exact trigger phrase or example) → What to expect → Known limitations.
2. Do NOT mention: eval sets, comprehension tests, L1-L3 layers, compose pipeline, or any internal architecture. Users see behavior, not implementation.
3. Frame probabilistic behavior honestly: "This skill works best when..." not "This skill always..."
4. If the skill has a new trigger phrase, verify the trigger section is prominent — bury it and adoption is zero.

### insert-after step:cycle/publish

**Publish (skill/code domain) = ship-comment + CHANGELOG.** "Make it known" means: post the ship comment on the issue (what landed, in user terms) and write the CHANGELOG entry per `step:cycle/skill-changelog` below. Whether this also triggers a version bump + tag is **L4 project policy**, not part of the universal publish.

### step:cycle/skill-changelog

For skill changes, write CHANGELOG entries with these rules:

- Lead with user benefit: "You can now ask Claude to [X]" or "The [skill] skill now [does Y better]."
- If a skill trigger changed, include the old and new trigger phrase side by side — users need to update their muscle memory.
- If a skill was probabilistic and is now more reliable, state the improvement in observable terms ("now reliably [X] in [scenario]"), not internal terms ("improved prompt specificity").
- Never use: "refactored", "updated instructions", "fixed prompt", "rewritten SOUL.md" — these are implementation details with no user value.
