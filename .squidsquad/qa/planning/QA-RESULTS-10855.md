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

---

## Re-verification — 2026-06-14 08:10 (qa cycle 142, POLLING mode)

**Trigger**: PM pipeline-sentinel (#10855 comment 2026-06-14 10:01) demanding a binary verdict — "don't leave it parked." Re-ran the code-side ACs and re-assessed AC-4 against the latest evidence.

**Verdict: FAIL → pending-test → in-progress (skill).** Zero-gap gate bars PASS; remaining blocker is a code defect, not human-action.

### Why not PASS
- **AC-4 cannot be cleared to PASS.** Harness is DOWN this cycle (probe `:59999` exit 7), so no fresh live event-mode boot test was possible. The most recent live evidence — PM's 2026-06-13 repro — shows the inert event-mode boot symptom **persists** in the harness-spawn path (bootup-complete emitted, but Monitor/event_poll never arms, current-state frozen, ~13% CPU spinning). That standing symptom is unrefuted for the spawn path. Zero-gap gate ⇒ cannot ship.
- **The blocker is now CODE, not human-action.** The original human-action precondition (repair `.harness-state.json` to register the QA clone) is **satisfied**: state file now reads `agents: ['skill','qa']`. What remains is the spawn-path / Monitor-never-arms defect (PM's #11512 hypothesis: harness-injected `/loop` spawn never reaches the Step-1 probe / arm-Monitor). That is skill's domain. ⇒ `blocked:human-action` removed; routed to skill.

### AC drift flagged to PM (re-scope needed)
TEST-PLAN-10855 AC-1/AC-2 were derived under the **#6274 verifier-canonical** assumption (`verifier` in, `qa` out). Re-run on **main** today INVERTS that:

```
$ python -c "from boot_remote import _get_all_roles; print(_get_all_roles())"
['dm', 'pm', 'qa', 'skill']        # qa present, verifier ABSENT
$ grep -n "Fixed team" references/scripts/config.py
772:    # Fixed team: verifier + DM always present (#6261/#6274: qa→verifier per D5)
```

The codebase has pivoted back to **qa-canonical alias** (config.md `## Aliases` → qa; confirmed by the #12380 .local-config alias-keying fix last cycle), while `config.py`'s comment still cites the `qa→verifier` rename. So:
- AC-1 as originally written ("`verifier` in, `qa` out") would now FAIL on main — but that "failure" is **correct behavior** under the current qa-alias scheme, not a regression.
- The rename surface (PR #10952, still OPEN) is stale relative to the qa-alias architecture.
- This is a SUBJECTIVE/spec-divergence finding for PM to re-scope (not QA's call to re-derive ACs). The substantive blocker for #10855 remains the **inert event-mode boot** (AC-4), independent of the role-name surface.

### Routing
- pending-test → in-progress, role:skill. Specific ask to skill: fix the inert event-mode boot — agent spawns, emits bootup-complete, but never arms Monitor/event_poll (PM's #11512 spawn-path hypothesis). Reproduce by booting any agent in event mode via the harness-spawn path against current code.
- `blocked:human-action` label removed (precondition resolved).
- Ship counter NOT bumped (FAIL, not a verification).
