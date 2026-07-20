# TEST-PLAN-13855

`_check_merged_pr`'s `--limit 20` blind spot (MEDIUM, type:issue, auto-approved). Derived independently from the bug report + my own earlier Discussion comment on the issue (confirming the adapter-path caveat was real, not hypothetical).

## TCs

- **TC1 — core repro, real case**: does the fix's server-side `--head` query find PR #13708 (the exact real case from the original report, still absent from the newest-20 window today)?
- **TC2 — old approach still fails (negative control)**: does the pre-fix `--limit 20` approach still miss PR #13708 today, confirming the bug is still live and the fix is not solving an already-resolved problem?
- **TC3 — adapter path covered too**: does the fix address the GitHubAdapter/ForgejoAdapter path I flagged in my Discussion comment, not just the gh-CLI fallback?
- **TC4 — fallback preserved**: does a larger (limit-100) global fallback still catch non-standard branch prefixes, preserving the pre-fix prefix-agnostic suffix-match behavior?
- **TC5 — regression coverage**: new + existing merged-PR/ship-gate tests green.
- **TC6 — full tracker.py module**: no collateral regression in the surrounding module.
- **TC7 — DM's second real-world manifestation**: DM's Discussion comment reports the bug recurring even without eventual-consistency lag (pure list-window aging from repo velocity) — confirm the fix's design (exact server-side match) is immune to this variant too, not just the original timing-based manifestation.
