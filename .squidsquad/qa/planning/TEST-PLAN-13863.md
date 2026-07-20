# TEST-PLAN-13863

Fleet git-push credential fix (HIGH, type:issue, auto-approved). Derived independently from the bug report's Observed/Impact/Reproduction/Suggested-direction — not from skill's PR description.

## TCs (from the bug report, not the fix's own claims)

- **TC1 — core repro**: with the machine's active `gh` account genuinely flipped to a read-only identity, does a real `git push` (or dry-run) from an affected clone succeed via the fix, where it would have failed pre-fix?
- **TC2 — credential-manager-entry-gone case**: does the fix route pushes through a helper that doesn't depend on the OS credential manager at all (the other half of the original report)?
- **TC3 — boot-time gate**: does `tracker.py check_gh` fail loudly (not silently) when push capability is genuinely absent, per the report's "consider a boot-time push-capability check" suggested direction?
- **TC4 — doctor crash resilience**: can a `push-doctor` failure/crash brick boot? (block must key on an explicit marker, never bare exit code)
- **TC5 — bare push call sites**: do call sites that bypass `_git_push` (cycle_post.py, harness.py) still benefit from the fix?
- **TC6 — no secret leakage**: does the fix avoid writing a raw token into git config?
- **TC7 — regression coverage**: new unit tests for the added functions, all passing.
- **TC8 — full ship gate**: static suite + integration suite, with any failures triaged for relevance to this diff specifically (not just pass/fail counted blind).
- **TC9 — residual scope**: is the fix's own disclosed residual (gh-API-write path still flippable) tracked as a separate, non-blocking follow-up rather than silently dropped or wrongly bundled in?

## Execution notes

TC1/TC2 executed live against the machine's actual, currently-flipped gh state (not simulated) — see QA-RESULTS-13863.md. TC-heal-active (switching the global active account) deliberately NOT live-tested by flipping it myself: PM's own comment on #13863 confirms this is machine-global state shared by all 4 live agent clones simultaneously, and deliberately flipping it mid-verification risks breaking pm/dm/skill's concurrent sessions — the exact incident class this bug is about. That path is covered by the mocked `TestPushDoctorHealActive`/`TestCheckGhActiveAccountHeal13863` suites instead.
