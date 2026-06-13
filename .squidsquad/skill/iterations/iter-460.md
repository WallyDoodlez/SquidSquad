# Iteration 460 — caught #11505 scope conflict before making a mess

**Mode**: loop (harness DOWN). Manual ops.

## What happened
- Gates re-checked (all closed): #11683 unshipped (8th cycle), harness down, no PM CQ answer on #11505.
- Decided to convert the blocked cycle into progress by EXECUTING the #11505 removal (operator-decided per §8.3; CQ-AC is a pending-test gate, not a do-the-work gate; plan already published iter-458). Branched task/11505 off main.
- **Before editing**, traced the exact footprint deeper than iter-458 — and found a SCOPE CONFLICT that stops execution:
  1. capability_check.py is load-bearing in **PM task-intake** (references/sub-skills/roles/pm/task-intake.md:70 'Capability gap analysis' + :110 template), which composes into PM's CLAUDE.md (pm/includes.yml:31). AC4's 'sweep all L1-L3 sources' would silently delete a PM workflow step — PM-domain behavioral change.
  2. references/sub-skills/manifest.md:149 + docs/sub-skill-catalog.md:143 EXPLICITLY say capability-check removal is 'not this PR — paired with the broader capability-framework retirement (INSTALLER-ARCH §8, #10025)'. **#10025 is OPEN** and titled '...retire [capability framework]'.
  3. The capabilities/ DIRECTORY (AC1) is already gone (2026-05-27 cleanup, manifest.md:147) — the only cleanly-bounded deadwood is already done.
- So #11505's ACs over-reach into #10025's territory + PM's domain. Per discipline (stop on ambiguous/contradictory scope; don't cross role boundaries; don't implement blindly), I STOPPED — made zero edits, posted the finding + 3 disambiguation options (downscope / close-as-superseded-by-#10025 / confirm-full-retirement-with-PM-signoff) on #11505, deleted the empty branch.

## Why this is the right outcome
Executing AC4 as written would have (a) removed a live PM task-intake step without PM sign-off, (b) contradicted the documented #10025 plan, (c) orphaned capability_check.py. Catching it pre-edit IS the front-loaded-planning payoff.

## Blocked on (external)
- #11505: PM/operator to disambiguate #11505↔#10025 overlap.
- 3 PRs (#11709/#11715/#11722): #11683 ship. All MERGEABLE/CLEAN.

## Next cycle
- Re-check #11683 + #11505 disambiguation + PM CQ. Act when any clears.
