# TEST-PLAN-12800 — human as a (non-agent) role

**Derived independently from the issue #12800 AC list + LOCKED design doc `HUMAN-AS-ROLE-ASYNC-DESIGN.md` (rev-16), NOT from the worker's PR diff.**

- **Task**: #12800 (type:task/high, role:skill) — `human` as a first-class non-agent role: aliases, compose-skip, `role:human` routing, inline status bar.
- **PR**: #12902, branch `squidsquad/task/12800` @ e3e83a0c7 (MERGEABLE/CLEAN, single commit, NO closing keyword).
- **TRD of record**: AGENT-RUNTIME (Terminology / §3 / §8.3). Pairs with #12799 (async-no-pause L1, already shipped) + #12853 (PM advertise-duty, shipped).

## Scope note (narrowed contract)
The issue body lists **AC1–AC8** (the task contract); the design doc's AC1–AC10 span BOTH #12799 (async-no-pause L1 slice, shipped) and #12800. I verify against the **issue body's AC1–AC8**. Per QA independence (#9184) I author my own checks; per the comprehension standard I author + run my own CQ spec (`tests/comprehension/12800_spec.json`) since #12800 changes LLM-consumed instruction text (inline status-bar behavior in `instructions.md` + 4 `ralph-loop-overview.md`).

## Test cases

| TC | AC | Method (independent / live) | Expected |
|----|----|----|----|
| TC1 | AC1 alias registers | `config.parse_aliases_registry` over table + bullet registries with 2 humans; negative-control unknown role-class; `tracker.FEEDBACK_ROLES` + free-form `role:` label | multi-human parse `('human',None)`; unknown class rejected (real gate); `role:human` valid |
| TC2 | AC2 compose skips human | `deploy_alias_v2('wallace'/'alice', registry=…)` direct guard; on-main `deploy-all` agent outputs | human → `None` + no CLAUDE.md written; agents compose; rc=0 |
| TC3 | AC3 routing flip | direct read of `harness._STATUS_ROUTING`; `is_handoff` human-exclusion; worker routing assertions | pending-human-review\|setup → `("role_class","human")`; human excluded from re-emit; `human-comment`→pm documented (spec-only, unchanged) |
| TC4 | AC4 inline status bar | live `cycle.py status-bar-self inline ""` then clear; grep instruction text | bar = `inline\|`; clear → `idle\|`; text updated in `instructions.md` + 4 fragments; #9358 superseded |
| TC5 | AC5 return path | `tracker.LEGAL_TRANSITIONS`/`ROLE_AUTHORITY` pending-human-*→in-progress; `work_queue` surfaces re-assigned ticket | legal {pm,_assignee}; ticket #77 surfaces in originator queue (matches locked C2 inline-mediated return) |
| TC6 | AC6 docs reconcile | AGENT-RUNTIME rev-17 + §3 #9358-superseded reword; composed CLAUDE.md grep; dangling-ref scan | rev-17 present; §3 reworded; async-no-pause in composed qa/CLAUDE.md; no dangling refs |
| TC7 | AC7 installer-files | `git diff --name-status main...branch` | no new source files (all in-place edits) → installer-files.txt correctly unchanged |
| TC8 | AC8 DS-audit | `DS-REVIEW-12800.md` | present, NO_FINDINGS, 8 paths incl. human-never-an-agent |
| CQ | comprehension HARD GATE | fresh sonnet agent given ONLY modified instruction text; 5 verifier-derived Qs | all answers from text alone, no anti-patterns |
| REG | no regression | `test_harness` full, config/compose/cycle/tracker suites, `run_tests.py static` | all green, 0 new failures |
