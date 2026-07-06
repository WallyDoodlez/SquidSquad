---
type: learning
role: verifier
created: 2026-06-28
tags: [verification, consolidation, deletion, consumer-sweep, ac-coverage, gotcha]
owner: qa-lead
status: active
confidence: high
source: observation
updated: 2026-06-28
---

# Verify a deletion/consolidation task by a repo-wide sweep for the removed artifact's name

## Context

A task that **deletes or moves files** (launcher consolidation #13318: 7 scripts → `.squidsquad/start.{ps1,sh}`) almost always lists a "repoint all consumers" AC. The worker reliably updates the obvious code consumers but **misses narrative/doc references** — README, ARCH docs, install runbooks — that still point at the deleted/moved path. Those are live, now-broken references the AC explicitly required to be handled.

## The verification move

1. **`git grep` the branch tree for every removed/old artifact name** (e.g. `start-harness`, `restart-harness`, `./start.sh`, `start.bat`), not just the changed files.
2. **Filter archival noise**: matches under `.squidsquad/*/planning`, `*/iterations`, `DS-REVIEW-*`, `CHANGELOG.md`, and the worker's/your own historical TEST-PLAN/QA-RESULTS are **frozen records** — they legitimately mention the old name and are NOT live consumers. Exclude them.
3. **What remains is the live-consumer set.** Cross-check each against the PR diff: was it repointed? If the AC has a lane-split clause ("repoint mechanical refs; flag deeper narrative rewrite to PM/DM"), the worker must have done **one or the other** — a doc that was neither touched nor flagged is an AC gap, even if it's narrative.
4. A moved file also breaks **doc links** (`[start.sh](../start.sh)`) and **printed command strings** (`run ./start.sh`) — grep for those forms too, not just bare names.

## Apply

When an AC enumerates specific doc consumers by name ("README §X, INSTALLER-ARCH/HARNESS-ARCH launch references"), treat the enumeration as a checklist and confirm each was repointed-or-flagged. "Code consumers updated, tests green" is necessary but not sufficient — the doc surface is where deletion/move tasks leak. This is an **objective** finding (broken/stale reference to a nonexistent path), so it rejects under the zero-gap gate; it is not a subjective style flag. Related receiver-side gate discipline: [[learning-harness-only-ship-restart-required-is-noop]] (verify from facts, not the worker's claim).
