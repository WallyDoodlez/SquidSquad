# TEST-PLAN #12799 — L1 async-no-pause (never block on a human)

**Derived**: 2026-06-18 19:07 by verifier (qa), independently from the 3 ACs in the issue body + the LOCKED design AGENT-RUNTIME §3.1. PR #12822, branch `squidsquad/task/12799`. Source-only PR (`references/roles/SOUL.md`), per the #12585 L1-Soul precedent.
**Design contract**: AGENT-RUNTIME §3.1 — inline is the only sync human channel; in autonomous mode never pause/wait; assign `role:<human>` + `pending-human-*` via a transition (never a bare comment) and immediately continue; agent-mediated return path (originator self-reassigns / PM reassigns; human never makes the transition; wrong-agent → "not my territory").

## ACs (verbatim)
- **AC1 (compose):** the async-no-pause rule is present in every composed event-mode + loop-mode agent CLAUDE.md after `compose.py deploy-all` (verify composed output, not just source).
- **AC2 (comprehension, REQUIRED):** a fresh agent quizzed "you need a human decision mid-task and you are NOT in inline mode — what do you do?" answers "assign a human-attention ticket and continue/release; I do not wait," NOT "I pause and wait."
- **AC3 (DS-review):** high-blast-radius L1 change → DS-review per project discipline.

## Test cases
- **TC1 (AC1):** run `compose.py deploy-all`; grep all 4 composed CLAUDE.md (dm/pm/qa/skill) for "Never Block on a Human" + the rule body. Soul slot is mode-independent → one base-soul section lands in both event- and loop-mode composed outputs. PASS: present in all 4. (Discard the verification-side recompose so the PR stays source-only.)
- **TC2 (AC2):** extract the new SOUL section in isolation; fresh sonnet agent reads ONLY it; quiz the AC2 question + return-path + bare-comment-vs-transition. PASS: "assign-and-continue, do not wait"; agent (not human) makes the transition.
- **TC3 (AC3):** DS-REVIEW-12799.md exists; error finding addressed; current SOUL.md text reflects the fix. PASS: record present + fix corroborated in-text.
- **TC4 (§3.1 conformance):** the SOUL rule matches every §3.1 element (inline-only, never-wait, role:<human>+pending-human-* via transition, immediate-continue, agent-mediated return, wrong-agent reply). PASS: all elements present, no divergence.
- **TC5 (no contradiction):** the new rule must not contradict the existing "Professionalism: when uncertain, ask — don't guess." PASS: bridged by "'Ask, don't guess' means ask asynchronously."
- **TC6 (clean diff):** PR touches only `references/roles/SOUL.md` (source-only; installer files / composed outputs not committed). PASS.
- **TC-REG:** static gate green (SOUL.md feeds compose). PASS: `run_tests.py static` EXIT 0.

## Pass criteria
All 3 ACs observable, §3.1 conformance exact, no contradiction with prior soul rules, clean source-only diff, no regression.
