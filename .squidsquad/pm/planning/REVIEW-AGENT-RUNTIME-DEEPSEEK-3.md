After careful re-review of the full document, I found two new issues that survived the round-1 and round-2 passes. Both are internal inconsistencies.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~377 (EAD cadence) and ~390 (latency table); same pattern at ~770 (event_poll cadence)
- **Severity**: MED
- **Issue**: The EAD cadence algorithm in §4.4 describes a single backoff step: `3 consecutive empty polls → step up to 30s`. But the latency table immediately below lists "EAD safety net, quiet period | Worst case | 60s" — a value the single-step algorithm can never produce. The `hard ceiling: 60s` is unreachable. The same pattern appears for `event_poll` in §7.0 (`step up to 30s` + `hard ceiling: 60s`). Either multi-step backoff (10s→30s→60s / 5s→30s→60s) is implied but never described, or the ceiling and latency-table values are incorrect.
- **Evidence**: Cadence block says only "step up to 30s" with no mention of a second backoff tier, yet `hard ceiling: 60s` is declared and the latency table cites 60s as worst-case quiet. The numbers don't reconcile without an unstated second step.
- **Suggested fix**: Either (a) add explicit second-tier backoff language ("after 3 more empty polls at 30s → step up to 60s") to both EAD and event_poll cadence blocks, or (b) reduce the hard ceiling / latency-table worst case to 30s to match the single-step algorithm actually described.

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~1004 (§8.5 catalog-trim table) vs ~167 (§4.2 signal catalog)
- **Severity**: LOW
- **Issue**: The catalog-trim replacement table in §8.5 introduces `ack_only=true` as a field on the `assigned-to` event for `event_context="probe"` — it appears at the same syntactic level as `target_role` and `event_context` in the table's notational convention. The `assigned-to` signal catalog entry in §4.2 specifies the payload structure as only `{issue_number, target_role, event_context, payload}`. `ack_only` is not documented there at any level (top-level or nested).
- **Evidence**: §8.5 entry reads `assigned-to(target_role=R, event_context="probe", ack_only=true)` — using the same top-level-field convention as `target_role` and `event_context`, which ARE in the catalog. The §4.2 catalog entry omits `ack_only` entirely.
- **Suggested fix**: Either add `ack_only` (optional boolean, default false) to the §4.2 `assigned-to` catalog payload specification, or nest it explicitly as `payload.ack_only` in §8.5 and note that `payload` carries role-specific extensions. The former is cleaner given the table's top-level placement.