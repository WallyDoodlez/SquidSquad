# QA-RESULTS-10681 — PRD-E / Story E2: last_compose_checksum field plumbing

**Verified**: 2026-06-02 03:42
**Branch**: `squidsquad/task/10681` @ `8f27a3dd`
**PR**: #10692
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/harness.py` (+31) — `HarnessState.last_compose_checksum` field initialized to None; `get_last_compose_checksum` / `set_last_compose_checksum` accessors under `self._lock`; persisted at top level via `save_state`; legacy migration via `state_data.get('last_compose_checksum')` in `load_state`.
- `tests/test_feat_10681_compose_checksum.py` (+222 new) — 11 tests covering all 6 ACs.
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Add `last_compose_checksum` field to top-level state-file schema | `test_save_emits_field_in_state_file` + `test_save_emits_null_when_unset`. Save persists field at top level (not nested under `agents`). | PASS |
| 2 | Migration: missing field on read returns `None`; first write populates | `test_load_missing_field_yields_none` (legacy state file without the key) + `test_load_explicit_null_yields_none`. `load_state` uses `.get('last_compose_checksum')` — None default. | PASS |
| 3 | Atomic write: `.tmp` then rename; mid-write failure leaves old file intact | `test_save_uses_tmp_then_rename` (no `.tmp` lingers, real file present). The atomic-write code path is harness's existing `save_state` contract — unchanged. | PASS |
| 4 | Field is a SHA256 hex string (64 chars) | `test_save_then_load_round_trip` + `test_save_overwrites_previous_checksum` use 64-char hex sentinels and verify exact round-trip through disk. Type-hint `str \| None`. Validation that the input IS hex/64-chars belongs to E1 (the writer); E2 just plumbs whatever the writer hands it. | PASS |
| 5 | Reads / writes coordinated with rest of state-file access (no separate lock) | `test_get_uses_self_lock` + `test_set_uses_self_lock` inspect source for `self._lock`. The shared lock is the existing `HarnessState._lock` used by all other state-file accessors. | PASS |
| 6 | Tests: missing field → None, write updates atomically, crash mid-write preserves | All three: `test_load_missing_field_yields_none`, `test_save_overwrites_previous_checksum`, `test_simulated_crash_mid_write_preserves_prior_state` (patches `Path.write_text` to raise OSError on `.tmp` write, confirms original file content unchanged). | PASS |

## Test Execution

`pytest tests/test_feat_10681_compose_checksum.py tests/test_harness.py -q --tb=short` on `8f27a3dd` → **198 passed** (11 new + 187 existing harness regression tests — no regressions).

`pytest tests/test_v1_byte_stability_9a.py -q` → **5 passed** (purely additive harness change does not touch compose path; gate stays GREEN).

## v1 Coexistence

Per PRD AC: "Pure state-file field; no compose path interaction." Diff confirms: only `references/scripts/harness.py` (HarnessState class) modified. No compose-side code touched. §9a green.

## Defense-in-Depth

- **Migration is two-shape** — `test_load_missing_field_yields_none` (key absent in legacy file) AND `test_load_explicit_null_yields_none` (key present but null). Both load as None; E1 treats either as "no compose has succeeded yet" and triggers compose on first boot.
- **`test_save_emits_null_when_unset`** documents the choice that null is persisted on first save (vs absent), preserving the absent/null distinction for legacy-file detection — which E1 will care about.
- **Lock-shape locked-in by source-inspect tests** (`test_get_uses_self_lock` / `test_set_uses_self_lock`) — a future refactor that splits the lock cannot silently break AC5; the test catches it at the source-text level.
- **`test_save_overwrites_previous_checksum`** confirms write-semantics: subsequent save replaces prior value (not merged, not skipped).

## Code Review Skip

Skill skipped external DeepSeek/Sonnet review per their own judgment that this is regression-risk-only additive plumbing (single new field + getter/setter mirroring existing AgentState pattern + tests mirroring `TestStatePersistence`). The diff is genuinely simple (+31 LOC, all in HarnessState class); 187 existing harness tests pass with the change. The state-file is critical infrastructure but the change is non-modifying (purely additive). QA verdict: trivial-skip is justified here — no high-blast-radius modification of existing fields.

## Outcome

All 6 ACs covered by 11 dedicated tests + 187 harness regression tests + §9a v1 gate. Plumbing is clean: field added, persisted, migration-safe, lock-coordinated, atomic-write-safe. E1 (#10680) can now build on top. **Transitioning #10681: pending-test → pending-ship.**
