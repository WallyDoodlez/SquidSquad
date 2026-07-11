# TEST-PLAN-13338 — installer step-8 independent-verification sub-agent

**Issue**: #13338 (type:task, priority:medium) — INSTALLER-RUNTIME.md §4 step 8.
**PR**: #13448 `squidsquad/task/13338`.

## ACs
- AC1: installer spawns a fresh independent sub-agent, handed customizations + project context.
- AC2: sub-agent checks (a) compose-clean, (b) no §3 invariant breached, (c) roster end-to-end.
- AC3: on failure self-solve + re-verify; only clean pass proceeds; never asks user.
- AC4: define the check protocol concretely (inputs, pass/fail) — executable.

## Test cases
- TC-1 (AC1/AC4): read §9 Step-8 playbook — fresh sub-agent, inputs (L4 + context + protocol), structured verdict.
- TC-2 (AC2b): cross-check the enumerated §3-invariant list against §3 verbatim — all six, exact match, none missing/invented.
- TC-3 (AC2a): verify check-1 compose commands against compose.py — deploy-all, deploy <alias> --check --staged-l4, bare --check error, deploy-all --check retired.
- TC-4 (AC3): self-solve loop prose — revise-to-fit, re-run, never-ask-user, clean-pass-only.
- TC-5 (AC5 CQ): 13338_spec; fresh Sonnet on §9 Step-8; zero misreads.
- TC-6 (gate): full static gate + new runbook test; branch 0-behind-main (post-merge state).

CQ REQUIRED — INSTALLER-RUNTIME.md is LLM-consumed (AC5 explicit).
