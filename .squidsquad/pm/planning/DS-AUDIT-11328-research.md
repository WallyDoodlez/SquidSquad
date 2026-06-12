All evidence gathered. Here are my findings:

---

## Findings

### Finding 1

- **File**: `.squidsquad/pm/planning/RESEARCH-11328.md`
- **Line**: §1.2 cursor-management.md row ("Line 31 already references `ack-cursor(current_head)`...")
- **Severity**: **error**
- **Issue**: The research claims `cursor-management.md` line 31 "already references `ack-cursor(current_head)` for eviction-gap recovery." This is factually false. Line 31 of `cursor-management.md` reads: `**Eviction gap.** Your cursor predates the oldest retained event in the harness deque... advance the cursor to that oldest available id; proceed to a forge-read for current state. Do NOT crash.` — there is **zero** mention of `ack-cursor` anywhere in this file. A grep for `ack` across the entire file returns only a single match: the word "acks" on line 33 in a historical note about a dropped gap scenario (`"multi-process pipeline with acks that could drop intermediate events"`), which is not a protocol reference.
- **Evidence**: 
  - `cursor-management.md` line 31 content verified above: the eviction-gap bullet says "advance the cursor" but gives no mechanism.
  - Grep for `ack-cursor` across all three `common-events/` sub-skill files returns **zero matches**.
  - The research appears to have confused AGENT-RUNTIME.md line 375 (`"Recovery: agent reads forge for current state, emits ack-cursor(current_head), re-enters idle."`) with the sub-skill file's content.
- **Suggested fix**: Strike the "already references `ack-cursor(current_head)`" claim from the §1.2 cursor-management.md verdict row. Replace with a direct statement: "File has zero `ack-cursor` references; eviction-gap recovery describes cursor advancement generically with no mechanism specified. The entire file needs a rewrite that introduces the `POST /events ack-cursor` protocol." Add an explicit note to §2 (or §4) flagging this as a missed surface: the `ack-cursor` POST protocol is completely absent from all three sub-skill files, not merely anchored to the wrong storage.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/RESEARCH-11328.md`
- **Line**: §1.2 / §2 (no explicit flag)
- **Severity**: **warning**
- **Issue**: **Missed surface — the `ack-cursor` protocol is entirely absent from all three sub-skill files.** A grep for `ack-cursor` across `references/sub-skills/common-events/cursor-management.md`, `event-mode-contract.md`, and `event-driven-workflow.md` returns zero matches. These files describe cursor advancement exclusively through the legacy `event_poll.py`-writes-to-`working-state.md` model with `.tmp`+`mv` atomic writes, never mentioning `POST /events {type: ack-cursor}`. While the research correctly identifies these files as needing rewrites (`"Rewrite confirmed needed — entire file written around legacy model"`), it does not explicitly surface the scope of what's missing: the `ack-cursor` protocol — the core mechanism D2 makes per-event — literally does not exist in the agent-facing instruction set. The false "line 31 already references `ack-cursor`" claim (Finding 1) compounds this by giving a misleading impression of partial alignment where none exists.
- **Evidence**: Grep for `ack-cursor` on `references/sub-skills/common-events/` returns no matches (`No matches found`). The three files collectively describe cursor advancement 15+ times, all in the legacy `working-state.md`-write model.
- **Suggested fix**: Add to RESEARCH §4 (Suggested PRD amendments) or a new §2 discrepancy: "AC2 scope is larger than a wording refresh — the `ack-cursor` POST protocol must be introduced into the sub-skill files from scratch. Currently zero of the three sub-skill files reference it. Specifically: `cursor-management.md` needs a new section describing `POST /events {type: ack-cursor, event_id, role}` as the canonical cursor-advance mechanism; `event-mode-contract.md` lines 55, 96-97 need the ownership discipline rewritten to account for harness-owned cursor (agent POSTs ack, harness writes `.event-state.json`); `event-driven-workflow.md` line 23 needs the cursor bullet updated to reference `ack-cursor` POST rather than `event_poll.py` persisting to `working-state.md`."

---

### Finding 3

- **File**: `.squidsquad/pm/planning/RESEARCH-11328.md`
- **Line**: §3.3 (lines 387-412 discussion)
- **Severity**: **warning**
- **Issue**: **Incomplete coverage of diagrams containing `ack-cursor` semantics needing D2 review.** §3.3 correctly flags the §4.3 mermaid diagram (lines 387-412) as showing a single `POST /events {ack-cursor, event_id=g7}` at cycle end — conflicting with D2's per-event ack. However, the research does not flag that the §7.6 improvement-subloop diagram (line 1067) also contains an `ack-cursor` reference (`Start(["nudge processed, ack-cursor emitted"])`) whose semantics shift under D2: in the D2 eager model, the ack happens per-event *inside* the walk, so the subloop's start node should reflect "per-event ack just completed, queue drained" rather than "nudge processed, ack-cursor emitted" (which implies a single batched ack at nudge boundary). Additionally, the §7.3 work-handoff sequence diagram (line 933) shows `POST /events {type:ack-cursor, event_id, role:verifier}` — this one is already per-event in context (it's a single event being acked after work completion on it), so it likely needs no change, but the research should at least note it as reviewed-and-clean.
- **Evidence**: 
  - Line 1067: `Start(["nudge processed, ack-cursor emitted"])` — this start node implies a single ack per nudge-walk, contradicting D2's per-event ack inside the walk.
  - Line 933: `VC->>H: POST /events {type:ack-cursor, event_id, role:verifier}` — per-event in narrative context, probably D2-clean.
- **Suggested fix**: Add to RESEARCH §3.3 or §3.4: "§7.6 diagram line 1067 start node (`'nudge processed, ack-cursor emitted'`) needs D2-aware reframing — under D2 the ack happens per-event inside the walk, so the subloop entry condition becomes 'per-event ack just emitted, GET returned empty' rather than 'nudge processed, single batch ack emitted.' §7.3 line 933 ack-cursor is per-event in narrative context and likely D2-clean; flag as reviewed."

---

### Finding 4

- **File**: `.squidsquad/pm/planning/RESEARCH-11328.md`
- **Line**: §1.2 event-mode-contract.md row
- **Severity**: **warning**
- **Issue**: **Line count understated — at least 7 lines need rewording, not 6.** The research lists "6 lines at minimum need rewording (19, 30, 32, 55, 86, 96, 97)" — that's 7 line numbers, not 6. While this is a trivial arithmetic error, it feeds into the broader pattern of the research undercounting the sub-skill surface (see also Finding 2). Additionally, line 30's cursor mention is in the prose "Skim events from cursor forward" which the research correctly counts but the list is misnumbered.
- **Evidence**: Count of line numbers in parentheses: 19, 30, 32, 55, 86, 96, 97 = 7 distinct lines.
- **Suggested fix**: Change "6 lines" to "7 lines" or list them without a count: "lines 19, 30, 32, 55, 86, 96, and 97 need rewording."

---

### Findings Summary

| # | Severity | Issue |
|---|----------|-------|
| 1 | **error** | §1.2 falsely claims `cursor-management.md` line 31 references `ack-cursor(current_head)` — zero `ack-cursor` references exist in any sub-skill file |
| 2 | **warning** | Missed surface: `ack-cursor` protocol entirely absent from all three sub-skill files; scope larger than acknowledged |
| 3 | **warning** | §7.6 diagram's `ack-cursor` start node (line 1067) not flagged for D2 review; §7.3 line 933 not noted as reviewed-and-clean |
| 4 | **warning** | §1.2 event-mode-contract.md row says "6 lines" but lists 7 line numbers (19, 30, 32, 55, 86, 96, 97) |

### What the Research Got Right

All §1.1 line/section references to AGENT-RUNTIME.md (§4.2 catalog row, §4.3 cursor model, §7.1 pseudocode/diagram/paragraph, §7.5 Nudge handling, §7.5 crash-safety table, §9 location vs §10.4 revision log) are **verified accurate**. The three §2 discrepancies (section-attribution slip, revision-log location, undercounted event-driven-workflow.md lines) are **real and correctly identified**. The net-new observations in §3.1 (§5 persistence map alignment), §3.2 (§9 Q7 lock), §3.5 (Glossary Cursor entry), §3.6 (Glossary Improvement subloop entry), and §3.7 (line 414 insertion point) are **correctly grounded**. The §3.3 (§4.3 diagram conflict) and §3.4 (§7.6 placement) observations are valid.