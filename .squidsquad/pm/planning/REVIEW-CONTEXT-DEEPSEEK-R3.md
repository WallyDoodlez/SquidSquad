I have conducted a thorough review of the revised CONTEXT.md, tracing all three fixes (F20, F21, F22) and verifying cross-section consistency. Here are my findings:

---

## F20 Resolution Check — "L1–L4" → "L1–L3" Phrasing

All instances now correctly distinguish L1–L3 (separate per mode) from L4 (shared, mode-agnostic):

| Location | Wording | Verdict |
|----------|---------|---------|
| Executive summary, line 28 | "Two completely separate L1–L3 fragment sets" | ✓ |
| §2 locked decision, line 111 | "Two completely separate L1–L3 fragment sets, mode-agnostic L4" | ✓ |
| §4.3 compose selection, lines 314–315 | "L4 project instructions... are mode-agnostic" | ✓ |
| §5.3 title, line 476 | "separate L1–L3 sets per wake mode, shared L4" | ✓ |
| Glossary "Mode separation", lines 953–955 | "two completely separate L1–L3 fragment trees + two manifests per role, with shared mode-agnostic L4" | ✓ |
| §2 line 117–118 | "Phase 6 cleanup deletes the /loop L1–L3 tree wholesale" | ✓ |
| §7.1 Phase 6 cleanup | Deletes L1–L3 loop trees only | ✓ |

**No "L1–L4 fragment sets" language remains.** The §5.3 fallback (splitting L4 files that can't be generalized into mode-specific variants, line 514–515) is an acceptance-criteria pragmatic acknowledgement, not a contradiction of the shared-L4 design goal — the "or" conveys acceptable outcomes, not a requirement to split.

---

## F21 Resolution Check — Mid-Operation Harness Failure

Three locations now lock the policy:

| Location | Key Text | Verdict |
|----------|----------|---------|
| §5.1 event_poll.py deliverable, lines 366–373 | "Mid-operation harness failure is a manual-recovery scenario — ... agent keeps retrying at the capped backoff but does NOT pivot to forge-direct work. The operator manually restarts the harness" | ✓ |
| Glossary "Degraded mode", lines 914–922 | "**boot-time only.** ... Mid-operation harness failure (after `bootup-complete`) does NOT trigger degraded mode — the agent simply retries `event_poll.py`" | ✓ |
| §3.1 step 5, lines 171–181 | Only describes boot-time degraded mode — no mid-operation override | Consistent — mid-operation is handled at §5.1 |

Degraded mode is now unambiguously boot-time-only. The boot path (§3.1 step 5) and the event_poll.py deliverable (§5.1) use different recovery strategies for different failure windows, and the glossary explicitly scopes them.

---

## F22 Resolution Check — 5-Minute Backoff Cap Consistency

All references to the retry cap now converge on a single policy:

| Location | Cap Specified | Verdict |
|----------|--------------|---------|
| §3.1 step 5 (boot retry), line 178 | "exponential backoff capped at 5 minutes" | ✓ |
| §5.1 event_poll.py deliverable, lines 363–365 | "same 5-minute cap as the boot-time retry loop (§3.1 step 5) for a single consistent retry policy" | ✓ |
| §5.1 mid-operation, line 367 | "capped backoff" (references same cap as above) | ✓ |
| Glossary "Degraded mode", lines 917, 920 | Boot: "5 minutes"; Runtime: "same 5-minute cap" | ✓ |
| §10 RESEARCH Q6 closure, line 872 | "5-minute backoff cap handles harness-down scenarios" | Consistent |

**No uncapped backoff references remain.** The event_poll.py spec now pins its cap to the boot-time cap explicitly.

---

## Cross-Section Self-Consistency Audit

I verified the following cross-reference chains for internal consistency:

1. **Boot sequence ownership**: §2 (line 119) → §3.1 title → §5.1 (lines 354–356) → §5.1 Acceptance (line 425–426) → §7.1 (lines 736–738) → Glossary "Event-mode L1 base" (lines 904–908). All agree: boot is part of #8694's L1 base fragment, no standalone file. **Consistent.**

2. **Thin harness / no dispatch**: §2 (lines 50–52) → §5.2 (lines 435–437) → §5.2 Acceptance (lines 466–467) → Glossary "Thin harness" (lines 889–891) → Glossary "bootup-complete event" (lines 923–926). All affirm no queuing, gating, or dispatch. **Consistent.**

3. **Atomicity rule**: §2 (lines 66–68) → §3.4 (lines 205–209) → §3.6 (lines 239–240) → Glossary (lines 936–938). All agree: tasks run to completion, mid-task events are read-and-advanced but not acted on. **Consistent.**

4. **Cool-down policy**: §2 (lines 69–80) → §3.6 (lines 222–242) → §10 closure. All agree: 30m universal default, read from config.md at scan-completion time, value not stored in working-state.md. **Consistent.**

5. **DM comment handling**: §2 (lines 89–94) → §3.7 (lines 248–254) → §5.1 scope (line 344). All agree: re-read at task completion only, no sub-loop during PR-merge wait. **Consistent.**

6. **HITL / no designer special-casing**: §2 (lines 98–102) → §3.8 (lines 260–265) → §5.6 (lines 630–658). All agree: designer is a worker, human handoff = pending-human-* transition, design:* labels are metadata only (Phase 6 retirement candidate). **Consistent.**

7. **#8699/#8696 folding**: Header (line 5) → §5.1 scope → §5.3 → §6.2 → §9 notes (lines 833–835). All agree: #8696 folded into #8694; #8699 folded into #8697. No orphan references. **Consistent.**

8. **Pre-flip checklist**: §6.3 items → §9 diagram annotation → §10 RESEARCH Q8 closure. All reference the same six-item checklist. **Consistent.**

9. **TUI architecture**: §5.4 (line 553 references TUI panels) → §5.6 → §5.7 (cross-cutting section) → Glossary "TUI" (lines 966–968). All describe a single harness-served TUI hosting both panels. One minor imprecision: §5.4 line 553 says "see §5.6" (human-queue section) rather than "see §5.7" (cross-cutting TUI architecture section). This is a cross-reference pointing to a related panel discussion rather than the architectural overview — not a contradiction. **Acceptable.**

10. **Mode-conditional logic prohibition**: Executive summary (line 30) → §2 (line 112) → §4.3 (line 312) → §5.1 Acceptance (lines 423–424) → §5.3 Acceptance (lines 538–539). Consistent: no `event-driven:` runtime branches in fragment bodies. **Consistent.**

---

## Summary

- **F20, F21, F22**: All three fixes are applied cleanly with supporting evidence in every relevant section.
- **No regressions**: Verified that all previously-resolved findings (F1–F19) remain intact — no re-introduced dispatch gating, no missing event-listening mechanism, no uncapped retries, no orphaned boot fragment references.
- **No new contradictions**: All cross-section references, glossary entries, acceptance criteria, and architectural decisions are mutually consistent. The degraded-mode scoping (boot-only) is explicit and unambiguously echoed in §5.1, the glossary, and §3.1.
- **Self-consistency**: The document's internal references (task numbers, section cross-references, glossary definitions, sequencing diagram vs. per-task specs) are coherent throughout.

**Verdict: NO_FINDINGS**