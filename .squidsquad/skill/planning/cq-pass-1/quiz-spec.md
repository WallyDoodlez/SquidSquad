# CQ Pass 1 — Quiz Spec

## Purpose

Validate that the composed `.squidsquad/{role}/CLAUDE.md` carries enough specific instruction that a fresh Sonnet agent reading only that file can execute every runtime decision without confusion. Hedges, missed sub-skill invocations, wrong commands, or "I'd need more info" responses on documented behavior all count as gaps.

## Quiz items (shared skeleton — 10 items)

All roles answer items 1-7 and 9-10. Item 8 is role-specific.

1. **Boot, no working-state.** "You just spawned as a fresh process. Your CLAUDE.md instructs Step 1 — step:cycle/boot. Walk through what you check, what mode you enter (EVENT vs POLLING), how you decide, and what fragment you Read next. Name the actual commands you'd run."

2. **Resume with prior task.** "You spawn and `.squidsquad/<your-alias>/working-state.md` shows an active task at Step 4. What do you trust, what do you re-verify, and what's your first concrete action toward continuing? Include any pull-or-skip decision."

3. **Context pressure trigger.** "Live context-pressure file shows 87%; your configured threshold is 80%. You are mid-cycle with uncommitted prose changes to `references/sub-skills/common/foo.md`. What is your sequence of actions BEFORE the cycle exits? What MUST land in working-state.md before you let yourself respawn?"

4. **Cross-domain bug found.** "While doing your primary work, you find a bug whose root cause is owned by a different role class. Walk: investigation, classification, the exact `tracker.py` command(s), the role label, and what you do NOT do."

5. **Discussion comment received.** "Another agent left a comment on a GitHub Issue addressed to you with a question you can answer. Walk the response: which tool, which command, what label/role alias prefix appears in your comment, and what is forbidden."

6. **Checkpoint discipline.** "Cycle complete: code change on feature branch, tracker transitioned `in-progress` → `pending-test`. Walk commit + push protocol. What gates the transition? What's the order: commit first or transition first? What do you NEVER do at this step?"

7. **L4-curation trigger.** "User in conversation says 'in this project, from now on, every commit message must include the issue number in square brackets.' What is the trigger classification, what sub-skill do you invoke, what do you do BEFORE invoking, and name the safety gates in order."

8. **Role-specific primary work item** — see per-role section below.

9. **Vault-remember after novel work.** "You completed a non-trivial task that yielded a reusable insight (e.g., 'docker network host mode breaks DNS resolution on rootless Podman on RHEL 9 — workaround is --network=slirp4netns:enable_ipv6=true'). Walk: do you write to vault? Which PARAG bucket? What's the write-budget rule? When do you NOT write?"

10. **Self-restart vs exit.** "Cycle just ended successfully. Should you self-restart, exit, or wait? What triggers each? What does your CLAUDE.md tell you to check?"

## Role-specific item 8

### PM
"Worker tracker shows a new comment on an issue: 'Should we use postgres or sqlite for the queue?' — the worker is blocked on a scope question. Walk PM's response: pickup vs deferral, planning-artifact protocol (RESEARCH.md / CONTEXT.md / TEST-PLAN.md per #9184), decision recording, who approves."

### Verifier (QA)
"Tracker shows a `pending-test` item from a worker. Walk verification: how do you derive a TEST-PLAN, where do you write QA-RESULTS, what determines pass/fail, what transitions happen on each outcome, and what role boundary you must NOT cross."

### DM
"Tracker shows a `pending-ship` item with the `delivery:skip` label. What do you do? Now: same item, no `delivery:skip` label — walk delivery: branch handling, CHANGELOG framing, version-bump-counter logic, final transition."

### Skill (worker)
"Tracker shows an approved task. Walk implementation: branch creation, plan vs code-first, test discipline, when to invoke `→ run sub-skill: l4-curation` if at all, what counts as zero-gap submission, transition to pending-test."

## Grading rubric

Per item, grade one of:

- **PASS** — answer is specific, cites the right sub-skill / command / fragment, no hedging on documented behavior.
- **HEDGE** — answer is *roughly* right but vague ("I'd probably..." / "the docs would tell me..."); a real agent under this prose might do the wrong thing in adversarial cases.
- **FAIL** — answer is materially wrong: wrong command, wrong transition order, wrong sub-skill, wrong role boundary.
- **GAP** — the doc is genuinely silent or contradictory; answer is "doc doesn't say."

For HEDGE / FAIL / GAP, the subagent quotes the specific composed CLAUDE.md heading(s) it consulted, and (where possible) suggests what would close the gap.

## Subagent contract

The subagent is told:
- It IS playing the role (PM / Verifier / DM / Worker).
- Its sole source of truth is the composed CLAUDE.md path provided.
- It MUST read the file in full before answering.
- It MUST cite headings/line numbers for its answers.
- It MUST output structured JSON-like markdown (one section per item) with grade + answer + citation + (where applicable) gap-close suggestion.
- It MUST NOT invent commands not in the doc.
- It MUST flag any contradiction it finds between two sections of the doc as a separate finding.
