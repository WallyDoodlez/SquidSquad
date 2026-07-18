# TEST-PLAN-13585 — harness /merge stale sys.modules git_ops.py, restart remedy

**Source**: GitHub issue #13585 body + PM's final Discussion comment, which explicitly states the three verifiable ACs for this ticket's scope (a diagnosis + one-time-restart-remedy record; the durable code fix is deliberately routed to a separate ticket, #13588).
**Derived without reading a diff — this issue carries no code changes of its own (confirmed: no PR exists for #13585).**

## Acceptance Criteria (PM-stated, issue-scoped)

- **AC1**: PR #13583 (the previously-blocked #13582 follow-up) shows `state == MERGED` with `mergedAt` strictly after the fresh harness's `boot_time_iso` (2026-07-18T05:26:17Z) — proving the restart, not a code change, cured the false refusal.
- **AC2**: `GET /status` shows all 4 team aliases (`pm`, `dm`, `skill`, `qa`) running on the fresh boot.
- **AC3**: A durable-fix follow-up issue exists, labeled `role:skill`, referencing the `harness.py:4625` stale-`sys.modules`-caching diagnosis (so the underlying defect is tracked, not just patched over by a one-time restart).

## Test Cases

### TC-1 (covers AC1): PR #13583 merged after the fresh boot
- **Steps**: `gh pr view 13583 --json state,mergedAt`; compare `mergedAt` to the harness's current `boot_time_iso`.
- **Expected**: `state=MERGED`, `mergedAt` (2026-07-18T05:44:08Z) > `boot_time_iso` (2026-07-18T05:26:17Z).
- **Verification command**: `gh pr view 13583 --json state,mergedAt -q '.state, .mergedAt'` + `curl http://127.0.0.1:7373/status`

### TC-2 (covers AC2): All 4 agents running post-restart
- **Steps**: `GET /status`, inspect `agents[].status` for all 4 aliases.
- **Expected**: `dm`, `pm`, `qa`, `skill` all `status=running`.
- **Verification command**: `curl -sf http://127.0.0.1:7373/status`

### TC-3 (covers AC3): Durable-fix ticket filed and correctly scoped
- **Steps**: `gh issue view 13588 --json title,body,labels`.
- **Expected**: exists, `role:skill` label present, body references `harness.py:4625` / stale-cached-`git_ops`-module diagnosis.
- **Verification command**: `gh issue view 13588 --json title,body,labels`

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-2
- AC3 → TC-3

No code diff to run a test suite against (this issue is a diagnosis + restart-remedy record, not a code change — confirmed `gh pr list --search 13585` returns empty). No LLM-consumed instructions touched — no Comprehension Questions section required.
