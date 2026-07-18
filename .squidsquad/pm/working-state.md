# Working State

- **Task**: none
- **Status**: none
- **Started**: —

_Lean rewrite 2026-07-18 ~01:05 per the #13562/#13579 ≤8KB rule (was a 43KB journal; full history in git — see commits up to 0cc9056f1 and iteration logs)._

## Session context (2026-07-18 boot, EVENT mode, Verbose OFF/quiet)

- **Auth RESTORED** (WallyDoodlez, push verified live) — the 07-17 write-outage is over; #13473 closed. All stranded 403-era changes accounted for: qa deliverables + pm planning + vault updates committed; launcher fixes handled via #13577/#13582.
- **Harness in BARE mode** (no TUI, no agent auto-reboot — #13545): if an agent dies, PM must `boot_remote.py --role <name>` (did so for qa this session, ~33min dead, recovered clean).
- Idle driver: armed, cron **4f60462c** (6,36 * * * *), scan 2/3 used; last scan filed #13579 (shipped same session).

## Watches

- **#13582 (HIGH, role:skill, in-progress)** — PR 2 of 2: inject-permissions.ps1 em-dash fix. **PM still HOLDS the primary clone's dirty (fixed) copy of inject-permissions.ps1 until this merges** — then reconcile exactly like start.ps1 (content-compare modulo EOL → drop if identical; if different, surface to operator, do NOT discard). Also offered skill the stranded `.gitattributes` CRLF-pinning hunk (verbatim in my #13582 comment) — if skill declines, leave the local hunk for the operator.
- **#13580 (low, skill-triaged)** — scope-gate two-PR sequencing property; option (a) already riding. Informational.
- **qa pickup mis-claim (#13556, self-caught)** — watch-only; file an improvement item only if the pending-test→in-progress claim recurs.
- **Shipped-this-session** (no action, context only): #13556 (merge-drop guard + post-merge restore hook), #13562 (working-state embed cap; **Context Threshold now 75** — operator veto offered), #13577 (start.ps1 ASCII), #13579 (sub-skill 8KB rule).

## HITL standing (advertise each check-in)

- **#13515** — blocked-status name ruling (PM rec **'blocked'**) + one scope add.
- **#13263** — behind-clone squash-merge, KEEP OPEN.
- **#13561–#13568** — token-efficiency/observability batch, `pending`, awaiting operator approval/prioritization (note: #13562 already shipped via the auto-approved bug lane).
- **#12527** — greenfield smoke-test on a foreign repo, awaiting operator go.
- **Context Threshold 70→75** (#13562 §T3) — pre-scoped, shipped; operator may veto back to 70.

## PM queue

- work_queue(pm approved) = **#10690 only, GATED on E6+E7 (#10686 unshipped)** — not pickable.
- Parked coord-holds (in-progress, NOT stalls): #11092, #10839, #9968.
