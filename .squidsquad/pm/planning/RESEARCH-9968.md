# RESEARCH-9968 — Compose pipeline + composed-output structure review (DRY across L1-L4)

**Issue**: #9968
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-23
**Status**: approved → in-progress (PM-owned, picked up cycle 1604)
**Triggers**:
- Human redirect 2026-05-23: "file it to PM — the task is to review how compose is done, and structure of the final output."
- Human follow-up 2026-05-23 cycle 1603/1604: "I see instructions scattered in different places. Instructions should be only in one section, step by step."
- Adjacent symptom #9969 — manifest.md `CLAUDE.md` vs `instructions.md` naming drift (one drift artifact among several)
- Adjacent process gap — dev agents (skill) not catching composed-output inconsistencies during code review

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/RESEARCH-9968.md` (this doc) + `CONTEXT-9968.md` (to be written in Phase 2) + the GitHub issue body for #9968. The companion #9969 is filed separately for tracking but its resolution should fall out of #9968's Phase 2 decisions.

---

## 1. Goal recap

Two intertwined deliverables:

1. **Composed-output structural target** — define what `.squidsquad/<role>/CLAUDE.md` *should* look like as a reading artifact. Primary human concern: instructions for "what the agent does each cycle" must live in **one ordered step-by-step section**, not be scattered across many H2 sections introduced by individual L1/L2 includes.

2. **Code-review protocol for compose** — produce a checklist skill (and any future dev agent) follows when changing L1-L4 source files, so structural inconsistencies in composed output are caught before merge. Direct counter to the gap that surfaced manifest.md / `CLAUDE.md`-vs-`instructions.md` drift and structural scatter without anyone noticing.

Non-goal in Phase 1: no file-touching. This artifact establishes the problem, inventories the current state, and proposes target options for Phase 2 human lock-in.

---

## 2. Measured inventory (2026-05-23, post-cycle-1300 of #9965)

### Composed output sizes

| Role | Lines | H2 sections (`## `) | Includes (per manifest) |
|---|---|---|---|
| pm  | 2066 | 46 | 27 |
| skill | 1698 | 27 | 20 |
| qa  | 1383 | 27 | 13 |
| dm  | 1230 | 27 | 16 |

PM is the outlier — ~50% more H2 sections than its include count, which means a single include is emitting multiple top-level sections into the composed output instead of a single bounded chapter.

### PM's 46 H2 sections (current order, grouped semantically by hand)

```
A. Foundation (read-once, identity)
   - Agent Foundation
   - Tracker Protocol — GitHub Issues
   - Soul
   - Your Responsibilities
   - Team Awareness
   - Your Teammates' Responsibilities
   - PM — General Responsibility

B. Boot (one-time, session start)
   - Boot — Mode Detection (#9588)   [Steps 1-4 inside]

C. Cycle execution (the per-cycle Ralph Loop)
   - Cycle Runner (Transport Layer)  [Phase 1 / Phase 2 / Phase 3 inside]
   - Step 1b — Context Pressure Check
   - Step 1c — Resume From Working State
   - Step 2 — Check In With Human
   - Steps 3-6 — Testing & Verification
   - Delivery
   - Step 6f — Pipeline Sentinel (always runs)
   - Own-Domain Auto-Fix (PM Rule)
   - Step 7 — Agent Health Check
   - Step 7b — Triage External Issues
   - Step — First-Cycle Health Report (PM Only)
   - Step — Soul Shepherd (Character Signal Detection)

D. Quiet-cycle work (also per-cycle, but conditional)
   - Improvement Scanning (Quiet Cycle Productivity) — PM Override
   - Step 4b — Vault Remember (End-of-Cycle Reflection)
   - Step — Vault Optimize (Quiet Cycle)
   - Step — Vault Synthesis (Quiet Cycle)

E. Lifecycle (cross-cutting, mostly at cycle boundaries)
   - Self-Restart (Context Pressure Only)
   - Graceful Stop — Self-Quit Protocol
   - Agent Lifecycle

F. Protocols (reference / lookup, not per-cycle steps)
   - Issue Filing Protocol
   - Task Lifecycle (5-Phase)        [Phase 1-5 inside, plus 2A/2B/3B]
   - Discussion Protocol
   - Working State File
   - Vault — Shared Memory Layer

G. Conventions (reference)
   - File Conventions
   - Status Line
   - What You Must Never Do

H. Project-specific L3 (operations + identity)
   - PM Project Operations — SquidSquad
   - PM Project Identity — SquidSquad

I. Project-specific L4 (auto-included after L3)
   - Setup & Upgrade Sync Check
   - Setup/Upgrade Sync Check         ← near-duplicate H2 of the line above
   - Project Operations — SquidSquad   ← parallel to H section above
   - Project Identity — SquidSquad     ← parallel to H section above
```

### Scattered-instructions evidence (the primary human finding)

The current PM CLAUDE.md interleaves cycle-execution steps with non-cycle protocols and reference material. To execute one cycle, an agent must mentally stitch together steps that appear in this physical reading order:

1. `## Cycle Runner (Transport Layer)` — line 359 — introduces Phase 1/2/3 (mechanical pre, creative middle, mechanical post)
2. `## Step 1b` — line 459 — context check (logically *between* Phase 1 and Phase 2, but written as its own H2 a hundred lines later)
3. `## Step 1c` — line 481 — resume working state
4. `## Step 2` — line 497 — check in with human
5. `## Steps 3-6` — line 528 — testing & verification (PM-delegating to QA)
6. `## Delivery` — line 538 — delivery delegation to DM
7. `## Step 6f` — line 546 — pipeline sentinel
8. `## Own-Domain Auto-Fix` — line 677 — embedded inside the sentinel section
9. `## Step 7` — line 700 — agent health
10. `## Step 7b` — line 723 — triage external issues
11. `## Step — First-Cycle Health Report` — line 752 — one-shot at session start (re-numbering breaks)
12. `## Step — Soul Shepherd` — line 770 — character signal (per-cycle)
13. `## Improvement Scanning ...` — line 813 — different H2 group, but still per-cycle
14. `## Step 4b — Vault Remember` — line 919 — number 4b appearing **after** 6f/7/7b is unambiguously misordered
15. `## Step — Vault Optimize` — line 1008 — drops the number entirely
16. `## Step — Vault Synthesis` — line 1042 — drops the number entirely

Four distinct symptoms in just the cycle-execution slice:

- **Numbering grammar is mixed**: `Step N` (some lettered: 1b/1c/6f/7b), `Phase N`, and `Step — <name>` (no number) coexist.
- **Numbering order is broken**: Step 4b appears physically after Step 7b.
- **One logical activity (the cycle) is fragmented across ≥16 H2 sections** instead of being one section with ordered sub-steps.
- **Cross-cutting concerns (Pipeline Sentinel's "Own-Domain Auto-Fix") are H2-promoted**, breaking the "Step 6f" subtree into siblings.

### Duplicate / near-duplicate sections in PM composed output

| Section A | Section B | Source |
|---|---|---|
| `## PM Project Operations — SquidSquad` (L3) | `## Project Operations — SquidSquad` (L4) | L3 `references/roles/pm/project-operations-squidsquad.md` vs L4 `.squidsquad/project/pm-project-operations.md` |
| `## PM Project Identity — SquidSquad` (L3) | `## Project Identity — SquidSquad` (L4) | same split |
| `## Setup & Upgrade Sync Check` | `## Setup/Upgrade Sync Check` | two near-identical H2 titles, content overlap not yet diffed |

This is unintended structural duplication (L3 content effectively re-stated by L4 with slightly different framing). Not yet measured: how much of the body text overlaps.

---

## 3. Root cause analysis

### How the scatter is generated

`compose.py` resolves `{{include: path}}` directives in each role's `references/roles/<role>/CLAUDE.md` entry file (per `references/roles/<role>/includes.yml`). Each include emits its source file's content verbatim, wrapped with `<!-- sub-skill: name -->` markers. There is no contract on the **heading level** an include can introduce — a single include is free to emit one H2 or many.

Consequences:

1. **Each sub-skill author decides their own top-level header**. Most sub-skills emit one H2; some emit multiple (e.g., `pipeline-sentinel` emits both a `## Step 6f` section AND a `## Own-Domain Auto-Fix` peer at the same level).
2. **The composed document's reading order = the includes.yml order**, with no narrative grouping. Cycle steps land in `cycle-runner` → `context-pressure` → `resume-working-state` → role-specific sub-skills (`checkin`, `testing-and-verification`, `delivery`, `pipeline-sentinel`, ...) one after the other, but reference material (`issue-filing`, `task-intake`, `discussion-protocol`, `working-state`, `vault-protocol`, `file-conventions`, `status-line`) appears interleaved on the same H2 level immediately after, then per-cycle quiet-cycle sub-skills (`improvement-scan`, `vault-remember`, `vault-optimize`, `vault-synthesis`) appear *after* the reference block.
3. **Step numbering is local to each sub-skill author**. No central plan ensures `Step 4b` is physically before `Step 6f`; numbers are inherited from older flat-file documents and never renormalized when sub-skills were extracted.
4. **L3 / L4 collision is not detected**. There is no rule preventing both layers from emitting top-level sections with overlapping titles.

### Why dev-agent (skill) code review didn't catch this

- The compose pipeline has no automated structural-output check. Skill code review verifies source diffs, not the rendered composed CLAUDE.md.
- Composed outputs (`.squidsquad/<role>/CLAUDE.md`) are git-tracked but marked `DO NOT EDIT` — humans skim them at install time only. Day-to-day code review never reads them.
- Manifest drift (#9969: `CLAUDE.md` vs `instructions.md`) is the same family of bug: documentation about composition is decoupled from what compose actually does, and no review pass cross-checks them.

---

## 4. Candidate target structures (Phase 2 input, not decisions)

### Option α — "One Cycle Section" (minimal restructure)

- Collapse all per-cycle steps under a single `## Each Cycle (Ralph Loop)` H2 with sub-steps as H3/H4.
- Keep boot, protocols, reference, and project-specific content as separate top-level H2 sections.
- Renormalize step numbering: `1. Pre-cycle`, `2. Context check`, `3. Resume working state`, `4. Check in`, `5. Pickup`, ..., `N. Post-cycle`. Drop `1b/1c/4b/6f/7b` legacy numbering.
- Mechanism: introduce a `## ` heading-level contract in the manifest; each sub-skill declares whether it contributes "to the cycle section" or "as its own top-level section", and compose.py groups cycle-contributing sub-skills under one H2 wrapper.
- Risk: requires touching every sub-skill source to declare its category; backward-compat shim needed for in-flight #9965 work.

### Option β — "Four-Chapter Layout" (medium restructure)

- Four mandatory top-level chapters: `## 1. Identity` (foundation, soul, responsibilities, team), `## 2. Boot Sequence`, `## 3. Each Cycle`, `## 4. Reference` (protocols, conventions, vault).
- Project-specific L3/L4 nest under chapter 4 (or get their own `## 5. This Project`).
- Stronger contract than α — compose.py rejects sub-skills that try to emit outside their assigned chapter.
- Risk: bigger contract change; the L3/L4 collision (PM Project Operations vs Project Operations) must be resolved as part of the migration.

### Option γ — "Composed-Output AST" (heavy restructure)

- Composed CLAUDE.md becomes a derived view of a structured authoring model: each sub-skill authors a small YAML+markdown unit with declared `chapter`, `position`, `headers_to_emit`; compose.py renders the final document deterministically.
- Solves duplicate-title detection mechanically (compose.py can refuse to emit two sections with the same title).
- Solves DRY (compose.py can detect content overlap via fingerprinting before emit).
- Risk: largest blast radius; biggest authoring-ergonomics change; potentially conflicts with the "extract-and-reference, never duplicate inline" rule in feedback memory.

### Cross-cutting (applies to all options)

- **Code-review checklist (deliverable b from §1)**: a small `references/sub-skills/common/compose-output-review.md` that includes specific assertions: "does my change introduce a new H2?", "does my change re-emit content already present in another layer?", "did I regenerate composed outputs and diff them?". Skill (and any future dev agent) must run this checklist when L1-L4 source changes.

---

## 5. Adjacent / context

### Tied issues

- **#9969** (manifest.md naming) — should be resolved as a fallout of #9968 Phase 2: Option B from #9969's triage maps cleanly to any of α/β/γ; Option C (rename source file) becomes more attractive if γ is picked.
- **#9970** (composed CLAUDE.md drift from #9925) — DM cycle 1314 surfaced 182 lines of source-vs-composed delta across dm/qa/skill (sub-skills updated by #9925, composed outputs never regenerated). Measurable proof that today's pipeline allows ship-without-recompose. Concrete data point for §3's root cause: no PR check, no auto-recompose, no pre-ship gate. Resolution falls out of Phase 2 lock-in; interim PR-check could ship ahead as a quick-win.
- **#9965** (6274.2 terminology rename, in-progress) — actively rewrites the L1-L4 source files this audit operates on. Phase 1 research (this doc) is read-only and parallel. Phase 2 discussion and beyond should sequence after 6274.2 ships so any concrete structural changes don't conflict on the same files.
- **#9925** (4-layer responsibility model, shipped cycle 1583) — established the L1-L4 model that produces today's scatter; this audit is the natural follow-on that didn't happen at the time. Also the source of #9970's drift evidence — #9925 shipped without committing the regenerated composed outputs.

### Vault references

- `decision-l1-l4-only.md` — all agent instructions composed from L1-L4; no ad-hoc instruction files outside the compose pipeline. Constrains target structure: no escape hatch for "just put the cycle steps in a separate file".
- `decision-compose-dry.md` — within L1-L4 each creative-work concept must have exactly one authoring location; extract-and-reference, never duplicate inline. Directly relevant to the L3/L4 duplicate-section finding in §2.

---

## 6. Phase 2 open questions for human lock-in

Each needs a discrete decision before `CONTEXT-9968.md` can be written.

1. **Target structure**: α / β / γ — or a hybrid?
2. **Cycle-section grammar**: keep "Step N + Step Nb" legacy numbering, or renormalize to flat `1, 2, 3, ...`?
3. **Naming**: in the new layout, do sub-skill authors get to pick their H-level, or does the manifest dictate it?
4. **L3 vs L4 collision rule**: forbid duplicate H2 titles at compose time (hard fail), warn (soft), or merge (auto-collapse)?
5. **Code-review checklist scope**: does it gate compose pipeline changes only, or any L1-L4 source change?
6. **Composed-output diff in PR**: should skill be required to commit the regenerated `.squidsquad/<role>/CLAUDE.md` diff in the same PR as the L1-L4 source change, so review sees both?
7. **Migration sequencing**: do we ship #9968's changes (a) entirely after 6274.2 merges, (b) in sub-phases interleaved with 6274.2, or (c) as a "rename-aware" PR that lands the new structure on top of 6274.2?
8. **#9969 resolution**: pick Option A/B/C inside this task, or keep it as a separate downstream task that follows whatever #9968 decides?
9. **Scope of "reference" content**: are protocols (issue-filing, discussion, vault) per-cycle reading or one-time reference? Determines whether they live inside or outside the "Each Cycle" chapter.
10. **Composed-output audit cadence**: one-shot cleanup, or recurring (e.g., every M cycles, PM runs a structural check)?

---

## 7. Out of scope (Phase 1)

- No file edits to compose.py, manifest.md, includes.yml, or any L1-L4 source.
- No commits to composed outputs.
- No decision on α/β/γ.
- No re-triage of #9969 beyond noting the linkage.
- No changes to the 4-layer responsibility model itself (that's #9925, already shipped).

---

## 8. Next step

PM cycles forward into Phase 2: a structured 10-question discussion pass with the human (see §6) to lock in CONTEXT-9968.md. Phase 2 cannot start until the human is online for a discussion; PM stays at `in-progress` and surfaces this in `working-state.md`.
