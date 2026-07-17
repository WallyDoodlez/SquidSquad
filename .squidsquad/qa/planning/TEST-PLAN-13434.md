# TEST-PLAN #13434 — build_config_md<->FIELD_MAP round-trip gate

**Derived from the issue body "Suggested fix" — not the diff.**

Bug class: `build_config_md` (emit side, wizard.py) has twice written a config
field under a heading `config.py`'s FIELD_MAP (read side) does not read — #13328
(interval/threshold under dead `## Loop`) and #13355/#13421 (`PR Flow` under
dead `## Flags`). The existing #5366 guard checks FIELD_MAP against a
hand-maintained SAMPLE_CONFIG fixture, not against build_config_md's actual
output, so emit/read drift slips through.

## Acceptance Criteria (independent reading — scope = test-only gate, no production change)

| AC | Contract |
|----|----------|
| AC1 | A round-trip invariant test exists: render `build_config_md(spec)`, assert `config._parse_field` reads back every FIELD_MAP-covered dedicated-section field |
| AC2 | The gate would have caught the #13328 incident (interval/threshold under `## Loop`) |
| AC3 | The gate would have caught the #13355/#13421 incident (PR Flow under `## Flags`) |
| AC4 | Negative control: reintroducing a dead-heading regression makes the gate FAIL (proves it's a real gate, not vacuous) |
| AC5 | Guard-the-guard: a typo'd allowlist short-name (not in FIELD_MAP) is itself caught |
| AC6 | No production code changed (test-only); real `generate_default_spec()` output also round-trips |

## Verification

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | `test_every_dedicated_section_field_reads_back` — 23-field positive allowlist, all round-trip | **PASS** |
| TC2 | AC2, AC3 | `test_historically_dead_pairs_carry_spec_values` — exact-value check for `interval`/`context-threshold` (#13328) and `auto-merge`/`pr-flow` (#13355) | **PASS** |
| TC3 | AC4 | Independent negative-control repro (outside the PR's own test file): rendered spec text, replaced `## Iteration Interval` -> `## Loop`, confirmed `_parse_field` flips from `'20'` to `None` | **PASS — gate is non-vacuous** |
| TC4 | AC5 | `test_allowlist_keys_exist_in_field_map` | **PASS** |
| TC5 | AC6 | `test_generated_default_install_round_trips` (real `generate_default_spec()`); PR diff = test file only (`gh pr view --json files`) | **PASS** |

## Branch-staleness handling

`squidsquad/task/13434` forked from `8b8bf7b82` — **before** #13323's docstring
fix landed on main (`c161bbd1c`). Running the gate on the bare branch tip
produced 2 false failures in my own previously-promoted
`test_feat_13323_no_stale_start_sh_docstrings_qa.py` (comparing against the
pre-#13323 wizard.py). Confirmed via `gh pr view --json files` that PR #13538
touches only the new test file (no wizard.py overlap) — resolved by a local
`git merge origin/main --no-edit` (no push) to verify the actual combined
state that will exist after merge. Full static gate on combined state: **5412
gated, 0 failures, 0 errors**.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (test-only file, not an LLM-consumed instruction).
- No worker unit-test gap to flag — the deliverable IS the test.
