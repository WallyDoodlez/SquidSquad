# QA-RESULTS-10855

**Run**: 2026-06-03 12:46 (qa cycle 621)
**Branch**: `squidsquad/task/10855`
**PR**: #10952
**Verdict**: **HUMAN-REQUIRED** — code-side ACs (AC-1..3) PASS; E2E AC-4 cannot be verified without operator action. Item stays at `pending-test` with `blocked:human-action` label.

## AC walk

| AC | Statement | TC | Result |
|----|-----------|----|--------|
| 1 | `_get_all_roles()` returns canonical post-#6274 trio (`verifier` in, `qa` out). | TC-1 | PASS — direct import returns `['dm', 'pm', 'skill', 'verifier']`. |
| 2 | `boot_remote.py` fixed-team set matches `config.py:_collect_install_agents` (line 742). | TC-2 | PASS — both files now name `verifier` as canonical; comment at boot_remote.py:151–155 explicitly cites the `config.py:742` mirror. |
| 3 | Combined test suite green (`test_boot_remote.py` + `test_9242_harness_wedge_fixes.py` + `test_harness.py`). | TC-3, TC-4 | PASS — 243 passed, 1 skipped (matches PR claim). `TestGetAllRoles` both cases PASS. |
| 4 | Verifier boots and writes `.squidsquad/verifier/current-state` against a repaired harness state. | TC-5 | **HUMAN-REQUIRED** — `.harness-state.json` is in a partial state (`'agents': ['skill']` only; no `verifier` entry); requires operator manual repair per PM's option-1 sequence before TC-5 can execute. |

## Test runs

### TC-1 (functional check)

```
$ python -c "from boot_remote import _get_all_roles; print(_get_all_roles())"
['dm', 'pm', 'skill', 'verifier']
```

### TC-2 (canonical-mirror grep)

```
$ grep -n "Fixed team" references/scripts/config.py
740:    # Fixed team: verifier + DM always present (#6261/#6274: qa→verifier per D5)
$ grep -n "Fixed team" references/scripts/boot_remote.py
151:    # Fixed team: PM + verifier + DM always present (#6261/#6274 D5: qa→verifier).
```

### TC-3 + TC-4

```
$ python -m pytest tests/test_boot_remote.py::TestGetAllRoles -v
tests/test_boot_remote.py::TestGetAllRoles::test_includes_pm_from_config PASSED
tests/test_boot_remote.py::TestGetAllRoles::test_mandatory_roles_always_present PASSED
2 passed in 0.08s

$ python -m pytest tests/test_boot_remote.py tests/test_9242_harness_wedge_fixes.py tests/test_harness.py
243 passed, 1 skipped in 9.86s
```

Note: an initial run on the branch reported 133 failed + 38 errors. Root cause was operator's uncommitted WIP in `references/scripts/harness.py` (unresolved `<<<<<<< Updated upstream` merge marker at line 417 — same operator-side artifact noted in QA-RESULTS-10818). Re-run with that file stashed yielded the clean 243/1. Operator WIP is unrelated to this PR.

### TC-5 — HUMAN-REQUIRED

Cannot run from a QA cycle. PM cycle-2094's option-1 sequence is required: operator (or PM) must edit `.squidsquad/.harness-state.json` to add a `verifier` agent entry with `clone_path` pointing at the canonical verifier clone (e.g. `../SquidSquad-qa` per PM's analysis), then `python references/scripts/boot_remote.py --role verifier`, then wait one cycle interval (30 min), then confirm:

- `.squidsquad/verifier/.claude-pid` exists with a live PID.
- `.squidsquad/verifier/current-state` mtime is fresh.
- A recent `.squidsquad/verifier/iter-*.md` exists.

Current `.harness-state.json` agents dict is `['skill']` — the corrupted `qa` entry has been removed in a partial cleanup but `verifier` was not added. PR #10952 prevents recurrence of the corruption but does not retroactively repair an install whose state file is missing the verifier entry; that remains PM/operator work per skill-lead's explicit split in their cycle-1567 comment.

## Decision

- Code-side ACs (AC-1..3) PASS with zero gaps.
- E2E AC-4 is HUMAN-REQUIRED — not a code bug; needs operator-side state repair.
- Per the HUMAN-REQUIRED gate, the item stays at `pending-test` with the `blocked:human-action` label added; transition to `pending-ship` deferred until TC-5 can be executed and reported back.
