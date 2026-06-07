Now let me systematically verify each AC requirement against the document.

---

### AC Check (1): §7.6 lead paragraph framing

**Line 1066**: `"The improvement subloop is the **drained-queue branch of the §7.1 main loop**."` ✓

**Throttle** (line 1089): `".squidsquad/<alias>/.subloop-last-run` records the last-fire timestamp"` — unchanged discipline. ✓

**Role-class catalog** (lines 1091-1096): pm, verifier, worker, dm entries all unchanged. ✓

**Cross-mode pair acknowledgement** (line 1066-1067): `"Loop mode reaches the same outcome on quiet cycles via §6.4 — same role-class subloops, different trigger surface; this section is the event-mode side of that pair."` ✓ And §6.4 (lines 664-667) already cross-references back to §7.6. ✓

### AC Check (2): §3.1 cross-ref

**Line 183**: `"`.event-state.json` shown in the harness host above persists the per-alias **event-tending cursor** — what it represents and when it advances are defined in §4.3."` — exactly one sentence after the mermaid diagram, pointing to the right section, anchoring on the file shown in the diagram. ✓

No other cursor mentions in §1-§3 have been edited (the §2 table line 61 has a high-level reference that doesn't contradict §4.3). Light cross-ref only. ✓

### AC Check (3): §10.4 rev 16 entry

**Lines 1280-1289** — bullet structure matches rev 14's multi-bullet format. Contents cover:
- D1 (cursor semantics) ✓
- D2 (§7.1 eager per-event loop) ✓
- D3 (mid-cycle nudge = no action) ✓
- D4 (separate state machines) ✓
- §7.6 reframing ✓
- Collateral vocab cleanup ✓
- §3.1 cross-ref ✓
- Out of scope (#11330, #11329) ✓
- DS audit trail ✓

### Cross-check (a): §7.6 lead ↔ flowchart consistency

**Lead** (line 1066): `"drained-queue branch of the §7.1 main loop"` — matches flowchart semantics.

**Flowchart** (lines 1070-1087):
- Start node (line 1072): `"per-event ack just emitted; top of §7.1 eager loop"` ✓
- Process node (line 1077): `"process next event (§7.1 inner loop body)"` ✓
- Subloop → Start edge (line 1085): `"Subloop --> Start"` ✓
- Idle → Start edge (line 1086): `"Idle -->|NUDGE wakes agent| Start"` ✓

### Cross-check (b): §3.1 cross-ref target

Points to §4.3 (`"…defined in §4.3"`) — §4.3 is "Harness internals" which contains the Cursor model subsection (lines 379-407). ✓

### Cross-check (c): rev-16 entry accuracy vs actual edits

Verified each claim:
1. **D1**: §4.3 cursor-model lead (line 381) rewritten, §4.2 ack-cursor row (line 268) refined, §4.3 mermaid diagram (lines 393-403) simplified. ✓
2. **D2**: §7.1 pseudocode (lines 791-809) is `loop forever` with per-event ack, §7.1 sequence diagram (lines 819-859) redrawn, §7.2 boot steps (lines 873-876) consolidated to step 4. ✓
3. **D3**: §7.5 (lines 1042-1062) collapsed to single instruction + crash-safety table in eager-loop terms. ✓
4. **D4**: §4.1 Principle 4 (line 257) rewritten, §4.2 catalog row separator sentence (line 271) reframed, §4.1 Principle 1 (line 254) refined. ✓
5. **Collateral vocab cleanup**: §2.2 (line 64), §4.3 (line 407), §7.0 (line 782), §7.4/EAD note (line 1032) — all verified clean. ✓

### Cross-check (d): Doc-wide consistency

**Remaining batched-walk vocab**: Only the intentional "pre-D2 batched walk" commentary at line 811 and the rev-16 entry itself (line 1286). No stale usage elsewhere. ✓

**§7.x cross-ref integrity**: §6.4→§7.6 (line 665-667), §7.1→§7.6 (line 805), §7.6→§7.1 (line 1066), §7.2→§7.1 (line 876), §7.5→§7.1 (line 1044), §7.0→§7.1+§7.2 (line 782), §4.3→§7.1 (lines 387, 407) — all resolve to correct sections. ✓

**§1-§3 cursor mentions vs §4.3**: Only cursor mention in §1-§3 is the new §3.1 cross-ref (line 183) which defers to §4.3, and the §2 table high-level mention (line 61: `"agents subscribe with a cursor"`) which doesn't redefine cursor semantics. No contradiction. ✓

---

NO_FINDINGS