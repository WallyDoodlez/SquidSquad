---
type: learning
tags: [qa, verification, git_ops, pr-merge, bootstrap, self-reference]
created: 2026-07-19
updated: 2026-07-19
owner: verifier
status: active
confidence: high
source: observation
links: [learning-prove-regression-test-fails-pre-fix]
---

## Context

Verifying #13691 (`git_ops.py`'s `pr_merge()` now passes explicit `--subject`/`--body`
on squash-merge so a single-commit PR's own commit message — e.g. a stray "Closes #N"
in a `git commit -m` call — can never leak into the squash commit that lands on `main`).
Live-tested the fix three times against real disposable scratch PRs once actually
running from the fix branch: it works, cleanly, every time.

Then shipped it for real via the harness `/merge` endpoint (PR #13704, itself a
single-commit PR whose commit message ended in "Closes #13691"). The resulting squash
commit on `main` (`03f94ba8e`) still carries the raw, unneutralized "Closes #13691" —
the exact bug the fix exists to prevent, on the fix's own shipment.

## Lesson

**A fix to the merge-execution mechanism cannot protect the one merge that lands it.**
`harness.py`'s `_reload_git_ops()` (#13588) already does the right thing —
`importlib.reload()` from on-disk `git_ops.py` fresh on every merge, so no stale
in-process module caching is at play. The gap is purely temporal: at the moment the
harness begins merging the PR that *contains* the fix, `main` (and therefore the
harness's own checkout) still has the *pre-fix* code, because landing the fix on
`main` is exactly what that merge is in the process of doing. There is no way for the
new logic to govern the commit that first introduces it — chicken-and-egg, not a
caching bug, not a logic bug, not fixable by iterating on the same PR.

This is the same shape as the `_pr_state_scope_violations` self-exemption note already
in `git_ops.py` (a gate can never exempt a path from itself in the same PR that adds
the exemption — "the gate evaluates main's CURRENT predicate, by design") generalized
from a static allow-list gate to a merge-mechanism fix.

**Verification implication**: don't read the fix's own landing commit as evidence
either way. A merge-mechanism fix must be verified by testing it *as if it were
already on `main`* — check out the fix branch locally, confirm the target script's
on-disk content includes the fix, and only then invoke the merge path (a real live
merge test on a disposable scratch base branch, never `main`, is the strongest form —
see #13691's TEST-PLAN). The fix's OWN shipping merge commit is expected to still
exhibit the pre-fix behavior once, and that is not a finding against the fix — reject
only if a *later* merge (one genuinely running the fixed code) still shows the bug.

**Practical mitigation, not required but available**: since the verifier already knows
the exact clean subject/body the fixed code would have produced, it's possible to
bypass `pr_merge()`'s implicit default entirely for this one bootstrap merge — call
`gh pr merge --squash --subject "..." --body "..."` directly with pre-computed
neutralized values instead of going through the (still pre-fix) harness `/merge`
endpoint. Not done for #13691 (the resulting closed-but-labeled issue is already a
safe, designed-for state per the tracker's #9837 handling), but worth considering when
the landing commit's exact text matters more (e.g. a security-sensitive keyword
rewrite where even one leaked instance is unacceptable).

## Rationale

The verifier's job is to confirm the fix works for its *actual, ongoing* protective
purpose — every merge from this point forward — not to demand the impossible (a fix
that also retroactively governs its own introduction). Understanding this class lets a
future verifier distinguish "the fix is broken" from "this is the one merge no fix to
this fix could ever protect," and avoid an endless reject-reship loop chasing a
one-time, structurally unavoidable exception.

## Related

- [[learning-prove-regression-test-fails-pre-fix]] — the general discipline of testing
  fixed vs. unfixed code deliberately and precisely, which is what surfaced this: only
  because I insisted on confirming *which* code was actually running did the bootstrap
  gap become visible instead of being silently attributed to test flakiness.
