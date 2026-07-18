# TEST-PLAN #13562 — working-state.md unbounded embed in cycle-input.json

**Derived from the issue body's own contract ("Expected"/"Implementation guidance") — my own independent reading, not the worker's diff.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | Structured fields (Task/Status/etc.) still parse from the FULL working-state.md regardless of size |
| AC2 | `raw_content` embedded in `cycle-input.json` is capped at ~8KB |
| AC3 | Truncation keeps the TAIL (journals append; newest = actionable), not the head |
| AC4 | An explicit marker referencing #13562 is present when truncated, instructing the agent to rewrite the file to spec shape |
| AC5 | Files under the cap embed verbatim — no marker, no mutation |
| AC6 | Marker/embed starts at a clean line boundary — no mid-line fragment leak, including the edge case where the tail's only newline is its very last byte |
| AC7 | Multibyte UTF-8 sequences at the truncation boundary never crash |
| AC8 | Symmetric `cycle_post` warning (same threshold, no drift) on an oversized write — warn-only, the write itself still succeeds in full (file is agent-owned; git keeps history) |
| AC9 | Regression tests use only synthetic fixtures — never mutate live role state |
| AC10 | Config `Context Threshold` 70→75 bump is explicitly sequenced AFTER this PR merges — must NOT be bundled into this PR |
| AC11 | No CQ spec required (marker is runtime-generated diagnostic output embedded in cycle-input.json, not a change to a CLAUDE.md/sub-skill/SOUL.md source file) — worker flagged this call for verifier veto; independently concurred, see Verdict below |

## Verification (branch squidsquad/task/13562 combined with current main, freshly fetched)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | PR's own `test_structured_fields_parse_from_full_file_despite_cap` | PASS |
| TC2 | AC2, AC3, AC4 | PR's own `test_oversized_raw_is_capped_with_marker_and_tail` (200KB fixture) | PASS |
| TC3 | AC5 | PR's own `test_small_file_embedded_verbatim_no_marker` + `test_cap_boundary_exact_size_not_truncated` | PASS |
| TC4 | AC6 | PR's own `test_tail_ending_partial_line_yields_marker_only` (DS-13562 F1) | PASS |
| TC5 | AC7 | PR's own multibyte parametrized test (2/3/4-byte chars, DS-13562 F3) | PASS |
| TC6 | AC8 | PR's own `test_oversized_write_warns_but_still_writes` + `test_lean_write_no_warning` | PASS |
| TC7 | full `test_cycle_pre.py` + `test_cycle_post.py` on combined state | regression check | **262/262 PASS** |
| TC8 (independent, not the worker's fixture) | AC1, AC2, AC3, AC4 | **My own** 250KB synthetic journal fixture (different shape/content from the PR's own test), fed through the real `_read_working_state` via a throwaway temp dir (never touching live `.squidsquad-state/`): task/status parsed correctly from the full file; capped to 8453 bytes; newest cycle line present, oldest absent; marker text correct and referencing #13562 | **PASS** |
| TC9 (independent) | AC5 | Ran the real function against my own qa role's actual live `.squidsquad-state/qa/working-state.md` (231 bytes, under cap) — `raw_content` byte-identical to the file, no marker | **PASS** |
| TC10 (independent) | AC8 | My own live call to `cycle_post._do_working_state_update` with an 11KB synthetic update (not the worker's fixture) — stderr WARNING fires referencing #13562 and the role, AND the file is written in full (not truncated) | **PASS** |
| TC11 (independent) | AC10 | `git diff origin/main...HEAD -- .squidsquad/config.md` — empty; `Threshold` still 70 in current config.md | **PASS — correctly deferred, not bundled** |
| TC12 | AC9 | `squid_dir`/`patch_dirs` fixtures in `test_cycle_pre.py`/`test_cycle_post.py` are `tmp_path`-rooted — confirmed isolated, no live-state path used | **PASS** |
| TC13 | full static gate on combined state | `python tests/run_tests.py static` | 3 failures, 5495 gated — **identical to the pre-existing #13577 finding** (confirmed disjoint from origin/main baseline during #13556's verify), **0 new failures from #13562** |

### AC11 (CQ-gate call) — independent judgment

The `[TRUNCATED (#13562): ...]` marker string is generated at runtime and
embedded in `cycle-input.json`, which agents read as **data**, not as a
modification to any `CLAUDE.md` fragment, sub-skill, or `SOUL.md` file. The
comprehension-testing standard (#9184) gates changes to LLM-consumed
**instruction files**; a diagnostic string produced by a Python function at
cycle-pre time is categorically the same class as any other `cycle-input.json`
field (e.g. `context_pressure`, `pull_result`) — informational payload, not an
instruction-file edit. Concur with skill's read: **no CQ spec required.**
Separately sanity-checked the marker text itself for clarity/actionability
(not a formal CQ harness, just a plain read): it names the file, its size, the
spec shape, the cap, and the corrective action in one sentence — unambiguous.

## Verdict: PASS

All 11 ACs hold, corroborated independently (not just re-running the worker's
own suite) via a differently-shaped 250KB fixture, a live check against real
(small) role state, a live write-side warning check, and a direct config.md
diff confirming the sequencing contract. Full `test_cycle_pre.py` +
`test_cycle_post.py` combined-state run: 262/262, 0 regressions. The 3 static
gate failures present are the pre-existing, already-filed #13577 (confirmed
disjoint in the #13556 verify pass) — not caused by this PR.
