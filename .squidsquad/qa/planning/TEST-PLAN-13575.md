# TEST-PLAN #13575 — comprehension-spec staleness gate

**Derived from my own issue body's contract (my own filed improvement-scan finding) — independent reading.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | A checked-in baseline maps each spec naming a fragment to that fragment's blob sha as of last review |
| AC2 | The gate FAILS when a named fragment's committed sha drifts from the baseline (fragment changed, spec not re-reviewed) |
| AC3 | The gate FAILS when a fragment-naming spec is entirely missing from the baseline (new spec, never consciously paired) |
| AC4 | `superseded_by` specs are permanently exempted (not re-flagged forever) |
| AC5 | Not auto-invalidating — a mechanical prompt for review, not a content judgment |
| AC6 | My own `13175_spec.json` → `superseded_by: 13569` annotation (made ad hoc during #13569's verify) is preserved verbatim, not overwritten |
| AC7 | Remediation tooling (`refresh`) exists and works correctly, including pruning entries for deleted specs while preserving `_note` metadata |
| AC8 | No regressions; static gate clean modulo already-tracked, unrelated residuals |

## Verification (branch squidsquad/task/13575, freshly fetched, merged with current origin/main — 2 commits ahead)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | Live `comprehension_staleness.py check` on combined state | **exit 0, clean** — baseline in sync with HEAD |
| TC2 | AC2 (**decisive, my own falsification, not the worker's unit tests**) | Appended a line to a REAL fragment (`references/sub-skills/common/l4-curation.md`, backing a real spec `10659_spec.json`), committed it, re-ran `check()` | **Correctly flagged**: `"10659_spec.json <- ...l4-curation.md changed since last review (baseline 638aff62b != HEAD b0c7e8767)"`, exit 1. Reverted (`git reset --hard HEAD~1`) — confirmed back to clean (exit 0) |
| TC3 | AC3 (**my own falsification**) | Dropped a new spec file naming a real, existing fragment but absent from baseline, re-ran `check()` | **Correctly flagged**: `"99999_spec.json: not in baseline"`, exit 1. Removed the test file — confirmed back to clean |
| TC4 | AC4 | `check()` skips any spec with `superseded_by` present regardless of drift (code path read directly: `if "superseded_by" in spec: continue`) | Confirmed by code read + the passing baseline check with `13175_spec.json` present and drifted-but-superseded |
| TC5 | AC6 | Live read of `13175_spec.json` on combined state: `superseded_by` == `13569`, `superseded_note` present | Confirmed — my ad hoc annotation from the #13569 pass landed verbatim, not paraphrased or dropped |
| TC6 | AC7 | Worker's own `test_refresh_prunes_deleted_specs_and_keeps_note` + my own read of `refresh()`'s prune logic | Prunes non-`_`-prefixed keys absent from the live spec set; `_note` (and any `_`-prefixed key) always survives |
| TC7 | — | Live-verified the two claimed "real staleness events caught during development" | Confirmed via baseline `_note` history + git log: (1) a main-merge sha drift re-baseline, (2) my own new `13579_spec.json` correctly flagged as unbaselined then refreshed in — both genuine, not fabricated claims |
| TC8 | AC8 | Full `tests/test_comprehension_spec_staleness_13575.py` | **10/10 PASS** |
| TC9 | AC8 | Full static gate on combined state | 1 failure, 0 errors, 5521 gated — confirmed this is `#13582`'s fix (`inject-permissions.ps1`) **not yet merged to `origin/main`** at test time (PR #13583 still OPEN, `mergedAt: null` per live `gh pr view`) — a timing artifact, not a regression from this PR. Re-confirmed identical single-file failure signature. |

## Verdict: PASS

The gate does exactly what it claims, verified via my own live falsifications
(not just trusting the worker's mocked unit tests) against two real fragment/
spec pairs pulled from the live corpus — both the sha-drift and
missing-baseline paths fire correctly and were cleanly reverted. My own prior
ad hoc `13175_spec.json` annotation survives byte-for-byte. The design
decision to reject naive date-comparison (~40 false positives on any
unrelated fragment edit) in favor of an explicit review-baseline is sound and
documented. The one static-gate failure present is `#13582`'s not-yet-merged
fix, unrelated to this PR.
