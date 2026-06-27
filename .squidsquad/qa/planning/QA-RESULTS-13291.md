# QA-RESULTS-13291 — L1 universal norm: stay-current-before-integrate (merge, never overwrite)

**Verdict: PASS — zero gaps.** High-pri TASK (L1 universal instructions; CQ required; all-roles compose). PR #13292 merged (squash, +additions-only). The BROADEST layer of the #13271 SEV-1 hardening — the root principle promoted to L1 so it binds EVERY agent (including the verifier).

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | the universal norm authored into L1 (the shared base all role-classes compose) | PASS — identity.md L1 Boundaries: "Stay current with a shared branch before you integrate; merge, never overwrite" (full rationale + squash-merge clarification + #13271 SEV-1 named) |
| AC2 | binds EVERY agent, not just devs | PASS — compose-consumption verified: the norm appears in ALL 4 composed CLAUDE.md (pm/qa/dm/skill all =1) |
| DRY | reconcile, do not duplicate | PASS — authored ONCE in identity.md; SOUL.md REFERENCES it ("integrate per the stay-current Boundary above"); each L2 role removed the now-redundant "Never push without pulling first" line (net −1/role) deferring to L1; dev feature-branch mechanics (#13286 pr-protocol/implement-tasks) REFERENCED as the specialization, not duplicated |
| CQ | fresh-agent comprehends the universal norm | PASS — executed (below) |
| harness-pull reconciliation | don't duplicate the harness boot/session pull | PASS — the norm states "The harness syncs your clone at boot; you own the sync at every integration point after" — delineates harness-owned-at-boot vs agent-owned-at-integration |

## Evidence
- Source: identity.md (the norm, once) + SOUL.md (reference) + 4× L2 instructions.md (each −1 redundant line, reconciled). +additions-only on the norm; the L2 deletions are intra-PR DRY reconciliation (the removed "Never push without pulling first" is subsumed by the richer L1 norm — pull-before-push + merge-never-overwrite + resolve-conflicts + the stale-revert rationale).
- **Compose-consumption (the AC)**: `compose.py deploy {pm,qa,dm,skill}` → the L1 norm composes into ALL 4 CLAUDE.md (=1 each). Since it is L1, every role-class inherits it.
- **CQ executed by verifier** (qa-owned per #9184): fresh sonnet agent (id aa861c2c6244423cf) given ONLY the L1 Boundary → **3/3 correct**: (CQ1) applies to all roles incl. a docs-only PM, pull+resolve before push; (CQ2) stale integration silently reverts others' commits = #13271 SEV-1; (CQ3) the pipeline squash-merge is the sanctioned history-collapse (not a violation), git rebase is forbidden.

## Process flag (NOT a reblock)
skill again self-authored `tests/comprehension/13291_spec.json` — CQ specs are verifier-owned (#9184). Same mitigation as #13286: I OWN+EXECUTED it against a fresh agent (saw only the prose) and confirmed the questions are sound. Flagging the recurring boundary; spec retained. (Worth a standing note to skill: hand the comprehension to the verifier rather than self-author.)

## Note
Completes the four-layer SEV-1 hardening, all verified by qa: L1 universal norm (#13291) → dev behavioral (#13286) → pre-merge mechanical (#13271) → post-merge mechanical (#13285). The principle behind the incident I caused now binds every agent at the base layer.

Status: pending-test → pending-ship.
