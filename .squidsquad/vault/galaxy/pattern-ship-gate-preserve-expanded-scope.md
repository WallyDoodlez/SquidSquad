# pattern-ship-gate-preserve-expanded-scope

**Type:** pattern (DM delivery)
**Coined:** 2026-06-19 (#12853 ship)

## Pattern

When an operator/PM **strengthens or expands an issue mid-flight** (adds scope via comments) but the worker built + the verifier verified/promoted **only the original ACs**, the DM at the ship gate should:

1. **Ship the verified atomic unit.** Do NOT gate-keep the verifier — if they verified the original ACs zero-gaps and moved it to `pending-ship` *after* the strengthening, that is a deliberate signal the original scope is a coherent shippable slice. DM never overrides a PASS/pending-ship verdict.
2. **BUT first file a follow-up task** (`create-task --role pm --reporter dm`, `status:pending` — DM can't approve) routing the **un-delivered expansion** to PM for decomposition, capturing the strengthening comments' intent.

## Why

The `pending-ship → shipped` transition **auto-closes** the issue. Operator scope that was added by comment but not built lives only in that issue. Once closed, it drops out of every open-queue scan → PM never picks it up to decompose → **operator-directed scope is silently orphaned**. Filing the follow-up before the close preserves it.

Watch for the signal phrase in the strengthening comment, e.g. *"this expands #X into a coherent deliverable; <worker> may decompose into stories/tasks at implementation"* — that explicitly means the expansion is separate follow-up work, not a reason to hold the verified slice.

## How to apply

- Read **all** issue comments at the ship gate (not just the body ACs). Compare the operator's latest intent against what the PR actually delivered + what the verifier walked.
- If expansion > delivered: search open issues for an existing follow-up; if none, file one to PM (route-only, not a build-ready spec — DM doesn't plan), then ship + close.
- Keep the ship comment honest: name what landed, name the expansion, point to the follow-up issue number.

Concrete instance: #12853 shipped the L1 SOUL doc generalization (6 ACs); the operator's relentless-autonomy expansion (inline 20-min auto-timeout etc.) was preserved as #12896 (role:pm). Related: [[decision-agents-never-stop-while-work-pending]], [[learning-closing-keyword-in-state-commit-autocloses-issue]], [[feedback_bump_requires_pm_signal]].
