# Working State

- **Task**: #9968 architectural reframe — human reaffirmed cycle 1621 (sub-skills should BE Claude skills); PM offered three paths, awaiting choice. #9965 skill steady on AC2.8.
- **Status**: awaiting human choice on #9968 reframe shape
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-23 19:35, cycle 1621)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external untriaged
- 1 approved (long-running): #3 (DM lane, going-public)
- 2 in-progress:
  - #9965 (6274.2/AC2.8, 0.5h since update) — skill steady; trajectory ~7-8 more cycles to 0 failures
  - #9968 (EPIC: L1-L4 doc, 5.3h since update) — reframe in conversation, no commits
- 1 pending (gated): #9966 (6274.3)
- 2 planning (skill, 58.3h): #9874 (harness architecture review), #9875 (L2 vault writeback)
- 1 planned (skill, 58.9h): #9845 — withholding human nudge while #9968 decision pending
- 3 issues at status:open: #9967 (skill), #9969 (pm), #9970 (pm)
- 42 pending tail (known backlog, no triage this cycle)
- shipped_since_bump=6 of 10

## #9968 reframe — choice surfaced cycle 1621
Human reaffirmed direction: SquidSquad = main skill; sub-skills should BE Claude skills (SKILL.md + .claude/skills/ registration).

PM offered three paths to proceed:
  - **(a) Hybrid**: mandatory tier inline in small CLAUDE.md + situational tier as Claude skills. Lower-risk; PM's recommendation. File T4/T6/T7 conversion tasks.
  - **(b) Pure-Claude-skills with reliability test first** (T5): test whether description-matching reliably triggers mandatory procedures every cycle/boot. If reliable, pure model works; if not, fall back to hybrid.
  - **(c) Something else**: human picks an alternative framing.

Awaiting human choice. Once selected, file the implementing tasks.

## #9967 cursor-advance bug — observed symptom this cycle
Pre-cycle re-emitted mechanical_reactions for PRs #9923/#9924/#9911/#9929 (issues #9902/#9904/#9901/#9927), all of which were closed last cycle. Last Processed Event ID stuck at df9f33751a6a. Idempotent on closed issues, but confirms #9967 is still live. Not filing a separate bug — already tracked.

## Pending decisions captured (unchanged from cycle 1620)
- T1: sub-skill cruft audit
- T2: doc v1.4 §15 Schemas
- T3: §6.5 wake-mode revision
- T4: convert situational sub-skills to Claude skills (SKILL.md format)
- T5: test mandatory-procedure reliability under Claude skill mechanism
- T6: redefine compose.py scope to just the small mandatory CLAUDE.md
- T7: doc #9968 v2.0 rewrite

## #9965 — standard monitoring
- Skill execution steady; no PM action needed
- shipped_since_bump=6/10 — under DM threshold, no bump

## #9966 — unchanged
- Conditions: AC2.8 ships, cutover date passed
