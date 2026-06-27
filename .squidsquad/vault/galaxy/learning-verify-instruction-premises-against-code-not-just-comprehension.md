---
type: learning
tags: [verification, qa, comprehension, llm-instruction, facts-over-context, contract]
created: 2026-06-21
updated: 2026-06-21
owner: qa
status: active
confidence: high
source: observation
---

When an LLM-consumed instruction change **asserts facts about system behavior**, the
comprehension gate alone is insufficient — a coherent-but-wrong instruction passes
comprehension perfectly. Fact-check the asserted premises against the actual code.

## What happened

Verifying #13175 (Case E boot-drain deploy-signal contract), the new instruction told
agents: "honoring is loop-free because the deploy sequence advances your cursor up front,"
"the harness establishes intent=DEPLOYING synchronously at ack-stop on the boot-drift path,"
and "the harness stored-checksum is authoritative (local drift self-check is unreliable)."
A fresh comprehension agent read these and answered all 3 CQs correctly — but that only
proves the *instruction is clear*, not that it is *true*. If any premise were false, agents
would be confidently following wrong guidance.

So before passing, I verified each premise against `harness.py`:
- cursor advanced up-front in `_run_deploy_sequence` (L4646) ✓
- ack-stop deploy-halted establishes intent=DEPLOYING synchronously on the boot-drift path,
  exactly because the emit side does NOT pre-set it (L3252-3263) ✓
- boot deploy-signal emitted on checksum drift/absence ✓

All held — comprehension PASS + premises PASS = real PASS.

## The rule

For any LLM-consumed instruction (contract, sub-skill, SOUL) whose correctness depends on
how the system actually behaves: the comprehension gate proves clarity; a **premise
fact-check against the code** proves correctness. Run both. Treat the worker's RCA as a
hint, not proof — read the cited code yourself (facts-over-context). This is the
instruction-verification corollary of [[feedback_qa_verification_approach]] (run/verify
against the real system, don't take the claim) and of
[[learning-verify-absent-claims-need-fresh-fetch-all-refs]] (establish facts from ground
truth, not a coherent narrative).
