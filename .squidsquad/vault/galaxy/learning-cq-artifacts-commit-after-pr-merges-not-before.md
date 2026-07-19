---
type: learning
tags: [qa, comprehension-staleness, sequencing, cq-authorship]
created: 2026-07-19
updated: 2026-07-19
owner: verifier
status: active
confidence: high
source: observation
links: [learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]
---

## Context

Verifying #13565 round 2: authored `tests/comprehension/13565_spec.json` and
its `.staleness-baseline.json` entry, correctly capturing the blob hash of
`references/roles/instructions.md` **on the feature branch** (the content
that will land once the PR merges). But #13565 itself was still blocked
(AC1 needed a PM ruling) — not yet merged to `main`. Committed the spec +
baseline entry to `main` anyway as part of round-2 state cleanup.

Immediately after, `comprehension_staleness.py check` on `main` flagged the
brand-new spec as stale: the baseline recorded the branch's future hash, but
`main`'s actual current `instructions.md` (pre-#13565) didn't match it.

## Lesson

**A CQ spec's baseline entry must be committed to `main` only after the
underlying PR has actually merged — never during an earlier verification
round while the item is still blocked.** The baseline hash is a claim about
what's true on `main`; committing it early makes a claim about content that
doesn't exist there yet, and `comprehension_staleness.py` immediately
(correctly) flags the mismatch — a self-inflicted false alarm, not a real
regression.

This generalizes the established pattern from #13563/#13566/#13654/#13666:
those all authored the CQ spec *during* verification but only committed it
to `main` alongside the PASS-and-merge sequence — spec authored last, but
landed after the merge, not before. #13565's round 2 broke that ordering
because AC1's approval blocked the ship even though AC3's CQ work was
independently done; the fix is to keep the finished spec staged locally (or
in the round's working notes) until the item actually reaches pending-ship,
not to commit it the moment it's written.

**Practical check**: before committing a `.staleness-baseline.json` entry,
confirm the target file's `HEAD` blob hash on `main` already matches what
the spec was verified against — if the underlying PR hasn't merged yet, it
won't, and the commit should wait.

## Related

- [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]] —
  a different axis of the same tooling (who refreshes an *existing* spec's
  baseline after a merge lands) rather than when to first commit a *new*
  spec's baseline.
