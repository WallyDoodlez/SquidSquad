# QA-RESULTS-13857 (round 2)

**Verdict: PASS → pending-ship**

Round 1 (FAIL, back to in-progress) already established AC1/AC2/AC4 live-verified PASS; only AC3 (grep-audit) failed. This round verifies the AC3 fix and completes AC5.

## TC Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | PASS (carried from round 1, unchanged) | `git diff main...HEAD --stat` confirms every file underlying AC1 (the engine scripts, `SKILL.md`, etc.) is byte-identical to round 1 — only `test_vault_engine_boundary_13857.py` changed this round. Round 1's live, non-mocked evidence (real scratch install, real `vault-query.mjs` invocation, real top-K JSON + telemetry shard) still holds. |
| TC2 | AC2 (installer half) | PASS (carried from round 1, unchanged) | `wizard.py` byte-identical to round 1 — round 1's live, non-mocked `node`-stripped-`PATH` test still holds (`degraded: True`, `node: None`, install not blocked). |
| TC3 | AC2 (query half) | PASS (carried from round 1, unchanged) | Same unchanged code path — round 1's live confirmation (clean exit-127 "command not found" with `node` genuinely absent) still holds. |
| TC4 | AC3 | **PASS (fixed this round)** | The audit now scans EVERY `*.md`/`*.j2` file under `references/` (only the engine package itself excluded, correctly — its own `SKILL.md` teaches the ban). Independently re-derived: confirmed no vault-grep pattern exists outside `.md`/`.j2` anywhere under `references/` (broad extension sweep, zero hits beyond the already-covered scope). Independently re-counted both my previously-flagged files against the raw regex myself: `vault-reference.md` → 6 hits, `research.md.j2` → 1 hit — exact match to the new allowlist entries. Boundary suite 7/7. |
| TC5 | AC4 | PASS (carried from round 1, unchanged) | `--no-write` code path byte-identical to round 1 — round 1's live confirmation (zero telemetry events, zero new shard content) still holds. |
| TC6 | AC5 | **PASS (completed this round)** | Authored `tests/comprehension/13857_spec.json` independently (5 questions covering invocation syntax + required identity flags, metadata-only output contract, the raw-grep ban with rationale, `--no-write`, and honest degradation) and ran the live comprehension harness (`run_comprehension_test.py`, fresh agent, `SKILL.md` only, no other context): **5/5 PASS**. Refreshed the staleness baseline in-PR per the gate's own instructions (a same-PR spec+file pair — distinct from the vault learning about refreshing an *existing* baseline for a file a *different* PR is still changing, which is what that learning actually governs). |
| TC7 | — | PASS | `test_vault_engine_boundary_13857.py` + `test_vault_engine_13857.py` + `test_vault_engine_installer_13857.py`: 43/43. |
| TC8 | — | PASS | See "Ship gate" below. |

## Ship gate

- Official static gate (`tests/run_tests.py static`): first pass caught a genuine, expected gap — the new comprehension spec had no baseline entry yet (`test_no_silently_stale_comprehension_specs` FAILED with an explicit, actionable message). Ran `comprehension_staleness.py refresh 13857_spec.json` in-branch (the gate's own instructed remedy for a same-PR spec+file pair), re-ran: **PASS — 6060 gated test(s) passed (0 failures, 0 errors)**.
- Integration suite: first run showed a transient failure in `harness` (1) and `status_flow` (3 failures + 9 errors) — re-ran both immediately, both clean (`OK`, 5/5 and 12/12). Consistent with this session's established pattern of transient gh-API-load flakiness under heavy concurrent multi-agent activity (pm/skill/dm all active throughout), not a regression from this diff — the same two test files ran clean on this exact branch's content moments apart.

## Conclusion

All 5 ACs now verified with live, non-mocked, independently-re-derived evidence (AC1/AC2/AC4 carried from round 1 unchanged; AC3's fix confirmed complete via an independent re-scan; AC5's comprehension spec authored and run fresh, 5/5). Zero gaps. → **pending-ship**.
