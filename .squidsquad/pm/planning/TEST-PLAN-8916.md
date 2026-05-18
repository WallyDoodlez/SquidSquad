# TEST-PLAN #8916 — L2 dev: mandate reading CONTEXT.md / TEST-PLAN.md before implementing

## Revision Log

- **R2 (2026-05-18)** — Addressed 6 deepseek R1 findings: AC-3 verification command corrected (no `--diff-only --mode loop` flags); R1 regression note corrected (skill/dev CLAUDE.md WILL change in both modes; non-dev roles must stay byte-identical); Scope clarifies the existing step 2 in `implement-tasks.md` is **replaced** by the new authoritative-artifact step (not augmented); CQ-4 added for the non-divergence (bodies-in-sync) case; CONTEXT.md heading level corrected to `### 5.X` (h3); Scope and AC-2 aligned — pass the FULL `CONTEXT.md` and `TEST-PLAN-<NUMBER>.md` as additional `--input-files` beyond `$CHANGED_FILES`.

## Scope (locked)

Replace **step 2 of `references/sub-skills/roles/dev/implement-tasks.md`** (the existing "Read planning artifacts" step at current lines ~13-18) with a new authoritative-artifact step that preserves the prior fallback-location logic AND adds the new authority rule:

> **Step 2 — read planning artifacts first; CONTEXT.md is authoritative.**
>
> Before writing any code for a task, check whether planning artifacts exist:
> - `.squidsquad/pm/planning/CONTEXT.md` (bundle-level; the per-task section is `### 5.X #<NUMBER> — ...`)
> - `.squidsquad/pm/planning/CONTEXT-<NUMBER>.md` (per-task)
> - `.squidsquad/pm/planning/TEST-PLAN-<NUMBER>.md` (acceptance criteria + comprehension tests)
> - Fallback location: `.squidsquad/<role>/planning/` (preserved from prior step 2)
>
> If a planning artifact exists, **the planning artifact is the authoritative scope.** The GitHub issue body is a high-level pointer; the planning artifact is the contract.
>
> Read the relevant CONTEXT section (`### 5.X #<NUMBER>` for bundle CONTEXT.md, OR the full per-task `CONTEXT-<NUMBER>.md`) AND the `TEST-PLAN-<NUMBER>.md` acceptance criteria in full BEFORE writing code.
>
> **Divergence handling**:
> - If the issue body and the planning artifact **agree**, proceed normally. Do not add a planning-artifact note to the PR description.
> - If the issue body and the planning artifact **disagree**, the planning artifact wins. Implement to the planning artifact. Flag the divergence in your implementation PR description (one sentence pointing PM at the body/artifact mismatch) so PM can update the body via the #8917 workflow.

Plus update **§9c (the deepseek code-review loop)**: when planning artifacts exist for the task, pass the FULL `.squidsquad/pm/planning/CONTEXT.md` (bundle) or `.squidsquad/pm/planning/CONTEXT-<NUMBER>.md` (per-task) AND `.squidsquad/pm/planning/TEST-PLAN-<NUMBER>.md` as additional `--input-files` (in addition to `$CHANGED_FILES`). The review prompt must direct deepseek to check the diff against architectural locks documented in CONTEXT.md, not just code quality.

## Acceptance Criteria

### AC-1: fragment edit replaces old step 2
- **File**: `references/sub-skills/roles/dev/implement-tasks.md`
- **Verification**:
  - grep for the phrase `the planning artifact is the authoritative scope` → matches one fragment block.
  - grep for the old phrasing being replaced (the prior "Read planning artifacts" step) → does not match (or matches only inside the new step's preserved fallback-location text).
  - the new step retains the prior fallback location reference to `.squidsquad/<role>/planning/`.

### AC-2: §9c passes full planning files as additional --input-files
- **File**: `references/sub-skills/roles/dev/implement-tasks.md` §9c
- **Verification**:
  - §9c shows the `model_router.py code-review` invocation passing `$CHANGED_FILES` plus the full path to the relevant `CONTEXT.md`/`CONTEXT-<NUMBER>.md` and `TEST-PLAN-<NUMBER>.md` via `--input-files`.
  - the §9c context/prompt mentions "architectural locks" or equivalent direction telling deepseek to verify the diff against CONTEXT.md.

### AC-3: recompose succeeds; non-dev roles byte-identical
- **Verification**:
  ```
  # Snapshot before
  cp .squidsquad/pm/CLAUDE.md /tmp/pm-before.md
  cp .squidsquad/qa/CLAUDE.md /tmp/qa-before.md
  cp .squidsquad/dm/CLAUDE.md /tmp/dm-before.md
  python references/scripts/compose.py deploy-all
  diff /tmp/pm-before.md .squidsquad/pm/CLAUDE.md  # must be empty
  diff /tmp/qa-before.md .squidsquad/qa/CLAUDE.md  # must be empty
  diff /tmp/dm-before.md .squidsquad/dm/CLAUDE.md  # must be empty
  ```
- **Note**: `.squidsquad/skill/CLAUDE.md` WILL change (the new step is in `roles/dev/implement-tasks.md`, which is included in both `references/roles/dev/includes.yml` and `references/roles/dev/includes-events.yml`). That change is the intended behavior — verify it contains the new step.

### AC-4: skill clone receives updated fragment after recompose
- **Verification**: after `deploy-all`, `.squidsquad/skill/CLAUDE.md` contains the new authoritative-artifact step under the dev section. (Clone re-sync via boot/restart is out of scope; deploy-all updates the in-repo copy only.)

## Comprehension Tests

### CQ-1: artifact authority on divergence
- **Setup**: fresh agent given only the updated `references/sub-skills/roles/dev/implement-tasks.md` fragment.
- **Question**: "The GitHub issue body for task #1234 says 'harness dispatches work' but the relevant CONTEXT.md section says 'thin harness, no dispatch logic.' Which one do you implement and why?"
- **Expected**: implement CONTEXT.md scope. Issue body is a pointer; planning artifact is the contract. Flag divergence in PR description.

### CQ-2: where to look
- **Question**: "Before writing code for a task, list the planning-artifact file patterns and locations you must check under `.squidsquad/pm/planning/` (and the fallback)."
- **Expected**: `CONTEXT.md` (bundle, look up the `### 5.X #<NUMBER>` section), `CONTEXT-<NUMBER>.md` (per-task), `TEST-PLAN-<NUMBER>.md` (ACs + CQs); fallback location `.squidsquad/<role>/planning/`.

### CQ-3: code-review loop input
- **Question**: "When invoking the §9c deepseek code-review loop for a task that has planning artifacts, what do you pass via `--input-files`, and what does the review prompt direct deepseek to check?"
- **Expected**: pass `$CHANGED_FILES` plus the full path to `.squidsquad/pm/planning/CONTEXT.md` or `CONTEXT-<NUMBER>.md` AND `TEST-PLAN-<NUMBER>.md`. Prompt directs deepseek to check the diff against architectural locks in CONTEXT.md, not just code quality.

### CQ-4: non-divergence behavior
- **Setup**: fresh agent given only the updated fragment.
- **Question**: "Issue body for #1234 says 'thin harness, no dispatch logic' and CONTEXT.md §5.X also says 'thin harness, no dispatch logic.' After reading CONTEXT.md and implementing, what do you put in the PR description about planning artifacts?"
- **Expected**: nothing about divergence. The "flag in PR description" instruction is conditional on divergence — when bodies are in sync there is nothing to flag. (No always-on planning-artifact ref expected.)

## Regression Risks

- **R1: skill/dev CLAUDE.md changes in both modes (expected).** The fragment `roles/dev/implement-tasks.md` is referenced by both `references/roles/dev/includes.yml` (/loop) and `references/roles/dev/includes-events.yml` (events). After recompose, `.squidsquad/skill/CLAUDE.md` WILL show the new step in both modes — this is intended, mode-agnostic. The byte-identical regression check applies to **non-dev roles** (PM, QA, DM) — their composes must remain unchanged.
- **R2: PR description noise.** Skill might flag divergence on every PR even when bodies are in sync. Mitigation captured in CQ-4 and fragment phrasing — flag is conditional on divergence, not always-on.
- **R3: missing planning artifacts.** Many tasks (especially bug fixes) have no planning artifacts. Step 2 must be a no-op for those — proceed straight to step 3. Fragment phrasing: "If a planning artifact exists, …" — the `If` is load-bearing.

## Out of Scope

- The PM-side body sync (covered by #8917).
- Defense-in-depth gates for QA / DM (covered by #8950).
- Adding `--diff-only` / `--mode` flags to `compose.py` (those flags do not exist; verification uses snapshot+diff instead).
- Backfilling AUTHORITATIVE SCOPE banners on closed issues.
