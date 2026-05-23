# Working State

- **Task**: #9968 — major architectural discussion this cycle on manifest's role; PM recommended elimination + 2 new frontmatter fields. Human deferred filing planning artifact. #9965 skill batch #5: 48→31 fails over 5 cycles.
- **Status**: monitoring (skill steady; doc architectural decisions pending human direction)
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-23 18:33)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external untriaged
- 1 approved (long-running): #3 (DM lane, going-public)
- 2 in-progress:
  - #9965 (6274.2/AC2.8) — skill steadily executing:
    - cycle 1315 (16:44): ACK STOP+nudge
    - cycle 1316 (16:58): batch #2 48→47 (-1)
    - cycle 1317 (17:06): batch #3 47→41 (-6)
    - cycle 1318 (17:37): batch #4 41→36 (-5)
    - cycle 1319 (18:08): batch #5 36→31 (-5) — test_manifest.py
    - Trend: -17 failures in 5 cycles (avg -3.4/cycle), zero regressions; trajectory to 0 ≈ 9-10 more cycles if rate holds
  - #9968 (EPIC: L1-L4 doc) — v1.3 shipped 8b33aebd cycle 1616. v1.4 gap analysis delivered cycle 1617 (20 gaps, 3 tiers). Cycle 1618: major manifest-architecture discussion (see below). v1.4 drafting still deferred by human.
- 1 pending (gated): #9966 (6274.3)
- 3 issues at status:open: #9967, #9969, #9970
- shipped_since_bump=6 of 10

## #9968 architectural decisions captured this cycle (NOT YET IN DOC)
Human directives during cycle 1618 discussion:
1. **Sub-skills should be visible to everyone** — no per-role inclusion filter. Pool is universal.
2. **Wake mode is config.md's authority** — not parallel manifests. Two manifests (`includes.yml` + `includes-events.yml`) collapse.

PM analysis (delivered to human; awaiting selection):
- Manifest had 4 jobs: J1 inclusion, J2 ordering, J3 mode gating, J4 variant inheritance
- After human's corrections: J1, J3, J4 die; J2 is already moving to frontmatter
- **Manifest has zero remaining structural jobs**. Pure legacy cruft.
- BUT two distinctions need nailing down before deleting:
  - 'Visible to everyone' ≠ 'composed-in for everyone'. Need `load: always | on-demand` field.
  - Wake mode in config.md still needs per-fragment frontmatter `wake_mode: polling | event | any` to gate which cycle prose lands in CLAUDE.md (rejecting #8697 was right — no in-fragment conditionals).

PM's recommended target state:
```yaml
---
slot: instructions
sub-slot: cycle
ordinal: 30
load: always | on-demand
wake_mode: polling | event | any
---
```
Compose: read config.md → walk tree → filter (load=always AND wake_mode in {config.wake_mode, any}) → sort (slot, ordinal) → emit. No manifest. ~40 yaml files deleted.

Follow-up tasks (NOT YET FILED):
- T1: sub-skill cruft audit — every fragment defaults to `on-demand`; promote `always` only when proven
- T2: doc v1.4 §15 Schemas — capture the new frontmatter contract + manifest-removal migration
- T3: §6.5 wake-mode section needs revision (the parallel-manifests rationale is now wrong)

Human deferred filing these as tasks this cycle. PM holds.

## #9965 — back to standard monitoring
- Skill is consistent: -3 to -6 fails per cycle, no regressions
- No PM intervention needed

## #9966 — unchanged
- Conditions: AC2.8 ships, cutover date passed
