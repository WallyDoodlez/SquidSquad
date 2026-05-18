## Analysis

### 1. AUTHORITATIVE SCOPE banner sufficiency

The banner is a stopgap, not a systematic fix. **Marginally sufficient** for the next pickup if PM actively monitors. The banner explicitly tells skill to read CONTEXT.md/TEST-PLAN.md. Since skill reads the issue body as its entry point (per implement-tasks.md), the banner will be seen. However, without #8916 formalizing this as a rule in the dev workflow, there's no guarantee skill will follow the pointer.

**Verdict**: Sufficient as a stopgap for the immediate next pickup, but #8916 should be prioritized to make it systematic.

### 2. Optimal pick-up order

Recommended order:
1. **#8914** (revert) — FIRST. Remove violating code from main. This is the cleanup.
2. **#8916** (L2 dev rule) — SECOND. Install the process guard before re-implementing anything.
3. **#8915** + **#8918** — in parallel after #8916. Re-implement #8694 correctly and fix #8701.
4. **#8917** (PM rule) — can run anytime, low dependency.
5. Then resume Phase 5 bundle: #8697 → verify #8694/#8695 → #8700/#8704 → #4792.

**Rationale**: Revert first so no bad code sits in main. Process fix second so re-implementation is protected. Then re-implement correctly. Then continue.

Alternative: #8916 first, then #8914, then #8915/#8918. This also works — the process fix protects the revert. But revert first gets bad code out faster. Either order for #8914/#8916 is acceptable; the key is both before #8915.

### 3. In-flight risks

The remaining Phase 5 tickets (#8697, #8700, #8704) and #4792 were transitioned `planned → approved` alongside the three that were violated. If they remain `approved`, skill could pick them up before #8916 lands. Their bodies have been rewritten with banners (mitigating factor), but no systematic guard exists.

**Recommendation**: Move #8697, #8700, #8704, #4792 back to `planned` or add a `blocked` label pending #8916 landing. The remediation tickets (#8914, #8915, #8916, #8917, #8918) are newly filed and not yet approved — PM should approve only #8914 and #8916 first.

### 4. Pre-flip checklist coverage

CONTEXT.md §6.4 items 5-6 do NOT account for the violations. They state #8694 and #8695 as prerequisites without noting that what shipped was wrong. A naive checklist check would see "shipped" and mark them complete, missing that remediation is required.

**Recommendation**: Update §6.4 to add a note or sub-item referencing remediation tickets #8914, #8915, #8918 as blockers, or add a general note that items 5-6 must be re-verified post-incident.

Now let me produce the findings in the required structured format.## Findings

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: §6.4 items 5–6 (lines ~255–262)
- **Severity**: error
- **Issue**: The pre-flip checklist references #8694 and #8695 as shipped prerequisites, but both shipped with incorrect implementations per the 2026-05-18 incident. Item 5 says "#8694 fragments (event-mode L1 base, including boot sequence and event_poll.py) are in place" — in reality a `TrackerHandoffDispatcher` was shipped instead. Item 6 says "#8695 (bootup_complete flag) is deployed" — in reality it shipped with gating logic that contradicts the informational-only lock. The checklist gives a false-positive readiness signal.
- **Evidence**: INCIDENT-2026-05-18-issue-body-drift.md documents: #8694 shipped `TrackerHandoffDispatcher` (violates thin-harness lock), #8695 shipped gating on `GET /events/for/<role>` (violates informational-only lock). The CONTEXT.md checklist was written before these violations and has not been updated.
- **Suggested fix**: Add a note or sub-item under §6.4 items 5–6 stating that remediation tickets #8914, #8915, #8918 must ship and the items must be re-verified before a flip. Alternatively, add a general post-incident re-verification gate: "All Phase 5 shipped tickets (#8694, #8695, #8701) have been re-verified against CONTEXT.md scope after remediation" before any flip.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT.md`
- **Line**: §6.4 item 7 (line ~263)
- **Severity**: warning
- **Issue**: Item 7 says `compose.py deploy <role>` must produce "a CLAUDE.md with zero /loop language and the events-mode boot sequence at L1." But the events-mode boot sequence content (owned by #8694) was never correctly implemented — #8915 is the re-implementation ticket. Until #8915 ships, the compose output cannot contain the correct boot sequence. This item is implicitly gated on #8915 but doesn't say so.
- **Evidence**: CONTEXT.md §5.1 defines #8694's scope as "the complete event-mode L1 base agent definition" including the boot sequence. INCIDENT documents that #8694 shipped wrong code (PR #8790 — TrackerHandoffDispatcher). The correct L1 base fragment doesn't exist yet.
- **Suggested fix**: Add explicit dependency: "7. #8915 (re-implementation of #8694) has shipped, and `compose.py deploy <role>` produces a CLAUDE.md with zero /loop language and the events-mode boot sequence at L1."

---

### Finding 3

- **File**: `.squidsquad/pm/planning/INCIDENT-2026-05-18-issue-body-drift.md`
- **Line**: "Remediation filed" section (lines ~39–48)
- **Severity**: warning
- **Issue**: The post-mortem does not state whether the four remaining in-flight tickets (#8697, #8700, #8704, #4792) were moved back from `approved` to a safe status. It says "PM transitioned 7 bundle/4792 tickets planned → approved" and documents three were violated. The other four could still be `approved` and thus pick-up-able by skill before #8916 lands. The AUTHORITATIVE SCOPE banner rewrite mitigates but does not eliminate the risk — the same dev workflow that doesn't read CONTEXT.md today still applies.
- **Evidence**: The post-mortem's "Gates that failed" section states "Skill (implementation) — read only the issue body; never opened CONTEXT.md or TEST-PLAN.md." The banner in the body tells skill to read CONTEXT.md, but without #8916 formalizing this as a workflow rule, the same gate could fail. The post-mortem doesn't document a status change for the four untouched tickets.
- **Suggested fix**: Add a line in the post-mortem stating the current status of #8697, #8700, #8704, #4792 (moved back to `planned` or held with a `blocked` label). Additionally, PM should gate any `planned → approved` transition on these tickets until #8916 ships.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/INCIDENT-2026-05-18-issue-body-drift.md`
- **Line**: "Remediation filed" cleanup bugs list (line ~41)
- **Severity**: warning
- **Issue**: The cleanup bug list includes #8914 (remove TrackerHandoffDispatcher + gating) and #8918 (mode-gate + cursor removal), but does not explicitly name which ticket removes the #8695 gating logic from `GET /events/for/<role>`. #8914's description says "events-endpoint gating from harness.py" which covers it, but this spans two violated tickets (#8694 and #8695) in a single remediation ticket. A reader mapping violations to remediation could miss that #8695 is addressed by #8914 rather than a dedicated #8695-cleanup ticket.
- **Evidence**: The violation table shows #8695 shipped "bootup_complete flag + gating logic on GET /events/for/<role>". #8914's scope says "remove TrackerHandoffDispatcher + events-endpoint gating from harness.py." The "events-endpoint gating" portion covers #8695's violation, but this isn't called out explicitly. The flag itself (correct part) remains in place after #8914, which is the intended state — but this subtlety is easy to miss.
- **Suggested fix**: Add a sentence clarifying: "#8914 removes the gating from #8695's implementation; the `bootup_complete` flag (the correct part of #8695) remains in place, so #8695 does not need a separate re-implementation ticket." Or split the "Remediation filed" section with a per-violation mapping.

---

## Answers to Audit Questions

### Q1: Is the AUTHORITATIVE SCOPE banner sufficient to prevent recurrence on the next pickup?

**Marginally sufficient as a stopgap, but not systematically safe.** The banner sits at the top of the issue body — the exact entry point skill reads per `implement-tasks.md`. It explicitly names the locked planning artifact (CONTEXT.md / TEST-PLAN.md). This is a strong signal and should cause skill to read the planning artifact before implementing.

However, the root cause was that the dev workflow *doesn't direct skill to read planning artifacts*. The banner tells skill *what* to read, but without #8916 formalizing the *requirement to read it*, there is no enforcement. The same three downstream gates (skill's code-review loop checking only the diff, QA verifying implementation against itself, DM merging on QA's verdict) would still pass a violation if skill ignored the banner.

**Verdict**: Sufficient for the immediate next pickup **if** PM adds an explicit instruction comment on each approved ticket reminding skill to follow the AUTHORITATIVE SCOPE pointer. #8916 must ship before the system is genuinely safe.

### Q2: Optimal pick-up order to minimize risk

```
1. #8914 (revert)          ← FIRST. Remove bad code from main.
2. #8916 (L2 dev rule)     ← SECOND. Install process guard before re-implementation.
3. #8915 + #8918           ← In parallel. Re-implement #8694 correctly + fix #8701.
4. #8917 (PM rule)         ← Anytime. No dependencies on other remediation.
5. Resume Phase 5: #8697 → verify #8694/#8695 → #8700/#8704 → #4792
```

**Rationale**: Revert first gets violating code out of main so no other agent or process interacts with it. Process fix second ensures the re-implementation of #8694 (a heavy instruction-design task per §5.1) is protected by the new rule. #8915 and #8918 are independent and can run in parallel. #8917 has no code dependencies and can ship whenever. After remediation, the original Phase 5 sequence resumes with #8697 as the spine.

An acceptable alternative is #8916 before #8914 — the process fix protects the revert too. The critical invariant is **both #8914 and #8916 must ship before #8915** to avoid re-implementing under the same unprotected workflow.

### Q3: In-flight tickets that could repeat the violation pattern before #8916 lands

**Yes — four tickets.** #8697, #8700, #8704, and #4792 were all transitioned `planned → approved` in the same batch as the three violated tickets. If any remain in `approved` status, skill could pick them up before #8916 lands.

Their bodies have been rewritten with AUTHORITATIVE SCOPE banners (mitigation), but the underlying dev-workflow gap (#8916 not yet implemented) still exists. The same pattern could recur: skill reads body, may or may not follow the banner to CONTEXT.md, implements to body text rather than locked spec.

**Recommendation**: Move #8697, #8700, #8704, #4792 back to `planned` or apply a `blocked` label until #8916 ships. The remediation tickets (#8914, #8915, #8916, #8917, #8918) are newly filed — PM should approve only #8914 and #8916 in the first wave.

### Q4: Does the pre-flip checklist (CONTEXT.md §6.4) account for the violations?

**No.** The checklist was authored 2026-05-17, before the 2026-05-18 incident. Items 5–6 check off #8694 and #8695 as prerequisites without any indication that their shipped implementations were incorrect. A reviewer checking the list would see both tickets as "shipped" and mark them complete — missing that #8914/#8915/#8918 must land first before these items are truly satisfied. Finding 1 and Finding 2 above cover the specific gaps.

---

## Recommended Go-Forward Order

**Not safe to proceed in original sequence.** The original sequence assumed #8694 and #8695 were correctly implemented and could serve as prerequisites for the pre-flip checklist. That assumption is false. Recommended order:

| Step | Ticket | Action | Rationale |
|------|--------|--------|-----------|
| 1 | #8914 | Revert violating code | Clean main first |
| 2 | #8916 | Implement L2 dev rule | Install process guard |
| 3 | #8915, #8918 | Re-implement #8694 correctly, fix #8701 | Parallel; both gated on #8916 |
| 4 | #8917 | PM rule (body sync) | Low dependency |
| 5 | #8697 | Resume Phase 5 spine | Original sequence resumes |
| 6 | — | Re-verify §6.4 items 5–7 | Confirm #8914/#8915/#8918 shipped |
| 7 | #8700, #8704 | Status line, TUI human queue | Original sequence |
| 8 | #4792 | Harness sole-authority lifecycle | Original sequence |

**Pre-pickup gate**: Before approving any ticket for skill, ensure #8697, #8700, #8704, #4792 are not in `approved` status (move to `planned` or `blocked`). Only #8914 and #8916 should be approved in the first wave.