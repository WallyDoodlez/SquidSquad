Now I have all the evidence. Let me compile the full line-by-line audit.

---

# FEAT-PM-7630-PRD-AUDIT-v2 Research — L3/L4 Layer Mislabeling & Architecture Alignment Audit

## Summary

This audit compared every architectural claim in the PRD (`FEAT-PM-7630-PRD-branch.md`) against the canonical L1–L4 layered architecture defined in `references/roles/LAYERS.md` (lines 27–34) and the actual directory structure at `references/roles/`. The core finding: **the PRD invents a parallel L1–L4 "reaction layer model" that redefines L3 and L4 to mean things they do not mean in the architecture**. Specifically, the PRD labels L3 as "Behavioral adaptation" (project-tunable reaction parameters) and L4 as "Human overrides" (config.md), when LAYERS.md defines L3 as "Domain specialization (iOS, web, skill)" at `roles/<role>/<variant>/` and L4 as "Project-specific adaptations" at `.squidsquad/<agent>/` owned by soul-shepherd + human. This is not a minor terminology drift — it's a category error that would cause confusion in any implementation phase because the PRD is asking engineers to create "L3 behavioral adaptation" files while the compose.py assembly pipeline expects L3 to be domain variants.

The PRD's event-reaction *mechanism* design is sound and well-specified. The problem is strictly the layer labeling. The fix is to rename PRD's "L3" → a new cross-cutting concern (e.g., "Behavioral Tuning Profile") and PRD's "L4" → remains at L4 but with acknowledgement that L4 is broader than just config.md overrides. Additionally, the PRD makes zero reference to actual L3 domain variants — how dev/skill vs dev/web should react differently to the same event — which is an architectural gap.

## Vault Context

- **BRIEFING.md priorities**: #7630 EPIC is the active priority; "#6581 Wizard reframing — L3 picks agents, L4 records project specifics" recently shipped, meaning the L3/L4 definitions were just confirmed/refined. The PRD must align with this freshly-shipped understanding.
- **Related decisions**: [[decision-cycle-runner-architecture]] — explicitly references #7630 as successor. All mechanical operations move to harness. No layer conflict, but confirms the PRD's direction.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — foundational for #7630. No conflict.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose" — drives #7630 as noted in human-profile.md lines 34-35.
- **Related learnings**: [[decision-self-healing-sentinel]] — two-tier self-healing (immediate unstick + root-cause bug). PRD correctly applies this to event timeout handling.

## Impact Analysis

- **Files touched**: PRD lines 21–37 list ~20 files + ~15 test files. The audit doesn't dispute the file list but flags that some "ABSORBED INTO HARNESS" claims (lines 493, 506) contradict the "retained for backward compat" disposition — both are labeled "eliminated" in the heading but "retained" in the fine print.
- **Behavior changes**: No dispute with the behavioral changes listed.
- **Dependencies**: No dispute.

## Findings

### Finding 1 — CRITICAL: L3 label completely wrong (PRD lines 330–334)

**PRD text (lines 330–334):**
```
- **L1 (Universal)**: Reactions ALL roles share — defined in `common/event-driven-workflow.md`. Only `stop-requested` and idempotency rules.
- **L2 (Role-specific)**: Per-role reactions — defined in `roles/{role}/event-reactions.md` sub-skills.
- **L3 (Behavioral adaptation)**: Project-tunable reaction parameters — separate mechanism from SOUL.md (soul is personality only). Categories: `event-sensitivity`, `reaction-latency`, `scan-priority`.
- **L4 (Human overrides)**: Config.md fields for muting events, timeout tuning, grace periods.
```

**Architecture file that contradicts:**
`references/roles/LAYERS.md`, lines 29–34:
```
| **L3 — Domain** | `roles/<role>/<variant>/` | Domain specialization (iOS, web, skill) | Preset authors |
| **L4 — Project** | `.squidsquad/<agent>/` | Project-specific adaptations | soul-shepherd + human |
```

**Also confirmed by:** `references/roles/dev/skill/includes.yml` (line 1): `# Layer 3 variant manifest — dev-skill` — L3 IS the domain variant manifest.

**Severity**: **CRITICAL**

**Why this matters**: The compose.py assembly pipeline (referenced in BRIEFING.md line 39) assembles L1+L2+L3 → CLAUDE.md. If implementers read "L3 (Behavioral adaptation)" and create files outside the `roles/<role>/<variant>/` directory structure, compose.py won't pick them up. Conversely, if they try to add event-reaction differences between dev/skill and dev/web (which is a genuine architectural need), the PRD gives them no L3 slot to do so.

**Recommended correction**: Remove the "Reaction layer model (L1-L4)" heading and replace with a terminology that doesn't collide with the architectural layer system:
- Keep "L1 (Universal)" → rename to "Universal Tier" (lives in `common/`)
- Keep "L2 (Role-specific)" → rename to "Role Tier" (lives in `roles/{role}/`)
- Rename "L3 (Behavioral adaptation)" → "Behavioral Tuning Profile" (cross-cutting, location TBD — possibly L4 config or a new `behavior-tuning.md` per role)
- Rename "L4 (Human overrides)" → keep as "L4 (Project Overrides)" but acknowledge it's one facet of L4, not the entirety of L4

---

### Finding 2 — CRITICAL: PRD never references actual L3 domain variants (omission)

**PRD text (lines 638–644):**
```
**NEW L2 sub-skills: `roles/{role}/event-reactions.md`** (× 4 files)

Each role gets its own event-reaction sub-skill with reactions from the matrix in Section 3.3:
- `references/sub-skills/roles/dev/event-reactions.md` — Technical Worker reactions
...
```

**What's missing**: The PRD never proposes `references/sub-skills/roles/dev/skill/event-reactions.md` or `references/sub-skills/roles/dev/web/event-reactions.md` — the actual L3 domain-variant layer. A dev/skill agent (building Claude Code skills) and a dev/web agent (building web apps) may need different event-reaction guidance for the same event type (e.g., `pr-merged` → skill dev checks if skill eval templates changed; web dev checks if frontend dependencies changed).

**Architecture reference**: `references/roles/LAYERS.md` lines 53–57 define how L3 variants are added; `references/roles/dev/skill/includes.yml` shows `base_role: dev` + `additional_includes: - roles/dev/skill/domain-context`. An L3 event-reactions variant would follow the same pattern.

**Severity**: **CRITICAL**

**Recommended correction**: Add a section or at minimum an open question: "**Q5**: Do event reactions need L3 domain specialization? E.g., should dev/skill and dev/web have different reactions to `pr-merged`? If yes, add `roles/{role}/{variant}/event-reactions.md` sub-skills at L3, inheriting from L2 role reactions."

---

### Finding 3 — MAJOR: L3 "Behavioral Adaptation" proposal should reference actual L4 mechanism

**PRD text (lines 646–654):**
```
**L3 — Behavioral Adaptation (separate from SOUL.md)**

SOUL.md is personality only. Event-reaction behavioral tuning uses a SEPARATE mechanism:
- New script or config section for behavioral adaptation (NOT `soul_adaptation.py`)
- Categories: `event-sensitivity` (reactive ↔ proactive), `reaction-latency` (response urgency), `scan-priority` (which events trigger scans)
- Storage: `config.md` section or dedicated `behavior-adaptation.md` per role
- PM writes behavioral tuning entries that shape how agents interpret their L2 event reactions
```

**Architecture context**: `references/roles/LAYERS.md` lines 61–73 describe L4 as having two channels:
1. **Automatic**: Soul Shepherd writes `role-adaptations.md` → `soul_adaptation.py` renders into deployed SOUL.md's `## Project Adaptation` section
2. **Manual**: PM pushes project sub-skills to `references/sub-skills/project/*.md` → `compose.py deploy-all` includes them in every agent's CLAUDE.md

The PRD's "behavioral adaptation" concept is a good fit for L4's manual channel (project sub-skills) or a new L4 mechanism. Calling it "L3" misattributes it.

**Severity**: **MAJOR**

**Recommended correction**: Relocate to L4: "**L4 — Behavioral Tuning** (Project Sub-Skill mechanism)". Storage: either `references/sub-skills/project/behavior-tuning.md` (auto-included in all agents) or a per-role `references/sub-skills/project/{role}-behavior-tuning.md`. The PRD's statement "PM writes behavioral tuning entries" aligns perfectly with L4 manual sub-skills (LAYERS.md line 73: "PM owns this directory directly — no task filing, no QA verification needed").

---

### Finding 4 — MAJOR: "L4 — Human Overrides" is too narrow for what L4 actually is

**PRD text (lines 655–662):**
```
**L4 — Human Overrides (config.md)**

Human can override any L2/L3 reaction via config.md fields:
- `Muted Event Types`: comma-separated list...
- `Stop Grace Period`: seconds before forced kill...
- `Max Event Retries`: max re-emissions...
- `Scan Idle Timeout`: minutes of idle before scan-due...
- Event-reaction preferences in `human-profile.md`: escalation threshold...
```

**Architecture contradiction**: `references/roles/LAYERS.md` line 34 defines L4 as "Project-specific adaptations | soul-shepherd + human" covering `.squidsquad/<agent>/CLAUDE.md`, `SOUL.md`, and `role-adaptations.md`. Config.md overrides are ONE facet of L4, not L4's entire definition. Additionally, the PRD lists `human-profile.md` as L4 — but `human-profile.md` is actually `.squidsquad/vault/areas/human-profile.md`, which is a vault area file, not part of the L4 deployment layer. It's read by agents at runtime but isn't composed into CLAUDE.md or SOUL.md.

**Severity**: **MAJOR**

**Recommended correction**: Rename to "**L4 — Project Overrides & Adaptations**" and explicitly note that config.md fields are the *config override* channel, while L4 also includes the soul-shepherd adaptation channel (`role-adaptations.md`) and manual project sub-skills (`references/sub-skills/project/`). Remove the reference to `human-profile.md` as an L4 mechanism — it's a vault file, not a deployment artifact.

---

### Finding 5 — MAJOR: Includes.yml changes section mislabels event-driven-workflow as "L1 mechanism"

**PRD text (line 669):**
```
- KEEP: `common/event-driven-workflow` (L1 mechanism — how to watch inbox, close events)
```

**Analysis**: This is actually **correct** in the architectural L1 sense — `common/` sub-skills are auto-included by all roles and are universal. However, because the PRD introduced a conflicting "reaction layer" L1–L4 scheme at lines 330–334, a reader may be confused about which "L1" this refers to. The architectural L1 = base agent (roles/ root), and `common/` sub-skills are the L1 mechanism for shared behaviors. This line is fine IF the conflicting layer terminology at lines 330–334 is fixed first.

**Severity**: **MAJOR** (derived from Finding 1; resolves automatically if Finding 1 is addressed)

**Recommended correction**: Resolves when Finding 1 is fixed. Keep the label as-is once the primary layer terminology is corrected, since `common/` = universal = architectural L1 is correct.

---

### Finding 6 — MINOR: "L2" for role event-reactions is architecturally correct but muddied by PRD's parallel L-system

**PRD text (lines 638–644):**
```
**NEW L2 sub-skills: `roles/{role}/event-reactions.md`** (× 4 files)
```

**Analysis**: Placing role-specific event reactions at `references/sub-skills/roles/{role}/` IS architecturally L2. This mapping is correct. The problem is only that the PRD invents a "reaction-layer L3" that collides with architectural L3, making the "L2" label ambiguous. Fix Finding 1 and this resolves.

**Severity**: **MINOR** (derived; correct in isolation)

---

### Finding 7 — MINOR: "Phase 3: Template Migration" config gating section doesn't mention L3 includes.yml inheritance

**PRD text (lines 664–670):**
```
**Includes.yml changes (all roles):**

Each role's `includes.yml` changes:
- REMOVE: `common/event-reactions` (old flat L1 file)
- ADD: `roles/{role}/event-reactions` (new L2 role-specific file)
- KEEP: `common/event-driven-workflow` (L1 mechanism...)
```

**What's missing**: No mention of L3 `includes.yml` files (`references/roles/dev/skill/includes.yml`, etc.). These inherit from L2 via `base_role`, so if L2 adds `roles/dev/event-reactions`, L3 variants (dev/skill, dev/web) automatically inherit it. This is correct behavior but should be noted — the PRD should confirm that L3 variants DO inherit L2 event-reactions via the existing `base_role` mechanism, and optionally allow L3 overrides.

**Architecture reference**: `references/roles/dev/skill/includes.yml` lines 1–5 show `base_role: dev` + `additional_includes`.

**Severity**: **MINOR**

**Recommended correction**: Add a note: "L3 variant includes.yml files inherit L2 event-reactions automatically via `base_role`. No L3 changes needed unless a domain variant needs to override or extend its role's event reactions."

---

### Finding 8 — MINOR: PRD lines 493, 506 say "ABSORBED INTO HARNESS" / "eliminated" but then says "retained for backward compat"

**PRD text (lines 493–503):**
```
**cycle_pre.py** (references/scripts/cycle_pre.py):
- **ABSORBED INTO HARNESS** — per Locked Decision #3, cycle_pre.py is eliminated.
...
- **File disposition**: Retained in codebase for `event-driven: no` backward compat. Not called by agents when event-driven mode is active.
```

**Analysis**: The heading says "ABSORBED INTO HARNESS" and "eliminated" but the file is retained. The Locked Decision #3 concept (if it exists) may say "eliminated" but the PRD's own Phase 4 cleanup (line 827) says "Remove legacy sub-skills" — it doesn't say "remove cycle_pre.py." This is internally inconsistent: if the file is retained indefinitely for backward compat, it's not eliminated. If it's truly eliminated in Phase 4, the PRD should say when.

**Severity**: **MINOR** (implementation clarity, not architectural)

**Recommended correction**: Replace "eliminated" with "bypassed when event-driven mode active; retained for backward compat." Clarify whether Phase 4 removes it or keeps it permanently.

---

### Finding 9 — MINOR: Proposed event-driven-workflow.md path uses `common/` not `references/sub-skills/common/`

**PRD text (line 89):**
```
- `references/sub-skills/common/event-driven-workflow.md` — new sub-skill replacing cycle-runner.md
```

**Analysis**: This is correct — `references/sub-skills/common/` IS where common sub-skills live. But throughout the PRD the path is sometimes written as `common/event-driven-workflow.md` (lines 552, 562, 564) and sometimes as `references/sub-skills/common/event-driven-workflow.md` (line 89). In compose.py includes.yml, the short form `common/event-driven-workflow` is used — this is fine, as compose.py resolves relative to `references/sub-skills/`. Not an error, just noting inconsistency.

**Severity**: **MINOR** (documentation polish)

---

### Finding 10 — MINOR: No reference to architectural concept of "project sub-skills" for L4 behavioral rules

**PRD text (lines 655–662)** proposes config.md for L4 overrides but never references the existing L4 "project sub-skills" mechanism.

**Architecture reference**: `references/roles/LAYERS.md` lines 67–73:
```
### Manual: Project Sub-Skills (CLAUDE.md)
PM can push behavioral sub-skills to ALL agents without a dev cycle:
1. Write sub-skills to `references/sub-skills/project/*.md`
2. Run `python references/scripts/compose.py deploy-all`
3. Reboot affected agents
...
PM owns this directory directly — no task filing, no QA verification needed.
```

**Severity**: **MINOR**

**Recommended correction**: Add to L4 section: "Behavioral override sub-skills can also use the existing L4 project sub-skills mechanism (`references/sub-skills/project/`) for rules that need to be composed into CLAUDE.md rather than read at runtime from config.md."

---

## Summary Table

| # | PRD Lines | Claim | Actual Architecture | Severity |
|---|-----------|-------|---------------------|----------|
| 1 | 330–334 | L3 = Behavioral adaptation | L3 = Domain variant specialization (LAYERS.md:29–34) | **CRITICAL** |
| 2 | — | No L3 domain-variant event reactions | L3 exists and may need event reaction variants | **CRITICAL** |
| 3 | 646–654 | Behavioral adaptation is L3 | Should be L4 (project-specific) or cross-cutting | **MAJOR** |
| 4 | 655–662 | L4 = Human Overrides (config.md only) | L4 = broader: soul-shepherd + human + project sub-skills | **MAJOR** |
| 5 | 669 | event-driven-workflow labeled "L1 mechanism" | Correct architecturally but ambiguous given Finding 1 | **MAJOR** (derived) |
| 6 | 638–644 | Role event-reactions at L2 | Correct architecturally | **MINOR** (derived) |
| 7 | 664–670 | No L3 includes.yml inheritance note | L3 automatically inherits L2 includes | **MINOR** |
| 8 | 493, 506 | "Eliminated" but retained for backward compat | Internally inconsistent | **MINOR** |
| 9 | 89 vs 552 | Inconsistent path notation | Both resolve correctly | **MINOR** |
| 10 | 655–662 | No reference to L4 project sub-skills mechanism | Existing mechanism could host behavioral rules | **MINOR** |

## Open Questions

- **Q1**: Should event reactions have L3 domain specialization? E.g., should `dev/skill` and `dev/web` react differently to `pr-merged`? — **Why**: If yes, the PRD must add L3 event-reaction sub-skills. If no, the PRD should explicitly state that event reactions are domain-invariant (which seems unlikely — different domains have different concerns).
- **Q2**: Does the PRD's "behavioral adaptation" concept (event-sensitivity, reaction-latency, scan-priority) belong at L4 (project-specific) or as a new cross-cutting mechanism that spans roles? — **Why**: If project-specific, use L4 project sub-skills. If role-specific but project-tunable, it might need its own file per role at L4 (e.g., `.squidsquad/<role>/behavior-tuning.md`).

## Recommendation

**Feasible with caveats**. The event-driven architecture design is well-reasoned and the infrastructure analysis is thorough. The problem is strictly the L3/L4 labeling — a terminology collision with the canonical layered architecture that would cause implementation confusion. **Fix the "Reaction layer model (L1-L4)" section (lines 330–334) first** — rename to avoid collision with architectural L1-L4. Then relocate the "behavioral adaptation" concept to L4 (where project-specific tuning belongs). Add an explicit section or open question about whether L3 domain variants need event-reaction specialization. All other findings are minor and can be addressed during implementation.

## Vault Candidates

- **Type**: learning — **PRD layer terminology must match LAYERS.md exactly** — **Why**: This PRD audit found a complete redefinition of L3/L4. Future PRDs should include a "Layer Alignment" section that maps proposed behaviors to the canonical L1–L4. Avoids wasted implementation cycles.
- **Type**: pattern — **Cross-cutting behavioral tuning via L4 project sub-skills** — **Why**: The PRD's "behavioral adaptation" concept (event-sensitivity, reaction-latency, scan-priority) is a new cross-cutting concern. Capturing how to express it within the existing L4 project sub-skills mechanism would be reusable for future behavioral tuning needs.
- **Type**: decision — **Event reactions are L2 by default, opt-in L3 specialization** — **Why**: If confirmed, the pattern that role-specific event reactions live at L2 (`roles/{role}/event-reactions.md`) and domain variants inherit them by default (via `base_role`) but can override at L3 (`roles/{role}/{variant}/event-reactions.md`) is worth capturing as an architectural decision.