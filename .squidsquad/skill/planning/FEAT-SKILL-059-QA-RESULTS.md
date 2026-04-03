# FEAT-SKILL-059 QA Results — SOUL.md: Agent Personality and Operational Philosophy

**QA Agent**: Fresh QA (no prior context)
**Date**: 2026-04-02
**Verdict**: FAIL — 3 test case failures requiring dev fixes

---

## Per-TC Results

### TC-1: Soul files exist for all 5 roles
**PASS**

Files found in `references/sub-skills/souls/`: `designer.md`, `dev.md`, `dm.md`, `pm.md`, `qa.md`. Exactly 5 files, no extras.

---

### TC-2: Each soul contains all 7 dimensions
**PASS**

Grep for dimension keywords returns >= 7 for all files:
- dev.md: 7
- pm.md: 8
- qa.md: 7
- designer.md: 7
- dm.md: 8

All 7 dimensions present as `###` section headings in every file: Professional Identity, Quality Bar, Decision-Making Style, Communication Style, Boundaries, Collaboration Posture, Self-Improvement Lens.

---

### TC-3: 70% philosophy / 30% personality ratio
**PASS**

Manual review confirms each file is dominated by operational philosophy (how to approach work, what to check, how to decide) with personality traits appearing as modifiers in Communication Style. For example:
- Dev: "Terse and technical" (personality) vs "Act first on clear requirements. Ask when requirements are ambiguous." (philosophy)
- QA: "Direct and evidence-based" (personality) vs "Assume every implementation has a defect until you've proven otherwise" (philosophy)

Philosophy statements outnumber personality adjectives roughly 3:1 across all files. Satisfies the 70/30 target.

---

### TC-4: Structure + anti-patterns format used
**PASS**

Anti-pattern grep counts per file:
- dev.md: 6
- pm.md: 11
- qa.md: 10
- designer.md: 12
- dm.md: 10

Every file has explicit "Anti-pattern:" labeled items in multiple dimensions (Quality Bar, Communication Style at minimum). Anti-patterns are specific and actionable (e.g., "Marking Pending Test when known edge cases are unhandled", not generic).

---

### TC-5: 2-3 example Discussion entries per role
**PASS**

Each file contains exactly 2 example Discussion entries, formatted as `> Example:` blockquotes with inline code blocks. Examples are clearly labeled with "Example:" prefix so they cannot be mistaken for real history. All 5 files verified.

---

### TC-6: Vault references present (BRIEFING.md + human-profile)
**FAIL**

TC requires each soul file references BOTH `BRIEFING.md` AND `human-profile`. Results:

| File | BRIEFING.md | human-profile |
|------|-------------|---------------|
| dev.md | Yes | **NO** (references `[[code-conventions]]` instead) |
| pm.md | Yes | Yes |
| qa.md | Yes | **NO** (only BRIEFING.md) |
| designer.md | **NO** (references `[[design-system]]` instead) | Yes |
| dm.md | Yes | Yes |

**3 files fail**: dev.md missing human-profile, qa.md missing human-profile, designer.md missing BRIEFING.md.

The Self-Improvement Lens sections reference role-specific vault items (which is good) but the TC requires BOTH BRIEFING.md and human-profile in every file. Only pm.md and dm.md pass this criterion.

---

### TC-7: Soul is first include in template composition
**FAIL (documentation gap)**

**Functionally PASS**: All 6 entry files (`roles/dev-agent.md`, `roles/pm-agent.md`, `roles/pm-lean.md`, `roles/qa-agent.md`, `roles/designer.md`, `roles/dm-agent.md`) have `{{include: souls/<role>}}` on line 1 as the very first directive. The composed output in `agent-instructions.md` confirms soul content appears before any procedural content.

**Documentation FAIL**: The manifest's "Composition Order" sections for each role do NOT list souls as a numbered include. For example, Dev Agent lists items 1-5 starting with `common/pull-latest`. The TC verification says "For each role entry in the manifest, the first numbered include references `souls/<role>`" — this fails because the manifest numbering skips souls entirely.

The manifest needs to be updated to show `souls/<role>` as item 0 (or item 1 with the rest renumbered) in each role's composition order.

---

### TC-8: One PM soul shared by both pm-agent and pm-lean
**PASS**

Only one PM soul file exists: `souls/pm.md`. Both `roles/pm-agent.md` (line 1: `{{include: souls/pm}}`) and `roles/pm-lean.md` (line 1: `{{include: souls/pm}}`) reference the same file. Verified in composed output — both PM templates contain identical soul content.

---

### TC-9: Soul file size within ~60-80 lines
**FAIL**

Line counts:
- designer.md: 48 lines
- dev.md: 46 lines
- dm.md: 48 lines
- pm.md: 48 lines
- qa.md: 48 lines

All files are 46-48 lines. The acceptable tolerance is 50-100 lines. **All 5 files are below the 50-line minimum.** The files are approximately 37-40% shorter than the target midpoint of 70 lines.

---

### TC-10: Soul is static — no dynamic/mutable content
**PASS**

Grep for mutable language (`update this`, `modify this`, `evolve`, `change over time`, `learn from`, `adapt this file`) returns 0 for all 5 files. Souls are static artifacts with no self-modification instructions.

---

### TC-11: Human instruction override clause present
**PASS**

All 5 files contain the override clause as their opening italic line:
> _Human instructions always override these defaults. When overriding, comply and note the deviation in Discussion._

This is clear, per-instance (not blanket), and includes the Discussion-logging requirement.

---

### TC-12: No procedural duplication with existing templates
**PASS**

Grep for procedural content (Ralph Loop, Step N, git commands, working-state.md, INDEX.md, iter-N) returns only one benign hit: dev.md's example Discussion entry mentions "INDEX.md" in the context of describing a bug fix ("Root cause was stale INDEX.md after archival"). This is narrative content in an example, not procedural instruction. No soul file contains loop steps, file path conventions, git commands, or tool-specific instructions.

---

### TC-13: Roles have distinct voices
**PASS**

Each role has a clearly distinguishable voice:
- **Dev**: Terse, action-first ("Fixed. Root cause was...")
- **PM**: Structured, diplomatic ("Human approved with scope revision...")
- **QA**: Direct, evidence-cited ("FAIL TC-7. vault-protocol.md references...")
- **Designer**: Descriptive, options-focused ("Three directions explored with the human...")
- **DM**: User-centric, benefit-framed ("CHANGELOG entry: 'New: Shared knowledge vault...'")

Example Discussion entries are clearly different in structure, tone, and content. No two roles could be confused.

---

### TC-14: Anti-patterns are specific and verifiable
**PASS**

All anti-patterns are concrete and testable. Examples:
- "Marking Pending Test when known edge cases are unhandled" — yes/no checkable
- "Filing a feature with 'TBD' in acceptance criteria" — grep-verifiable
- "Noting gaps 'for follow-up' instead of blocking the ship" — observable in Discussion
- "Leaving visual states as 'standard' or 'typical'" — checkable in design specs
- "CHANGELOG entries that are commit messages" — pattern-matchable

No generic anti-patterns found.

---

### TC-15: Self-improvement lens dimension is forward-looking
**PASS**

Each role's lens contains role-specific scan targets:
- **Dev**: code quality debt, missing error handling, performance bottlenecks, repeated patterns, test gaps
- **PM**: process bottlenecks, stuck features, stale Pending items, coordination gaps
- **QA**: test coverage gaps, uncovered edge cases, regression risks, stalled bugs, agent health anomalies
- **Designer**: UX friction, design system inconsistencies, missing component patterns, accessibility gaps
- **DM**: outdated README sections, missing guides, unclear CHANGELOG entries, adoption barriers

No two roles share identical scan targets.

---

### TC-16: Manifest updated with souls directory
**PASS**

The manifest's Sub-skill File Inventory section (line 106) lists the `souls/` directory with all 5 files documented with descriptions:
```
├── souls/
│   ├── dev.md       (Dev agent soul — pragmatic engineer)
│   ├── pm.md        (PM soul — diplomat and strategist)
│   ├── qa.md        (QA soul — evidence-first skeptic)
│   ├── designer.md  (Designer soul — creative collaborator)
│   └── dm.md        (DM soul — user-centric delivery)
```

---

### TC-17: Composed templates include soul content
**PASS**

Verified in `references/agent-instructions.md`:
- Dev template: Soul appears at lines 25-72 (very top of template, before "SquidSquad — [ROLE] Lead")
- PM template: Soul appears at lines 513-562 (first content in PM template section)
- QA template: Soul at lines 2273-2322
- Designer template: Soul at lines 2766-2815
- DM template: Soul at lines 3332-3381

Soul content is consistently the FIRST content in each composed template, before any procedural instructions.

---

### TC-18: Collaboration posture defines inter-agent relationships
**PASS**

Each collaboration posture mentions at least 2 other roles:
- **Dev**: PM ("scope decisions"), QA ("verification"), designer ("specs")
- **PM**: dev agents ("shield from ambiguity"), QA ("trust findings absolutely"), DM ("support with delivery notes"), designer ("Design Brief")
- **QA**: dev ("challenge constructively"), PM ("scope decisions"), DM ("give confidence")
- **Designer**: human, dev ("technical constraints"), PM ("design estimates")
- **DM**: dev ("delivery notes"), PM ("user-facing context"), QA ("confidence that docs reflect behavior")

Postures are complementary — QA challenges dev, dev respects QA; PM shields dev from ambiguity, dev respects PM scope.

---

## Summary

| TC | Result | Notes |
|----|--------|-------|
| TC-1 | PASS | 5 files, no extras |
| TC-2 | PASS | All 7 dimensions in all files |
| TC-3 | PASS | ~75/25 philosophy/personality ratio |
| TC-4 | PASS | Anti-patterns in all files, specific |
| TC-5 | PASS | 2 examples per file, clearly labeled |
| TC-6 | **FAIL** | 3 files missing either BRIEFING.md or human-profile |
| TC-7 | **FAIL** | Functionally correct but manifest docs don't reflect soul position |
| TC-8 | PASS | Single pm.md shared by both PM variants |
| TC-9 | **FAIL** | All files 46-48 lines, below 50-line minimum |
| TC-10 | PASS | Static, no mutable content |
| TC-11 | PASS | Override clause in all files |
| TC-12 | PASS | No procedural duplication |
| TC-13 | PASS | Distinct voices confirmed |
| TC-14 | PASS | Anti-patterns are concrete and testable |
| TC-15 | PASS | Role-specific forward-looking scan targets |
| TC-16 | PASS | Manifest inventory lists all 5 soul files |
| TC-17 | PASS | Soul is first content in all composed templates |
| TC-18 | PASS | Inter-agent relationships defined, complementary |

**15 PASS / 3 FAIL**

## Gaps Requiring Dev Fixes

### Gap 1 — TC-6: Missing vault references (FAIL)
Three soul files are missing required vault references:
1. **dev.md**: Add `[[human-profile]]` reference (currently only has `[[code-conventions]]` and BRIEFING.md)
2. **qa.md**: Add `[[human-profile]]` reference (currently only has BRIEFING.md)
3. **designer.md**: Add `BRIEFING.md` reference (currently only has `[[design-system]]` and `[[human-profile]]`)

Each file's Self-Improvement Lens should reference BOTH BRIEFING.md and human-profile. Role-specific additional references (code-conventions, design-system) can remain.

### Gap 2 — TC-7: Manifest composition order doesn't show souls (FAIL)
The manifest's "Composition Order" sections for each role need to include `souls/<role>` as the first numbered item. Currently the numbered lists start with `common/pull-latest` and omit the soul include entirely, even though the entry files correctly have it on line 1.

### Gap 3 — TC-9: All soul files below minimum line count (FAIL)
All 5 files are 46-48 lines, below the 50-line acceptable minimum (target 60-80). Files need approximately 4-30 additional lines of content. Options:
- Expand existing dimensions with more operational guidance
- Add more anti-patterns (currently 2-3 per file, could add 1-2 more per dimension)
- Expand example Discussion entries (currently 2, could add a third per TC-5's "2-3" allowance)
- Add more specific guidance to Self-Improvement Lens

## Overall Verdict

**FAIL — Back to dev.** Three test cases failed. All three gaps are straightforward to fix in one dev cycle. The core design is solid — distinct voices, proper structure, correct anti-pattern format, and functional composition ordering. The failures are in completeness (vault refs, line count) and documentation accuracy (manifest).
