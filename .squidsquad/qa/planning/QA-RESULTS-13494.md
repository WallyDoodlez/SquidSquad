# QA-RESULTS-13494 — _git_in_clone forces LC_ALL=C (deploy-pull locale robustness)

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13501. **Type**: type:issue (bug, auto-approved). **Provenance**: verifier improvement-scan finding (filed this session).

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | _git_in_clone passes env with LC_ALL=C to subprocess.run | hermetic capture: env['LC_ALL']=='C' | PASS |
| AC2 | env is a SUPERSET of os.environ (PATH/HOME/creds preserved), not bare | hermetic: PATH present, len(env)>1 | PASS |
| AC3 | deploy-pull helpers still work under the forced locale (no regression) | re-ran TEST-13456 + TEST-13472: 8 passed, 1 xpass | PASS |
| live | a real git invocation through the env override works + emits English | live smoke: git status via _git_in_clone rc=0, 'branch' wording | PASS |
| AC4 | regression test present | tests/test_13494_git_in_clone_c_locale.py | PASS |

## Test runs

- Independent verifier tests (TEST-13494-tests.py): **4 passed**.
- Deploy-pull regressions (#13456/#13472 planning tests, exercise _git_in_clone heavily): **8 passed, 1 xpass**.
- Worker regression test: **2 passed**.
- Full static gate: (recorded at merge).

## Fix

harness._git_in_clone now runs git with env={**os.environ, "LC_ALL": "C"} (harness.py:4987) — single choke point makes every English-substring check in the deploy-pull helpers locale-robust at once (my suggested central fix on the #13494 filing). Superset env preserves PATH/credentials.

## Decision

All ACs satisfied (hermetic + live + deploy-pull regression); worker regression present. Zero gaps. -> PASS: verdict comment BEFORE transition + merge PR #13501 + Pending Ship.
