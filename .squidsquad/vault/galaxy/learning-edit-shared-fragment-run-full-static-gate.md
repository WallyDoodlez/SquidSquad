---
type: learning
tags: [qa, verification, static-gate, sub-skills, common-events, regression, invariant-tests]
created: 2026-06-19
updated: 2026-06-19
owner: verifier-lead
status: active
confidence: high
source: observation
links: [learning-fix-inverting-an-invariant-is-a-regression, learning-suite-exit-code-not-proof-of-all-pass, pattern-runtime-loaded-subskill-change-no-recompose]
---

## Context

Verifying #12912 (deploy-signal recompose model). The PR edited
`references/sub-skills/common-events/event-mode-contract.md` (added a Case E
deploy-signal bullet). Feature-specific tests (test_harness_deploy_12912,
test_event_catalog, etc.) were all green — 368 passed. But the FULL static gate
FAILED on `test_event_mode_fragments.py::TestAc5NoModeConditional`: the new
loop-mode bullet wrote "via `cycle_pre.py`'s pull", and `cycle_pre` is on the
AC-5 FORBIDDEN-token list — common-events fragments MUST be mode-agnostic. The
implementer's "run_tests.py → exit 0" claim disagreed with my independent
branch-HEAD run (exit 1); the bullet was likely added in a late DS-audit iter
without re-running the full gate.

## Content

**When a task edits a SHARED runtime fragment (`references/sub-skills/`,
especially `common-events/` and `common/`), run the FULL static gate, never just
the feature's own tests.** Cross-cutting *invariant* tests for these fragments
live in their OWN test files the feature author usually doesn't touch and may not
know exist:

- `test_event_mode_fragments.py` — forbidden mode-conditional tokens
  (`cycle_pre`, `cycle_post`, `/loop`, `event-driven:`, `if /loop`, `30-minute`),
  wikilink resolution, topic-coverage headers (common-events fragments).
- `test_galaxy_notes_have_frontmatter` — YAML frontmatter on vault galaxy notes
  (cf. [[learning-fix-inverting-an-invariant-is-a-regression]] / my own gate-break).
- manifest-completeness gates (`installer-files.txt` listed-or-allowlisted).

Why feature tests miss it: they exercise the feature's *behavior*; the invariant
tests enforce *global properties of the file class*. A behaviorally-correct edit
can still violate a class-wide rule. This is the same root as
[[learning-suite-exit-code-not-proof-of-all-pass]] — a green subset is not a green
whole.

**Verifier action:** for any PR touching `sub-skills/` or `vault/`, the
no-regression evidence MUST be a full `run_tests.py static` (fail-closed, #12408),
captured to a readable file so the failing-test name survives (background capture
keeps only the tail). Prove regression vs pre-existing by running the specific
failing test on `origin/main` (passes) vs the branch (fails) before rejecting.
