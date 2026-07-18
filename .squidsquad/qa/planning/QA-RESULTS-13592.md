# QA-RESULTS-13592

## Summary
REJECTED — back to in-progress. AC1/AC3 confirmed live (including a real, unmocked `repo_scan` against an actual React fixture). AC2 — the PR's own explicitly stated non-regression guarantee ("SquidSquad's own self-dev repo... falls back to the original 'skill' id/alias/variant unchanged") — **fails live and is reproducibly false**: running the real `repo_scan.scan(".")` against this actual repo detects `fastapi` (harness.py's dependency) as a confident backend-framework signal, and `generate_default_spec(".")` renames the worker off `skill` to `worker`.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Real `repo_scan` against a fixture React app (`package.json` + `.jsx`): worker renamed `worker`, variant `web` |
| AC3 | PASS | All 4 role classes (pm/worker/verifier/dm) present in both the signal-less and confident-signal live runs |
| AC2 | **FAIL** | Real `repo_scan.scan(".")` against THIS repo: `languages=['javascript','python']`, `frameworks=['fastapi']` → `_infer_project_type_from_scan` returns `"backend"` (a confident signal, not ambiguous) → `generate_default_spec(".")` renames the worker to `worker`. Reproduced 3× deterministically. |
| AC4 | worker's own 13/13 PASS | All use mocked/constructed `scan_data` dicts — none run a real `repo_scan` against an actual repo with mixed-language/dependency signal, which is exactly why this gap was invisible to the worker's own suite |

## Decisive finding — AC2, self-hosted non-regression claim is false

The PR's own summary states the design intent explicitly: *"An ambiguous/signal-less scan (including SquidSquad's own self-dev repo) falls back to the original 'skill' id/alias/variant unchanged — preserving existing self-dev install behavior."* This is directly testable and directly false: `_infer_project_type_from_scan`'s `backend_frameworks` set includes `"fastapi"`, and this repo's `harness.py` uses FastAPI — so a real scan of this repo is NOT signal-less, it confidently infers `"backend"`.

**Why this matters beyond "an edge case"**: this isn't a hypothetical foreign repo — it's THIS repo, the one every self-hosted agent (including me) runs from. If `generate_default_spec` or `wizard.py generate-defaults`/`setup-yes` is ever invoked against this repo again (a repair script, a migration test, an accidental re-scaffold), the worker's id/alias silently flips from `skill` to `worker` — breaking every `role:skill` label, every `ROLE_AUTHORITY`/alias-registry entry keyed on `skill`, and the entire self-hosted team's identity model. The worker's own tests never caught this because none of them run a real `repo_scan` against a repo with genuinely mixed signals (all construct a scan dict by hand, choosing values that don't include a backend framework alongside self-dev-shaped content).

**The underlying design gap**: `_infer_project_type_from_scan` treats "any confident framework signal, anywhere in the repo" as proof the repo IS that stack — it has no way to distinguish "this repo's actual product is a FastAPI backend" from "this repo happens to use FastAPI as one dependency of its own tooling" (SquidSquad's harness.py). A safer heuristic would need either an explicit self-dev opt-out (e.g., detect the SquidSquad repo itself specifically) or a materially stronger confidence bar than "framework name appears in the scan."

## Zero-gap check
FAILS. Not a minor/cosmetic gap — this is a live, reproducible contradiction of the fix's own stated non-regression guarantee, on the actual repository the guarantee was specifically written to protect.

## What's needed to re-pass
1. Either add an explicit self-dev detection (this repo specifically, or a `.squidsquad/` marker indicating an EXISTING self-hosted install — `generate_default_spec` should probably never run against an already-initialized repo in the first place) so the fallback genuinely holds for self-dev, or tighten `_infer_project_type_from_scan`'s confidence bar so incidental tooling dependencies (like FastAPI powering an internal harness) don't trigger a stack inference.
2. Add a regression test that runs `generate_default_spec` against a REAL `repo_scan` of THIS repo (not a constructed dict) and asserts the worker stays `skill` — the exact live check that caught this gap.
3. Re-verify AC1/AC3 are unaffected by whatever fix is chosen.

## Verdict
FAIL. Back to In Progress with the above concrete, narrow fix list.
