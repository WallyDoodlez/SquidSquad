## R1 Finding Verification

I've systematically checked each of the 6 R1 findings against the R2 version of TEST-PLAN-8917.md:

### F1 — Structured comparison vs raw diff ✅ Addressed
- **R1 issue**: Change 2 said "diff the current issue body against the corresponding CONTEXT.md section" — non-deterministic.
- **R2 fix at lines 25–31**: Change 2 now prescribes a four-step procedure: read CONTEXT `## Scope` + `## Locked Decisions` + `## Out of Scope`, read body, compare scope bullets, re-read confirmation. Line 31 explicitly states "structured comparison, not raw `diff`." CQ-3 (line 89) reinforces "(NOT a raw text diff.)" R3 (line 99) documents the fix.

### F2 — CQ-1 bundle scenario rewrite ✅ Addressed
- **R1 issue**: CQ-1 described a single-task Phase 2 scenario where the issue didn't yet exist (issues created in Phase 3).
- **R2 fix at lines 78–81**: CQ-1 now matches the real incident: bundle Phase 2 discussion, pre-existing sub-task #1234 filed last week, CONTEXT.md `### 5.4 #1234` narrows scope, issue body still has old text.

### F3 — DECISIONS-N.md removed ✅ Addressed
- **R1 issue**: Change 1 referenced DECISIONS-N.md, an artifact not in PM's documented workflow.
- **R2 fix at line 14**: Change 1 now only references `CONTEXT.md` (or per-task `CONTEXT-<NUMBER>.md`). No mention of DECISIONS. Out of Scope (lines 37–38) explicitly scopes out TEST-PLAN-N.md as a trigger.

### F4 — Change 1 / Change 2 artifact scope aligned ✅ Addressed
- **R1 issue**: Change 1 listed multiple artifacts; Change 2 only checked CONTEXT.md — mismatch.
- **R2 fix**: Change 1 (line 14) and Change 2 (lines 25–29) both reference only CONTEXT.md / CONTEXT-<NUMBER>.md. Line 38 confirms TEST-PLAN-N.md is not a scope-rewrite trigger. Single authority: CONTEXT.

### F5 — Change 3 added for issue-creation banner placement ✅ Addressed
- **R1 issue**: No instruction for placing the banner at initial issue creation; only reactive placement on scope rewrite.
- **R2 fix at lines 33–34**: Change 3 explicitly added — Phase 3 §A `create-task` invocation must prepend the AUTHORITATIVE SCOPE banner when the task has a CONTEXT artifact. AC-3 (lines 52–54) and CQ-4 (lines 91–93) verify this.

### F6 — R2 backfill check for currently-approved tasks ✅ Addressed
- **R1 issue**: Regression risk noted only in-flight `planned` tasks; `approved` tasks could be picked up stale.
- **R2 fix at lines 69–74**: AC-5 adds a one-time pre-deploy backfill — `list-tasks --status approved`, manually verify banner presence + body-CONTEXT consistency for each approved task with a planning artifact. R2 risk (line 98) now explicitly references AC-5 as capturing this.

## New Issues Check

I reviewed every line for new problems: internal consistency across the three Changes, AC verifiability, comprehension test accuracy, regression risk coverage, out-of-scope boundaries, and interplay between Change 1 (rewrite trigger), Change 2 (pre-approval gate), and Change 3 (creation-time placement). No new genuine issues found.

NO_FINDINGS