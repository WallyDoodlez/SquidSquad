---
type: learning
tags: [skill, worker, testing, quarantine, known-failures, triage, scope-discipline]
created: 2026-06-13
updated: 2026-06-13
owner: skill
status: active
confidence: high
source: observation
links: [learning-gate-collection-abort-masks-reds, decision-deterministic-testing]
---

## Context

#11503 was chartered as "23 post-cutover stale tests red since the v0.44.0
gate-death — rebind each to v2 reality and un-quarantine." That framing
assumed every quarantined red was *stale* (test asserts old structure that
legitimately changed). Working the tail (cycle 1644), 2 of the 23 turned out
NOT to be stale: `test_agent_boundaries` (20 missing L3 responsibility stubs)
and `test_compose_author_comments_11142::test_10360_cleanup_markers_preserved`
were failing because they correctly demand work that is **genuinely
incomplete** — the Responsibility compose slot tracked by still-OPEN #10360
(COMPOSE-ARCHITECTURE §5.2). The gate-death had masked them too, so they sat
in the same quarantine bucket as the stale ones and looked identical.

## Lesson

**A quarantine list mixes two species of red, and they need opposite
treatment. Triage each before un-quarantining:**

- **Stale test** — source legitimately restructured; the assertion describes
  a world that no longer exists. → Rebind the assertion to current reality,
  un-quarantine. (This is the expected #11503 work.)
- **Blocked-on-open-work test** — the assertion is *correct*; the source is
  genuinely missing something an OPEN issue is chartered to deliver. → Do NOT
  weaken or delete the assertion to force the gate green. Keep it quarantined,
  re-point its KNOWN_FAILURES reason to the blocking issue, and cross-link the
  test on that issue so it un-quarantines when the work lands.

The tell: when a "stale test" fix would require you to *delete a real
assertion* or *create the missing thing yourself*, stop — you've crossed from
stale-test-rebind into the blocking issue's scope. Check `gh issue view` on
any issue the test/source references before deciding. Front-loaded
reading-everything-first (not skim-then-fix) is what surfaces this before you
wrongly paper over a real gap.

This is the same shape as the recurring "shipped-but-unwired" audit pattern —
a surface that *looks* complete (here: a quarantine framed as pure stale-debt)
hiding an unfinished one. And it complements
[[learning-gate-collection-abort-masks-reds]]: that one is how the gate should
be *built*; this one is how to *work the backlog* the gate exposed.

## How to apply

When clearing any quarantine / KNOWN_FAILURES / xfail backlog: for each entry,
classify stale vs blocked-on-open-work BEFORE editing. Verify the issue state
of anything the failing assertion references. Un-quarantine only the stale
ones; route the blocked ones to their owning issue with a re-pointed reason
and a cross-link. Surface the re-scoping to PM — an umbrella chartered as "N
stale tests" that contains M blocked-on-other-work tests cannot reach N/N.
