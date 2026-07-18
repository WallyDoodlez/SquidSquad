# QA-RESULTS-13465 — tracker.py create-issue --role qa role-label filter

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13474 (branch squidsquad/task/13465). **Type**: type:issue (bug, auto-approved).

## Verification approach

Independent TEST-PLAN-13465.md from the DM bug report. Verified BOTH live (real forge + real taxonomy) and hermetically (stubbed taxonomy). This bug is squarely in the verifier's own tooling (create-issue is a core forge op I use every cycle), so the live E2E is the definitive gate.

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | create-issue --role qa succeeds, stamps role:qa not role:verifier | LIVE E2E: created #13475 exit 0, labels [type:issue, role:qa, squidsquad, status:open, severity:low], role:verifier absent; closed artifact | PASS |
| AC2 | --role verifier drops non-existent primary, keeps role:qa | live + hermetic: verifier -> role:qa | PASS |
| AC3 | non-dual roles (skill/pm/dm/designer) unchanged | live + hermetic: -> role:<role> | PASS |
| AC4 | degraded taxonomy -> fallback primary role:<role> | hermetic (empty cache): qa->role:qa, skill->role:skill | PASS |
| AC5 | regression test present | tests/test_13465_create_issue_role_label_filter.py (10 cases) | PASS |
| fwd | dual-emit resumes when role:verifier exists (#6274.3) | hermetic: qa -> role:qa,role:verifier | PASS |

## Live evidence

- Repo taxonomy (gh label list): role:{designer,dm,pm,qa,skill} — NO role:verifier. Confirms the bug's premise.
- Live filter: `_filter_role_labels_to_existing(_build_dual_role_labels_6274(r), r)` -> qa='role:qa', verifier='role:qa', skill='role:skill'.
- Live E2E: real `create-issue --role qa` exit 0, #13475, correct labels, closed.

## Test runs

- Independent verifier tests (TEST-13465-tests.py): **6 passed**.
- Worker regression test (tests/test_13465_create_issue_role_label_filter.py): **10 passed**.
- Full static gate (python tests/run_tests.py): (recorded at merge — 53 OK / exit 0).

## Meta-note

This fix directly unblocks the verifier's own filing path: earlier this session I filed #13457/#13472/#13473 via --role skill/pm (which worked) but a --role qa filing would have failed pre-fix; DM's #13464 filing-note and this issue both cite that break. Post-fix, --role qa works (proven by #13475).

## Decision

All ACs observably satisfied (live E2E + hermetic); worker regression + full suite green. Zero gaps. -> PASS: verdict comment BEFORE the pending-ship transition (per #13464 ordering) + merge PR #13474 + Pending Ship.
