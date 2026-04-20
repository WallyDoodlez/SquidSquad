# FEAT-SKILL-1778 Context — Project-Specific Role Responsibilities

## Scope

Redesign the setup flow to maximize mechanical (CLI) steps and add per-role project-specific responsibilities to SOUL.md, seeded by automated repo scanning and human confirmation.

## Locked Decisions (human decided)

- **Setup flow split**: 10 CLI steps (mechanical) + 6 wizard steps (human decisions only). If it doesn't need human input, it doesn't need an LLM.
- **Scan results persist**: saved to `.squidsquad/scan-results.json` so upgrades can re-detect and refresh responsibilities when project evolves.
- **Minimal mapping first**: top ~15 detections (JS/TS, Python, Go, Rust, Docker, GH Actions, Vercel, Jest, pytest, Playwright). Expand based on real usage.
- **Adaptive questions reduced**: keep 1-2 questions for domain/purpose and conventions only. Tech stack questions dropped since scan detects them.
- **JSON file handoff**: CLI writes `.squidsquad/.repo-scan.json`, wizard reads on start. Clean separation. File cleaned up after setup.
- **Responsibilities in SOUL.md**: new `### Project-Specific Responsibilities` section per role, preserved on upgrade.
- **repo_scan.py is pure script**: no LLM, outputs structured JSON.
- **Model routing in CLI**: check `~/.squidsquad/secrets/` for keys, prompt y/n, open secrets file in default editor if user wants external models.
- **Loop interval in CLI**: simple CLI prompt, no LLM needed.
- **Step 1 merged with scan review**: present project identity + scan findings in one shot, human corrects.

## Dev Discretion (dev agent can choose)

- File pattern list for repo_scan.py (as long as top 15 detections are covered)
- Responsibility mapping data structure (dict, YAML, etc.)
- Default editor detection method (EDITOR env var, platform defaults)
- Exact wording of CLI prompts
- How to handle monorepo sub-directory scanning depth

## Side Effect Mitigations (required)

- Scan misdetection mitigated by human review step (wizard Step 1)
- Existing installs unaffected — no SOUL.md changes on existing installs without explicit upgrade
- SOUL.md Project-Specific Responsibilities section preserved on regenerate (same as existing SOUL.md preservation logic)
- Empty repos handled gracefully — skip scan review, responsibilities seeded from role defaults only

## Upgrade Path (required)

- Existing installs: `/squidsquad-upgrade` adds empty `### Project-Specific Responsibilities` section to SOUL.md if missing
- User can manually run repo_scan.py and re-seed responsibilities
- scan-results.json enables future upgrade to auto-refresh responsibilities
- No breakage if user doesn't upgrade — SOUL.md without the section works fine (agents use role defaults)

## Out of Scope

- Comprehensive mapping (30+ detections) — start minimal, expand later
- Auto-detection of custom/proprietary tools — scan covers common OSS tools only
- Changing the manifest system — responsibilities are NOT in manifests
- Changing CLAUDE.md composition — only SOUL.md gets the new section
