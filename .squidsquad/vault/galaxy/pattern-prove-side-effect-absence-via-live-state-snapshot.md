---
type: pattern
tags: [testing, verification, qa, isolation, side-effects, harness, 12282]
created: 2026-06-14
updated: 2026-06-14
owner: verifier-lead
status: active
confidence: high
source: observation
links: [pattern-verify-unmocked-paths-stubbed-by-units, learning-default-port-fallback-is-live-egress-trap-in-tests, learning-tests-must-not-mutate-shared-live-state]
---

# Verify a side-effect REMOVAL with a live shared-state before/after snapshot

**Pattern (#12282 verification):** the fix removed a test-isolation leak that POSTed a real `/restart` to the live harness (:7373) during every full-suite run. The worker added a correct in-suite autouse guard that converts the leak into a loud test failure. But a verifier who only re-runs the suite is trusting *the worker's guard to be correct* — circular. The independent move is to probe the **shared resource the side-effect would have touched**, before and after.

**How to apply (verifier independent-perspective lane):**
- For a fix that claims to *stop* a side-effect (leaked network call, file mutation, process restart, shared-state write), pick an observable on the affected resource and snapshot it **before and after** running the historically-offending operation. Equality across the run is direct proof of absence — and it does not depend on the worker's own guard logic being right.
- Concretely for #12282: captured the live harness skill agent's `boot_time` / `last_spawn_at` / `pid` / `consecutive_fast_deaths` from `/status`, ran the full suite ×2, re-captured. Byte-identical → zero restarts triggered. The historical leak fired a real `/restart` *every* run, so an unchanged agent is unambiguous: the engine is gone.
- This is the AC-first complement to [[pattern-verify-unmocked-paths-stubbed-by-units]]: that one proves a behavior is *present and faithful* by live-running the stubbed seam; this one proves a behavior is *absent* by watching the resource it would have perturbed. Use both — one confirms the guard fires (run the regression test), one confirms reality agrees (live snapshot).
- Safety: when reproducing the *old* leak would itself fire the destructive side-effect against production (here, a real restart of a live agent), do NOT reproduce on old code. Verify the fix positively (regression test + live before/after) instead of re-triggering the bug.
