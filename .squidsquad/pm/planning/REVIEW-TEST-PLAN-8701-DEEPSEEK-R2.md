I've reviewed the revised TEST-PLAN-8701.md against the task context. The specific verification items all check out:

### UT-10 — All 3 sub-cases covered

- **UT-10a** (event-mode pass): `cycle-output.json` has `task_id`, no `cycle_number`, config `event-driven: yes` → validation passes.
- **UT-10b** (loop-mode reject): `cycle-output.json` has no `cycle_number` and no `task_id`, config `event-driven: no` → validation rejects, stderr names `cycle_number`.
- **UT-10c** (event-mode reject — no task identifier): `cycle-output.json` has no task identifier, config `event-driven: yes` → validation rejects, stderr names the missing field.

All three are explicitly enumerated with distinct preconditions, expected behaviors, and verification assertions. This fully closes PM Gap 2 / F6.

### NT-5 — Negative grep is concrete

Steps specify `git grep -n '_advance_event_cursor' references/scripts/cycle_post.py`. Expected: zero matches. Verification: assert grep output is empty. The test demands both function definition AND call sites are absent — not a fuzzy "file doesn't exist" or "not called" proxy. This directly closes PM Gap 3 / F4.

### OQ5 and OQ6 — Closed

Both are strikethrough-marked in Section 10:
- OQ5: `~~cycle-output.json shape change~~ — CLOSED (PM Gap 2)`
- OQ6: `~~Event bus cursor advancement~~ — CLOSED (PM Gap 3)`

Each cites its covering test (UT-10 and NT-5 respectively) and references the scope expansion section.

### All 7 F1–F7 findings addressed

- F1: UT-9 heading now reads "(mandatory, review F1)" — no "bonus" label.
- F2: UT-1 Pre includes spy/mock of `_get_cycle_number`; Verification asserts invocation count == 0.
- F3: NT-2 Pre includes spy/mock of `_write_status_bar()`; Expected asserts invocation count == 0 **and** file absence.
- F4: Closed via NT-5 as described above.
- F5: IT-5 Steps specifies **sequential** execution with rationale.
- F6: Closed via UT-10 as described above.
- F7: PV-3 appends a note acknowledging trivial config-mock removal may be needed post-Phase 6.

No new defects introduced by the revisions. No remaining findings.

---

```
NO_FINDINGS
```