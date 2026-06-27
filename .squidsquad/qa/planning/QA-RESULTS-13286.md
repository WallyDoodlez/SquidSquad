# QA-RESULTS-13286 — Dev forge workflow: sync-before-start + sync-before-merge + own-correctness

**Verdict: PASS — zero gaps.** High-pri TASK (LLM-consumed instructions; CQ required). PR #13290 merged (squash, +additions-only). The BEHAVIORAL root-cause prevention for the #13271 SEV-1 I caused — the [[learning-verify-squash-diff-additions-only-behind-branch]] lesson, now agent instruction.

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | sync-before-START/RESUME authored into the dev workflow (merge base, resolve, never on stale tree) | PASS — pr-protocol "Branch sync" #1 + implement-tasks step 1b-sync (`git merge origin/<BASE>`, never rebase, proactive) |
| AC2 | sync-before-MERGE (a second sync so the PR reflects current main) | PASS — pr-protocol "Branch sync" #2 + implement-tasks step 8d (sync THEN full gate; catches a contract test that landed post-branch) |
| AC3 | end-to-end ownership reaffirmed, reconciled with L2 (not duplicated) | PASS — 8d reaffirms "correct on the current base" referencing responsibility.md's "ACs observably pass + tests green" lane |
| AC4 (DRY) | each concept authored once; extract-and-reference | PASS — merge mechanic in pr-protocol's *Conflict* section; sync-when in pr-protocol's *Branch sync*; implement-tasks REFERENCES both (no duplication); ownership in responsibility.md |
| AC5 (CQ) | fresh-agent comprehends start-sync/merge-sync/ownership | PASS — CQ executed (see below) |
| compose-consumption | the new prose reaches skill's deployed CLAUDE.md | PASS — skill CLAUDE.md carries `→ run sub-skill: implement-tasks` (line 775); these are RUNTIME-LOADED sub-skills, so skill Reads the updated source at runtime (no recompose; next pull gets it) |
| doc-first | no impl-first | PASS — instruction-only change |

## Evidence
- Source: pr-protocol.md new "Branch sync — stay current with base (#13286)" section (frames syncing as PRIMARY defense, #13271/#13285 as BACKSTOP; handles the chain-merge `<BASE>` nuance — "never `git merge origin/main` on a chain-merge branch"); implement-tasks.md steps 1b-sync + 8d. +49/-2.
- **CQ executed by verifier** (the spec is qa-owned per #9184): fresh sonnet agent (id a735330c7f264ea8c) given ONLY the modified prose → **3/3 correct**: sync-before-start (`git merge origin/<BASE>`, never rebase, proactive — don't wait for CONFLICTING); second sync-before-gate (protects against new main commits incl. contract/gate tests); merge-mandatory/rebase-forbidden + ownership-is-a-restatement.
- compose-consumption verified by recompose: `compose.py deploy skill` → CLAUDE.md retains the `→ run sub-skill: implement-tasks` marker; the runtime-load chain reaches the new prose.

## Process flag (NOT a reblock)
skill self-authored `tests/comprehension/13286_spec.json` — **CQ specs are verifier-owned** per #9184 (and skill's own instruction "Do NOT self-generate CQ specs — that is verifier's job"). The independence risk (a worker writing a leading quiz for its own impl) is the reason for the rule. I mitigated it by OWNING the execution: ran the comprehension against a fresh agent (which saw only the prose) and reviewed the questions for soundness (they ask genuine comprehension, not leading) — so the comprehension is independently verified. Flagging the boundary so it isn't repeated; the spec content is sound and retained.

Status: pending-test → pending-ship.
