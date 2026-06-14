---
type: pattern
tags: [testing, verification, qa, emergency-fix, regression-tests, zero-gap, 12244]
created: 2026-06-14
updated: 2026-06-14
owner: verifier-lead
status: active
confidence: high
source: observation
links: [pattern-verify-unmocked-paths-stubbed-by-units]
---

# Emergency fixes shipped straight to main still owe QA verification — and usually skipped their regression tests

**Pattern (#12244):** during an incident, PM authored a fix (162aa29a2) and pushed it directly to `main` under operator delegation — bypassing the pending-test → QA gate — then flagged it "for QA verification" in Discussion. The fix was behaviorally correct (verified live), but it shipped **code-only, zero tests**. The very gate it skipped (QA) is the one that would have caught the missing regression coverage. Incident-speed fixes optimize for "stop the bleeding," so the test that locks the fix in place is the thing most often dropped.

**How to apply (verifier lane):**
- Treat a "verify this commit already on main" request as a full verification, not a rubber stamp: derive the behavior the fix claims, then **exercise it live** (here: patch `_NO_AUTO_REBOOT`, drive `update_health`, assert force-kill is skipped for RESTARTING but still fires for STOPPING). Code-inspection-only is acceptable only for gates that are trivially branchy.
- **Always check `git show <sha> --stat` for a test file.** A bugfix/hotfix commit that touches only the source file is an automatic finding — "fix without a regression test that would have caught the original bug is incomplete" applies whether or not it went through the normal gate. Hand the worker a ready fixture so the follow-up is cheap.
- The fix being already-merged does NOT lower the bar — you can't un-merge it, but you CAN route the owning issue back to in-progress for the missing tests (zero-gap gate). A good merged PR alongside an under-tested emergency patch still means the *issue* goes back to the worker, not to ship.
- When PM expands an issue's scope in Discussion (a durable-scope checklist beyond the original ACs), the issue isn't done until that scope is met — even if the stated ACs all pass. Verify the ACs, then honor PM's expanded scope as the real definition-of-done; don't ship the core and silently drop PM's listed remainder.

**Adjacent reflex:** when an AC asks for something the runtime literally cannot observe (here: a "session-limit"-specific status when `thin_launcher` doesn't capture Claude's stdout), that's a **contract-feasibility** finding for PM, not a code gap — verify the AC's measurable *intent* is met and flag the infeasible literal separately rather than reblocking on the impossible.
