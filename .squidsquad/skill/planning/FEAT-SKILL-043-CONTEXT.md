# FEAT-SKILL-043 Context — Separate QA from PM

## Scope

Split PM/QA into two independent roles. PM becomes purely the human interface (intake, planning, discussions, coordination). QA becomes an independent verification agent that tests work from ALL dev and designer agents and hands verified work to DM for delivery.

**Pipeline**: Human → PM (intake, planning) → Dev/Designer (build) → QA (verify) → DM (docs, release) → Ship

**In scope:**
- QA role sub-skill under FEAT-SKILL-030 sub-skill architecture
- QA Ralph Loop (pull → scan trackers → verify fixed bugs → test pending features → file bugs → commit)
- PM template reduction (remove all verification steps)
- QA tracker directory (`.squidsquad/qa/`)
- QA log file (`qa/qa-log.md`)
- Setup recommendation ("Would you like to add a QA agent?" when dev/designer exists)
- QA boot script and template
- Status handoff: QA marks Pending Ship → DM picks up

## Locked Decisions (human decided)

- **One QA across all agents**: Single QA verifies work from all dev and designer agents. Only duplicate if workload demands it.
- **QA is recommended, not hardcoded**: Setup prompts "Would you like to add a QA agent?" when adding dev or designer. Not always-present like PM.
- **No PM fallback**: Once QA is introduced, its presence is expected. PM does NOT absorb QA work if QA is stalled — PM flags it as a health issue. PM drops all verification steps permanently when QA exists.
- **QA hands to DM (not PM)**: After verification passes, QA marks feature Pending Ship. DM picks it up for docs/release. If DM absent, PM takes over DM's delivery role (existing pattern).
- **PM does zero verification**: PM is purely human interface + coordination. No E2E tests, no bug verification, no feature testing.
- **Same discovery as dev/DM**: QA reads `Dev Agents` from config.md, scans each agent's trackers for `Pending Test` features and `Fixed` bugs. Checks designer directory if it exists.
- **Global loop interval**: QA uses the same interval from config.md as all other agents.
- **New qa/qa-log.md**: QA owns its own log file. Old `pm/qa-log.md` preserved as history. When QA is added later to existing project, upgrade creates QA directory and fresh log.
- **Direct bug filing for objective failures**: Test case pass/fail results get filed as bugs immediately. Subjective findings (coherence issues, style concerns) flagged in Discussion for human review via PM.
- **Built as sub-skill**: `references/sub-skills/roles/qa-agent.md` with QA-specific sub-skills. Composed via build-time engine.

## Dev Discretion (dev agent can choose)

- QA Ralph Loop step numbering and exact step names
- How QA reads and executes test plans from planning artifacts
- Format of QA results files (QA-RESULTS.md)
- How QA classifies findings as objective vs subjective
- Health check responsibility — stays with QA or moves to a shared concern
- Discussion signature format (`**qa**` vs `**qa-agent**`)

## Side Effect Mitigations (required)

- PM template must be reduced — all verification steps removed when QA exists
- Dev agent templates unchanged — they mark Pending Test as today, QA picks up instead of PM
- DM template unchanged — it reads Pending Ship as today
- Designer template unchanged — marks Pending Test, QA picks up
- Existing Discussion entries signed `**pm/qa**` are NOT bulk-renamed — new entries use separate signatures
- Config.md needs `BUG-QA` and `FEAT-QA` counters if QA gets its own tracker

## Upgrade Path (required)

- `/squidsquad-upgrade` detects QA: check for `.squidsquad/qa/` directory
- If QA directory exists: regenerate PM template (lean version without verification)
- If QA directory absent: PM template keeps full PM/QA behavior (backward compatible for installs without QA)
- Adding QA to existing project: create `.squidsquad/qa/` directory structure, generate QA template, regenerate PM template without verification steps
- Old `pm/qa-log.md` stays in place, QA starts fresh `qa/qa-log.md`

## Out of Scope

- Per-agent QA (one QA per dev) — single QA handles all
- PM fallback when QA is absent (PM drops verification permanently once QA introduced)
- Per-agent loop intervals
- QA web interface or GitHub Issues integration
