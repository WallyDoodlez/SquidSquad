# TEST-PLAN-13592 — greenfield default spec: stack-appropriate worker + verifier/dm

**Source**: GitHub issue #13592 body (Observation + Impact, no formal AC list — bug report shape).
**Derived without reading the diff first.**

## Acceptance Criteria (derived from the issue's stated problems)

- **AC1**: A confident stack signal (mobile language, recognized frontend/backend framework) renames the default worker off `skill` to a generic/stack-appropriate identity for a foreign install.
- **AC2 (non-regression, explicitly claimed by the fix's own PR summary)**: An ambiguous/signal-less scan — **including SquidSquad's own self-dev repo** — preserves the original `skill` id/alias/variant unchanged.
- **AC3**: The default `--yes` spec includes all 4 role classes (pm, worker, verifier, dm), not just pm+worker.
- **AC4**: Full regression + static gate pass.

## Test Cases

### TC-1 (covers AC1): Live confident-signal reproduction
- **Steps**: Created a REAL fixture directory (`package.json` declaring `react`, a `.jsx` file) and ran the actual `repo_scan.scan()` against it (not a mocked scan dict), then `generate_default_spec`.
- **Expected**: `languages=['javascript']`, `frameworks=['react']`; worker id/alias != `skill`.
- **Result**: PASS — worker renamed to `worker`, variant `web`, matching verifier/dm variants.

### TC-2 (covers AC3): Role completeness
- **Steps**: Same run + the signal-less throwaway-target run.
- **Expected**: `{pm, worker, verifier, dm}` all present.
- **Result**: PASS in both runs.

### TC-3 (covers AC2, DECISIVE): Live self-hosted non-regression check — FAILED
- **Steps**: Ran the REAL `repo_scan.scan(".")` against THIS actual SquidSquad repo (the exact case the PR's own summary calls out: "An ambiguous/signal-less scan (including SquidSquad's own self-dev repo) falls back to the original 'skill' id/alias/variant unchanged") — not a mocked/constructed scan dict.
- **Expected** (per the PR's own claim): worker id/alias == `skill`.
- **Result**: **FAIL.** `repo_scan` detects `languages=['javascript', 'python']`, `frameworks=['fastapi']` on this repo (harness.py uses FastAPI). `fastapi` is in `_infer_project_type_from_scan`'s `backend_frameworks` set, so it returns `"backend"` — a CONFIDENT signal, not ambiguous. `generate_default_spec(".")` therefore renames the worker to `worker` (variant `web`), directly contradicting the stated self-dev-preservation guarantee. Reproduced deterministically (3 separate runs, identical result).

## Coverage matrix
- AC1 → TC-1 (PASS)
- AC2 → TC-3 (**FAIL** — decisive, live, reproducible)
- AC3 → TC-2 (PASS)
- AC4 → worker's own 13/13 tests PASS (all use mocked/constructed scan dicts — this is exactly why TC-3's gap was invisible to them)
