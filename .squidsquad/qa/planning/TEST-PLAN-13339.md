# TEST-PLAN-13339 — installer maturity probe + workflow->roster mapping

**Issue**: #13339 (type:task, priority:medium) — INSTALLER-RUNTIME.md §4 empty-project + §9 Steps 3 & 5-6.
**PR**: #13398 `squidsquad/task/13339`, head 2d97897de.
**Derived from**: the issue Scope/ACs (independent of the worker diff).

## ACs
- **AC1**: map workflow (built/verified specifics) -> proposed Worker/Verifier counts + specializations (PM/DM singletons). Define the mapping heuristic.
- **AC2**: detect project maturity (empty -> scaffolded -> established) via a testable wizard.py probe; branch the flow per empty-project adaptations (step 2 external refs, step 3 default workflow, step 4 no-op, roster from intended type, hand-off first-step prompt).

## Test cases
- **TC-1 (AC2)**: read detect_maturity; verify tier logic (>=N src OR tests => established; 0 src + no structure => empty; else scaffolded); signal-transparent envelope; scan-absent degrade. Live CLI E2E on established + empty dirs.
- **TC-2 (AC1)**: read propose_roster; verify intended + scan paths (both->be+fe, fullstack->worker, one-surface->one, nothing->fullstack); PM/DM/verifier singletons; error envelope for bad --intended. Live CLI E2E.
- **TC-3 (AC1 scope)**: verify the verifier-singleton design decision against references/roles/verifier/manifest.yaml (always_installed/show_in_roster/variant) — is multi-verifier even buildable?
- **TC-4 (CQ)**: 13339_spec.json review vs my derived Qs; fresh Sonnet agent on the named INSTALLER-RUNTIME.md sections only; zero misreads (esp CQ4 = verifier singleton not count).
- **TC-5 (tests)**: run test_wizard_13339_maturity_roster.py.
- **TC-6 (gate)**: full static gate on branch HEAD.
- **TC-7 (landing)**: branch behind main + shares wizard.py/runbook with #13355 -> verify COMBINED state (local merge, no push): clean 3-way, consistent dispatch, combined gate green, #13369/#13355 preserved.

CQ REQUIRED — docs/INSTALLER-RUNTIME.md is LLM-consumed and modified by this task.
