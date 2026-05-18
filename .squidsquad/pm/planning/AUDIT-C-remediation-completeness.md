Now I have a complete picture of the code surface. Let me compile my analysis.

---

Based on my review of the changed files (the incident post-mortem, CONTEXT.md, CONTEXT-4792.md, DECISIONS-4792.md) and the actual code surfaces in `harness.py` and `cycle_post.py`, here are my findings:

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 1962–1966, 1968–1979 (ExternalActivityDetector._emitted_lock, is_emitted, mark_emitted)
- **Severity**: warning
- **Issue**: When #8914 removes `TrackerHandoffDispatcher`, the cross-dedup infrastructure added to `ExternalActivityDetector` for PR #8790 (#8694) becomes dead weight. The comment at line 1963–1966 explicitly states `#8694: shared lock for _emitted_issues — TrackerHandoffDispatcher writes here from a separate thread`. Without the dispatcher, `_emitted_lock` protects only a single-threaded access pattern (ExternalActivityDetector's own poll loop), and `is_emitted()`/`mark_emitted()` lose their cross-thread reason to exist. Neither #8914's title ("remove TrackerHandoffDispatcher + events-endpoint gating") nor #8918's scope capture this residual cleanup.
- **Evidence**: The `_emitted_lock`, `is_emitted()`, and `mark_emitted()` methods were introduced specifically for cross-dedup between `TrackerHandoffDispatcher` (line 2175: `activity_detector.is_emitted(issue_num)`) and `ExternalActivityDetector`. After dispatcher removal, the `is_emitted`/`mark_emitted` calls at lines 2175 and 2185 disappear, and these methods serve only internal single-thread use in `_check_for_changes()`.
- **Suggested fix**: Either expand #8914 scope to include cleanup of `_emitted_lock` → plain `threading.Lock()` (or remove entirely), simplify `is_emitted`/`mark_emitted` to direct dict operations, and remove stale #8694 comment at lines 1963–1966; OR file a separate follow-up cleanup ticket.

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 1946–2084 (ExternalActivityDetector), specifically 2073–2074
- **Severity**: warning
- **Issue**: `ExternalActivityDetector._check_for_changes()` polls GitHub for tracker changes and emits `assigned-to` events (lines 2073–2074: `_emit_event("assigned-to", "harness", payload={...})`). This is a thin-harness violation per CONTEXT.md §2 ("No tracker observation. No dispatch logic."). The incident report attributes this to #7630 (line 1947), not the violating PRs #8790/#8801. However, none of the 5 remediation tickets address it. If #8914 removes `TrackerHandoffDispatcher` but `ExternalActivityDetector` continues emitting `assigned-to`, the harness still performs tracker observation + dispatch — a partial thin-harness violation that survives remediation.
- **Evidence**: CONTEXT.md §2 locked decision: "Thin harness, pure broadcast — harness is an event bus only. No tracker observation. No dispatch logic." ExternalActivityDetector at line 1947 docstring: "Polls GitHub for external changes and emits assigned-to events." It calls `subprocess.run(["gh", "issue", "list", ...])` (line 2028) and emits `assigned-to` events (line 2074).
- **Suggested fix**: File a follow-up ticket to either remove `ExternalActivityDetector` entirely or restrict it to non-dispatch observation only. The existing 5 tickets are clean for their stated scopes, but the collective remediation set does not achieve a fully thin harness.

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 101–105, 268–269, 923–924, 1097–1100, 1480–1481, 1870–1873
- **Severity**: warning
- **Issue**: After #8914 removes the gating logic from `get_events_for_role` (lines 1187–1197), at least 6 comment blocks throughout `harness.py` will be stale — they frame `bootup_complete` as a dispatch gate rather than an informational flag. For example, line 101–105 says "bootup-complete gating. False until the agent emits bootup-complete. While False, get_events_for_role returns no events so the harness never dispatches..." After cleanup, `bootup_complete` is informational only (CONTEXT.md §5.2), and these comments will mislead future readers about the flag's purpose.
- **Evidence**: CONTEXT.md §5.2: "bootup-complete Event (Informational Only) ... No dispatch gate, no per-role queue, no event holding." Lines 101–105, 268–269, 923–924, 1097–1100, 1112 ("event dispatch unlocked"), 1196 ("gated": "bootup-incomplete"), 1480–1481, 1870–1873 all use gating/dispatch language.
- **Suggested fix**: Expand #8914 scope to include updating these comments to reflect informational-only semantics, matching CONTEXT.md §5.2 and the glossary entries for `bootup-complete event`. Alternatively, add a note to #8914's acceptance criteria that all comments referencing bootup-complete as a "gate" must be corrected.

### Finding 4

- **File**: `.squidsquad/pm/planning/INCIDENT-2026-05-18-issue-body-drift.md`
- **Line**: 60–61 (description of #8916 and #8917)
- **Severity**: warning
- **Issue**: #8916 (L2 dev rule to read CONTEXT.md/TEST-PLAN.md) and #8917 (PM body sync) address the root cause (stale issue bodies) and gate #1 (skill's implementation). However, the incident identified 4 failed gates. After remediation, gates #2 (code-review loop at `implement-tasks.md` §9c), #3 (QA verification), and #4 (DM merge) still have no explicit check against the planning contract. The post-mortem acknowledges this at Lesson #5: "All three downstream gates (skill / QA / DM) keyed off implementation rather than planning artifact. At least one of those gates needs to check the planning artifact directly — most efficient is the PM-side body sync (#8917)." The strategy relies entirely on #8917 working perfectly. If PM forgets to sync a body, gates #2–#4 still offer no defense.
- **Evidence**: Post-mortem Gates that failed section lists 4 gates. #8916 addresses gate #1 (skill). #8917 addresses root cause (body not synced). Gates #2–#4 are not addressed by any remediation ticket. The code-review loop at `implement-tasks.md` lines 37–77 checks diff quality against ACs (line 51: "review against ACs and project philosophy") but does not verify diff against CONTEXT.md architectural constraints. QA at `references/sub-skills/roles/qa/` runs tests but doesn't verify TEST-PLAN.md AC list (post-mortem line 47). DM merges on QA verdict (post-mortem line 49).
- **Suggested fix**: At minimum, add a step to the code-review loop (§9c) that requires checking the diff against CONTEXT.md architectural locks when the task has planning artifacts. Alternatively, add a QA gate that explicitly verifies TEST-PLAN.md AC list, not just test pass/fail. Either would provide defense-in-depth when #8917's body sync misses a change.

### Finding 5

- **File**: N/A (scope gap — #8915 description in incident report vs. CONTEXT.md §5.1)
- **Line**: INCIDENT-2026-05-18-issue-body-drift.md line 57
- **Severity**: warning
- **Issue**: The incident report describes #8915 as "implement #8694 actual scope (`event_poll.py` + agent event-mode L1 base content)." CONTEXT.md §5.1 (the locked #8694 scope) is approximately 80 lines of detailed deliverables including: boot sequence (Case A), all event reactions (Cases B–E), cursor management with atomic `.tmp`+`mv`, forge-read pattern, idle improvement-scan cool-down loop with `Status: running` crash recovery, comment handling + DM end-of-task re-read exception, transition-on-handoff rule, eviction-gap handling, `event_poll.py` script with specific retry/timeout/cursor behavior, per-role events fragments for all 4 roles, `includes-events.yml` manifests, CQ spec, integration tests, mode-conditional-language ban, and no-standalone-`l1-boot.md` constraint. Without reading the actual #8915 GitHub issue body (unavailable via `gh issue view`), it is impossible to verify whether all §5.1 deliverables are enumerated vs. just the abbreviated parenthetical. The one-line summary suggests a subset.
- **Evidence**: CONTEXT.md §5.1 Scope section lists 10+ bullet items under "Scope" plus 6+ acceptance criteria. The incident description of #8915 captures 2 of them explicitly (event_poll.py, agent event-mode L1 base content). The actual issue body may be comprehensive — this finding flags the verification gap, not a confirmed omission.
- **Suggested fix**: Verify #8915's body against the full CONTEXT.md §5.1 scope checklist (found in TEST-PLAN-8694.md AC-1 through AC-7 and §3–§5). Any missing deliverables should be added to #8915's acceptance criteria.

---

**Summary**: The 5 remediation tickets collectively address the core violations from the incident. However, there are residual gaps: (1) cross-dedup cleanup in `ExternalActivityDetector` after `TrackerHandoffDispatcher` removal is not explicitly covered, (2) `ExternalActivityDetector`'s `assigned-to` emission itself violates thin-harness but is not addressed, (3) stale bootup-complete "gating" comments will survive cleanup, (4) gates #2–#4 (code review, QA, DM merge) still lack architectural conformance checks, and (5) #8915's scope summary in the incident report is abbreviated relative to CONTEXT.md §5.1 — the actual issue body must be verified. I cannot say "remediation complete" due to findings 1, 2, and 4.