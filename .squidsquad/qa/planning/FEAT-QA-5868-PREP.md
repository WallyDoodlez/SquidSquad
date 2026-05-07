# QA Prep — #5868 Event Consumption Sub-skill

## Summary
Large feature: 10 ACs, 23 TCs, 7 smoke tests, 9 CQs, 6 regression risks.
Label: `review:human-required` — cannot auto-merge. Route to human review after QA passes.

## Test Plan Gap Analysis (reviewed against ACs)

### CRITICAL GAPS — These are ship-blocking if not covered by implementation tests

| # | Gap | AC | What to check |
|---|-----|-----|----------------|
| TC-24 | Derivation idempotency | AC-3 | compose twice → identical Event Reactions output |
| TC-25 | Derivation accuracy (controlled input) | AC-3 | Known L1-L4 input → expected contracts |
| TC-26 | Derivation partial/malformed output rejection | AC-3 | Stub Claude CLI bad output → compose rejects, no write |
| TC-27 | Reaction cycle detection | AC-4 | A reacts-to B's emit + B reacts-to A's emit → error |
| TC-28 | Atomic write verification | AC-2 | Interrupted write → config.md section intact or absent, never partial |
| TC-29 | Corrupt section runtime fallback | AC-5,7 | Malformed Event Reactions section → cycle_pre falls back, no crash |
| TC-30 | Cursor deduplication preserved | AC-5 | Same event ID twice → only processed once |
| TC-31 | Concurrent config.md reads | AC-5 | Multiple cycle_pre processes → no race/corruption |
| TC-32 | Side-effect catalog entries | AC-9 | verification-failed/passed, agent-health, phase-change = recognized tier |
| TC-39 | E2E pipeline integration | AC-8 | compose → config.md → cycle_pre → correct events in cycle-input.json |

### HIGH GAPS — Missing deployment scenarios (AC-10)

| # | Gap | AC-10 Scenario |
|---|-----|----------------|
| TC-35 | Fresh setup | No prior Event Reactions → compose creates section |
| TC-36 | Upgrade | Stale/absent section → compose updates correctly |
| TC-37 | Add role | 3 roles exist → compose 4th → appends without corruption |
| TC-38 | Post-merge recompose | Changed references/ → compose updates contracts |

### MEDIUM GAPS — Quality/completeness

| # | Gap | AC |
|---|-----|-----|
| TC-33 | agent_compose() prose unaffected by derivation | AC-9 |
| TC-34 | Config.md size increase bounded | AC-9 |
| TC-40 | event-reactions.md distinguishes mechanical vs creative | AC-6 |
| TC-41 | Validation happy path (zero errors → exit 0) | AC-4 |
| TC-42 | Validation output deterministic (same input → same output) | AC-4 |

### AC Coverage Summary
- **AC-1**: Covered (TC-1,2)
- **AC-2**: Partial — atomic writes NOT tested
- **AC-3**: WEAK — 3 of 4 requirements uncovered (idempotency, partial rejection, accuracy)
- **AC-4**: Partial — reaction cycles NOT tested, happy path missing
- **AC-5**: Partial — concurrent safety, cursor dedup, corrupt fallback all missing
- **AC-6**: Partial — mechanical vs creative distinction not verified
- **AC-7**: Partial — corrupt section fallback untested (absent-section covered)
- **AC-8**: NOT COVERED — no E2E integration test
- **AC-9**: NOT COVERED — zero TCs for all 3 requirements
- **AC-10**: Partial — only 2 of 6 deployment scenarios tested

## Key Verification Points

### Must-Verify (Zero-Gap Gate)
1. **Backward compatibility first**: TC-18, TC-19, TC-20 — existing tests pass unchanged
2. **Graceful degradation**: TC-13 — hardcoded fallback works identically
3. **Self-event filter preserved**: TC-14 — agent doesn't react to own emissions
4. **Cascade safeguard**: TC-15 — cursor deduplication prevents infinite loops
5. **Cross-agent validation**: TC-7, TC-8, TC-9 — detects orphans, missing consumers, hallucinated
6. **Process-gap language**: TC-10 — no raw event names in user-facing output
7. **New test coverage**: TC-21 — implementation includes tests
8. **Reaction cycle detection**: TC-27 (GAP) — must be covered by dev tests
9. **Derivation correctness**: TC-25, TC-26 (GAP) — must be covered by dev tests
10. **E2E integration**: TC-39 (GAP) — full pipeline test

### Comprehension Testing (9 CQs)
Spawn fresh agent with ONLY modified files. Questions cover:
- How agents interpret Event Reactions (CQ-1, CQ-2)
- Three-tier catalog meaning (CQ-3)
- Malformed derivation handling (CQ-4)
- Runtime corruption handling (CQ-5)
- Cycle detection (CQ-6)
- Process-gap language rationale (CQ-7)
- Idempotency guarantees (CQ-8)

### High-Risk Areas
- `cycle_pre.py` refactoring — touches every agent's boot path
- `compose.py` derivation — LLM in the compose loop, hardest to test deterministically
- `config.py` new field parsing — config.md is shared state
- Cross-agent validation — must be deterministic

## Verification Strategy
1. Checkout feature branch
2. Run full existing test suite FIRST (backward compat)
3. Run new tests (TC-21)
4. Execute TC-1 through TC-23 via pytest subagent
5. **Check gap coverage** — verify dev included tests for gaps TC-24-42, especially:
   - Reaction cycle detection (TC-27)
   - Derivation accuracy + rejection (TC-25, TC-26)
   - Corrupt section fallback (TC-29)
   - E2E integration (TC-39)
6. Run smoke tests
7. Spawn comprehension agent for CQs
8. If gaps are NOT covered by dev tests → REJECT with specific missing TCs
9. If all pass: post QA results on PR → transition to `pending-human-review`

## Files to Watch
- `references/scripts/compose.py` — emission catalog, derivation, validation
- `references/scripts/cycle_pre.py` — config-driven event filtering
- `references/scripts/config.py` — Event Reactions field parsing
- `references/sub-skills/common/event-reactions.md` — creative-phase guidance
- `references/roles/*/includes.yml` — sub-skill inclusion
- `.squidsquad/config.md` — Event Reactions section format
- `tests/test_compose.py`, `tests/test_cycle_pre.py`, `tests/test_config.py` — new tests

## PR Flow
- PR exists with `review:human-required` label
- QA verifies → posts results on PR → transitions to `pending-human-review`
- Human reviews and merges manually
