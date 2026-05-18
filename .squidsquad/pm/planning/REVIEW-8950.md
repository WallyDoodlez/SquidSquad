Now I have all the context needed. Let me compile my findings.

---

```
### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8950.md`
- **Line**: 15-18
- **Severity**: error
- **Issue**: The DM soft-gate fragment defined in the Scope section (§Gate #4) lacks an artifact-discovery step. The instruction says "Before merging any PR for a task with planning artifacts, check whether the PR description references the locked planning artifact" — but provides no mechanism for the DM agent to determine whether planning artifacts **exist** for a given task.
- **Evidence**: 
  - The existing DM delivery workflow (`references/sub-skills/roles/dm/delivery-packaging.md` lines 40-53) has a PR merge gate that operates purely on PR existence and merge success — it never checks `.squidsquad/pm/planning/`. The DM has no existing habit of checking for planning artifacts before merging.
  - R1 (line 57) explicitly states the mitigation is: "scope to 'tasks WITH planning artifacts only' — bug fixes and trivial tasks without planning skip this gate." But the fragment on lines 15-18 contains no `ls .squidsquad/pm/planning/*[NUMBER]*` or equivalent discovery command.
  - Without this, the DM will either: (a) apply the citation check to every PR (causing the noise R1 warns against), or (b) need to guess whether planning artifacts exist (unreliable). Both outcomes violate R1's stated scoping intent.
- **Suggested fix**: Add a discovery step before the citation check in the Gate #4 fragment. E.g.: "First, determine whether planning artifacts exist: `ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null`. If no CONTEXT*.md or TEST-PLAN*.md files match the task number, this task has no planning artifacts — skip this gate entirely and proceed with merge normally."

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8950.md`
- **Line**: 24
- **Severity**: error
- **Issue**: AC-1's verification criterion says `CONTEXT*.md` in `--input-files`, but the scope section (line 8) and CQ-3 (line 53) both state that TEST-PLAN files must also be passed to `model_router.py code-review --input-files`. The glob `CONTEXT*.md` does not match TEST-PLAN files (e.g., `FEAT-PM-8950-TEST-PLAN.md` or `TEST-PLAN-8950.md`).
- **Evidence**:
  - Line 8 (Scope/Gate #2): "include those artifacts as --input-files" where "those artifacts" refers to "CONTEXT.md / TEST-PLAN-\<NUMBER\>.md"
  - Line 53 (CQ-3 expected): "pass the diff AND the relevant CONTEXT.md/TEST-PLAN-\<NUMBER\>.md"
  - Line 24 (AC-1 verification): only checks for "CONTEXT*.md in --input-files"
  - A reviewer verifying AC-1 would confirm CONTEXT*.md is present and pass the AC, even if TEST-PLAN files are missing from --input-files — contradicting the scope and CQ-3.
- **Suggested fix**: Change AC-1 verification from `CONTEXT*.md` to `CONTEXT*.md and TEST-PLAN*.md` (or the equivalent glob pattern), so the AC is consistent with the scope and comprehension test.

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8950.md`
- **Line**: 13, 18, 48
- **Severity**: warning
- **Issue**: The fragments use the naming convention `TEST-PLAN-<NUMBER>.md` (e.g., line 13: "TEST-PLAN-\<NUMBER\>.md"), but the existing filesystem uses a different convention: `FEAT-{ROLE}-{NUMBER}-TEST-PLAN.md` (confirmed by 30+ files in `.squidsquad/pm/planning/`). The existing QA code in `references/sub-skills/roles/qa/verification.md` line 151 already uses `FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md`. A QA agent reading the new fragment's literal `TEST-PLAN-<NUMBER>.md` pattern may look for files that don't exist by that exact name.
- **Evidence**:
  - Filesystem has `FEAT-PM-1075-TEST-PLAN.md`, `FEAT-PM-2361-TEST-PLAN.md`, etc. — never plain `TEST-PLAN-1075.md`.
  - The test plan itself is `TEST-PLAN-8950.md` (a new, different convention), so the PM may be transitioning conventions. But the fragments are universal instructions that must work for ALL tasks, including those with the old FEAT prefix naming.
  - `verification.md` line 151: `Read .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md` — uses the FEAT convention, inconsistent with the new fragment.
- **Suggested fix**: Either: (a) use a generic descriptor like "the task's TEST-PLAN file (e.g., `FEAT-*-{NUMBER}-TEST-PLAN.md` or `TEST-PLAN-{NUMBER}.md`)" so agents know to match by task number not literal name, or (b) add a discovery instruction before the AC walk: "Locate the TEST-PLAN file for this task in `.squidsquad/pm/planning/` by matching the task number in filenames (e.g., `ls .squidsquad/pm/planning/*[NUMBER]*TEST-PLAN*`)."

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8950.md`
- **Line**: 18
- **Severity**: warning
- **Issue**: The DM Gate #4 fragment says "block merge and route back to QA" but does not specify what tracker status transition occurs. The existing DM merge-failure pattern in `delivery-packaging.md` line 51 transitions `pending-ship → in-progress`, but "route back to QA" implies a different workflow — QA should re-verify, not dev re-implement. Without specifying the transition, implementers may choose incompatible behaviors (e.g., transitioning to `in-progress` vs. `pending-test` vs. staying at `pending-ship`).
- **Evidence**:
  - Line 18: "If not, block merge and route back to QA with: ..." — no transition command specified.
  - `delivery-packaging.md` line 51: existing merge-failure pattern uses `transition [NUMBER] pending-ship in-progress --role dm-lead`, but this routes back to dev, not QA.
  - Gate #3 (QA AC-walk, line 13) uses the transition "transition back to `in-progress`" — but that's QA rejecting work, not DM blocking merge. Different semantics.
- **Suggested fix**: Specify the exact transition, e.g.: "Transition the task back to `pending-test` and comment: `PR does not cite the planning contract... QA: confirm AC walk completed...`" so QA picks it up in its next cycle for re-verification rather than dev getting it as in-progress work.

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8950.md`
- **Line**: 47-48
- **Severity**: warning
- **Issue**: CQ-2's setup establishes only that "The task has a CONTEXT-1234.md" — it does not establish that a TEST-PLAN-1234.md exists. Yet the expected answer (derived from the DM fragment) routes back to QA with a canned message referencing "TEST-PLAN-1234.md." If no TEST-PLAN exists for this task, the DM's route-back message is nonsensical, and the QA agent will receive an instruction to confirm an AC walk against a non-existent file. This edge case (CONTEXT exists but TEST-PLAN does not) is realistic — many tasks have CONTEXT without TEST-PLAN.
- **Evidence**:
  - CQ-2 setup (line 47): "The task has a CONTEXT-1234.md but the PR description doesn't mention it."
  - CQ-2 expected (line 48): "route back to QA with the canned message asking for AC-walk confirmation against TEST-PLAN-1234.md."
  - The DM Gate #4 fragment (line 18): the canned message hardcodes "TEST-PLAN-\<NUMBER\>.md" regardless of whether such a file exists.
  - The file listing from `.squidsquad/pm/planning/` shows tasks can have CONTEXT without TEST-PLAN (e.g., `FEAT-PM-5932-CONTEXT.md` exists but no corresponding TEST-PLAN is visible).
- **Suggested fix**: Either (a) qualify the DM canned message: "QA: confirm AC walk completed against TEST-PLAN-\<NUMBER\>.md (if it exists) or the issue's acceptance criteria directly," or (b) add a precondition to CQ-2 establishing that both CONTEXT and TEST-PLAN exist for the task, so the CQ tests only the intended path.
```