Now I have a complete picture. Let me compile the full audit.

---

## Audit: AGENT-RUNTIME.md vs. Shipped + In-Flight Work Manifest

### Finding 1

- **TRD section**: §7.3 Harness validation / permission retirement (lines 960–967)
- **Verdict**: **GAP**
- **Evidence**: TRD line 967 explicitly states: *"Current code still reads `responsibility.md` and enforces class-from-class permission checks; removal is tracked in #10182."* The manifest lists shipped PRD-A through PRD-E, in-flight E6 (#10685) and #10781, and held D6 (#10677), E7 (#10686), #10690. **#10182 is absent** from all three categories (shipped, in-flight, held).
- **Severity**: **medium**
- **Suggested action**: Either (a) add #10182 to the held list gated on E6 (since E6 Group D alias-existence validation must land first), or (b) confirm #10182 is subsumed by E6 Group D and update the manifest accordingly, or (c) if #10182 is genuinely untracked, create a plan item for it. The TRD itself says this is tracked; the manifest should reflect that tracking.

---

### Finding 2

- **TRD section**: §6.6 Vault touchpoints — subagent lane implementation gap (lines 675–686)
- **Verdict**: **GAP**
- **Evidence**: TRD line 686 explicitly states: *"Implementation gap (today): the subagent lane is the architectural target, not the current behavior. Both `vault-remember` and `vault-synthesis` currently compose into the consuming agent's CLAUDE.md inline; closing the gap requires splitting each sub-skill source into a stub (composed into agent) plus a prompt (loaded by the subagent). Tracked as VAULT-ARCH §11.5 + #10180."* **#10180 is absent** from the manifest. The in-flight #10781 (PRD-D Sub-skills as Claude Skills) scope description mentions "Removes 3 catalog rows (`self-restart`, `context-pressure`, `cycle-runner`)" — it does not mention vault-remember or vault-synthesis subagent-lane migration. These are different concerns.
- **Severity**: **medium**
- **Suggested action**: Either (a) add #10180 to the manifest (held or planned), (b) confirm that #10781's Claude Skills migration explicitly includes vault-remember and vault-synthesis subagent-lane work and update #10781's scope description, or (c) accept this as a documented known gap deferred beyond the current delivery window and update the manifest to reflect that.

---

### Finding 3

- **TRD section**: §4.8 Design properties summary, Row 6 "Role authority" (line 561)
- **Verdict**: **DRIFT** (internal inconsistency)
- **Evidence**: Line 561 states: *"harness enforces `/work/assign` via L2 bus contract (§7.3)."* The concept of "L2 bus contract" was **retired in rev 10** (line 1232-1233) along with `responsibility.md` and permission tables. The referenced §7.3 (lines 960–965) actually describes the **new model**: alias-existence validation only (404 if unknown), self-assign invariant, no class-from-class permissions. The design properties table was not updated when rev 10 removed the L2 bus contract concept. This is a documentation drift — it claims the harness enforces via a mechanism that no longer exists in the target architecture.
- **Severity**: **low**
- **Suggested action**: Rewrite line 561 to match the rev 10 architecture: e.g., *"harness validates `/work/assign` via alias-existence check + self-assign invariant (§7.3); no class-from-class permissions — process discipline lives in L2/L3/L4."*

---

### Finding 4

- **TRD section**: §2 Two triggering modes (line 57), §8.1 No global config (line 1079)
- **Verdict**: **DRIFT** (TRD target vs. shipped code)
- **Evidence**: The TRD asserts there is *"no `event-driven:` config field in `.squidsquad/config.md`"* (line 57) and *"There is **no `event-driven:` field** in `.squidsquad/config.md`"* (line 1079). However, the manifest shows **D6 "Remove `event-driven:` config field (#10677)" is HELD**, gated on E6. This means the `event-driven:` field almost certainly still exists in shipped code. The TRD describes the post-E6+post-D6 target state, not the current shipped state. This is a spec/impl mismatch until D6 ships.
- **Severity**: **low** (the TRD is a draft design doc; E6 is actively closing this gap)
- **Suggested action**: No immediate action needed; this DRIFT resolves automatically when E6 ships (making the field inert) and D6 ships (removing it). The manifest correctly tracks both items.

---

### Finding 5

- **TRD section**: §4.2 Signal catalog "What is OUT of the v2 catalog" (lines 273–284)
- **Verdict**: **DRIFT** (TRD target vs. shipped code)
- **Evidence**: The TRD claims 20 event types are removed under v2 (lifecycle ticks, git/PR/tracker activity, harness internals, speculative entries — lines 277–282). However, the TRD itself acknowledges at line 284: *"today's loop-mode codebase still emits and reacts to most of the above. The catalog trim is part of the v2 migration (see §8)."* The v2 catalog trim is delivered by **E6 Group E — Migration** (line 1134), specifically sub-phase E3 "trim catalog + rewrite event_poll." E6 is IN PROGRESS, so the shipped code still has the v1 catalog. This is a known, tracked drift.
- **Severity**: **low** (covered by E6 Group E)
- **Suggested action**: No action needed; E6 Group E closes this. The TRD correctly self-documents the gap.

---

### Finding 6

- **TRD section**: §4.3 Role-based filtering "v1 loop-mode legacy" callout (lines 415–416)
- **Verdict**: **DRIFT** (TRD target vs. shipped code)
- **Evidence**: The TRD states the v2 target is *"every role-class reacts only to `assigned-to`"* (line 404), but acknowledges at lines 415–416: *"Today's loop-mode codebase still has a per-role-class event-type allowlist (client-side filter in `cycle_pre.py` via `_ROLE_EVENT_TYPES` dict)."* This per-role-class filter is retired as part of **E6 Group E2** — "collapse `Event Reactions` to `assigned-to` only" (line 1134). E6 is IN PROGRESS, so the shipped code still has the v1 allowlist.
- **Severity**: **low** (covered by E6 Group E2)
- **Suggested action**: No action needed; E6 Group E2 closes this.

---

### Finding 7

- **TRD section**: §7.3 Label lifecycle — "Initial set" bullet (lines 944–945)
- **Verdict**: **DRIFT** (target architecture vs. likely shipped state)
- **Evidence**: The TRD says PM owns initial `role:<alias>` label management and that *"This is the only point in the pipeline where a non-harness writer touches `role:*`"* (line 944). All subsequent rewrites are harness-side. For this to work, `tracker.py transition` must call `/work/assign` (which triggers the harness label write) instead of writing `role:*` directly. The TRD acknowledges at line 948 this *"Replaces the deprecated `status-transition` emit."* The `status-transition` emit retirement is part of **E6 Group E** migration (line 1134, E1: "stop emitting deprecated types"). Until E6 ships, `tracker.py` may still emit `status-transition` directly. This is a documented migration gap.
- **Severity**: **low** (covered by E6 Group E)
- **Suggested action**: No action needed; E6 Group E closes this.

---

### Finding 8

- **TRD section**: §8.5 Migration plan — 6 grouped PRs (lines 1127–1134)
- **Verdict**: **IN PROGRESS** (explicitly noted for completeness)
- **Evidence**: Group A (lifecycle plumbing), Group C (EAD + restart safety), Group D (alias-existence validation), Group B (cursor + delivery wire), Group F (observability), and Group E (migration) are all delivered by **E6 V2 CUTOVER (#10685)**, which is `status:in-progress`. The manifest confirms phases 1-6 + sub-phases committed, remaining in flight. Additionally, **E7 V2 migration smoke (#10686)** is HELD, gated on E6.
- **Severity**: N/A (IN PROGRESS / HELD — not a gap)
- **Suggested action**: None; correctly tracked.

---

### Finding 9

- **TRD section**: §7.6 Improvement subloop "What the subloop does" (lines 1067–1073)
- **Verdict**: **IN PROGRESS**
- **Evidence**: The improvement subloop in event mode (drained-queue detection with time-based throttle, `.subloop-last-run` file, per-role-class tasks) is part of the event-mode architecture delivered by **E6 V2 CUTOVER (#10685)**. No separate work item exists for the subloop itself; it's folded into the E6 event-mode implementation. The loop-mode improvement subloop (§6.4) is already shipped (existing Ralph Loop behavior).
- **Severity**: N/A (IN PROGRESS via E6)
- **Suggested action**: None.

---

### Finding 10

- **TRD section**: §8.5 Catalog-trim replacements table (lines 1138–1144) and PM inbox `event_context` enumeration (lines 1146–1154)
- **Verdict**: **IN PROGRESS**
- **Evidence**: The translation of retired event types (`compose-completed`, `agent-health`, `noop`) into `assigned-to` with specific `event_context` values, plus the full PM inbox event_context set, is delivered by **E6 Group E — Migration** sub-phases E1-E3 (line 1134). The full set of `event_context` values (lines 1148–1152) spans the `tracker.py` routing table, catalog-trim translators, harness COMPOSE-ARCH §8.2, EAD, and direct `/work/assign` callers — all of which are part of the v2 event-mode architecture gated behind E6.
- **Severity**: N/A (IN PROGRESS via E6)
- **Suggested action**: None.

---

### Finding 11

- **TRD section**: §7.3 `role:*` label key → `alias:` rename (line 940)
- **Verdict**: **GAP** (deferred without tracking)
- **Evidence**: TRD line 940: *"A rename of the label key from `role:` to `alias:` is in the same family as #10358 (`role` → `alias` identifier rename) but is currently out of scope on that task to limit blast radius — every existing issue label would need editing in lockstep with `tracker.py`, every care-filter caller, and every composed agent file that mentions `role:<name>`. Revisit once #10358 has phased through code-side first."* **#10358 is not in the manifest** (shipped, in-flight, or held). The TRD defers the label-key rename to "once #10358 has phased through," but #10358 itself has no manifest entry. This is a deferred dependency chain with no tracking.
- **Severity**: **low** (the TRD explicitly calls it out of scope; the system functions correctly with the legacy `role:` key)
- **Suggested action**: Add #10358 to the manifest (held or planned) so the dependency chain is visible. The label-key rename should be a separate follow-on item keyed to #10358 completion.

---

### Finding 12

- **TRD section**: §1 Terminology — per-agent identity (line 30)
- **Verdict**: **STALE** (partial)
- **Evidence**: Line 30 states: *"Per-agent identity (personality, situational tone) lives in `SOUL.md`."* This is the rev 10 framing where *"Specialty/skill (FE/BE/iOS/etc.) lives in SOUL.md + L4."* However, the rev 10 entry itself (line 1231) includes a parenthetical correction: *"(Note: §1 Terminology now locates specialty in **L3 (the domain layer)** instead — see `feedback-l3-specialty-layering`. This rev-10 entry preserves the as-of-rev-10 framing; current canonical statement is §1.)"* Line 29 now says *"Specialty/skill (FE vs BE vs iOS, etc.) lives in **L3 (the domain layer)**"* — which is correct. Line 30 then says per-agent identity (personality, tone) lives in SOUL.md, which is consistent. However, the rev 10 log entry (line 1231) is itself referencing a stale framing and noting the correction — this is intentional self-documentation. **No actual stale claim remains in the body text.** The rev log entry is historical.
- **Severity**: **low** (historical note, not an active claim)
- **Suggested action**: None. The rev log correctly self-documents the evolution.

---

### Finding 13

- **TRD section**: §4.3 Mermaid diagram — `BootAgent` label (line 317)
- **Verdict**: **DRIFT** (minor diagram inconsistency)
- **Evidence**: Line 317 in the harness internals Mermaid diagram labels the agent lifecycle component as: `BootAgent["boot_agent(role)<br/>spawns thin_launcher + event_poll"]`. The TRD's own vocabulary note (line 353) states that `{role}` in code is actually `{alias}`, and line 749 states `event_poll`'s `--role` flag accepts the alias value. The diagram label uses `role` instead of `alias`, which is inconsistent with the TRD's own convention of writing `{alias}` to "surface the actual semantics" (line 353). This is a minor presentation inconsistency in a diagram, not a logic error.
- **Severity**: **low** (cosmetic diagram label)
- **Suggested action**: Update the Mermaid label from `boot_agent(role)` to `boot_agent(alias)` to match the TRD's own stated convention.

---

### Finding 14

- **TRD section**: §8.5 Migration plan Group D description (line 1131)
- **Verdict**: **CONFIRMED** / **IN PROGRESS** (clarification)
- **Evidence**: Line 1131 says Group D does: *"Harness validates `target_alias` against the install's registered aliases (per `.squidsquad/config.md` `## Aliases`); 404 on unknown. No class-from-class permissions."* The `## Aliases` schema itself was locked in rev 14 and shipped via **PRD-C (L4 customization)** C1-C10. The alias-existence validation endpoint is part of **E6 V2 CUTOVER (#10685)** Group D. The "No class-from-class permissions" part depends on #10182 (see Finding 1).
- **Severity**: N/A
- **Suggested action**: None beyond Finding 1.

---

### Summary Table

| § Section | CONFIRMED | IN PROGRESS | HELD | GAP | DRIFT | STALE |
|---|---|---|---|---|---|---|
| **Terminology** (lines 11–35) | Role classes, L4-per-role-class, L3 specialty, alias routing rule | — | — | — | — | — |
| **§2 Triggering modes** (lines 55–107) | — | Boot-probe selection, per-session binding, bus-fallback, loop-mode fallback | — | — | `event-driven:` field claim vs. shipped code (Finding 4) | — |
| **§3 Process tree** (lines 111–222) | `cmd→thin_launcher→claude`, OS variants, `.claude-pid` | event_poll placement, thin_launcher/event_poll separation | — | — | Mermaid label `role`→`alias` (Finding 13) | — |
| **§4 Event bus** (lines 225–563) | 5 architectural commitments, port discovery | Signal catalog, deque, cursor, EAD, reactions, cascade protection, HTTP 410 | — | — | v1 catalog still in shipped code (Finding 5), v1 allowlist in shipped code (Finding 6), "L2 bus contract" wording (Finding 3) | — |
| **§5 State persistence** (lines 566–581) | File ownership invariants | — | — | — | — | — |
| **§6 Loop mode** (lines 584–726) | Ralph Loop cycle, `/loop`, mechanical reactions, exit-42, subagent rules | — | — | #10180 vault subagent lane (Finding 2) | — | — |
| **§7 Event-driven mode** (lines 729–1074) | Forge-as-channel principle | event_poll sidecar, nudge contract, boot sequence, state machine, `/work/assign`, routing table, EAD safety net, care filter, nudge-while-busy, improvement subloop | — | — | `role:*` label lifecycle vs. `status-transition` emit still in code (Finding 7) | — |
| **§8 Wake-mode selection & migration** (lines 1077–1155) | — | E6 Groups A-F migration, catalog-trim replacements, PM inbox event_context set | D6 `event-driven:` removal (#10677), E7 smoke (#10686) | — | `event-driven:` field claim vs. shipped code (Finding 4) | — |
| **§9 Open questions** (lines 1158–1182) | Q1–Q13 all closed/locked | — | — | — | — | — |
| **§10 References** (lines 1186–1211) | Glossary, related docs, source material | — | — | — | — | — |
| **Cross-cutting** | — | — | — | #10182 permission-check removal (Finding 1), #10358 role→alias rename + label-key rename (Finding 11) | — | — |

**Counts**: CONFIRMED: 11 feature groups | IN PROGRESS: 14 feature groups (via E6 #10685 + #10781) | HELD: 2 items (D6 #10677, E7 #10686) + 1 (#10690) | GAP: 3 (#10182, #10180, #10358) | DRIFT: 6 (Findings 3, 4, 5, 6, 7, 13) | STALE: 0 active claims

### Overall Assessment

The TRD is **well-covered** by the manifest. The vast majority of architectural promises are either shipped (PRD-A through PRD-E) or in active development (E6 V2 CUTOVER #10685). The three genuine gaps are:

1. **#10182** (remove class-from-class permission checks / `responsibility.md`) — referenced by the TRD but untracked in the manifest. Medium severity because it's a concrete code-change dependency the TRD itself calls out.
2. **#10180** (vault-remember/vault-synthesis subagent lane) — referenced by the TRD as a known implementation gap but untracked in the manifest. Medium severity; may be subsumed by #10781 but scope description doesn't confirm this.
3. **#10358** (role → alias identifier rename) — deferred by the TRD itself as "out of scope," but the TRD makes multiple forward references to it without a manifest entry. Low severity because the system is designed to function correctly with legacy `role` naming.

The six DRIFT findings are all low-severity and expected for a draft design document describing a target architecture that is actively being built (E6 in flight). None represent a spec/impl contradiction that requires urgent reconciliation.