## PM Project Operations — SquidSquad

These instructions apply to the PM agent on this project.

### Tracker & Cycle

- **All tracker operations via `tracker.py`** — never construct `gh issue edit` label commands manually.
- **Timestamp discipline**: all timestamps from `cycle.py timestamp-short` or `timestamp`. Never guess.
- **Cycle runner**: `cycle_pre.py` → creative work → `cycle_post.py`. Don't use bash for mechanical operations.
- **Atomic writes** for any file other agents or statusline may read concurrently (`.tmp` + `mv`).
- **Test suite**: `python tests/run_tests.py`. Run before verifying any pending-test item.
- **Read issue comments every cycle** — don't rely on cached state. Fresh queries via tracker.py.
- **Trust script output over context.** If a script says the agent is dead, it's dead. Don't second-guess deterministic output.

### Pipeline Management

- **Pipeline sentinel**: check PR conflicts, stall detection, PR status sync, stuck-state detection every cycle.
- **QA fallback**: if QA agent is not installed, PM handles Steps 3-6 (testing + verification).
- **Post-merge recompose**: when merged branches touch `references/`, run `compose.py deploy-all`.
- **Agent lifecycle via `start_team.py`** — PM does not boot agents directly. Report stalled agents to human.

### Task Lifecycle

- **5-phase task approval gate**: Research → Discussion → Planning → (Human approves) → Execution. Never skip phases.
- **Re-research gate**: if CONTEXT.md locked decisions deviate heavily from RESEARCH.md, re-run research.
- **Test promotion**: copy test `.py` files to `tests/` before marking pending-ship.
- **`delivery:skip` check**: internal-only tasks skip delivery packaging.
- **DM fallback version bump**: if DM absent, PM handles version bumps (minor bump, config + SKILL.md + CHANGELOG, tag, push, reset counter).
- **CQ specs required for instruction changes**: any task touching LLM-consumed instructions needs comprehension questions in TEST-PLAN.md.
- **Comprehension testing standard**: spawn fresh agent, give only modified files, answers must come from files alone.

### Soul & Vault

- **Soul shepherd**: 5-category evaluation (deliverable-type, tech-stack, domain-vocabulary, quality-preference, user-persona) on every new task/bug.
- **Vault remember 4-gate logic**: write budget → dedup → reusability → fresh context test. Max 2 writes per cycle.
- **Vault synthesis**: every 5 quiet cycles, synthesize cross-agent patterns into posture notes.
- **Vault optimize**: run on quiet cycles when vault has 20+ notes.

### Scanning & Distribution

- **Improvement scan after 3 quiet cycles** — process files only (templates, sub-skills, config). PM never scans application source code.
- **Distribution packaging check**: verify `installer-files.txt` and `packages/cli/package.json` are current when changes affect distributed files.
