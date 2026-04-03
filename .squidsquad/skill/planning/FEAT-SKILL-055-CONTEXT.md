# FEAT-SKILL-055 Context — Take SquidSquad Public

## Scope

Prepare SquidSquad for public release as an open-source community-driven Claude Code skill. This is a strategy + delivery feature — produces the proposal document, license setup, community infrastructure, and pre-launch checklist. The actual README rewrite is FEAT-SKILL-056.

**In scope:**
- AGPL-3.0 license setup (LICENSE file, SKILL.md header, README badge)
- Community governance documentation (CONTRIBUTING.md, CODE_OF_CONDUCT.md)
- GitHub Issues templates (bug, feature, sub-skill proposal)
- GitHub Discussions setup
- Pre-launch checklist execution (security audit, .gitignore review, working setup test)
- Separate community sub-skill repo setup
- Purpose-built demo project
- Version bump to v1.0.0 (after test project succeeds)
- Launch announcement plan

## Locked Decisions (human decided)

- **AGPL-3.0 license**: Can be used freely as a whole. Modifications must stay open-source if distributed. Companies using internally are safe — AGPL triggers on distribution/network deployment of modified versions only.
- **Benevolent dictator community model**: Human approves all PRs. Promote trusted contributors to maintainers over time. SquidSquad has strong opinions (pipeline, Ralph Loop, SOUL.md philosophy) — open contributions but curated merges.
- **Purpose-built demo project**: Create a small project specifically to showcase SquidSquad. Controlled narrative, becomes the official demo. Test on this before going public.
- **Keep .squidsquad/ as dogfooding proof**: The internal trackers, planning artifacts, and iteration logs stay tracked in the public repo. Shows SquidSquad was built by SquidSquad — powerful credibility signal.
- **Launch as v1.0.0**: Signals confidence and maturity. 8+ features shipped, working pipeline, tested on a second project. Conditional on test project success.
- **Separate skill repo for community sub-skills**: Community-contributed sub-skills live in a separate repository, not in the main SquidSquad repo. Keeps the core clean, allows independent versioning, lowers the contribution bar.
- **Full README redesign**: Complete rewrite as public landing page. Hero section, what/why/how, quickstart, architecture, badges. Handled by FEAT-SKILL-056.
- **Wait on Discord until demand**: Start with GitHub Discussions. Create Discord when 50+ stars or community requests. Empty Discord is worse than no Discord.
- **Test on another project first**: Proves SquidSquad works outside its own repo. Gating milestone before going public.

## Dev Discretion (dev agent can choose)

- Demo project technology choice (web app, CLI, API — whatever best showcases SquidSquad)
- GitHub Issues template exact format
- CONTRIBUTING.md structure and wording
- Launch announcement wording and timing
- Community sub-skill repo name and structure

## Side Effect Mitigations (required)

- Security audit before going public — no secrets, API keys, internal paths in tracked files
- .gitignore must cover .obsidian/, .local-config, current-state files, .active-role
- Test the setup flow end-to-end on a clean machine / fresh clone
- Verify AGPL compatibility with any dependencies

## Upgrade Path (required)

- N/A — this is a one-time transition, not a recurring upgrade

## Out of Scope

- README rewrite (FEAT-SKILL-056)
- Community sub-skill development (separate repo)
- Marketing beyond initial announcement
- Paid features or hosting
