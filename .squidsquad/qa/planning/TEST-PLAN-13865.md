# TEST-PLAN-13865

gh API writes ride the flippable machine-global active account (HIGH, type:issue, auto-approved, companion to #13863). Derived independently from the bug report.

## TCs

- **TC1 — override mechanism proof**: does `GH_TOKEN` in a subprocess env actually override gh's active-account identity for a single call, without touching global state?
- **TC2 — gh_identity resolves correctly**: does `gh_identity.pinned_identity()`/`pinned_token()` resolve the correct real identity and a real usable token?
- **TC3 — end-to-end pin, live**: does `gh_identity.gh_env()`'s constructed env, used for a real `gh api` call, correctly authenticate as the pinned identity?
- **TC4 — wiring coverage**: are all of tracker.py's gh call sites (`_run_list`, `_run_list_timeout`, `_run_gh_with_body`) and git_ops.py's `_run_list` wired to use the pinned env?
- **TC5 — standalone-copy contract preserved**: does git_ops.py's defensive import keep the module working when copied standalone (post-merge hook contract)?
- **TC6 — exemptions correct**: `gh auth` subcommands, an operator-set `GH_TOKEN`/`GITHUB_TOKEN`, and non-gh commands must NOT be touched by the pin.
- **TC7 — chokepoint completeness**: is harness.py (named in the issue's suggested direction as a chokepoint) actually exposed to this bug, or correctly out of scope?
- **TC8 — regression coverage**: new unit tests pass.
- **TC9 — full ship gate, byte-exact regression check**: static + integration suite, with the pre-existing failure cluster diffed byte-exact against clean main (not just eyeballed) to catch any genuinely new regression.

## Execution notes

TC1/TC3 executed live without flipping the shared machine-global active account myself: proved the override mechanism using a manually-supplied `GH_TOKEN` for a read-only account (Naahtec) while the active account remained WallyDoodlez throughout, then separately proved `gh_identity.gh_env()` itself constructs a correctly-pinned env end-to-end against a real `gh api user` call. This composes to the same proof skill's own deliberate-flip live test gave, without repeating the shared-state risk.
