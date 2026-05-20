## PM Project Operations — SquidSquad

These instructions apply to the PM agent on this project.

### Tracker & Cycle

- **All tracker operations via `tracker.py`** — never construct `gh issue edit` label commands manually.
- **Timestamp discipline**: all timestamps from `cycle.py timestamp-short` or `timestamp`. Never guess.
- **Mechanical/creative split**: mechanical operations (git pull/commit/push, triage queries, iteration logging, status transitions) are handled by deterministic project scripts — your creative analysis and decision-making sits between them. Don't reach for ad-hoc shell commands for these mechanical steps. The cadence and exact entry points differ by mode — see role L1/L2 layers for the runner contract.
- **Atomic writes** for any file other agents or statusline may read concurrently (`.tmp` + `mv`).
- **Test suite**: `python tests/run_tests.py`. Run before verifying any pending-test item.
- **Read issue comments every cycle** — don't rely on cached state. Fresh queries via tracker.py.
- **Trust script output over context.** If a script says the agent is dead, it's dead. Don't second-guess deterministic output.

### Pipeline Management

- **Pipeline sentinel**: check PR conflicts, stall detection, PR status sync, stuck-state detection every cycle.
- **NEVER modify dev agent branches.** If a PR has merge conflicts, comment on the issue telling the dev agent to merge main and re-push. The dev agent owns their branch — conflict resolution is their responsibility, not PM's.
- **QA handles all verification**: PM holds QA accountable but never verifies directly.
- **Post-merge recompose**: when merged branches touch `references/`, run `compose.py deploy-all`.
- **Agent lifecycle via `start_team.py`** — PM does not boot agents directly. Report stalled agents to human.

### Task Lifecycle

- **5-phase task approval gate**: Research → Discussion → Planning → (Human approves) → Execution. Never skip phases.
- **Re-research gate**: if CONTEXT.md locked decisions deviate heavily from RESEARCH.md, re-run research.
- **Test promotion**: copy test `.py` files to `tests/` before marking pending-ship.
- **`delivery:skip` check**: internal-only tasks skip delivery packaging.
- **DM handles all delivery**: DM owns version bumps, CHANGELOG, and delivery packaging.
- **CQ-coverage AC required for instruction changes** (#9184): any task touching LLM-consumed instructions must include an explicit comprehension-coverage AC in the issue body. PM writes the AC; QA writes the CQ spec into `.squidsquad/qa/planning/TEST-PLAN-<NUMBER>.md` and `tests/comprehension/<NUMBER>_spec.json` when picking up verification.
- **Comprehension testing standard**: spawn fresh agent, give only modified files, answers must come from files alone. Production of CQs is owned by QA, not PM.

### Planning Review via Draft PR (#4979)

- **Draft PR after Phase 3**: After planning artifacts are created and task is filed, commit artifacts to a feature branch and create a draft PR for human review.
- **Inline review**: Human reviews PRD/CONTEXT.md via PR comments — enables inline feedback on specific sections. (Under the #9184 workflow PM no longer ships a TEST-PLAN.md for review; QA's test plan is produced at verification time.)
- **Approval converts draft**: When human approves, convert draft PR to ready and transition task to Approved.

### Planning Artifact Quality (#4967)

Task bodies and CONTEXT.md must include PRD-quality output when complexity warrants it:

- **Implementation sequence** (always): recommended step order / migration path. What gets done first, what depends on what.
- **Mermaid diagrams** (when task touches 3+ files, has state machine logic, or involves flow/pipeline changes): architecture diagrams, sequence diagrams, or state charts embedded in the task body or CONTEXT.md.
- **PRD format** (for epic-scale tasks): vision statement, user stories, what gets added, what gets removed, migration impact.

These requirements apply during Phase 3 (Planning) when PM creates CONTEXT.md and the task body. Simple bug fixes and single-file changes do not need diagrams or PRD format — use judgment on complexity threshold.

### Soul & Vault

- **Soul shepherd**: 5-category evaluation (deliverable-type, tech-stack, domain-vocabulary, quality-preference, user-persona) on every new task/bug.
- **Vault remember 4-gate logic**: write budget → dedup → reusability → fresh context test. Max 2 writes per cycle.
- **Vault synthesis**: every 5 quiet cycles, synthesize cross-agent patterns into posture notes.
- **Vault optimize**: run on quiet cycles when vault has 20+ notes.

### Scanning & Distribution

- **Improvement scan after 3 quiet cycles** — process files only (templates, sub-skills, config). PM never scans application source code.
- **Distribution packaging check**: verify `installer-files.txt` and `packages/cli/package.json` are current when changes affect distributed files.

### AC Quality for This Project

- ACs must verify deliverables are composed into deployed CLAUDE.md/SOUL.md via compose.py
- ACs must verify agents read the content at boot (includes.yml or auto-include path)
- ACs must verify installer-files.txt is updated if references/ files change
- ACs must verify .squidsquad/project/ content is read by compose.py (L4 location)
