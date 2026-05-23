Now I have all evidence needed. Let me compile the findings.

---

### Finding 1

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 85, 499 vs 907, 1038
- **Severity**: error
- **Issue**: The `booted` signal payload is stated as `{role}` in two locations (the §3 signal catalog table at line 85, and the §6.0 boot sequence step 4 at line 499), but the locked §13 Q1 decision (line 907) and the §15.7 question lock table (line 1038) both lock the payload as `{role, pid, clone_path, version}`. The main body text was never updated after the Q1 decision was locked.
- **Evidence**: 
  - Line 85: `| **`booted`** | agent → harness | First action after the agent's Claude session boots | `{role}` |`
  - Line 499: `4. **Agent emits `booted`** via `POST /events` with payload `{role}`.`
  - Line 907: `**CLOSED (2026-05-23, §15.1)**: `{role, pid, clone_path, version}` — full diagnostic from day 1.`
  - Line 1038: `| Q1 | Booted payload shape | `{role, pid, clone_path, version}` — full diagnostic from day 1 | §3 catalog entry + §15.1 spawn flow |`
- **Suggested fix**: Update line 85 to `{role, pid, clone_path, version}` and line 499 to `with payload {role, pid, clone_path, version}`. Also update the §6.0 sequence diagram (line 431) from `POST /events {type: booted, role}` to reflect the full payload.

---

### Finding 2

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 285 vs 222
- **Severity**: error
- **Issue**: The §5.1 text component list for `POST /events` includes `assigned-to` in the parenthetical `(booted, ack-cursor, ack-stop, assigned-to)`. But `assigned-to` is a harness→agent signal (per §3 line 86: direction "harness → agent"), not something agents ever POST. The §5.0 Mermaid diagram for the same endpoint (line 222) correctly lists only `(booted, ack-cursor, ack-stop)`. The text contradicts both the diagram and the architectural principle that `POST /events` is an agent→harness emit endpoint.
- **Evidence**:
  - Line 285: `├── POST /events <- emit (booted, ack-cursor, ack-stop, assigned-to)`
  - Line 222 (Mermaid): `EmitEP["POST /events<br/>(booted, ack-cursor, ack-stop)"]`
  - Line 86: `| **`assigned-to`** | harness → agent (queue entry) |`
  - Principle §2 item 1: harness is a transport bus. Agents don't emit work assignments to themselves.
- **Suggested fix**: Remove `assigned-to` from the parenthetical on line 285. Change to `(booted, ack-cursor, ack-stop)`.

---

### Finding 3

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 741, 749, 913, 934, 985
- **Severity**: warning
- **Issue**: Five locations state that `event_poll` re-nudges "within 10–60s." But `event_poll`'s active cadence is 5s (per locked §13 Q4 at line 910: "5s active / 30s idle, adaptive backoff, hard bounds 2s floor / 60s ceiling"). The value "10s" is the *EAD* active cadence (per §5.4), not `event_poll`'s. Additionally, line 741 cross-references "per §5.4 cadence," but §5.4 documents EAD cadence, not `event_poll` cadence.
- **Evidence**:
  - Line 741: `event_poll's next poll within 10–60s (per §5.4 cadence)`
  - Line 749: `` `event_poll`'s next poll (within 10–60s) ``
  - Line 913: `event_poll's re-poll within 10–60s covers crash-loss of context`
  - Line 934: `` `event_poll` re-nudges within 10–60s ``
  - Line 985: `` `event_poll` re-nudges within 10–60s ``
  - Line 910 (correct value): `5s active / 30s idle, adaptive backoff, hard bounds 2s floor / 60s ceiling`
- **Suggested fix**: Change all five instances from `10–60s` to `5–60s` (or `2–60s` if bounding by floor). Fix the cross-reference on line 741 from `(per §5.4 cadence)` to reference the event_poll cadence definition (currently only in §13 Q4 lock and §15.7 lock table — consider adding a dedicated event_poll cadence sentence to §15.1 or §4.2).

---

### Finding 4

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 1041
- **Severity**: warning
- **Issue**: The §15.7 question lock table says Q4 (event_poll polling cadence) is "Enforced in: §15.1." But §15.1 (lines 973–980) covers Group A lifecycle plumbing — `boot_agent`, health poller PID watching, cold start order, wizard at install — and contains **zero** event_poll cadence values. The lock table Q4 row claims enforcement in a section that doesn't contain the decision. The actual cadence values live only in §13 Q4 (line 910).
- **Evidence**:
  - Line 1041: `| Q4 | `event_poll` polling cadence | 5s active / 30s idle, adaptive backoff, 2s floor / 60s ceiling | §15.1 (same pattern as §5.4) |`
  - Lines 973–980 (§15.1 entire content): no cadence values appear.
  - Line 910 (actual values): `4. ~~**`event_poll` polling cadence**~~ **CLOSED (2026-05-23, §15.1)**: 5s active / 30s idle...`
- **Suggested fix**: Either (a) add event_poll cadence to §15.1 Group A so the cross-reference holds, or (b) change the lock table's "Enforced in" column to reference §13 (the locked question) or a new explicit section.

---

### Finding 5

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 1003 vs 1053–1058
- **Severity**: warning
- **Issue**: §15.4 Group D specifies that the permission table "reloads when `compose.py deploy <role>` runs (via the compose-needed PM trigger from §15.5)." But the compose-needed trigger is defined in §15.5 Group E. The §15.8 implementation sequence puts D at PR #3 and E at PR #6. This means D's permission-table reload mechanism depends on infrastructure that won't exist until three PRs later — the reload feature is dead on arrival at D's merge time.
- **Evidence**:
  - Line 1003: `Permission table reloads when `compose.py deploy <role>` runs (via the `compose-needed` PM trigger from §15.5).`
  - Lines 1053–1058: PR sequence puts D (#3) before E (#6).
  - §15.5 (Group E) is where compose-needed trigger is defined (line 1017).
- **Suggested fix**: Either (a) move the permission-reload mechanism to Group E so it lands with its dependency, leaving Group D to only build the table once at harness boot; or (b) reorder the PR sequence so E's compose-needed sub-piece (or a minimal compose-change-detection stub) lands before D; or (c) explicitly note in §15.4 that the reload mechanism is a placeholder wired to a trigger not yet built, and will activate once E lands.

---

### Finding 6

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 120
- **Severity**: warning
- **Issue**: §3.1 ("What is OUT of the catalog") closes with "20 catalog entries removed. Down to 3." But §15.5 Phase C (line 1015) specifies the catalog will be trimmed to **4** entries (`booted`, `assigned-to`, `ack-cursor`, `ack-stop`). The sentence "Down to 3" is in a section about the event catalog — it reads as a catalog entry count, not a concept count. The conceptual "3 signals" distinction (booted, assigned-to, ack with two emit helpers) is explained in §3 line 89, but the closing count in §3.1 misleadingly says 3 when the catalog will have 4 entries.
- **Evidence**:
  - Line 120: `20 catalog entries removed. Down to 3.`
  - Line 1015: `Trim `event_catalog.py` to 4 entries (`booted`, `assigned-to`, `ack-cursor`, `ack-stop`).`
- **Suggested fix**: Change line 120 to `Down to 4 (3 signal concepts — ack has two catalog subtypes: ack-cursor, ack-stop).` or similar language that distinguishes catalog entries from concepts.

---

### Finding 7

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 1067
- **Severity**: warning
- **Issue**: §16 References describes `event_catalog.py` as "to be trimmed to 3 entries." This should say 4 entries, matching §15.5 Phase C (line 1015). Same root cause as Finding 6.
- **Evidence**:
  - Line 1067: `- `references/scripts/event_catalog.py` — current catalog (to be trimmed to 3 entries).`
  - Line 1015: `Trim `event_catalog.py` to 4 entries`
- **Suggested fix**: Change "3 entries" to "4 entries" on line 1067.

---

### Finding 8

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 637
- **Severity**: warning
- **Issue**: The `tracker.py` routing table uses `"qa-rejected"` as the `event_context` for the `pending-test → in-progress` transition. "qa" is the concrete instance name; the L2 categorical name is "verifier." Post the dev→worker / qa→verifier rename pass (documented in the rev 3 log at line 1085), event_context values should use the categorical role name for consistency.
- **Evidence**:
  - Line 637: `| `pending-test → in-progress` | assigned role from `role:*` label | `"qa-rejected"` |`
  - Line 14 (terminology table): `| **`verifier`** | `qa` | ...`
  - All other event_context values in the table use categorical naming or functional descriptions: `"verification-needed"`, `"delivery-needed"`, `"merge-conflict"`, `"human-needed"`, etc.
- **Suggested fix**: Change `"qa-rejected"` to `"verifier-rejected"` on line 637.

---

### Finding 9

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 1013–1015 vs 1053–1055
- **Severity**: warning
- **Issue**: Group E's 3-phase migration sub-phases are named "Phase A", "Phase B", "Phase C" (lines 1013–1015), which collides with the top-level implementation group names "Group A", "Group B", "Group C" used in §15.8 (lines 1053–1055). When someone references "Phase A" in implementation discussions, it's ambiguous whether they mean Group A (lifecycle plumbing, PR #1) or Phase A of Group E (stop emitting deprecated types, part of PR #6).
- **Evidence**:
  - Lines 1013–1015: `- **Phase A** — Stop emitting...`, `- **Phase B** — Stop reacting...`, `- **Phase C** — Delete catalog...`
  - Lines 1053–1055: `| 1 | **A** — Lifecycle plumbing`, `| 2 | **C** — EAD + restart safety` (table continues with D, B, F, E)
- **Suggested fix**: Rename Group E's sub-phases to "Sub-phase 1", "Sub-phase 2", "Sub-phase 3" or "Phase E1", "Phase E2", "Phase E3" to disambiguate from the top-level Groups A–F.

---

### Finding 10

- **File**: docs/EVENT-ARCHITECTURE.md
- **Line**: 741 (also affects 749, 913, 934, 985)
- **Severity**: warning
- **Issue**: Line 741 says `event_poll`'s next poll occurs "within 10–60s (per §5.4 cadence)." But §5.4 documents **EAD** forge-polling cadence (10s active / 30s idle), not `event_poll` cadence. The `event_poll` cadence is locked at §13 Q4 (line 910) as "5s active / 30s idle / 2s floor / 60s ceiling" and is **not** documented in §5.4. This is a wrong cross-reference — §5.4 is about forge polling, not agent-side event polling. This is distinct from Finding 3 (which covers the number mismatch); this finding covers the cross-reference target being the wrong section.
- **Evidence**:
  - Line 741: `per §5.4 cadence`
  - §5.4 title (line 332): "The ExternalActivityDetector (EAD)" — entire section is about forge polling, not event_poll.
  - Line 910: event_poll cadence locked at §13 Q4, not in §5.4.
- **Suggested fix**: Change the cross-reference on line 741 from `(per §5.4 cadence)` to reference where event_poll cadence is actually documented. If event_poll cadence is to live in §15.1 (per the §15.7 lock table intent), add it there and cross-reference it.