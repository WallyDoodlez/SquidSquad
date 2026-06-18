---
type: pattern
tags: [dm, ship-gate, citation-soft-gate, delivery-packaging, qa-reported-bug]
created: 2026-06-17
updated: 2026-06-17
owner: dm
status: active
confidence: high
source: observation
links: [learning-ship-gate-squash-proof-window, pattern-chain-ship-per-item-auth]
---

## Context

delivery-packaging.md's contract-citation soft gate (#8950 Gate #4) says: if planning artifacts exist for an issue (`.squidsquad/<pm>/planning/*<n>*` or `.squidsquad/<verifier>/planning/*<n>*`) but the PR body cites none of them by filename, **do not merge — route back to the verifier**. Applied literally, this misfires on qa-reported bug fixes: the PR body is written at first submission, BEFORE the verifier commits TEST-PLAN-<n>/QA-RESULTS-<n>, so it cannot cite artifacts that don't exist yet.

## Content

The gate is a **soft gate** — DM exercises judgment. Judge it **satisfied (proceed to merge, do not route back)** when ALL of:

1. **No PM CONTEXT** — only verifier-side artifacts exist (TEST-PLAN/QA-RESULTS), no `CONTEXT-<n>.md`. The issue is a qa/worker-reported bug, not a PM-planned feature, so there is no architectural contract to "conform" to — which is the gate's whole purpose.
2. **Verifier artifacts post-date the PR body** — the PR couldn't have cited them.
3. **The qa AC-walk is fully documented in the issue Discussion** — explicit per-AC PASS verdicts with evidence and a "zero gaps" conclusion. The documented walk IS the architectural-conformance evidence the citation would have pointed to.

Record the judgment in the ship comment (audit trail), naming the precedent.

## Rationale

The gate exists to prevent shipping code never verified against its contract. When the verifier has demonstrably walked every AC in the Discussion and there is no PM contract to begin with, the gate's intent is met without a body-string citation. Routing back here would stall a clean ship on a paperwork artifact the PR author could not have produced.

Applied: **#12418** (first), **#12509** (test-only basename-shadow fix, qa PASS 5 ACs cy289). Both shipped clean; operator did not object.

**Boundary:** this does NOT relax the gate for PM-planned features that HAVE a `CONTEXT-<n>.md` — there the citation requirement stands (the contract exists and should be referenced).

## Related

- [[learning-ship-gate-squash-proof-window]]
- [[pattern-chain-ship-per-item-auth]]

---

### Changelog

- 2026-06-17 — Created by dm. Citation soft-gate judged satisfied without body citation for qa-reported bugs lacking PM CONTEXT when the verifier AC-walk is documented (#12418, #12509).
