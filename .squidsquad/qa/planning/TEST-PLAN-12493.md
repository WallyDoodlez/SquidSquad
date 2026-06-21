# TEST-PLAN-12493 — L2 pipeline-sentinel: halt detect → investigate → unblock-or-escalate

- **Task**: #12493 (type:task, priority:high, role:skill). Enhance `references/sub-skills/roles/pm/pipeline-sentinel.md` (L2/PM). **PR**: #12494, branch `squidsquad/task/12493` @ `61ed36f4d`.
- **Derived**: 2026-06-21 00:45 from the 8-AC contract (comprehension-gated). LLM-consumed sub-skill → CQ HARD GATE (AC7).
- **Method**: isolated worktree; source-diff review (AC1-6); compose marker/consumption (AC8, pm-only); fresh PM-agent scenario CQ (AC7); full fail-closed static gate (no-regression).

## ACs
1. Halt = lack of forward progress past 90 min, incl failed-handoff (comments exist but unactioned ask + idle owner).
2. Investigate → ≥4 classes (failed-handoff / dead-agent / blocked-on-decision / genuine-no-progress).
3. Remedies event-mode-effective; bare comment does NOT wake; cross-ref comment-handling.
4. PM-authority boundary (allowed/prohibited) for "unblock"; no remedy crosses it.
5. Escalate-for-decision via human-reaching surface (pending-human-review + options), not bare comment.
6. #12460 worked example: detect → classify → wake-event-unblock or escalate-with-options.
7. **CQ (REQUIRED):** fresh PM agent on #12460-shaped scenario produces detect→investigate→event-effective-unblock-or-escalate, NOT a bare-comment nudge.
8. Composes into PM's deployed CLAUDE.md (L2 ⇒ PM role).

## Result
**FAIL** — see QA-RESULTS-12493. Functional ACs (1-6, 8) + AC7 CQ all pass, but the section rename ("Stall Detection" → "Halt Detection…") broke 3 existing structural tests (`test_feat_1228_pipeline_sentinel.py` x2, `test_feat_1363_label_sync.py`) that were not updated → full static gate red (exit 1). Back to in-progress (skill) to update the stale tests.
