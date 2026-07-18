---
type: learning
tags: [verifier, testing, static-gate, run_tests, known-failures, false-positive]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: [learning-single-static-gate-red-may-be-flake-rerun-before-reject, learning-edit-shared-fragment-run-full-static-gate]
---

## Context

Verifying #13531 (an isolated `harness.py` change), I ran a raw `pytest tests/`
as my no-regression check and got 48 `FAILED` lines across
`test_agent_boundaries.py`, `test_compose_author_comments_11142.py`,
`test_comprehension_2183/2195.py`, and `test_model_router_live.py` — none of
them anywhere near the PR's actual surface. It took a side-by-side worktree
comparison against clean `main` (same 48ish failures pre-existed) before I
found the real explanation: `tests/run_tests.py` maintains an explicit
`KNOWN_FAILURES` / `KNOWN_NON_STATIC` / `*_live` exclusion list (documented in
`CONTRIBUTING.md` itself — `python tests/run_tests.py static` is the canonical
command). Running the canonical command directly gave the correct,
immediate answer: 5679/5679 PASS, 0 failures, matching the PR's own claim.
Cost: roughly 25-40 minutes of two full raw-suite runs plus a baseline
worktree comparison, entirely avoidable.

## Content

**For the no-regression check, run `python tests/run_tests.py static` — never
a raw `pytest tests/` — as the FIRST move, not a fallback after raw pytest
looks alarming.** The raw invocation collects every `test_*.py` file
including ones deliberately quarantined for reasons that have nothing to do
with the change under review:

- `KNOWN_FAILURES` — files red for a *different*, already-tracked, still-open
  issue (e.g. blocked on OPEN #10360) — not stale-test debt, a live wait state.
- `KNOWN_NON_STATIC` — comprehension/CQ tests that spawn a live model; not
  offline-static by design.
- `*_live.py` suffix — live network/GitHub/model tests, excluded by pattern.

`tests/run_tests.py` prints a `NOTICE:` block naming every exclusion and its
reason on every run — read it before concluding a raw-pytest red list means
anything. A red raw-pytest run is not evidence of a regression; it's evidence
you used the wrong command.

**Verifier action:** default to the canonical gate command from the start of
every verification pass. If you ever DO see raw-pytest reds you can't
immediately map to a `KNOWN_*` entry, that's the moment to dig deeper (compare
against clean `main`, as `learning-single-static-gate-red-may-be-flake` covers
for single-test flakes) — but check the canonical command's clean output
first, since it usually resolves the question outright.

## How to apply

Whenever a TEST-PLAN/QA-RESULTS AC needs a "no regression" check: run
`python tests/run_tests.py static` directly. Only reach for a broader raw
`pytest tests/` sweep when you have a specific reason to suspect the
exclusion list itself is stale or wrong (rare, and itself a separate finding
to file, not a verification blocker).
