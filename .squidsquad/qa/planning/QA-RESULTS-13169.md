# QA-RESULTS-13169 — comprehension live tests fail vs skip (result-id Q- echo mismatch)

**Verdict: PASS — zero gaps.** PR #13268 merged (squash). (verifier-filed; fixed via my RCA lead — the `_get_result('Q-1' vs '1')` id-key mismatch.)

## Root cause (confirmed)
The eval prompt presents questions as `### Q-<id>` headers; the judge LLM echoes `Q-1` as the result id, but the spec + every `test_comprehension_*` key on the bare id → `_get_result`/`test_all_questions_answered` fail even on a correct PASS. Isolated runs cache-hit→skip so it only showed when files ran live together.

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | judge-echoed `Q-<id>` normalized to bare id before results.json write | PASS |
| AC2 | bare id passes through unchanged | PASS |
| AC3 | single-strip only (`Q-Q-1`→`Q-1`); no over-strip | PASS |
| AC4 | **hyphenated-slug ids preserved** (`Q-1-grammar-scope`→`1-grammar-scope`, `Q-detection-durable-vs-oneoff`→…) | PASS |
| AC5 | case + whitespace (`q-`, ` Q-3 `) handled; non-string coerced | PASS |
| AC6 | end-to-end: judge returns `Q-1` → results.json on disk carries `1` | PASS |
| AC7 | original repro resolved (files run together no longer false-fail) | PASS |

## Evidence
- Code (run_comprehension_test.py): `_normalize_result_id` strips one leading `Q-`/`q-` (+ strip whitespace, `str()` coerce); applied to every result before `results_path.write_text`. Prompt tightened to request the bare id; display line `Q-{id}`→`Q[{id}]` (no double-prefix on CQ-slugs).
- skill tests (`TestResultIdNormalization13169`, 5): strip / bare-unchanged / single-strip / **end-to-end judge-echo→results.json** / prompt-instructs-bare. All PASS.
- **QA independent test** (`tests/test_feat_13169_normalize_id_real_spec_slugs.py`): exercises the **real-spec hyphenated-slug formats** (`1-grammar-scope`, `detection-durable-vs-oneoff`, `CQ1`) that skill's tests don't — confirms internal hyphens are preserved and only the leading `Q-` is stripped. ALL PASS.
- **Decisive integration repro** (the issue's exact command, live-model env): `pytest tests/test_comprehension_9184.py tests/test_comprehension_361.py` → **8 passed, 4 skipped in 74.5s** (9184 ran LIVE and PASSED; 361 skipped clean). Was **"12 failed in 118.80s"** pre-fix. Symptom resolved end-to-end.

## Notes
- **No CQ spec** (and none authored): the prompt change is LLM-consumed, but correctness rests entirely on the deterministic `_normalize_result_id` (it catches any judge echo regardless of prompt compliance). A CQ spec for the comprehension harness's OWN judge prompt would be circular. The prompt tightening is belt-and-suspenders only.
- Comprehension tests are excluded from the static gate; this was live-suite hygiene — now clean.

Status: pending-test → pending-ship.
