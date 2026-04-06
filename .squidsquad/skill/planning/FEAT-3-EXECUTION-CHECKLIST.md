# FEAT-3 Execution Checklist — Going Public

**Source**: Old CONTEXT.md (FEAT-SKILL-055) decisions reused + fresh assessment of current state.
**Date**: 2026-04-06
**Focus**: Human wants to go public with strong public materials including a sub-skill dev guide.

## Phase A — Clear Blockers (must ship first)

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | #182 — tracker.py label bug (shell injection in create-bug/create-feature) | skill | in-progress (bounced back) | HIGH — broken core script |
| 2 | #1 �� Templatize boot scripts (CRLF fix) | skill | in-progress (bounced back) | Clean boot experience for new users |
| 3 | #148 — git_ops.py test coverage | skill | open | Quality signal — agents can't ship phantom fixes |
| 4 | #180 — cycle.py stale docstring | skill | open | Low — cosmetic |

## Phase B — Security & Hygiene Audit

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 5 | Hardcoded local paths scan (D:\Dev, C:\Users) | pm/qa | TC-8 from old test plan. .squidsquad/planning/ artifacts may have paths — acceptable as dogfooding proof |
| 6 | API keys / secrets scan | pm/qa | TC-9. No API keys expected but must verify |
| 7 | .gitignore review | skill | TC-11-15. Must cover: .obsidian/, .local-config, current-state, .active-role, *.stackdump, __pycache__/ |
| 8 | bash.exe.stackdump removed from tracking | skill | TC-23 |
| 9 | PII scan | pm/qa | TC-10 |

## Phase C — Community Infrastructure (role:dm or role:skill)

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 10 | LICENSE file (AGPL-3.0) | dm/skill | Full AGPL-3.0 text in repo root |
| 11 | SKILL.md license field | skill | Add `license: AGPL-3.0` to frontmatter |
| 12 | CONTRIBUTING.md | dm | Bugs, features, sub-skills, PR process |
| 13 | CODE_OF_CONDUCT.md | dm | Contributor Covenant |
| 14 | .github/ISSUE_TEMPLATE/bug-report.md | skill | Version, OS, steps to reproduce |
| 15 | .github/ISSUE_TEMPLATE/feature-request.md | skill | Problem, proposed solution, alternatives |
| 16 | .github/ISSUE_TEMPLATE/sub-skill-proposal.md | skill | Name, description, roles, composition point |

## Phase D — Public Materials (NEW — human priority)

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 17 | #2 — README overhaul | dm | Full redesign as public landing page. Hero, what/why/how, quickstart, architecture, badges |
| 18 | **Sub-skill dev guide** (NEW) | dm/skill | How to create sub-skills: anatomy, template, include system, composition, testing. Primary contribution path for community. |
| 19 | CHANGELOG.md polish | dm | Ensure version history is clean and readable for public |
| 20 | Architecture overview doc or diagram | dm/skill | Visual explanation of Ralph Loop, agent coordination, sub-skill composition |

## Phase E — Demo Project & Testing

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 21 | Create purpose-built demo project | skill/pm | Small project to showcase SquidSquad. Controlled narrative. |
| 22 | Test setup flow end-to-end on demo | pm/qa | TC-19, TC-22. Fresh clone, setup, agent boot, one cycle |
| 23 | Review all .squidsquad/ content for public readiness | pm | Dogfooding proof stays — but review for embarrassing/confusing content |

## Phase F — Version Bump & Launch

| # | Item | Owner | Notes |
|---|------|-------|-------|
| 24 | Version bump to v1.0.0 | pm/dm | After demo project success |
| 25 | Git tag v1.0.0 | pm | |
| 26 | Make repo public on GitHub | human | Manual step |
| 27 | Enable GitHub Discussions | human | Start with Discussions, Discord when demand |
| 28 | Launch announcement | dm | GitHub release notes, social if desired |

## Dependencies

```
Phase A (blockers) → Phase B (security) → Phase C (community infra) → Phase D (materials) → Phase E (demo) → Phase F (launch)
```

Phase D items 17-18 (README, dev guide) can start in parallel with Phases B-C since they're content work.

## New Deliverable: Sub-Skill Dev Guide

Human specifically requested this. Should cover:
- What is a sub-skill (anatomy: markdown file with `<!-- sub-skill: name -->` markers)
- Where they live (`references/sub-skills/common/`, `references/sub-skills/roles/`)
- The include system (`{{include: common/vault-protocol}}`)
- How compose.py assembles them into agent CLAUDE.md
- The manifest (`references/sub-skills/manifest.md`)
- How to create a new one (step by step)
- How to test it (composition tests in test_composition.py)
- How to contribute it (PR process, separate community repo)
- Examples: walk through an existing sub-skill (e.g., vault-remember)
