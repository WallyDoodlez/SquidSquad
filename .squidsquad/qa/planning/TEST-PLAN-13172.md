# TEST-PLAN-13172 — fail-closed on wrong-type additional_includes

**Derived independently** from the issue body (skill-filed improvement-scan).

## Expected behavior
`compose._load_manifest_v2_from_file` must NOT silently reset a wrong-type `additional_includes` to `[]` (which silently drops a variant's sub-skills from the composed CLAUDE.md). It must fail closed (sys.exit(1)) with a stderr diagnostic, matching its same-branch sibling schema-error paths.

## ACs (independent)
- AC1 wrong-type (str / dict / int) → sys.exit(1) + stderr ERROR naming role + type
- AC2 valid list → base + additional concatenated (no regression)
- AC3 null / absent → normalizes to [] (no exit) — the `… or []` idiom

## Method
Direct invocation of `_load_manifest_v2_from_file` with temp manifests (base recursion patched to isolate the type guard). QA test (`tests/test_feat_13172_additional_includes_failclosed.py`) adds role-name + int coverage beyond skill's str/dict tests. No-regression: full `tests/test_compose.py`.

## Scope note
The function's reachability from the production deploy path post-E6 is a separate triage decision (skill-flagged) — not in this fix's AC scope; not a reblock.
