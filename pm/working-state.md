# Working State

- **Task**: #9965 catch-up active (skill landed 3a; 3b/3c pending). #9967 cursor fix shipping. In-session Q1-Q5 discussion on #9998 awaiting human Q2 reply.
- **Status**: pipeline healthy, no PM action needed this cycle
- **Last Processed Event ID**: df9f33751a6a (cursor stuck — fix shipping via PR #9997 this cycle, should advance after)

## Pipeline snapshot (2026-05-24 00:13, cycle 1624)
- 0 PRs open from PM's view (#9997 in DM's hands as pending-ship)
- 1 pending-ship: #9967 (skill, cursor-bug fix) — DM merging PR #9997
- 0 pending-test, 0 external untriaged
- 1 approved (long-running, DM lane): #3 (going-public)
- 2 in-progress:
  - #9965 (skill, 6274.2 / AC2.8) — (3a) landed cycle 1332 (commit 2afacb77, preset YAML + 7-8 feat328 tests). Expected next: (3b) compose.py disk-check shims, (3c) WIZARD.md prose. Suite trajectory: 14 → ~6 after 3a, → ~4 after 3b, → 3 after 3c (the 5 test_wizard.py stay red, freeze-blocked).
  - #9968 (PM, EPIC L1-L4 doc) — no PM work this cycle; trajectory unchanged.
- 2 pending tasks (PM, awaiting discussion-phase pickup):
  - #9996 (preset catalog drift) — filed cycle 1622
  - #9998 (multi-worker / multi-verifier doc gap + Q1-Q5) — filed cycle 1623
- 1 pending (gated): #9966 (6274.3) — gated on 6274.2 merge + cutover window
- 2 planning (skill, stale): #9874, #9875
- 1 planned (skill, stale): #9845 — still withholding nudge
- 2 issues at status:open: #9969 (manifest naming), #9970 (composed-md drift). #9967 moved to pending-ship.
- shipped_since_bump = 6 of 10

## In-session discussion (not on tracker yet) — #9998 Q1-Q5
Human engaged with all 5 open routing questions:
- **Q1** (routing target by class vs name): route by name; two agents of same class can do double-duty
- **Q2** (EAD label→role mapping): asked PM to explain EAD; PM explained + surfaced Option A vs B; awaiting human pick
- **Q3** (care filter granularity): each agent has unique instance name; duplicate-instance booting caught by care filter
- **Q4** (bus contract permission): unique names mandatory when >1 instance per class; team-roster manifest must declare
- **Q5** (subloop ownership): designate one agent per class for improvement subloop; declared in team roster
When Q2 settles, capture all 5 locked answers as a tracker comment on #9998.

## #9965 — (3a) landed, awaiting (3b)/(3c)
Skill cycle 1332 commit 2afacb77: `references/presets/software-dev/manifest.yaml` role_install_order [dev] → [worker] + paired feat328 test fixes. Suite progress will be visible in next skill cycle comment.

## #9967 cursor bug — shipping
Skill cycle 1330 landed fix on PR #9997. DM cycle pulled and is shipping (latest comment Z 04:05). Once shipped, cursor-stuck symptom should resolve (currently still at df9f33751a6a — visible in this very cycle-input).

## #9968 — unchanged
## #9966 — unchanged (gated)
## #9996, #9998 — both pending, awaiting human discussion-phase pickup
