# CONTEXT-11328 — Phase 2: Discussion locks for doc-codify

**Task**: #11328 (Doc-codify eager event-loop + per-event ack-cursor in AGENT-RUNTIME.md + sub-skills)
**Phase 1 artifact**: `.squidsquad/pm/planning/RESEARCH-11328.md`
**Locked by**: operator (Wallace) 2026-06-07
**Line-number basis**: all refs vs `origin/squidsquad/skill/compose-polish-session` HEAD

---

## §0. Branching strategy

- Skill works #11328 **on a branch off `compose-polish-session`** (not main). PRD line refs are polish-branch HEAD.
- `#11144` polish + `#11328` doc-codify ship as **one super-bundle** when polish merges to main.
- `#11329` (runtime migration) ships **second** — after the super-bundle lands.

---

## §1. Discussion locks

### D-Lock 1 — §4.3 cursor-model diagram strategy

**Decision**: Simplify §4.3 mermaid sequence diagram (polish-branch lines 387-412) to show the **generic ack-advance mechanism** only — agent POSTs ack-cursor, harness writes `.event-state.json`, cursor advances — **no cycle-boundary commitment**.

**Why**: §4.3 stays at "how cursor advance works mechanically" abstraction; §7.1 is the canonical per-event-loop source of truth. Avoids maintaining two per-event diagrams that can drift.

**How to apply**: Strip the "creative work" + "alt success / else crash mid-cycle" branches from the existing diagram. Replace with a minimal sequence: `Agent → Harness: POST ack-cursor(event_id) → Harness: write .event-state.json → Harness → Agent: 200 OK`. The "harness-owned + at-least-once" semantic carries over to the narrative paragraph (line 414).

### D-Lock 2 — §7.6 Improvement subloop placement

**Decision**: Keep §7.6 as its own section. Rewrite the lead paragraph to frame the subloop as **"the drained-queue branch of the §7.1 main loop"**. §7.1's sequence diagram adds a branch pointing to §7.6 for detail.

**Why**: §7.6's throttle paragraph, role-class subloop list (pm/verifier/worker/dm), and `.subloop-last-run` discipline need a home — folding them into §7.1 would bloat the main-loop diagram and prose. Preserves §7.1's compactness while honoring D2's "branch of main loop" framing.

**How to apply**:
- §7.6 lead paragraph: replace `"In loop mode, agents run improvement scans on quiet cycles. In event mode there are no cycles..."` with a one-paragraph framing that names the subloop as the eager loop's drained-queue branch and references §7.1.
- §7.1 sequence diagram: add a branch from the "drained" state pointing to §7.6 ("→ see §7.6 for throttle + role-class detail").
- §7.6 flowchart (lines 1065-1079): start node `Start(["nudge processed, ack-cursor emitted"])` reworded to D2-aware framing (e.g., `Start(["per-event ack just emitted; GET returned empty"])`).

### D-Lock 3 — §7.5 crash-safety row replacement

**Decision**: Replace the `"Between ack and walk"` row with the **per-event ack to next-event-check** framing.

**Why**: The "between ack and walk" state doesn't exist in the eager model — each loop iteration is process → ack → check-next, atomically. The new framing captures the actual remaining crash scenario.

**How to apply**: Replace row 2 of the §7.5 crash-safety table with:

```
| Crash after ack-cursor emitted, before next iteration's GET fires | Cursor sits at the just-acked event_id; on restart the agent re-enters the eager loop. The first iteration's GET /events/for/<alias>?since=<cursor> returns any events past the acked id, including events that arrived during the crash window. No state loss. |
```

The other two rows (`"Mid-current-event"`, `"Multiple nudges arrived..."`) stay — they're still valid scenarios under D2.

### D-Lock 4 — §1-§3 sweep extent

**Decision**: **Light cross-ref only**. No content edits to §1-§3 cursor mentions. Add a one-line forward-reference in §2 (or §3.1) pointing to §4.3 for cursor semantics.

**Why**: §1-§3 cursor mentions are purely mechanical (where cursor lives, when GET uses it, what fallback does). None claim "receipt" or batched-ack semantics. They're D1/D2-compatible as written. Repeating the semantic shift here would dilute its signal.

**How to apply**: Add one sentence at the end of §2 (Two triggering modes) overview prose, or at the §3.1 EAD diagram caption: `"Cursor semantics — what it represents and when it advances — are defined in §4.3."` Skill picks the natural insertion point.

### D-Lock 5 — DS audit sub-AC boundaries

**Decision**: **5 DS passes** for #11328, granular boundaries.

| Sub-AC | Surface | Files |
|---|---|---|
| **AC1.1** | §4.2 catalog row + line 269 sub-type sentence + §4.3 cursor model reframe (incl. simplified diagram per D-Lock 1) | `docs/AGENT-RUNTIME.md` |
| **AC1.2** | §7.1 pseudocode + sequence diagram (D2 eager loop — **load-bearing, DS non-negotiable**) | `docs/AGENT-RUNTIME.md` |
| **AC1.3** | §7.5 simplification + crash-safety row replacement (per D-Lock 3) + cite §9 Q7 | `docs/AGENT-RUNTIME.md` |
| **AC1.4** | §7.6 framing rewrite (per D-Lock 2) + flowchart node fix + §1-§3 cross-ref (per D-Lock 4) + §10.4 revision log entry | `docs/AGENT-RUNTIME.md` |
| **AC2** | 4 sub-skill files: `cursor-management.md`, `event-mode-contract.md`, `event-driven-workflow.md`, `agent-lifecycle.md` (verify clean) — **introduce ack-cursor POST protocol**, not just retarget | `references/sub-skills/common-events/*.md`, `references/sub-skills/common/agent-lifecycle.md` |

Iteration loop: edit → `model_router.py route --task-type code-review` → fix findings → re-audit → ship sub-AC when 0-BLOCK → advance to next sub-AC. Each sub-AC commits separately so DS audits land on coherent diffs.

---

## §2. PRD body corrections (folded from RESEARCH-11328 §2 + §4)

These need to land in #11328's body before skill begins editing:

| Where | From | To |
|---|---|---|
| AC1 bullet | "§4.3 line 269: sub-type-of-receipt sentence" | "§4.2 line 269: sub-type-of-receipt sentence" |
| AC1 bullet | "D2/D3/D4 added to §9 revision log" | "D2/D3/D4 added to §10.4 revision log" |
| AC2 bullet (event-driven-workflow.md) | "line ~23" | "lines 8, 13, 23" |
| AC2 scope statement | implied: retarget storage | explicit: **introduce** the `POST /events ack-cursor` protocol (zero matches in all 3 sub-skill files today) |

PM will fold these into the PRD body alongside the D-Lock 1-5 editing guidance.

---

## §3. Quality gates

- **DS R1 verdict**: research artifact validated (1 error + 3 warnings, all fixed inline). Line refs verified accurate on polish-branch HEAD.
- **Operator confirmation**: all 5 Discussion locks confirmed via single-question AskUserQuestion flow 2026-06-07.
- **Ready for Phase 3 (Planning)**: skill plans the per-sub-AC edit order + commit cadence on the new branch off `compose-polish-session`.

---

## §4. Source material

- `.squidsquad/pm/planning/RESEARCH-11328.md` — Phase 1 research
- `.squidsquad/pm/planning/DS-AUDIT-11328-research.md` — DS R1 audit of Phase 1
- `docs/AGENT-RUNTIME.md` @ `origin/squidsquad/skill/compose-polish-session` HEAD
- `references/sub-skills/common-events/*.md` @ polish-branch HEAD
- #11328 PRD body (rescoped + polish-branch-basis-noted)
- Operator confirmations: D-Lock 1 (simplify §4.3 diagram), D-Lock 2 (keep §7.6 + back-ref), D-Lock 3 (per-event ack to next-event-check), D-Lock 4 (light cross-ref only), D-Lock 5 (5 DS boundaries)
