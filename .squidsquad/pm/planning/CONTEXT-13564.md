# CONTEXT-13564 — cycle-input diet: strip GitHub label ballast and cap embedded comment bodies

**Light mode** (small, well-scoped code/data-shape change; research already covered by `PLAN-TOKEN-EFFICIENCY.md` §T4, ACs already fully specified at filing time). Confirmed with operator 2026-07-18 ("go ahead") after walking through the plain-language explanation.

## Scope

`cycle_pre.py`'s `_gh_fetch` post-processing strips full GitHub label objects (id/name/description/color) down to bare `name` strings, and caps embedded comment bodies at ~500 chars with a truncation suffix, in the `cycle-input.json` PM (and other roles) read every cycle. Target: PM cycle-input drops from 29KB to under 15KB on the current open-issue set.

## Locked Decisions (human decided)

- Proceed with the fix as scoped in the issue body (labels → name-only strings, comments → ~500-char cap) — no changes to which issues/fields are fetched (that stays out of scope, per the issue body).

## Worker Discretion (worker agent can choose)

- Exact truncation suffix wording (issue body suggests `…(read the issue)` as a model, not a hard requirement).
- Where in `_gh_fetch`'s post-processing pipeline the stripping/capping happens, as long as before/after size is measured and reported in the PR body per the ACs.

## Side Effect Mitigations (required)

- Before deleting label `id`/`color`/`description` fields, grep `cycle_pre.py` builders and the composed `CLAUDE.md` references to `cycle-input` fields to confirm nothing downstream reads anything but the label `name` — this is an explicit AC, not just guidance.
- Regression check: existing transition/pickup-logic tests must still pass (labels are resolved from `name` only).

## Upgrade Path (required)

- N/A — no upgrade impact (internal data-shape change to a generated per-cycle file, not a schema/config change existing installs need to migrate).

## Out of Scope

- Changing `gh` query limits or which issues are fetched (per issue body).
