I've completed a thorough review of `docs/AGENT-RUNTIME.md` for round 5 convergence.

## Cross-check summary

**Fix verification from round 4:**
- `route-handoff`: Only occurrence is in the rev-5 log entry (line 1054) describing its removal. Nowhere else in the doc. ✓
- PM inbox `event_context` exhaustive list (lines 989–996): I traced every value against its claimed source:
  - **Routing table (§7.3)**: `planning-needed` (line 789), `human-needed` (lines 794–795), `unowned-rejection` (lines 787–788 fallback), `unowned-approval` (line 791 fallback). All 4 present. ✓
  - **Catalog-trim translators (§8.5)**: `compose-needed`, `agent-down` (lines 985–986). Both present. ✓
  - **EAD**: `human-comment` (line 993). Present. ✓
  - **Direct `/work/assign`**: `process-concern` (lines 811–812). Present. ✓

**Internal consistency checks:**
- All cross-references (e.g., `§7.1`, `§4.4`, `§8.5 Group E`) resolve to existing sections. ✓
- No contradictions between `§4.2` signal catalog fields and wire-diagram payloads. ✓
- `§7.4` care-filter definition (`target_role == my_role`) is consistent with `§8.5` PM disambiguation (event_context used for dispatch after role-filter passes). ✓
- Revision log (lines 1048–1054) has all 5 entries in sequence, no gaps. ✓
- Routing table fallback prose (`unowned-rejection`, `unowned-approval`) embedded in the `target_role` column is correctly captured by the PM inbox list even though those values don't appear in the `event_context` column of the table. ✓

**No HIGH or MED issues found.** The document has fully converged.

CONVERGED