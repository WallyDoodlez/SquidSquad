Now I have a thorough understanding of the codebase, the incident that motivated this change, the workflow fragments involved, and the compose stack architecture. Let me compile my findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 20–21 (Change 2)
- **Severity**: error
- **Issue**: Change 2 says "diff the current issue body against the corresponding CONTEXT.md section. If they disagree, update the body." But the issue body and CONTEXT.md have **different formats** — the body is a summary with the AUTHORITATIVE SCOPE banner + bullets; CONTEXT.md has `## Scope`, `## Locked Decisions`, `## Out of Scope` sections. A literal diff will always show differences, making the step non-deterministic. The PM agent has no objective criterion to judge "agree" vs. "disagree" — it must decide what _content_ corresponds to what.
- **Evidence**: The task-intake.md fragment (lines 186–206) defines CONTEXT.md format with `## Scope`, `## Locked Decisions`, `## Dev Discretion`, `## Side Effect Mitigations`, `## Upgrade Path`, `## Out of Scope`. The proposed issue body format (Change 1 lines 12–14) is a banner + bullets. These are structurally incomparable with `diff`. No instruction tells PM WHAT to compare (Scope section? Locked Decisions? All of CONTEXT.md?) or how to operationalize the comparison.
- **Suggested fix**: Change the wording from "diff the current issue body against the corresponding CONTEXT.md section" to: "Read the CONTEXT.md section (or CONTEXT-<NUMBER>.md) `## Scope` + `## Locked Decisions` + `## Out of Scope`. Compare those to the scope bullet points in the issue body. If any locked decision or scope boundary is missing, outdated, or contradicted in the body, update the body."

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 37–42 (CQ-1)
- **Severity**: warning
- **Issue**: CQ-1 asks about "Phase 2 deepseek review on task #1234 and the review rewrote scope in CONTEXT.md." The expected answer is to update body for issue #1234. But in the normal 5-phase task lifecycle, the GitHub issue is created in **Phase 3** (task-intake.md line 281: "A) GitHub Issue — create via `python references/scripts/tracker.py create-task` with status `Pending`"), not before Phase 2. So during Phase 2 of task #1234, issue #1234 likely **doesn't exist yet**. The fragment rule would be inapplicable. The incident was about bundle/epic tasks where sub-task issues existed before bundle-level Phase 2 — a different scenario the CQ doesn't capture.
- **Evidence**: task-intake.md Phase 3 line 281 creates the issue. Phase 2 (lines 147–233) creates CONTEXT.md before any issue exists. The incident (INCIDENT-2026-05-18-issue-body-drift.md lines 30–37) documents that the stale bodies belonged to sub-tasks (#8694, #8695) that were filed in a prior planning cycle, then scope was rewritten during bundle-level Phase 2. The CQ conflates two different timelines.
- **Suggested fix**: Rewrite CQ-1 to match the real trigger: "You're PM running Phase 2 discussion for bundle CONTEXT.md. During the interactive discussion, the human locks a decision that narrows scope for pre-existing task #1234 (already filed as a GitHub issue). CONTEXT.md §5.4 now says 'thin harness, no dispatch.' The #1234 issue body still says 'implement dispatch logic.' What must you update before moving on?" Expected: update body for #1234.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 10 (Change 1 fragment text)
- **Severity**: warning
- **Issue**: The fragment mentions "DECISIONS-N.md" as a planning artifact that can be rewritten. But the task-intake.md fragment (the target for Change 1) doesn't produce or reference DECISIONS-N.md — it produces CONTEXT.md in Phase 2 and TEST-PLAN.md in Phase 3. DECISIONS-4792.md exists as a bundle-level artifact but is never mentioned in the PM's standard operating instructions. A PM agent reading the new fragment would encounter an undefined artifact type.
- **Evidence**: task-intake.md creates only CONTEXT.md (Phase 2, line 184) and TEST-PLAN.md (Phase 3, line 287). DECISIONS.md is never mentioned in task-intake.md or task-approval.md. The only reference to DECISIONS in the codebase is the actual file `.squidsquad/pm/planning/DECISIONS-4792.md`, which was a bundle-specific Phase 2 intermediate artifact, not a standard planning output. The fragment implicitly references a workflow path (bundle/epic DECISIONS files) that isn't part of the documented instructions the PM follows.
- **Suggested fix**: Either (a) restrict the fragment text to "CONTEXT.md or TEST-PLAN-N.md" (the artifacts PM's documented workflow actually produces), or (b) if DECISIONS-N.md is a valid artifact type, add a line explaining when it is created and what it contains (e.g., "DECISIONS-N.md is the Phase 2 decisions log for bundle/epic tasks that span multiple issues").

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 10 vs. 20 (Change 1 scope vs. Change 2 scope)
- **Severity**: warning
- **Issue**: Change 1 says body must be updated when scope is rewritten on **any** planning artifact (CONTEXT.md, DECISIONS-N.md, **or TEST-PLAN-N.md**). Change 2's pre-approval check only diffs against **"the corresponding CONTEXT.md section."** If TEST-PLAN-N.md was rewritten with scope-significant changes (e.g., scope clarifications in test preconditions that imply new constraints) but CONTEXT.md wasn't touched, the pre-approval gate wouldn't catch the drift because it only checks CONTEXT.md.
- **Evidence**: Change 1 line 10: "rewrites scope on a planning artifact (CONTEXT.md, DECISIONS-N.md, or TEST-PLAN-N.md)." Change 2 lines 20–21: "diff the current issue body against the corresponding CONTEXT.md section." This is a scope mismatch — Change 2 covers a subset of the artifacts Change 1 claims to protect.
- **Suggested fix**: Change 2 should say: "diff the current issue body against the corresponding planning artifact(s) — CONTEXT.md section (or CONTEXT-<NUMBER>.md) AND TEST-PLAN-<NUMBER>.md (specifically `## Scope` and any scope-constraining ACs)." Alternatively, if the intent is that CONTEXT.md is the sole scope authority and TEST-PLAN.md is derived from it, then Change 1 should drop TEST-PLAN-N.md from the list of artifacts that trigger body updates.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 10–14 (Change 1 fragment)
- **Severity**: error
- **Issue**: The fragment instructs PM to update the issue body "when Phase 2 rewrites scope" and to "Lead every issue body that has a planning artifact with an AUTHORITATIVE SCOPE banner." But there is no instruction for **when the banner is first placed.** The issue is created in Phase 3 (task-intake.md line 281). Should Phase 3's issue creation step include the banner? If the banner is only added reactively (when scope is rewritten), newly created issues for tasks that never have scope rewritten will lack the banner entirely. The fragment needs to also modify Phase 3 to add the banner at issue creation time.
- **Evidence**: The incident post-mortem (INCIDENT-2026-05-18-issue-body-drift.md line 64) documents that all 7 bundle ticket bodies were "rewritten on GitHub with AUTHORITATIVE SCOPE banner" as immediate remediation. But the permanent fix must ensure the banner is present from the start. The task-intake.md Phase 3 §A (line 281) says "GitHub Issue — create via `python references/scripts/tracker.py create-task` with status `Pending`, referencing planning artifacts" but says nothing about the AUTHORITATIVE SCOPE banner. Without modifying Phase 3, the banner only appears when scope is rewritten — a task created fresh will ship without it.
- **Suggested fix**: Add to Change 1's scope: "Also modify Phase 3 (Planning) §A: when creating the GitHub issue via `create-task`, the body MUST start with the AUTHORITATIVE SCOPE banner pointing at the newly created CONTEXT.md (or CONTEXT-<NUMBER>.md)." This covers the initial placement; the "update in same PM step" rule covers rewrites.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8917.md`
- **Line**: 53–55 (Regression Risk R2)
- **Severity**: warning
- **Issue**: R2 states "do NOT batch-update all existing open task bodies as part of this PR. PM updates bodies organically going forward." This addresses in-flight `planned` tasks (they'll hit Change 2's pre-approval gate before transitioning). But it doesn't address tasks already at `approved` status. An `approved` task is pickup-able by skill and won't pass through `planned → approved` again. If any `approved` task body is stale when #8917 lands, skill could pick it up and repeat the incident. The incident report (AUDIT-D line 63) flags this exact risk.
- **Evidence**: AUDIT-D-go-forward-readiness.md line 63: "The other four could still be `approved` and thus pick-up-able by skill before #8916 lands. The AUTHORITATIVE SCOPE banner rewrite mitigates but does not eliminate the risk." The TEST-PLAN acknowledges the risk exists but delegates it to "bodies were already rewritten" (the incident remediation), which is a one-time fix not encoded in this process change. R2 only addresses `planned` tasks; it doesn't require verifying that no `approved` tasks have stale bodies.
- **Suggested fix**: Add to R2 or Change 2: "Before this change lands, verify all currently `approved` tasks have AUTHORITATIVE SCOPE banners and body content matching their CONTEXT.md sections. If any mismatch, update the body manually before deploying the fragment edit." Alternatively, add a one-time check to the implementation steps.