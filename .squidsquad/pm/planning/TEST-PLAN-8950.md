# TEST-PLAN #8950 — Defense-in-depth: code-review / QA / DM each check planning artifact

## Revision Log

- **R3 (2026-05-18)** — Addressed deepseek R2 Finding 1: Gate #3 QA discovery glob was order-sensitive (`*<NUMBER>*TEST-PLAN*` failed to match new `TEST-PLAN-<NUMBER>.md` convention because `TEST-PLAN` precedes the number). Replaced with broad-glob-then-grep approach matching the pattern used by Gates #2 and #4 — works for both legacy (`FEAT-PM-1234-TEST-PLAN.md`) and new (`TEST-PLAN-1234.md`) conventions.
- **R2 (2026-05-18)** — Addressed 5 deepseek R1 findings: DM Gate #4 fragment now opens with a discovery step (`ls .squidsquad/pm/planning/*<NUMBER>*`) so the citation gate is scoped to tasks WITH planning artifacts only (R1 noise mitigation made executable); AC-1 verification updated — both `CONTEXT*.md` AND `TEST-PLAN*.md` (and the legacy `FEAT-*-TEST-PLAN.md` pattern) must appear in `--input-files`; planning-artifact discovery uses task-number-matching glob, not literal filename — covers both old (`FEAT-PM-1075-TEST-PLAN.md`) and new (`TEST-PLAN-8950.md`) naming conventions; DM "route back to QA" now specifies transition `pending-ship → pending-test`; CQ-2 setup updated to establish both CONTEXT and TEST-PLAN exist for the task (matches the DM canned message).

## Scope (locked)

Three sub-skill edits via the compose stack:

### Gate #2 — Code-review loop (`references/sub-skills/roles/dev/implement-tasks.md` §9c)
When a task has planning artifacts, the deepseek code-review invocation must include those artifacts as `--input-files`. **Same change as #8916 §9c — coordinate.**

> When invoking the deepseek code-review loop (§9c) for a task with planning artifacts, locate them via task-number match:
> ```
> ARTIFACTS=$(ls .squidsquad/pm/planning/*<NUMBER>* 2>/dev/null)
> ```
> Pass `$CHANGED_FILES` plus every match (covers both `CONTEXT-<NUMBER>.md` / `CONTEXT.md` AND `TEST-PLAN-<NUMBER>.md` / `FEAT-*-<NUMBER>-TEST-PLAN.md` legacy naming) as `--input-files`. The review prompt must direct deepseek to verify the diff against architectural locks documented in the planning artifacts, not only code quality.

### Gate #3 — QA AC walk (`references/sub-skills/roles/qa/verification.md` — the section that handles `pending-test → pending-ship`)

> **Before marking any task `pending-test → pending-ship`**, locate the TEST-PLAN for the task by task-number match (handles both legacy `FEAT-PM-<NUMBER>-TEST-PLAN.md` and new `TEST-PLAN-<NUMBER>.md` conventions):
> ```
> ls .squidsquad/pm/planning/*<NUMBER>* 2>/dev/null | grep -i 'test-plan'
> ```
> If a TEST-PLAN file is found, walk its AC list and confirm each AC is observably satisfied by the implementation — not just that tests pass. Tests passing is necessary but not sufficient. For each AC: run the verification command, check the file, or observe the output described. Do not infer from test names.
>
> If any AC is not observably satisfied, transition `pending-test → in-progress` and comment which AC failed.
>
> If no TEST-PLAN file exists for the task (e.g., bug fixes or trivial tasks without planning), this AC walk is skipped — proceed with the existing verification flow.

### Gate #4 — DM contract-citation soft gate (`references/sub-skills/roles/dm/delivery-packaging.md`)

> **Before merging any PR for a task**, first check whether planning artifacts exist:
> ```
> ARTIFACTS=$(ls .squidsquad/pm/planning/*<NUMBER>* 2>/dev/null)
> ```
> If `$ARTIFACTS` is empty (no planning files for this task), the citation gate does not apply — proceed with merge as normal.
>
> If `$ARTIFACTS` is non-empty, check whether the PR description references any of those files (substring match on any planning filename, e.g., `CONTEXT-<NUMBER>.md` or the TEST-PLAN filename, OR a `### 5.X #<NUMBER>` section pointer to the bundle CONTEXT). If no reference is present:
> 1. Do not merge.
> 2. Transition `pending-ship → pending-test` (route back to QA — the citation gap implies the AC-walk in Gate #3 may have been skipped).
> 3. Comment: `"PR does not cite the planning contract; cannot verify architectural conformance. QA: confirm AC walk completed against the planning artifacts listed in .squidsquad/pm/planning/*<NUMBER>*."`
>
> This is a soft gate scoped to tasks WITH planning artifacts. Bug fixes and trivial tasks without planning skip this gate entirely.

## Acceptance Criteria

### AC-1: code-review §9c includes planning files
- **File**: `references/sub-skills/roles/dev/implement-tasks.md` §9c
- **Verification**:
  - §9c shows task-number-match discovery (`ls .squidsquad/pm/planning/*<NUMBER>*`).
  - §9c's `model_router.py code-review` invocation passes those matches (both `CONTEXT*` and `TEST-PLAN*` / `FEAT-*-TEST-PLAN*` patterns possible) as `--input-files` beyond `$CHANGED_FILES`.
  - review prompt mentions architectural-locks check.
- **Note**: same fragment as #8916. Whichever ships first defines it; the second PR documents already-covered.

### AC-2: QA AC-walk fragment present + scoped to TEST-PLAN existence
- **File**: QA sub-skill (likely `references/sub-skills/roles/qa/verification.md`).
- **Verification**:
  - composed QA CLAUDE.md contains "walk the AC list" + "tests passing is necessary but not sufficient" + the task-number-match discovery glob.
  - Fragment explicitly handles the no-TEST-PLAN case (skip AC walk, proceed with existing flow).

### AC-3: DM contract-citation soft gate + discovery + explicit transition
- **File**: DM sub-skill (likely `references/sub-skills/roles/dm/delivery-packaging.md`).
- **Verification**:
  - composed DM CLAUDE.md contains the planning-artifact discovery glob.
  - composed DM CLAUDE.md contains the no-citation route-back behavior with explicit transition `pending-ship → pending-test`.
  - canned message references "AC walk completed against the planning artifacts" (not a hardcoded TEST-PLAN-<NUMBER>.md path).

### AC-4: recompose; PM CLAUDE.md byte-identical
- **Verification**:
  ```
  cp .squidsquad/pm/CLAUDE.md /tmp/pm-before.md
  python references/scripts/compose.py deploy-all
  diff /tmp/pm-before.md .squidsquad/pm/CLAUDE.md  # must be empty
  ```
- Dev/QA/DM CLAUDE.md WILL change — each contains its respective new fragment.

## Comprehension Tests

### CQ-1: QA AC walk
- **Setup**: fresh QA agent given only the updated QA sub-skill fragment. The task has a `TEST-PLAN-1234.md` (5 ACs).
- **Question**: "180 tests pass on the PR for task #1234. Do you transition `pending-test → pending-ship`?"
- **Expected**: No — must walk the 5 ACs and confirm each is observably satisfied (run command / check file / observe output). Tests passing is necessary but not sufficient. If any AC fails, route back `pending-test → in-progress` with a comment naming the AC.

### CQ-2: DM contract citation (with planning artifacts present)
- **Setup**: fresh DM agent given only the updated DM sub-skill fragment. Task #1234 has both `CONTEXT-1234.md` and `TEST-PLAN-1234.md` in `.squidsquad/pm/planning/`. PR is QA-approved and at `pending-ship`. PR description does not reference any planning file.
- **Question**: "Do you merge?"
- **Expected**: No. Run `ls .squidsquad/pm/planning/*1234*` → non-empty → citation gate applies. Block merge, transition `pending-ship → pending-test`, comment with the canned message asking QA to confirm AC walk completed.

### CQ-3: code-review architectural check
- **Setup**: fresh dev agent invoking §9c code-review on a task with planning artifacts (mix of `CONTEXT.md` and `FEAT-PM-1234-TEST-PLAN.md`).
- **Question**: "What files do you pass to `model_router.py code-review --input-files`, and what does the review prompt direct deepseek to check?"
- **Expected**: pass `$CHANGED_FILES` plus every match from `ls .squidsquad/pm/planning/*1234*` (handles both legacy `FEAT-*-TEST-PLAN.md` and new `TEST-PLAN-<NUMBER>.md` naming, AND bundle-level `CONTEXT.md`). Direct deepseek to check the diff against architectural locks in the planning artifacts.

### CQ-4: gate is no-op without planning artifacts
- **Setup**: fresh DM agent given only the updated DM sub-skill fragment. PR for task #5678 is QA-approved at `pending-ship`. `ls .squidsquad/pm/planning/*5678*` returns no matches.
- **Question**: "Do you apply the contract-citation gate?"
- **Expected**: No — discovery glob returned empty, no planning artifacts exist, gate does not apply. Proceed with merge as normal.

## Regression Risks

- **R1: DM gate noise (mitigated).** Scope is "tasks WITH planning artifacts only" — explicitly encoded via the discovery glob and the no-op path. Bug fixes and trivial tasks without planning skip the gate.
- **R2: QA AC-walk overhead (acceptable).** AC walks add per-task QA time. The incident showed AC-walk-skipped is exactly how violations slip through. Trade-off accepted.
- **R3: coordination with #8916 §9c.** Gate #2 is the same change as #8916 §9c. Whichever ships first defines the fragment; the other PR notes already-covered. Recommend single-PR if both approved together.
- **R4: file naming conventions (mitigated).** Legacy `FEAT-PM-*-TEST-PLAN.md` and new `TEST-PLAN-<NUMBER>.md` both covered via task-number-match glob `*<NUMBER>*`. Implementer must NOT use literal `TEST-PLAN-<NUMBER>.md` filenames in the fragments.

## Out of Scope

- New CI/automation enforcement of contract citation — instruction-layer soft gate only.
- Backfilling AC walks on previously-shipped tasks.
- Auto-extraction of architectural locks from CONTEXT.md (still text-prompt level — deepseek reads CONTEXT.md and interprets).

## Implementation Sequencing

Recommend single PR touching all 3 sub-skill fragments (dev §9c / qa verification / dm delivery-packaging) + recompose. Coordinate with #8916 — if #8916 ships first, this PR's §9c portion is a no-op; document in PR description.
