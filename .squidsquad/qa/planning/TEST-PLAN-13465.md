# TEST-PLAN-13465 — tracker.py create-issue --role qa role-label filter

**Source**: GitHub issue #13465 (DM bug report) + fix contract. Derived without reading the worker's test file.

## Acceptance Criteria (derived)

- **AC1** — `create-issue --role qa` SUCCEEDS (exit 0) and stamps `role:qa`, NOT the non-existent `role:verifier`.
- **AC2** — `--role verifier` also succeeds: drops the non-existent `role:verifier`, keeps `role:qa` (primary NOT force-kept — #13465 Finding-1).
- **AC3** — Non-dual roles (skill/pm/dm/designer) unchanged: emit exactly `role:<role>`.
- **AC4** — Safe-degrade: if the repo-label lookup is empty/unavailable, fall back to the primary `role:<role>` so the issue always carries a role label.
- **AC5** — Regression test ships covering the alias-absent (bug), alias-present (dual resume), non-dual, and degrade cases.

## Test Cases

### TC-1 (AC1) — LIVE E2E: create-issue --role qa succeeds, correct labels
- **Steps**: run real `tracker.py create-issue --role qa ...` against the live forge; capture number; read labels; close artifact.
- **Expected**: exit 0; labels include `role:qa`, exclude `role:verifier`.
- **Result**: PASS — created #13475, labels [type:issue, role:qa, squidsquad, status:open, severity:low]; closed. (One-time live evidence; not promoted.)

### TC-2 (AC1/2/3) — filter against REAL repo taxonomy
- **Steps**: live `_filter_role_labels_to_existing(_build_dual_role_labels_6274(r), r)` for r in {qa, verifier, skill}.
- **Expected**: qa->'role:qa'; verifier->'role:qa'; skill->'role:skill'.
- **Result**: PASS (live).

### TC-3 (AC1) hermetic — qa dual filtered to role:qa (stubbed taxonomy)
### TC-4 (AC2) hermetic — verifier dual -> role:qa (primary not force-kept)
### TC-5 (AC3) hermetic — skill/pm/dm/designer unchanged
### TC-6 (AC4) hermetic — empty/degraded taxonomy -> fallback primary role:<role>
### TC-7 (AC5) — worker regression test present

## Coverage matrix
- AC1 -> TC-1, TC-2, TC-3
- AC2 -> TC-2, TC-4
- AC3 -> TC-2, TC-5
- AC4 -> TC-6
- AC5 -> TC-7

## Comprehension Questions
N/A — executable Python (tracker.py), not LLM-consumed instructions.
