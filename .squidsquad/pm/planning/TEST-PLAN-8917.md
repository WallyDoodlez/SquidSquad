# TEST-PLAN #8917 — PM: sync issue body when planning rewrites scope

## Revision Log

- **R2 (2026-05-18)** — Addressed 6 deepseek R1 findings: Change 2 wording clarified — compare body's scope bullets against CONTEXT.md `## Scope` + `## Locked Decisions` + `## Out of Scope` (not raw diff which is non-deterministic across formats); CQ-1 rewritten to match the real incident trigger (bundle Phase 2 narrowing scope on a pre-existing sub-task issue); DECISIONS-N.md removed from the artifact list (not part of PM's documented workflow); Change 1 / Change 2 artifact scope aligned (TEST-PLAN-N.md NOT a scope-rewrite trigger in this ticket — CONTEXT is the sole scope authority); **Change 3 added** — Phase 3 §A (`task-intake.md` issue creation) updated so the AUTHORITATIVE SCOPE banner is placed at issue-creation time, not only on later rewrite; R2 expanded to verify currently-approved tasks have banners + body-CONTEXT match before the fragment edit deploys.

## Scope (locked)

Three PM-side changes via the compose stack:

### Change 1 — PM sub-skill fragment edit (scope-rewrite rule)
In `references/sub-skills/roles/pm/task-intake.md` (Phase 2 / Discussion fragment — the section that locks CONTEXT.md), add:

> **When Phase 2 (deepseek review, discussion locks, scope discussion) rewrites scope on `CONTEXT.md` (or per-task `CONTEXT-<NUMBER>.md`), the corresponding GitHub Issue body MUST be updated in the same PM step.** Use `gh issue edit <N> --body-file <new-body>`. The issue body and CONTEXT.md must always agree at the time of the `planned → approved` transition.
>
> Every issue body that has a planning artifact MUST lead with an **AUTHORITATIVE SCOPE banner** pointing at the locked planning file:
>
> ```
> > **AUTHORITATIVE SCOPE: `.squidsquad/pm/planning/CONTEXT.md §5.X` (or `CONTEXT-<NUMBER>.md`). Read that artifact in full. The bullets below are a summary; the planning artifact is the contract.**
> ```

### Change 2 — pre-approval body-vs-CONTEXT check
In the same fragment (or `task-approval.md` if that's the right boundary), add to the `planned → approved` transition workflow:

> Before transitioning any task `planned → approved`:
> 1. Read the corresponding CONTEXT section: bundle `CONTEXT.md` `### 5.X #<NUMBER>` heading OR the full `CONTEXT-<NUMBER>.md`. Focus on `## Scope`, `## Locked Decisions`, and `## Out of Scope`.
> 2. Read the GitHub issue body (`gh issue view <N> --json body`).
> 3. Compare the body's scope bullets against the three CONTEXT sections above. If any **locked decision** or **scope boundary** is missing, outdated, or contradicted in the body, update the body via `gh issue edit` BEFORE the transition.
> 4. Confirmation: re-read `gh issue view <N> --json body`; the AUTHORITATIVE SCOPE banner is present AND the body bullets are consistent with the CONTEXT sections.

This is structured comparison, not raw `diff` — the body and CONTEXT.md intentionally have different formats. The PM judges scope agreement, not text equality.

### Change 3 — issue creation must place the banner from the start
In `references/sub-skills/roles/pm/task-intake.md` Phase 3 §A (the issue creation step `python references/scripts/tracker.py create-task ...`), add: when the task has a CONTEXT.md or CONTEXT-<NUMBER>.md, the body passed to `create-task` MUST start with the AUTHORITATIVE SCOPE banner. This ensures every new task body has the banner at filing time — Change 1's "update on rewrite" handles drift; Change 3 handles initial placement.

### Out of scope this ticket
- Optional `audit_issue_bodies.py` script — file as separate follow-up if PM wants automation.
- TEST-PLAN-<NUMBER>.md changes alone do NOT trigger a body update under this ticket. Scope authority lives in CONTEXT.md; TEST-PLAN is derived. (If a future change makes TEST-PLAN scope-authoritative, that's a separate ticket.)

## Acceptance Criteria

### AC-1: scope-rewrite + banner fragment present
- **File**: PM sub-skill (likely `references/sub-skills/roles/pm/task-intake.md` Phase 2 section)
- **Verification**:
  - grep for `AUTHORITATIVE SCOPE banner` (literal phrase) → matches one fragment block.
  - grep for `issue body MUST be updated in the same PM step` → matches in PM-role fragment only.
  - The banner template text is present verbatim in the fragment.

### AC-2: pre-approval body check in workflow
- **Verification**: composed PM `CLAUDE.md` task-approval/intake section contains the four-step pre-approval procedure (read CONTEXT, read body, compare scope+locked+out-of-scope sections, re-read confirmation).

### AC-3: issue creation places banner
- **File**: PM sub-skill Phase 3 §A.
- **Verification**: grep around the `tracker.py create-task` invocation in PM fragments for the banner placement instruction; composed PM CLAUDE.md Phase 3 §A includes the rule "when the task has CONTEXT.md or CONTEXT-<NUMBER>.md, the body MUST start with the AUTHORITATIVE SCOPE banner."

### AC-4: recompose succeeds; non-PM roles byte-identical
- **Verification**:
  ```
  cp .squidsquad/qa/CLAUDE.md /tmp/qa-before.md
  cp .squidsquad/dm/CLAUDE.md /tmp/dm-before.md
  cp .squidsquad/skill/CLAUDE.md /tmp/skill-before.md
  python references/scripts/compose.py deploy-all
  diff /tmp/qa-before.md .squidsquad/qa/CLAUDE.md       # empty
  diff /tmp/dm-before.md .squidsquad/dm/CLAUDE.md       # empty
  diff /tmp/skill-before.md .squidsquad/skill/CLAUDE.md # empty
  ```
- `.squidsquad/pm/CLAUDE.md` WILL show the new fragment content.

### AC-5: backfill check for currently-approved tasks (one-time)
- **Verification**: before deploying the fragment edit, run:
  ```
  python references/scripts/tracker.py list-tasks --status approved
  ```
  For each `approved` task with a planning artifact, manually verify the issue body has the AUTHORITATIVE SCOPE banner AND its scope bullets are consistent with the CONTEXT.md section. Update bodies before deploy if any mismatch. This protects against skill picking up a stale-body `approved` task between #8917 deploy and #8916 deploy.

## Comprehension Tests

### CQ-1: when to update body (bundle scenario from the incident)
- **Setup**: fresh PM agent given only the updated sub-skill fragment.
- **Question**: "You're PM running Phase 2 discussion for a bundle CONTEXT.md (`.squidsquad/pm/planning/CONTEXT.md`). During the interactive discussion, the human locks a decision that narrows scope for pre-existing task #1234 (already filed as a GitHub issue last week). CONTEXT.md `### 5.4 #1234` now says 'thin harness, no dispatch.' The #1234 issue body still says 'implement dispatch logic.' What must you do before moving on?"
- **Expected**: update issue #1234's body via `gh issue edit 1234 --body-file <new-body>` to reflect the locked scope, with the AUTHORITATIVE SCOPE banner pointing at `CONTEXT.md §5.4`.

### CQ-2: what's the banner
- **Question**: "What is the AUTHORITATIVE SCOPE banner, where does it go, and what does it contain?"
- **Expected**: a blockquote at the top of every issue body that has planning artifacts. Points at the locked planning file (e.g., `CONTEXT.md §5.X` or `CONTEXT-<NUMBER>.md`). States the planning artifact is the contract; the bullets are a summary.

### CQ-3: pre-approval check
- **Question**: "Before transitioning a task from `planned` to `approved`, what comparison must you run, and against which CONTEXT.md sections?"
- **Expected**: read CONTEXT.md (`### 5.X #<NUMBER>` or `CONTEXT-<NUMBER>.md`) `## Scope` + `## Locked Decisions` + `## Out of Scope`; compare against the body's scope bullets; if any locked decision/scope boundary is missing/outdated/contradicted, update the body before transitioning. (NOT a raw text diff.)

### CQ-4: initial banner placement
- **Question**: "When you create a new task via `tracker.py create-task` in Phase 3 §A and the task has a CONTEXT-<NUMBER>.md, must the body include the AUTHORITATIVE SCOPE banner?"
- **Expected**: yes — the banner is placed at issue creation time, not only on later rewrite.

## Regression Risks

- **R1: fragment location.** PM sub-skills are split across several files. Implementer must put each Change in the right fragment so it composes into PM CLAUDE.md without leaking to dev/QA/DM roles. AC-4 byte-identical check catches leakage.
- **R2: in-flight `approved` tasks (pre-deploy backfill required).** Existing `approved` tasks are pick-up-able by skill and do not pass through `planned → approved` again. AC-5 captures the one-time backfill: before deploying the fragment edit, audit all `approved` tasks with planning artifacts and update any stale bodies.
- **R3: comparison non-determinism removed in R2.** Earlier draft said "diff the body against CONTEXT.md" which is non-deterministic across different formats. R2 replaces with structured comparison against the three named CONTEXT sections — agent has objective criteria.

## Out of Scope

- Optional `audit_issue_bodies.py` script — file as separate follow-up.
- Skill-side reading of CONTEXT.md (covered by #8916).
- Defense-in-depth gates for code-review / QA / DM (covered by #8950).
- Treating TEST-PLAN-N.md changes as scope-rewrite triggers — CONTEXT.md is the sole scope authority under this ticket.
- Backfilling AUTHORITATIVE SCOPE banners on closed/shipped issues.
