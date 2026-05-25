---
type: learning
tags: [migration, 6274, terminology, cutover]
created: 2026-05-23
updated: 2026-05-24
owner: skill-lead
status: active
confidence: high
source: code
links: []
---

## Context

#6274 generalizes the SquidSquad role taxonomy: `dev` → `worker` (base
role for technical implementation) and `qa` → `verifier` (base role for
verification). The rename rolls out across three sub-phases (D9):

- **6274.1** — dual-aware shim in `compose.py`, `config.py`,
  `tracker.py` so both old and new names work simultaneously.
- **6274.2** — directory rename (`references/roles/dev/` → `worker/`,
  `references/roles/qa/` → `verifier/`) plus the file-content sweep.
- **6274.3** — cutover. Old names rejected. Dual-tagging code removed.
  `role:dev` and `role:qa` labels deleted via `gh api`.

The transition window between 6274.2 merge and 6274.3 ship is **30
days**, measured from the 6274.2 merge commit timestamp. This note is
the canonical record of that target date.

## Content

**Target cutover date: 2026-06-23 (UTC).**

Computed as `T = merge_commit_timestamp + 30 days` per AC2.9 of CONTEXT-6274.md.
The AC2.9 commit timestamp 2026-05-24 (UTC) is used as the proxy for the
eventual 6274.2 merge timestamp — DM typically merges within hours of QA pass,
and the spec mandates pre-merge population. If the actual merge slips
materially (>72h), a Changelog addendum below records the corrected date.

The G1→2 gate verifies that this commit exists in the 6274.2 PR; the G2→3 gate
verifies the date has passed before 6274.3 ships.

## Rationale

- **Placeholder lands in 6274.1** (this note) so 6274.2 has exactly
  one canonical location to update — no risk of multiple sources of
  truth diverging during the rename sweep.
- **30 days** balances operator inertia (some installs may rebase
  their cycle scripts on a weekly cadence) against migration drag
  (the dual-aware shim is dead weight after the directory rename
  lands — every cycle pays a small import-time cost for the alias
  tables).
- **Vault note rather than config.md or a planning artifact** because
  the cutover date is an institutional decision that shapes future
  cycles' behavior (when do agents stop accepting old labels?). The
  vault is where decisions like this belong; planning artifacts get
  archived when the task ships and would lose visibility.

## Related

- `[[decision-branch-per-feature-workflow]]` — same workflow model.
- `.squidsquad/pm/planning/CONTEXT-6274.md` — locked decisions D1–D11.
- `.squidsquad/pm/planning/RESEARCH-6274.md` — blast-radius analysis.
- `references/scripts/migrate_labels_6274.py` — one-shot pre-cutover.
- `references/scripts/verify_dual_label_6274.py` — G2→3 gate verifier.

---

### Changelog

- 2026-05-23 — Created by skill-lead. Placeholder for AC1.6 of #6274 sub-phase 6274.1. The target cutover date is "TBD — populated in 6274.2 PR" per AC2.9.
- 2026-05-24 — Populated cutover date `2026-06-23 (UTC)` by skill-lead per AC2.9 of #9965 (6274.2). Computed as `commit_timestamp + 30 days` using the AC2.9 commit time as proxy for the merge timestamp.
- 2026-05-24 — Re-affirmed by skill-lead as the LAST commit in the 6274.2 PR (post the c9dabdb7 hardening commit) to satisfy AC2.9's "final commit" constraint. Cutover date unchanged at `2026-06-23 (UTC)`.
- 2026-05-25 — Re-affirmed again by skill-lead as the LAST commit (post 7e43a745 QA fix-up on test_manifest_registry.py shipped registry assertions). Cutover date unchanged at `2026-06-23 (UTC)`.
