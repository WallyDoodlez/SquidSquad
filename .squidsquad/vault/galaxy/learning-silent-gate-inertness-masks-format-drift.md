---
type: learning
tags: [tc_coverage, ship-gate, tracker, verifier, file-discovery, regression-testing]
created: 2026-07-19
updated: 2026-07-19
owner: skill
status: active
confidence: high
source: incident
links: [learning-single-static-gate-red-may-be-flake-rerun-before-reject]
---

## Context

`tracker.py`'s pending-test → pending-ship transition runs a TC coverage
gate documented as "NEVER bypassed, even with --force" (tracker.py:1577).
It delegates to `tc_coverage._discover_files(issue_number)` to locate an
issue's `TEST-PLAN`/`QA-RESULTS` files by globbing `.squidsquad/*/planning/`.

## Content

Filed and fixed as #13737: the discovery glob only recognized the pre-#9184
legacy naming shape (`*-<N>-TEST-PLAN.md`), never the current
`TEST-PLAN-<N>.md` (number last) convention that's been in effect for the
~2 months since #9184 shipped. Every real post-#9184 issue's discovery call
silently returned `(None, None)`, which short-circuits `transition()`'s gate
block (`if tp is not None:` never entered) — the gate never ran, but also
never warned. It looked exactly like a passing gate from the outside: no
error, no log line, `sys.exit(0)` behavior throughout.

**The deeper finding**: because nothing was checking format compliance for
2 months, verifier's actual `QA-RESULTS-<N>.md` authorship practice drifted
away from the documented `TC-N`-keyed template (`verification-templates.md`)
toward an "AC Walk" table with zero `TC-N` rows. Fixing the discovery bug
alone (without addressing this) would have flipped the gate from
silently-inert to hard-blocking essentially every future ship, since
`check_coverage()` would report 0/N coverage against every real file. Filed
that as a separate issue (#13738, high severity, routed to verifier) rather
than silently loosening the parser to accept the drifted format — that's a
content/practice decision belonging to the artifact's owner, not a call to
make unilaterally while fixing an unrelated discovery bug.

## Rationale

Two independent lessons, both general:

1. **A "never bypassed" gate whose activation depends on file-discovery
   logic is exactly as strong as that discovery logic** — and discovery
   logic (globs, path patterns) rots silently when a naming convention
   changes elsewhere, because nothing fails loudly when it stops matching.
   Any hard gate built this way needs its OWN regression test asserting it
   actually finds real current-format files — not just that its pass/fail
   arithmetic is correct once files are handed to it directly (the
   pre-existing test suite here had 43 tests for `check_coverage()`'s logic
   and zero live-format coverage for `_discover_files()` against the
   convention actually in use).
2. **A gate's inertness compounds** — the longer a check silently no-ops,
   the more the thing it was checking drifts, because nothing corrects it.
   Discovering gate #1 is broken is a signal to check whether the artifacts
   it was supposed to gate have ALSO drifted, not just to fix the gate and
   move on.

## How to apply

When fixing a "should have caught this" gate: (1) fix the mechanical bug,
(2) add a regression test using realistic current-format fixtures, not just
synthetic ones, (3) actually run the fixed gate against real current
artifacts before shipping to see what it reports now that it's live, (4) if
it surfaces a second problem the inertness was masking, disclose it loudly
and route it to the owning role rather than silently reconciling it
yourself — the scope of "fix the gate" and "fix what the gate now reveals"
are usually different owners' work.
