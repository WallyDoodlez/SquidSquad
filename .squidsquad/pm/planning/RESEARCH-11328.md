# RESEARCH-11328 — Phase 1: validate PRD against current docs

**Task**: #11328 (Doc-codify eager event-loop + per-event ack-cursor in AGENT-RUNTIME.md + sub-skills)
**Scope**: doc-only (AC1 + AC2 of the rescoped PRD). Runtime migration is split to #11329.
**Validation target**: `docs/AGENT-RUNTIME.md` + four sub-skill files named in AC2.
**Goal**: confirm every line/section reference in the PRD body is accurate; flag discrepancies before Phase 2 Discussion.

## §0. Branch-basis note (locked 2026-06-07)

**All line numbers in this research reference `origin/squidsquad/skill/compose-polish-session` HEAD**, not `origin/main`. The polish branch adds **§2.3 Inline mode** (16 lines, polish-branch lines 109-125) that has not yet merged to main; everything after shifts +16 on polish branch vs main. The PRD body's line refs (e.g., `§4.3 line 269`, `§7.1 pseudocode 800-815`, `§10.4 revision log`) were written against polish-branch state, so this research is internally consistent with the PRD and skill's editing target.

**Ordering decision (operator-locked 2026-06-07)**: Skill works #11328 on **a branch based off `compose-polish-session`** (not off main). Net effect: `#11144` polish + `#11328` doc-codify ship as one super-bundle when polish merges. This keeps line numbers correct throughout the work without forcing a -16 recompute against main.

PRD body's "Dependencies and ordering" section needs amendment to reflect this — current text says `"#11328 ships first → polish branch pulls main third"`, which contradicts the line-number basis. New ordering: **polish + #11328 ship together (one bundle) → #11329 ships second → no separate polish pull-down needed**.

---

## §1. Per-claim verdict table

### 1.1 AGENT-RUNTIME.md targets

| PRD claim | Section / line | Current state | Verdict | Notes |
|---|---|---|---|---|
| §4.2 catalog row `ack-cursor` framing change | line 266 | `\| **\`ack-cursor\`** \| agent → harness \| Agent has received a delivered signal; advances harness cursor \| ...` | ✓ **Accurate** | Receipt framing is exactly the wording PRD targets. One-line edit. |
| `ack-cursor`/`ack-stop` "sub-types of receipt confirmation" sentence | PRD says **§4.3 line 269** | Actual line 269 is in **§4.2** (not §4.3 — §4.3 starts at line 302). Wording exact match: `\`ack-cursor\` and \`ack-stop\` are sub-types of one concept (receipt confirmation)` | ⚠️ **Section-attribution slip** | Content is correct; PRD's section pointer is off by one subsection. Skill should target §4.2 line 269, not §4.3. |
| §4.3 Cursor model needs semantic reframe (lead with work-completed) | starts line 377 | Section already documents harness-owned cursor + `.event-state.json` + at-least-once delivery. Closing paragraph (line 414-416) already says "cursor is harness-owned, persisted in `.event-state.json`. The agent never writes the cursor directly…" + "At-least-once delivery: cursor advances only after a successful ack." | ✓ **Reframe valid but scope smaller than implied** | The mechanical model is already canonical. The change is *framing order*: lead with the "cursor IS work-completed indicator" semantic, then the mechanical paragraph. ~1-2 paragraph edit, not a section rewrite. |
| §7.1 pseudocode (batched ack model) | lines 800-815 | Exact match: `for event in events: ... POST /events ack-cursor {event_id: last_tended, role}` (single ack at end of walk) | ✓ **Accurate** | Replace with D2's eager loop. |
| §7.1 sequence diagram | lines 819-851 | Mermaid sequence diagram shows `loop for each event` → single `A->>H: POST /events {type:ack-cursor, event_id:last_tended, role}` after the loop | ✓ **Accurate** | Redraw per D2 (per-event ack inside the branch; drain-to-empty outer loop; improvement-subloop branch). |
| §7.1 paragraph after pseudocode | line 817 | Exact match: `"Pre/post-cycle wraps EACH cared event individually. ... The batched ack at the end signals 'I've handled or skipped everything up to last_tended; advance my cursor.'"` | ✓ **Accurate** | Replace per D2. |
| §7.5 Nudge handling while busy — 3-step procedure | lines 1035-1057 | Exact match: 3-step procedure incl. step 2 `"Emits ack-cursor for current event"` | ✓ **Accurate** | Simplify per D3. |
| §7.5 "Why no flag is needed" sub-section | lines 1043-1047 | Exact match: 3 bullets (cursor canonicality, event_poll self-healing, monotonic-forward cursor) | ✓ **Accurate** | Trim per D3 — D2 makes the rationale even simpler. |
| §7.5 crash-safety table | lines 1049-1055 | Exact match: 3 crash-point rows (mid-current-event, between-ack-and-walk, multiple-nudges-pre-walk) | ✓ **Accurate** | "Between ack and walk" row needs replacement (no longer a meaningful state in the eager model) — PRD calls this out correctly. |
| `D2/D3/D4 added to §9 revision log` | PRD says **§9** | §9 is actually "Open questions" (line 1174). Revision log is at **§10.4** (line 1229). | ⚠️ **Section number wrong** | Target should be **§10.4 Revision log**, not §9. Skill should add a rev-14-style multi-bullet entry. Q5 + Q7 in §9 may also need cross-references but are already locked. |

### 1.2 Sub-skill targets

| File | PRD claim | Current state (verified) | Verdict |
|---|---|---|---|
| `references/sub-skills/common-events/cursor-management.md` | Rewrite — cursor as harness-owned (.event-state.json); agent only reads via `GET /events/cursor`, never writes directly; eviction-gap recovery via `ack-cursor(current_head)` after forge-read | Line 8: `"Your event cursor is the last event id you have processed. It lives in .squidsquad/<role>/working-state.md"`; Line 14: `"event_poll.py reads and advances this cursor"`; Lines 18-24 describe `.tmp`+`mv` atomic write protocol; Line 31 describes eviction-gap recovery as "advance the cursor to that oldest available id" — generic advancement, **no `ack-cursor` mechanism named**. `grep ack-cursor` on this file returns **zero matches**. (The `ack-cursor(current_head)` recovery phrasing the PRD borrows is in AGENT-RUNTIME.md §4.3 line 375 — not in the sub-skill.) | ✓ **Rewrite confirmed needed** — entire file written around legacy model; `ack-cursor` POST protocol is entirely absent and must be **introduced from scratch**, not just retargeted. |
| `references/sub-skills/common-events/event-mode-contract.md` | Update §97-style notes; remove "event_poll.py is the sole writer of the cursor line" language; rework `working-state.md` ownership discipline section | Line 19: cursor cited as `working-state.md` field; Line 30-32: cursor advancement steps reference working-state; Line 55: `"event_poll.py persists the cursor to working-state.md"`; Line 86: stop-handling preserves cursor in working-state; Line 96: cursor advance per-event atomic via `.tmp`+`mv`; **Line 97**: exact phrase `"event_poll.py is the sole writer of the cursor line"` confirmed present | ✓ **Multiple touchpoints** — lines 19, 30, 32, 55, 86, 96, 97 (seven distinct lines) need rewording. The "sole writer" sentence at 97 needs deletion; ownership-discipline paragraph needs rewrite. `grep ack-cursor` on this file returns **zero matches** — protocol must be introduced. |
| `references/sub-skills/common-events/event-driven-workflow.md` | "Update the cursor mention on line ~23" | Line 8: `"event_poll.py advance your cursor automatically"` (sentence 1); Line 13: link to `[[cursor-management]]`; **Line 23**: `"Cursor — event_poll.py persists it to working-state.md automatically"` (confirmed match) | ✓ **Accurate** — line 23 needs rewording; lines 8 + 13 too (PRD missed those). `grep ack-cursor` returns zero matches — protocol must be introduced. |
| `references/sub-skills/common/agent-lifecycle.md` | "Verify for any cursor mentions that need updating" | `grep -n "cursor"` returns no matches. | ✓ **Clean** — no edits needed. |

### 1.3 PRD references to runtime code (now scoped to #11329 — verified for completeness)

| Claim | Status | Notes |
|---|---|---|
| `event_poll.py:299` pending-migration comment | ✓ **Verified present** | Lines 298-300: `"When #9873-B lands, this whole branch is replaced by an ack-cursor emit to the harness. Until then this ordering closes the loss window."` Per-event flow at line 301 (`print(json.dumps(event), flush=True)`) followed by `_write_cursor_atomic(role, str(event_id))` at 302. Runtime is per-event already on the read side — the migration is in WHERE the cursor is written. |
| working-state.md `- **Last Processed Event ID**:` schema line | (not directly grep'd in this research; #11329 will cover) | Out of scope for #11328. |

---

## §2. Discrepancies vs the PRD body

Three concrete corrections needed before skill begins editing:

1. **§4.2 vs §4.3 attribution** (PRD line: `§4.3 line 269`). The `"sub-types of receipt confirmation"` sentence is in **§4.2**, not §4.3. The line number is correct; the section pointer is off-by-one-subsection. Low-risk slip but worth fixing in the PRD body so the skill doesn't open §4.3 looking for it.

2. **Revision log location** (PRD line: `D2/D3/D4 design decisions added to §9 revision log`). §9 is "Open questions" (locked Q1-Q13). The Revision log is **§10.4** (line 1229). Skill should add a new entry there following the rev-13/rev-14 multi-bullet style.

3. **Sub-skill scope under-counted in event-driven-workflow.md**. PRD said "update the cursor mention on line ~23." There are actually **three** cursor mentions: lines 8, 13, 23. Lines 8 + 13 also describe the legacy model and should be updated together. Not a defect — just narrower than the actual surface.

4. **The `ack-cursor` POST protocol is entirely missing from all three sub-skill files** (grep returns zero matches across `cursor-management.md`, `event-mode-contract.md`, `event-driven-workflow.md`). AC2 is therefore **introduce + rewrite**, not just "retarget storage." The sub-skill set currently teaches the legacy `event_poll.py`-writes-`working-state.md` model with `.tmp`+`mv` atomicity; the canonical `POST /events {type: ack-cursor, event_id, role}` mechanism does not exist anywhere in the agent-facing instruction set. Concrete consequence: `cursor-management.md` needs a new section describing the POST protocol as the canonical advance mechanism; `event-mode-contract.md` lines 55, 96-97 need the ownership discipline rewritten around harness-owned cursor (agent POSTs ack, harness writes `.event-state.json`); `event-driven-workflow.md` line 23 needs the cursor bullet updated to reference the POST protocol rather than `event_poll.py` persisting to `working-state.md`. *(Discovered by DS audit of this research — original draft underweighted the surface.)*

---

## §3. Net-new observations (not in the PRD body)

### 3.1 The canonical doc is closer to D1/D2 than the PRD implies

- **§4.3 Cursor model already documents the canonical model** (harness-owned, `.event-state.json`, at-least-once). The change for AC1 is *framing order*, not content addition. The "cursor IS work-completed indicator" semantic can lead the section; the existing mechanical paragraph follows verbatim.
- **§5 State persistence map row for `working-state.md`** already explicitly says `"Does NOT carry an event queue (harness deque + cursor own that) AND does NOT carry a nudge flag (per §7.5...)"`. The canonical persistence map is already aligned with D1.
- **The drift lives in the sub-skills, not in the canonical arch doc.** AGENT-RUNTIME §4.3 + §5 + Glossary line 1208 (`"Cursor: per-alias harness-owned pointer to 'events tended through here.'"`) already match D1. The agent-facing sub-skill set is what currently teaches the legacy `working-state.md` model.

### 3.2 D3 is already locked in §9 Q7

- **§9 Q7** locks: `"Queue-while-busy = Context-only; no working-state.md flag"`. This is exactly D3. The PRD's §7.5 simplification is bringing the *prose* into line with an *already-locked* arch decision. Worth citing Q7 in the §7.5 rewrite to ground the change.

### 3.3 §4.3 Cursor model sequence diagram is in scope (PRD doesn't list it)

- Lines 387-412 contain a mermaid sequence diagram showing `POST /events {ack-cursor, event_id=g7}` after the cycle's "creative work" finishes (single ack at end). This diagram conflicts with D2's per-event ack semantics. PRD's AC1 should add this diagram to the §7.1 redraw list, OR explicitly note it stays at the §4.3 narrative level (cursor advances per-ack) and only §7.1's diagram becomes the per-event reference.
- **Recommended**: simplify the §4.3 diagram to show the mechanical model without binding it to "single ack per cycle" (e.g., reframe as "cursor advance via ack" generic — no cycle-boundary commitment), leaving §7.1's diagram as the per-event source of truth.
- **Additional ack-cursor sites flagged by DS audit**:
  - **§7.6 improvement-subloop flowchart (line 1067)**: start node reads `Start(["nudge processed, ack-cursor emitted"])`. Under D2 the ack happens per-event *inside* the walk — the subloop entry condition should reframe to `"per-event ack just emitted; GET returned empty"` (or similar wording that doesn't imply a single batched ack at the nudge boundary). **In scope for AC1.**
  - **§7.3 work-handoff sequence diagram (line 933)**: shows `VC->>H: POST /events {type:ack-cursor, event_id, role:verifier}` — narratively per-event (single event being acked after work on it), so already D2-compatible. **Reviewed-clean; no edit needed.**

### 3.4 §7.6 Improvement subloop has its own state diagram

- §7.6 starts at line 1059 with its own flowchart (lines 1065-1079) showing "GET returns empty → throttle → subloop / idle". D2 says the subloop becomes "a branch of the main loop, not a separate concern." Two options:
  - **(a) Fold the §7.6 diagram into the §7.1 sequence diagram** as a branch after each per-event ack — keeps the eager-loop narrative compact but doubles §7.1's diagram complexity.
  - **(b) Keep §7.6 as its own section** but rewrite the §7.6 paragraph to lead with "this is what happens when the main loop's drain-to-empty branch fires" and back-reference §7.1.
- **Recommended**: (b). The throttle mechanism, role-class-specific work table, and `.subloop-last-run` discipline all need a home; merging into §7.1 hides them. §7.1 mentions the branch; §7.6 stays as the detail page with a forward-pointer from §7.1.

### 3.5 §10.1 Glossary entry for "Cursor"

- Line 1208: `"Cursor: per-alias harness-owned pointer to 'events tended through here.'"` — already aligned with D1. No edit needed; possibly add a one-line cross-reference to the new §4.3 lead.

### 3.6 §10.1 Glossary entry for "Improvement subloop"

- Line 1211: `"Improvement subloop: time-throttled self-care work the agent runs when its queue is empty. Applies in both modes — quiet cycles in loop mode (§6.4) and drained-queue detection in event mode (§7.6)."` — already aligned with the "branch of main loop" framing.

### 3.7 §4.3 closing paragraph line 414 is the natural insertion point for D1's lead

- The paragraph at line 414 already says the right thing mechanically but doesn't lead with the work-completed semantic. Recommended edit: prepend two sentences establishing the semantic (per D1), then the existing mechanical paragraph follows unchanged.

---

## §4. Suggested PRD amendments

Before Phase 2 Discussion, the PRD body should be corrected for the three discrepancies in §2:

| Edit | From | To |
|---|---|---|
| AC1 bullet 5 | "§4.2 signal catalog row for ack-cursor refined" (correct) + (missing) | Add a bullet: "**§4.2 line 269**: `ack-cursor`/`ack-stop` sub-types-of-receipt sentence reframed per D1 + D4 (separate state machines, not sub-types)" |
| AC1 bullet 6 | "D2/D3/D4 design decisions added to §9 revision log" | "D2/D3/D4 design decisions added to **§10.4 revision log** (not §9; §9 is locked Open Questions)" |
| AC2 bullet 3 | "`event-driven-workflow.md`: update the cursor mention on line ~23" | "`event-driven-workflow.md`: update cursor mentions on lines 8, 13, 23 (sentence 1 + sub-skill link line + bullet)" |

Plus three additive bullets to AC1 covering the net-new observations:

| Add to AC1 | Reason |
|---|---|
| "§4.3 mermaid sequence diagram (lines 387-412): reframe to per-ack rather than per-cycle, OR explicitly punt to §7.1's diagram as the per-event source of truth" | §3.3 above — current diagram contradicts D2 |
| "§7.6 flowchart (lines 1065-1079): start node `'nudge processed, ack-cursor emitted'` reworded to reflect D2's per-event-inside-the-walk ack timing (e.g., `'per-event ack just emitted; GET returned empty'`)" | §3.3 above — DS-flagged; single-line edit but semantically load-bearing |
| "§7.6 paragraph rewritten to lead with 'this is the drained-queue branch of the §7.1 main loop' + forward-pointer from §7.1; §7.6 internal mechanics (throttle, role-class subloop table, `.subloop-last-run`) stay put" | §3.4 above — preserves the detail without bloating §7.1 |

Optional (citation-strengthening, not blocking):
- "§7.5 rewrite cites §9 Q7 to ground the no-flag policy"
- "§10.1 Glossary 'Cursor' entry receives an optional cross-ref to the new §4.3 lead"

---

## §5. Open questions for Phase 2 Discussion

1. **Diagram strategy for §4.3 cursor-model mermaid**: redraw to per-ack semantic vs. simplify to mechanical-only (D2 detail lives in §7.1's diagram). Either works; preferred not to maintain two per-event diagrams.

2. **§7.6 placement**: keep as own section with main-loop back-reference (recommended in §3.4), or fold into §7.1's sequence diagram. The "branch of main loop" framing fits both — Phase 2 should pick one.

3. **§7.5 crash-safety table**: PRD says update the "between ack and walk" row. Concrete replacement to land: `"Crash after ack-cursor but before checking for next event: cursor sits at the just-acked event_id; on restart the agent re-enters the eager loop; first iteration of `GET /events/for/<alias>?since=<cursor>` returns any events past the acked id, including events that arrived during the crash window. No state loss."` — propose verbatim for Phase 2 to ratify or amend.

4. **AGENT-RUNTIME §1-§3 sweep needed?** §1 Goal & scope and §2 Two triggering modes describe the runtime in cursor terms; need to confirm no consequential drift there. (Quick read of §2.3 inline mode addition from yesterday — DS-reviewed — shows no cursor wording conflict.)

5. **DS audit cadence**: AC3 says DS per-AC. AC1 is large (multiple §§ touched). Sub-AC boundaries to use:
   - **AC1.1**: §4.2 + §4.3 changes (semantic reframe, signal catalog row, sub-type sentence)
   - **AC1.2**: §7.1 pseudocode + sequence diagram (load-bearing — non-negotiable DS)
   - **AC1.3**: §7.5 simplification + crash-safety row replacement
   - **AC1.4**: §7.6 lead-paragraph rewrite + §10.4 revision log entry
   - **AC2**: sub-skill sweep (4 files; one DS pass)

---

## §6. Verdict

**PRD is structurally sound**; 4 PRD corrections (3 line/section-attribution + 1 missing-protocol scope note) + 3 additive AC1 bullets (§4.3 diagram, §7.6 flowchart node, §7.6 framing) needed before skill starts editing. Phase 2 Discussion should ratify the §3.3 / §3.4 / §3.7 / §5.3 framing choices, then planning can begin.

**No re-scope needed.** AC1 (AGENT-RUNTIME) + AC2 (sub-skills) + AC3 (DS audit) carry the right work. The body's scope statement (doc-only) is correctly aligned with operator clarification. **AC2's effort is larger than the PRD wording implies** — the sub-skill set needs the `ack-cursor` POST protocol *introduced*, not just retargeted.

---

## §8. DS audit trail (Phase 1 self-review)

DeepSeek code-review pass over the initial draft of this artifact surfaced 4 findings:

| # | Severity | Issue | Resolution |
|---|---|---|---|
| 1 | error | §1.2 falsely claimed `cursor-management.md:31` references `ack-cursor(current_head)` — conflated with AGENT-RUNTIME.md §4.3 line 375 | Corrected §1.2 cursor-management row; added explicit "zero matches" finding to §2 discrepancy #4 |
| 2 | warning | Missed surface — `ack-cursor` POST protocol entirely absent from all 3 sub-skill files; scope larger than acknowledged | Added §2 discrepancy #4 + per-file "zero matches" notes in §1.2 |
| 3 | warning | §7.6 flowchart line 1067 ack-cursor start node not flagged for D2 review; §7.3 line 933 not noted as reviewed-clean | Added both to §3.3 + new AC1 bullet in §4 |
| 4 | warning | §1.2 event-mode-contract.md row said "6 lines" but listed 7 line numbers (19, 30, 32, 55, 86, 96, 97) | Corrected to "seven distinct lines" + explicit enumeration |

DS audit artifact: `.squidsquad/pm/planning/DS-AUDIT-11328-research.md`.

All §1.1 AGENT-RUNTIME.md line/section references and the §2 discrepancies are DS-verified as accurate.

---

## §7. Source material referenced

- `docs/AGENT-RUNTIME.md` — lines 11-1272 (full file inspected at section, line, and content level for §§4.2, 4.3, 5, 7.1, 7.5, 7.6, 9, 10.1, 10.4)
- `references/sub-skills/common-events/cursor-management.md` — full grep + lines 8, 14, 18, 20, 24, 28, 30-33, 37, 39
- `references/sub-skills/common-events/event-mode-contract.md` — full grep + lines 19, 30, 32, 55, 86, 96, 97
- `references/sub-skills/common-events/event-driven-workflow.md` — full grep + lines 8, 13, 23
- `references/sub-skills/common/agent-lifecycle.md` — full grep (clean)
- `references/scripts/event_poll.py` — lines 285-315 (verification of pending-migration comment for #11329 cross-check)
- #11328 PRD body @ rescoped version
- #11329 PRD body (companion runtime task — confirmed clean separation of scope)
