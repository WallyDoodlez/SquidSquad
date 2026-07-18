# Working State

- **Task**: #13585 (harness restart coordination — TRIGGERING NOW)
- **Status**: in-progress
- **Started**: 2026-07-18 01:20

_Lean shape per #13562/#13579 (≤8KB). History in git._

## >>> RESPAWNED PM MUST (first cycle after this restart) <<<

1. **Verify restart outcome**: /status — all 4 aliases running + event mode + fresh harness boot_time; harness now imports CURRENT git_ops.py (the #13585 sys.modules staleness this restart cures).
2. **Confirm #13585 cure end-to-end**: ask dm (comment + work-assign wake on #13582) to RE-ATTEMPT the PR #13583 merge — it needs NO code changes (dm RCA: current git_ops passes it clean). If merge now succeeds → dm ships #13582 → then PM closes #13585 (transition per its type) and routes the DURABLE fix (importlib.reload / subprocess isolation at harness.py:4625 /merge handler) to skill as a new issue UNLESS #13580's shipped rework already covers it (check #13580 final content first).
3. **Reconcile inject-permissions.ps1** after #13583 merges: content-compare local dirty copy vs origin (modulo EOL, MSYS_NO_PATHCONV=1); identical → drop (`git restore`); different → surface to operator, do NOT discard. Same protocol as start.ps1 (done cleanly this session). `.gitattributes` local hunk: skill bundled it into PR #13583 — reconcile it the same way once merged.
4. **Bare-mode caveat still holds** (#13545): if any agent fails to come up, `boot_remote.py --role <name>` (qa needed this at 00:10 tonight).

## Watches (carry forward)

- **pending-test with qa**: #13574 (write-outage boot-gate; PM CQ ACs AC-F1/CQ1-4/D1 in issue body) + #13580 (scope-gate sequencing, PR #13586). #13575 verified+merged pre-restart (dm was mid-delivery at trigger — if #13575 not shipped, dm resumes it at boot).
- **#13582 (HIGH)**: waiting ONLY on the post-restart #13583 merge re-attempt (step 2 above).
- **qa pickup mis-claim (#13556)**: watch-only; improvement item only if the pending-test→in-progress claim recurs.
- Session context: auth RESTORED (WallyDoodlez, push verified); Context Threshold now 75 (#13562 §T3, operator veto offered); Verbose OFF/quiet.

## HITL standing (advertise each check-in)

- **#13515** — blocked-status name ruling (PM rec 'blocked') + scope add.
- **#13263** — behind-clone squash-merge, KEEP OPEN.
- **#13561–#13568** — token-efficiency batch `pending`, awaiting operator approval (#13562 already shipped via bug lane).
- **#12527** — greenfield smoke test, awaiting operator go.
- **Threshold 70→75** veto offer.

## PM queue

- work_queue(pm approved) = #10690 only, GATED (E6+E7) — not pickable.
- Parked coord-holds: #11092 / #10839 / #9968.
- Idle-driver: state file says armed, scan 2/3; session cron dies with this restart — Step A.2 CronList check re-creates on next idle.
