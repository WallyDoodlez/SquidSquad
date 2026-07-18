# QA-RESULTS-13515

## Summary
REJECTED — back to in-progress. AC1/AC2/AC4/AC5/AC6 all PASS, several independently verified beyond the worker's own coverage (live comprehension spawn, doc-first sequencing re-read). **AC3 FAILS live**: the actual `status:blocked` label was never provisioned on the repo, so every real attempt to park a task crashes. This is invisible to the worker's own test suite because all 135 of its tests mock the `gh` subprocess call — a decisive case where live-system testing catches what mocked unit tests structurally cannot.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | SKILL.md status table + tracker.py docstring both document `status:blocked`, semantics, legal transitions |
| AC2 | PASS | SOUL.md Never Stop + event-mode-contract Case D both updated, internally consistent, composed CLAUDE.md files match |
| AC3 | **FAIL** | Live `tracker.py transition <N> in-progress blocked --role qa` against a real disposable issue (#13598) crashed: `gh issue edit ... --add-label status:blocked` exited 1 — `status:blocked` does not exist on the repo (`gh label list`, 45 labels, none named `status:blocked`). Root cause: `wizard.py`'s label-provisioning source was never updated to include it. |
| AC4 | PASS | pipeline-sentinel excludes `blocked` from halt detection + adds the double-pickup anomaly check (4g), well-integrated |
| AC5 | PASS | Fresh general-purpose agent, given ONLY SOUL.md + event-mode-contract.md, answered PM's tightened scenario 4/4 correct, unprompted, exact terminology |
| AC6 | PASS | Discussion thread confirms Phase-1 spec (with a genuinely-recovered stranded-commit incident) was PM-reviewed and operator-confirmed before any Phase-2 code was written |

## Decisive finding — AC3, live transition crash (blocks shipping)

Reproduced with a real, disposable GitHub issue (created via `tracker.py create-issue`, closed after):
```
open -> in-progress: OK
in-progress -> blocked: CRASH
  gh issue edit 13598 --add-label status:blocked --remove-label status:in-progress
  -> subprocess.CalledProcessError, exit 1
```

`gh label list --limit 200` on the live repo returns 45 labels — no `status:blocked` among them (there IS a pre-existing, unrelated `status:on-hold`). `tracker.py`'s code changes (STATUS_LABELS, LEGAL_TRANSITIONS, ROLE_AUTHORITY) are logically correct — the transition matrix accepts the new edge — but the underlying GitHub label was never created. `wizard.py`'s label color/description maps (`~2514`/`~2551`, feeding `build_label_inventory()`/`ensure_labels()`) have no `status:blocked` entry, so this isn't provisioned on this repo NOR would it be on a fresh install.

**Why the worker's 135 tests missed this entirely**: every test in `test_13515_blocked_status.py` and `test_tracker_authority.py::TestBlockedStatus` either checks static text/data structures or mocks `_run_list`/subprocess so the `gh` call always "succeeds" without touching a real repo. None of them exercise the actual `gh issue edit --add-label status:blocked` call against live label state. This is squarely why the verifier's charter calls for testing against a real live instance, not trusting the worker's own (necessarily hermetic) unit tests as the gate.

**Impact if shipped as-is**: any agent following the new SOUL.md instruction ("transition it to `status:blocked`") — which AC5 confirms agents WILL correctly attempt, unprompted — hits a hard crash on the very first live use. The feature is non-functional end-to-end despite passing its own full test suite and static gate.

## Zero-gap check
FAILS on AC3. Not a minor/cosmetic gap — the feature's core mechanism cannot execute against the real system.

## What's needed to re-pass
1. Add `status:blocked` to `wizard.py`'s label inventory (color + description, matching the existing `status:in-progress`/etc. pattern) so `ensure_labels()` provisions it on install.
2. Create the label on THIS repo (either via `ensure_labels()` re-run, or `gh label create status:blocked`) — the fix must land as an actual live label, not just source code, before this can ship.
3. Add a live (unmocked) regression test exercising the real `gh issue edit --add-label status:blocked` path (or at minimum, assert the label exists via `gh label list` as a smoke check) so this class of gap can't recur silently.
4. Re-run TC-3 against a fresh disposable issue to confirm the live round trip actually works before re-submitting.

## Verdict
FAIL. Back to In Progress with the above concrete, narrow fix list.
