# Code Review — #13132 (tracker.py gh-CLI fallback fail-closed)

**External model (DeepSeek via model_router) returned a degenerate sub-threshold
response (11 chars) → auto-fell back to a Claude (sonnet) reviewer per
[[feedback_model_router_auto_fallback]].** One iteration; converged.

## Findings (Claude sonnet review of `git diff --cached`)

**1. [LOW] `get_labels` could inject `""` for a label object missing `"name"`.**
`l.get("name", "")` on a malformed-but-valid-JSON payload like `{"labels": [{}]}`
returns `[""]` instead of dropping the entry; the mirrored `_get_issue_*_labels`
helpers avoid this via their `startswith()` filter.
→ **Disposition: FIXED.** Changed to
`[n for n in (l.get("name", "") for l in data.get("labels", [])) if n]`
(drops empties; matches the mirrored idiom). Added regression test
`test_get_labels_drops_nameless_label_objects`.

**2–6. [CLEAN].** Reviewer confirmed:
- `check=False` correctly passed at all three call sites.
- `_check_unread_feedback` fail-closed preserved — `JSONDecodeError` returns the
  same sentinel `[("unknown (API error)", "unknown")]`; no path now returns `[]`
  (proceed) on error.
- `get_state` `(data or {}).get("state") or "UNKNOWN"` mirrors the adapter path;
  non-zero / empty / malformed / missing-key all → `UNKNOWN`.
- Success (happy) paths unchanged.
- All regression tests exercise the new branches with correct assertions.

## Result
Sole finding folded; rest clean. 62 tests pass in `test_tracker.py`; full static
gate green (known-failure baseline only). → pending-test.
