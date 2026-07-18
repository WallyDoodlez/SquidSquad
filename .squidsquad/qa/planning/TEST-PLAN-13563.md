# TEST-PLAN-13563

Derived independently from `.squidsquad/pm/planning/CONTEXT-13563.md` (the AUTHORITATIVE SCOPE per the issue body's banner — read in full, not just the issue body summary) plus the issue body's own AC list. This went through PM's full task-intake lifecycle (pending→planning→planned→approved), not an auto-approved bug.

## ACs (from CONTEXT-13563.md + issue body, cross-checked)

- **AC1**: BRIEFING.md at/under the 2000-token budget after the one-time trim; graduated content lands in `vault/archives/` with a pointer.
- **AC2 (CQ, verifier-owned)**: The every-cycle staleness check treats budget overage as must-fix (trim-on-contact), verified by a CQ scenario where a fresh agent encounters an over-budget BRIEFING result. Skill's own comment explicitly deferred CQ-spec authorship to me per the #9184 boundary (worker doesn't self-generate CQ specs) — I author it independently, not reused from the worker.
- **AC3**: No loss of operator-facing sections (Active Priorities / Recent Decisions / Constraints / Team State) — condensed, not deleted.
- **AC4 (Locked Decision compliance)**: Archive destination is `vault/archives/`, following the `archives/shipped-pre-2026-05-19.md` precedent — per CONTEXT-13563.md's Locked Decisions (human-confirmed), not a worker discretion call.
- **AC5**: No regressions — new tests pass; full static gate passes; comprehension_staleness clean.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | `python references/scripts/vault_remember.py briefing-budget` on the real repo state → 521 remaining (positive = under budget). `wc -l` → 56 lines. Manual word-count → ~1138 words / ~1479 estimated tokens, well under 2000 |
| TC2 | AC2 (independent CQ) | Authored `tests/comprehension/13563_spec.json` independently from CONTEXT-13563.md/issue AC2 (not from the worker's PR). Spawned a fresh sonnet `general-purpose` subagent given ONLY `vault-remember.md`, no other file/tool/prior knowledge; graded 4 questions |
| TC3 | AC3 (live) | `grep -n "^## " BRIEFING.md` → confirmed Active Priorities/Recently Shipped/Recent Decisions/Constraints & Blockers/Team State all present as headers |
| TC4 | AC4 (live) | Confirmed both archive files exist (`briefing-active-priorities-2026-06-15-to-07-17.md`, `shipped-2026-05-19-to-2026-06-21.md`), both referenced by pointer in BRIEFING.md, and spot-checked a genuinely-preserved fact (#13215's full context) survives verbatim in the archive |
| TC5 | AC5 | `tests/test_13563_briefing_budget_corrective.py` (12 cases); `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` (after registering the new spec's baseline) |

## Note
BRIEFING.md's one-time trim landed as a separate direct-to-main commit (not part of the feature PR) since `.squidsquad/vault/` is a state path stripped from feature PRs by the #11511 guard — verified this is exactly what happened (the trim commit is already on `main`, confirmed via `git log`).
