# TEST-PLAN #13569 — boot-drain deploy-signal deferred until boot completes (agent-side)

**Derived from the issue body's "Fix" / "Root cause" / "Boundedness" sections — my own independent reading, not the worker's diff.** LLM-consumed instruction change (event-mode-contract.md, runtime-loaded by every role's `boot-bootstrap`) — comprehension-coverage AC applies per #9184.

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | A deploy-signal reached during the boot drain is **not** honored (no `ack-stop`/halt) at the moment it is reached |
| AC2 | The boot drain **stops** at the deploy-signal — later drain events are neither processed nor lost; they re-deliver on the next boot drain |
| AC3 | The agent completes its first boot (reaches the post-drain / first steady-state decision boundary) **before** the deferred signal is honored |
| AC4 | The deferred signal **is** honored at that post-drain boundary — before entering idle/cool-down and before any new `work_queue()` pickup — provided on `main` with a clean tree |
| AC5 | If boot resumed an in-progress task onto a feature branch, finish-first still applies (complete/hand off + return to `main`) before honoring, and Case C's normal `work_queue()` pickup is skipped in favor of honoring the held signal |
| AC6 | Steady-state (post-boot) deploy-signal handling is **unchanged** — still honored immediately at the next on-`main`/clean-tree between-task boundary |
| AC7 | No loss on crash/restart during the deferral window — cursor never advances past the held signal, so it re-delivers on the next boot drain (deferred-then-honored again), never silently dropped |
| AC8 | Regression test pins the contract text; full static gate green |
| AC9 | Comprehension gate (QA-owned, #9184 hard gate for LLM-consumed instructions): a fresh agent given ONLY the modified fragment must correctly derive AC1–AC7 |

## Verification (branch squidsquad/task/13569, built directly on current main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC8 | Worker's own `TestBootDrainDeploySignalDeferral` (4 tests, text-pinning) | **PASS** (4/4) |
| TC2 | AC8 | Full static gate on combined branch state | **PASS** (5476/0) |
| TC3 | AC1–AC7 | Independent close read of the full Case E + Case C diff for internal consistency (no contradiction with cursor-management.md / idle-cooldown-loop.md — grepped, neither fragment references deploy-signal/boot-drain) | **PASS** — text explicitly and unambiguously states hold-not-honor, stop-the-drain, post-drain-boundary honor, finish-first + Case C gate, steady-state unchanged, and crash-safety (all 7 ACs directly quoted in the fragment) |
| TC4 | AC9 | Fresh sonnet general-purpose agent, given ONLY `event-mode-contract.md` from this branch, no other file/tool/prior knowledge, asked 4 targeted questions (hold-on-reach; honor timing; finish-first + Case C gate; steady-state contrast + crash-safety) | **PASS** — 4/4 correct, zero must_not violations, all answers cited exact supporting quotes. Spec: `tests/comprehension/13569_spec.json` |

## Corroboration of the worker's DeepSeek review claim

Worker's Discussion comment claims a DeepSeek pass found 3 gaps (F1 stop-the-drain, F2 Case C gate + finish-first, F3 context-loss re-delivery note), all fixed in commit `4795807d3`. Independently confirmed all three are actually present in the merged diff (not just claimed): the "Stop the boot drain here" bullet (F1), the Case C step-3 exception + Case E's "do NOT run Case C's work_queue() pickup" bullet (F2), and the "context-pressure checkpoint... loses nothing" bullet (F3) are all verbatim in the current fragment text (see TC3).

## Out-of-scope (explicitly, per the issue's own "Related" section)

- The pre-existing "residual vs live" deploy-signal ambiguity ([[learning-deploy-signal-boot-drain-residual-vs-live]], #13175) is a **different** surface (deploy-FAILURE / spurious-drift, not boot-drain honor-TIMING) and is untouched by this fix — confirmed the new text still explicitly forbids self-assessing drift ("Do NOT self-assess drift from your local clone and skip") and does not attempt to resolve #13175.
- No harness.py changes required or expected — this is a pure agent-side prose fix; `common-events/` fragments are runtime-Read, not compose-inlined, so no recompose is needed for it to take effect at next boot (confirmed against the sub-skill-catalog.md classification).

## Housekeeping performed as part of verification

`tests/comprehension/13175_spec.json`'s CQ1 expected answer ("HONOR it... do NOT dismiss as stale residual restart telemetry") is **directly contradicted** for the boot-drain case by this fix (the old expected answer *is* the #13569 bug). Left in place per preserved-test-artifact policy but annotated `superseded_by: 13569` with an explanatory note, pointing to `13569_spec.json` as current guidance — QA-owned artifact housekeeping, not a worker-routed finding (see QA-RESULTS for full rationale).

## Verdict

**PASS — zero gaps against AC1–AC9.**
