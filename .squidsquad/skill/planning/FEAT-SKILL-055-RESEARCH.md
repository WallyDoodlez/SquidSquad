# FEAT-SKILL-055 — Research: Taking SquidSquad Public

**Feature**: Proposal: take SquidSquad public as a community-driven skill
**Researcher**: research-agent (subagent)
**Date**: 2026-04-02
**Status**: Complete

---

## Table of Contents

1. [AGPL Licensing for a Claude Code Skill](#1-agpl-licensing-for-a-claude-code-skill)
2. [Repo Cleanup Before Going Public](#2-repo-cleanup-before-going-public)
3. [The Pitch — Positioning SquidSquad](#3-the-pitch--positioning-squidsquad)
4. [Community Infrastructure](#4-community-infrastructure)
5. [Pre-Launch Checklist](#5-pre-launch-checklist)
6. [Community Growth Strategy](#6-community-growth-strategy)
7. [Sub-skill Marketplace / Extension Model](#7-sub-skill-marketplace--extension-model)

---

## 1. AGPL Licensing for a Claude Code Skill

### What AGPL Means for SquidSquad Specifically

SquidSquad is a Claude Code skill — a `SKILL.md` file plus supporting `references/` source files. Users install it locally. AI agents run it locally. No network service is involved. This is an important distinction for AGPL analysis.

**AGPL copyleft triggers on two conditions:**
1. **Distribution** — giving a copy of the software (modified or not) to someone else
2. **Network interaction** — users interacting with a modified version over a network (Section 13, the "AGPL clause")

**What does NOT trigger AGPL obligations:**
- **Using the skill as-is** — Installing SquidSquad, running agents locally, building your project with it. This is pure "use" and creates zero obligations. Companies using SquidSquad internally on their codebases are completely safe.
- **Internal modifications** — A company that modifies SquidSquad for internal use (private fork, custom sub-skills, tweaked templates) has no obligation to share those modifications, as long as they don't distribute the modified version to others or offer it as a network service.

**What DOES trigger AGPL obligations:**
- **Distributing a modified version** — If someone forks SquidSquad, modifies it, and distributes the modified fork (e.g., publishes it as their own skill), the modified version must also be AGPL-licensed and source must be available.
- **Offering modified SquidSquad as a hosted service** — If someone builds a "SquidSquad Cloud" where users interact with a modified version over a network, they must provide source code. This is the key AGPL protection against proprietary SaaS wrappers.

### Companies Using SquidSquad Internally — Are They Safe?

**Yes, completely.** AGPL does not impose requirements on internal use. A company can:
- Install SquidSquad on developer machines
- Customize templates, add private sub-skills
- Modify the agent instructions for their workflow
- Run it on their proprietary codebases

None of this triggers any AGPL obligation. The copyleft only activates on distribution or network-accessible deployment to third parties.

**Important caveat**: Some large companies (notably Google) have blanket bans on AGPL software regardless of actual legal risk. This is a policy choice, not a legal requirement. SquidSquad's target audience (solo devs, small teams, indie hackers) is unlikely to have such policies. For enterprises with AGPL-averse legal teams, this could be a friction point — but AGPL is the correct choice for preventing proprietary forks while allowing free use.

### How to Add the License

The LICENSE file already exists with AGPL-3.0 text. Additional steps:

1. **SKILL.md header** — Already has the YAML frontmatter. Add a license field:
   ```yaml
   license: AGPL-3.0
   ```
2. **README badge** — Add near the top:
   ```markdown
   [![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
   ```
3. **Source file headers** — Not strictly necessary for markdown/instruction files, but consider a brief notice in `SKILL.md`:
   ```
   <!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
   ```
4. **GitHub repo settings** — GitHub already detects the LICENSE file and shows the license badge automatically.

### Compatibility with Claude Code's Own Licensing

Claude Code is a proprietary Anthropic product. SquidSquad does not link to, include, or derive from Claude Code's source code. SquidSquad is a set of instructions (SKILL.md) that Claude Code reads — similar to how a recipe book doesn't derive from the oven. There is no licensing compatibility concern.

The SKILL.md format is an open standard (Anthropic released Agent Skills as a public spec in December 2025, and OpenAI adopted it for Codex CLI). Licensing a skill under AGPL is fully compatible.

### Recommendation

AGPL-3.0 is the right choice. It:
- Allows free use (even commercial, even modified) for anyone running it locally
- Prevents proprietary forks from competing without contributing back
- Is well-understood in the open source community
- Matches the human's stated intent: "can be used freely as a whole, modifications must stay open-source"

---

## 2. Repo Cleanup Before Going Public

### Current Repo Contents Assessment

| Path | What it is | Keep/Remove/Archive |
|------|-----------|-------------------|
| `SKILL.md` | Core skill definition | **Keep** — this IS the product |
| `README.md` | Public landing page | **Keep** — rewrite (FEAT-SKILL-056) |
| `CLAUDE.md` | Auto-boot configuration | **Keep** — needed for SquidSquad to run on itself |
| `LICENSE` | AGPL-3.0 | **Keep** |
| `CHANGELOG.md` | Version history | **Keep** — valuable for users |
| `references/` | Sub-skill source files, templates, hints | **Keep** — this is the skill's source of truth |
| `evals/` | Evaluation/test data | **Keep** — useful for contributors |
| `.squidsquad/config.md` | Instance config for THIS repo | **Remove/Reset** — per-project generated data |
| `.squidsquad/skill/` | Dev agent tracker, bugs, features, iterations | **Remove** — internal development noise |
| `.squidsquad/pm/` | PM agent tracker, enhancements, migrations | **Remove** — internal development noise |
| `.squidsquad/dm/` | DM agent tracker | **Remove** — internal development noise |
| `.squidsquad/qa/` | QA agent tracker | **Remove** — internal development noise |
| `.squidsquad/vault/` | Knowledge vault for THIS project | **Remove** — per-project data |
| `.squidsquad/templates/` | Generated agent templates | **Remove** — regenerated on setup |
| `.squidsquad/start-*.sh/.ps1` | Boot scripts | **Remove** — regenerated on setup |
| `.squidsquad/statusline.sh` | Status bar script | **Remove** — regenerated on setup |
| `.squidsquad/hints-*.txt` | Hint text files | **Remove** — regenerated from references/ |
| `bash.exe.stackdump` | Windows crash artifact | **Remove** |
| `.squidsquad/skill/planning/` | Research, context, test plan artifacts | **Remove** — internal development artifacts |

### Recommended Approach

**Option A: Clean `.squidsquad/` completely (Recommended)**

The entire `.squidsquad/` directory is per-project generated data. When a user installs SquidSquad and runs setup, the skill generates this folder fresh. The public repo should NOT contain a populated `.squidsquad/` — it would confuse new users ("is this my data or the project's data?").

Actions:
1. Add `.squidsquad/` to `.gitignore` (except maybe a `.squidsquad/.gitkeep` or a small example)
2. Remove all `.squidsquad/` contents from tracking
3. The skill's own development tracker history lives in git history — always recoverable

**Option B: Keep `.squidsquad/` as a living example**

Argument: new users can browse the folder to understand the structure before running setup. Counter-argument: the README and SKILL.md already document the structure thoroughly, and stale example data is worse than no data.

**Verdict: Option A.** A new user cloning the repo should see a clean project, not someone else's bug tracker.

### Should `references/` Stay?

**Yes, absolutely.** `references/` is the skill's source of truth:
- `references/sub-skills/` — the actual sub-skill source files that compose into agent templates
- `references/vault-templates/` — vault structure templates
- `references/hints-*.txt` — status bar hint text
- `references/statusline.sh` — status line script source
- `references/logo/` — branding assets
- `references/agent-instructions.md` — composed agent instructions (generated but committed)

This is SquidSquad's "source code." Without it, the skill cannot set up new projects.

### Git History — Rewrite or Keep?

**Keep the history.** Reasons:
1. The history IS the proof of concept — it shows SquidSquad being used to build SquidSquad (dogfooding)
2. Rewriting history (squashing to a single commit) destroys the audit trail that demonstrates the project's philosophy
3. The `.squidsquad/` removal commit naturally separates "development era" from "public era"
4. Any secrets or sensitive paths can be checked without rewriting (there shouldn't be any — SquidSquad uses no API keys)

The history shows real multi-agent coordination through markdown files — bugs filed, features planned, QA verified, PM coordinated. This is powerful marketing material. Consider linking to interesting commits/PRs in the README.

### What a New User Needs

A new user cloning the repo needs exactly:
1. `SKILL.md` — to install the skill
2. `README.md` — to understand what it is and how to start
3. `references/` — skill source files (used during setup)
4. `CHANGELOG.md` — to understand the version they're using
5. `LICENSE` — legal clarity
6. `CLAUDE.md` — auto-boot instructions (only matters if they're developing SquidSquad itself)

They do NOT need:
- `.squidsquad/` with someone else's tracker data
- Planning artifacts from feature development
- Test vault data
- Iteration logs

### Updated `.gitignore`

```gitignore
# SquidSquad runtime (per-project generated data)
.squidsquad/

# SquidSquad local config (machine-specific, never committed)
.squidsquad/.local-config

# Claude Code local settings
.claude/commands/squidsquad-*
.claude/settings.local.json
.claude/scheduled_tasks.lock

# OS/shell artifacts
*.stackdump
```

Note: `.squidsquad/` being gitignored means it won't be tracked in consumer repos. For SquidSquad's OWN repo (where it dogfoods), the developers may want to NOT gitignore it during development — but the public-facing `.gitignore` should list it as a signal to users.

**Alternative approach**: Keep `.squidsquad/` out of `.gitignore` in the SquidSquad repo (since it's useful for dogfooding), but document clearly in the README that `.squidsquad/` is generated per-project and should be gitignored in user projects. The skill's setup flow could auto-add it to the user project's `.gitignore`.

---

## 3. The Pitch — Positioning SquidSquad

### Competitive Landscape

**Current multi-agent frameworks for Claude Code:**

| Project | Approach | Stars | Differentiator |
|---------|----------|-------|---------------|
| **oh-my-claudecode** | Plugin-based orchestration, task lists, N agents on shared tasks | 858+ (trending #1 on GitHub at launch) | Zero-config, speed (3-5x), token savings, HUD dashboard |
| **Everything Claude Code** | Harness optimization — skills, instincts, memory, security | Moderate | Research-first development, cross-platform (Codex, Cursor too) |
| **Ruflo** | Swarm intelligence, distributed agents | Moderate | Enterprise architecture, RAG integration |

**Broader multi-agent frameworks:**

| Framework | Model | Key Trait |
|-----------|-------|-----------|
| **CrewAI** | Role-based task execution | 44K+ stars, lowest barrier to entry |
| **LangGraph** | Stateful graph workflows | Production-grade, battle-tested |
| **AutoGen** | Multi-party conversations | Now in maintenance mode (merged into MS Agent Framework) |

### SquidSquad's Unique Value Proposition

SquidSquad is NOT competing with these frameworks directly. The key differentiators:

1. **No infrastructure** — Other frameworks require Python environments, API keys, orchestration servers, or cloud services. SquidSquad needs only git and Claude Code. The coordination layer is markdown files in a git repo.

2. **Persistent, autonomous agents with memory** — Agents loop indefinitely with context pressure management, working state persistence, and a shared vault (Zettelkasten-style knowledge base). They don't just execute a task and stop — they maintain institutional knowledge across sessions.

3. **Human-in-the-loop by default** — The PM agent provides a natural interface. You talk to the PM, the PM coordinates the team. No learning a new API, no configuration language, no task definition YAML.

4. **Full audit trail in git** — Every decision, discussion, bug fix, and feature negotiation is traceable through `git log`. No external database, no ephemeral state.

5. **Extensible via sub-skills** — The composition architecture (FEAT-SKILL-030) allows community-created behaviors without forking the core.

6. **Agent personalities** — Agents have distinct communication styles (SOUL.md). The PM is diplomatic, QA is skeptical, dev is pragmatic. Interactions feel like a real team, not identical clones.

### Target Audience (in priority order)

1. **Solo developers** who want a team without hiring one — the primary audience. "I want to describe what I want to build, and have an AI team build it while I sleep."

2. **Small teams (2-5 devs)** who want AI augmentation — each dev has their own SquidSquad instance, or the team shares one with multiple dev agents.

3. **AI/developer tooling enthusiasts** who want to experiment with multi-agent coordination patterns.

4. **Open source maintainers** who want automated bug triage, feature implementation, and QA on their projects.

5. **Enterprises** are a stretch goal, not an initial target. AGPL may create friction, and enterprise needs (SSO, audit compliance, SLAs) are beyond v1.0 scope.

### The Elevator Pitch

**One sentence:**
> SquidSquad is a Claude Code skill that turns your git repo into a self-coordinating AI dev team — PM, devs, QA — that works autonomously through markdown files, not meetings.

**One paragraph:**
> SquidSquad spins up a team of AI agents — a PM you talk to, dev agents that fix bugs and build features, and a QA that independently verifies everything — all coordinating through markdown files in a `.squidsquad/` folder in your git repo. No orchestration servers, no message queues, no API keys. Agents loop autonomously, persist their working state across context resets, build institutional knowledge in a shared vault, and communicate through Discussion entries in tracker files. Every decision is traceable in git history. Install a skill, run setup, and you have a dev team.

**One page (key talking points):**

> **The Problem**: You're a solo developer (or a small team) with more ideas than bandwidth. AI coding assistants help, but they're one-shot — you describe a task, they do it, you describe the next. You're still the bottleneck.
>
> **The Solution**: SquidSquad gives you an autonomous dev team. Define your roles (frontend, backend, API, whatever), run the setup command, and launch the agents. The PM takes your feature requests and bug reports. Dev agents pick up approved work, implement it, and run tests. QA independently verifies every change. Everything flows through git — no external services, no infrastructure, no cost beyond Claude Code itself.
>
> **How it works**: Each agent runs as a Claude Code CLI instance in its own terminal, looping through the "Ralph Loop" — pull latest, check for bugs, implement features, test, commit, push, sleep, repeat. Agents coordinate by reading and writing to shared markdown files in `.squidsquad/`. The PM checks in with you each cycle (non-blocking), surfaces blockers, and gets approvals. If an agent's context window fills up, it saves state and exits cleanly — the boot script restarts it automatically.
>
> **What makes it different**: Unlike other multi-agent frameworks that require Python, API orchestration, or cloud infrastructure, SquidSquad's entire coordination layer is markdown and git. Your project's `.squidsquad/` folder IS the system. `git log` shows you every decision, every bug discussion, every feature negotiation. Agents build knowledge about your codebase, your preferences, and your conventions in a shared vault. They get better at being YOUR team over time.
>
> **Getting started**: Install the skill. Say "Set up SquidSquad." Launch the agents. Talk to the PM.

### What Would Make Someone Star/Fork/Install?

Based on research into what drives open source engagement:

1. **A compelling demo** — A GIF or video showing agents working in parallel, a PM check-in, a bug getting filed and fixed across agents. "Show, don't tell."
2. **Dogfooding proof** — "SquidSquad was built by SquidSquad" is a powerful narrative. The git history proves it.
3. **Low barrier to entry** — "Install one skill, run one command" beats any framework that requires `pip install`, config files, or API keys.
4. **The vault/memory concept** — "Your AI team remembers your preferences and gets better over time" is novel and appealing.
5. **Personality** — The squid branding, emoji markers, agent souls — it's memorable and fun. Most AI tooling is dry and corporate.

---

## 4. Community Infrastructure

### GitHub Issues Templates

Create `.github/ISSUE_TEMPLATE/`:

**bug_report.md:**
```yaml
---
name: Bug Report
about: Something isn't working as expected
title: '[BUG] '
labels: bug
assignees: ''
---

**SquidSquad version**: (from SKILL.md header or config.md)
**Claude Code version**:
**OS**:

**Describe the bug**
A clear description of what's wrong.

**Steps to reproduce**
1.
2.
3.

**Expected behavior**

**Actual behavior**

**Relevant logs**
(Paste agent output, iteration logs, or error messages)

**Additional context**
```

**feature_request.md:**
```yaml
---
name: Feature Request
about: Suggest an improvement or new capability
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is this related to a problem?**
A clear description of the limitation or pain point.

**Describe the solution you'd like**

**Describe alternatives you've considered**

**Would you be willing to contribute this?**
[ ] Yes, I'd like to submit a PR
[ ] No, but I can help test
[ ] Just suggesting
```

**sub_skill_proposal.md:**
```yaml
---
name: Sub-skill Proposal
about: Propose a new community sub-skill
title: '[SUB-SKILL] '
labels: sub-skill, proposal
assignees: ''
---

**Sub-skill name**:
**Description**: What does this sub-skill add to agent behavior?
**Which roles benefit**: (dev / pm / qa / designer / all)
**Composition point**: Where in the agent template should it be included?
**Example behavior**: Describe what an agent would do differently with this sub-skill active.
```

### CONTRIBUTING.md

Key sections:
1. **How to report bugs** — Use the bug template. Include version, OS, reproduction steps.
2. **How to propose features** — Use the feature template. Discuss in the issue before PRing.
3. **How to contribute sub-skills** — The most important contribution path:
   - Follow the sub-skill format in `references/sub-skills/`
   - Include a manifest entry describing composition point
   - Test with at least one project before submitting
4. **How to submit a PR** — Fork, branch, test, PR against `main`. Human reviews all PRs.
5. **Code style** — Markdown formatting conventions, commit message format (`role: description`).
6. **What NOT to submit** — PRs that change core agent loop behavior without discussion, breaking changes to the tracker schema, modifications to SOUL.md personalities (these are curated).

### CODE_OF_CONDUCT.md

Use the Contributor Covenant (most widely adopted). Key points: be respectful, constructive, inclusive. Enforcement: the human (benevolent dictator) has final say.

### GitHub Discussions vs Issues

**Recommendation: Use both, with clear separation.**

- **Issues** — Bugs, feature requests, sub-skill proposals. Actionable items with a lifecycle.
- **Discussions** — "How do I..." questions, show-and-tell (share your SquidSquad setup), ideas that aren't ready for a feature request, general chat.

Enable Discussions categories:
- **Q&A** — Help and troubleshooting
- **Show & Tell** — Share your SquidSquad setup, sub-skills, results
- **Ideas** — Early-stage feature brainstorming
- **General** — Everything else

### CI/CD

Minimal for a skill repo (no compiled code), but some checks are valuable:

1. **Markdown linting** — Ensure SKILL.md, README.md, and references/ files are well-formed
2. **Sub-skill composition validation** — A script that runs the include resolution and verifies all `{{include: path}}` directives resolve to existing files
3. **Schema validation** — Verify tracker file templates match the expected schema
4. **Link checking** — Ensure internal links in README/docs aren't broken
5. **License header check** — Verify SPDX headers are present where required

GitHub Actions workflow — runs on PR and push to main. Lightweight and fast.

### Release Process

1. **Semantic versioning** — Already in place (currently v0.8.0)
2. **Git tags** — Tag each release: `git tag v0.9.0`
3. **GitHub Releases** — Create a release from the tag with CHANGELOG excerpt as the body
4. **CHANGELOG.md** — Already exists. Continue the format. Each release gets a section.
5. **Release cadence** — No fixed schedule. Ship when ready. Auto-versioning (already implemented) bumps minor version every N shipped items.

---

## 5. Pre-Launch Checklist

### Must-Have (Before Making Repo Public)

- [ ] **LICENSE file** — Already exists (AGPL-3.0). Verified.
- [ ] **Clean README** — FEAT-SKILL-056 deliverable. Must be rewritten as a public-facing landing page.
- [ ] **Remove `.squidsquad/` contents** — Remove all per-project tracker data, planning artifacts, iteration logs, working state files, vault data, generated templates, boot scripts. Either gitignore the entire folder or commit it empty with documentation.
- [ ] **Remove `bash.exe.stackdump`** — Windows crash artifact currently in repo root.
- [ ] **Proper `.gitignore`** — Update to cover `.squidsquad/` generated data, local config, OS artifacts.
- [ ] **Security audit** — Scan all files for:
  - Hardcoded paths (e.g., `D:\Dev\Dev\SquidSquad` in any committed file)
  - API keys, tokens, or secrets
  - Personal information (names, emails beyond what's in git commits)
  - Internal references that don't make sense publicly
- [ ] **Working setup flow** — Test the full flow: install skill, run setup, launch agents, file a bug, ship a feature. Must work on a clean repo with no prior `.squidsquad/` data.
- [ ] **SKILL.md license field** — Add `license: AGPL-3.0` to YAML frontmatter.
- [ ] **README license badge** — Add AGPL badge.
- [ ] **CONTRIBUTING.md** — Basic contribution guidelines.
- [ ] **GitHub issue templates** — Bug report, feature request, sub-skill proposal.

### Should-Have (Before or Shortly After)

- [ ] **CODE_OF_CONDUCT.md** — Contributor Covenant.
- [ ] **GitHub Discussions enabled** — With category structure.
- [ ] **At least one example project** — A separate repo showing SquidSquad in action on a real project. Could be a simple TODO app, a CLI tool, or an API server where SquidSquad manages the development.
- [ ] **CI/CD** — Basic markdown linting and sub-skill composition validation.
- [ ] **GitHub Release** — Create v0.8.0 (or v1.0.0) release with proper release notes.
- [ ] **SPDX headers** — Add to key source files.

### Nice-to-Have (Post-Launch)

- [ ] **Demo GIF/video** — Short recording of agents working in parallel.
- [ ] **Project website** — GitHub Pages or similar, with better landing page than README alone.
- [ ] **Discord server** — For real-time community interaction.
- [ ] **Blog post** — Launch announcement with the story of building SquidSquad with SquidSquad.
- [ ] **"awesome-squidsquad"** list — Community sub-skills, example projects, articles.

### Test on Another Project First

The human specified this explicitly: test on another project before going public. This means:

1. Pick a real (or realistic) project — not SquidSquad itself.
2. Install SquidSquad as a skill on that project.
3. Run the full setup flow.
4. Let agents work for several cycles.
5. Verify: setup works cleanly, agents coordinate correctly, bugs get filed and fixed, features get implemented, the PM check-in flow works, context pressure exits and restarts work.
6. Document any issues found and fix them.
7. Use this project as the "example project" in the README.

---

## 6. Community Growth Strategy

### Launch Announcements (in priority order)

1. **Hacker News** — The primary launch venue. Post Tuesday-Thursday, 8-10 AM PT. Title should be concise and intriguing: "Show HN: SquidSquad — An AI dev team that coordinates through markdown, not meetings". Be ready to answer questions for 2+ hours after posting.

2. **Reddit** — Key subreddits:
   - r/ClaudeAI — Direct audience
   - r/ChatGPTCoding — Broader AI coding audience
   - r/programming — If the HN post gains traction
   - r/SideProject — Solo dev audience

3. **Twitter/X** — Thread format: problem, solution, demo GIF, link. Tag @AnthropicAI, @claudeai. Use hashtags: #ClaudeCode, #AIAgents, #OpenSource.

4. **Claude community** — Anthropic's official forums/Discord if they exist. Claude Code skill listings and directories.

5. **Skill marketplaces** — Submit to:
   - SkillsMP (skillsmp.com)
   - awesome-claude-skills (GitHub)
   - awesome-claude-code (GitHub)
   - Claude Code Plugins directory (claudemarketplaces.com)

6. **Dev.to / Medium** — Longer-form launch post with technical details.

7. **Discord** — Create a SquidSquad Discord server before launch, link from README.

### Attracting Early Adopters

1. **Solve a real pain point visibly** — The "solo dev who wants a team" narrative resonates. Lead with this.
2. **Make it dead simple to try** — One skill install, one setup command. If setup takes more than 5 minutes, you'll lose people.
3. **Show the dogfooding** — "This project was built by its own agents" is a unique credibility signal. Link to interesting git history.
4. **Low-friction contribution path** — Sub-skills are the killer contribution model. Creating a sub-skill doesn't require understanding the entire system.
5. **Personality and brand** — The squid theme, emoji markers, agent personalities — lean into this. AI tooling is crowded; memorable branding helps.

### What Makes People Contribute to Open Source

Research consistently shows:

1. **Clear contribution guidelines** — People won't contribute if they don't know how.
2. **"Good first issue" labels** — Tag easy sub-skill ideas or documentation improvements.
3. **Fast PR review** — Respond to PRs within 48 hours. Nothing kills contributor enthusiasm faster than a PR that sits for weeks.
4. **Recognition** — Acknowledge contributors in CHANGELOG, release notes, README. Consider a "Contributors" section.
5. **A real community** — Discord or Discussions where people can talk, not just file issues.
6. **The project is useful to them** — Contributors contribute because they use the tool and want it to be better.

### Handling the First Wave

1. **Prepare issue templates** before launch.
2. **Have a FAQ ready** — Common questions: "Does this work with [X model]?", "Can I use this at work?", "How much does it cost in API usage?", "Is this like CrewAI?"
3. **Triage quickly** — Respond to every issue within 24 hours, even if just "Thanks, we'll look into this."
4. **Be honest about limitations** — "This is v0.8, here's what's known to be rough."
5. **Don't merge everything** — The benevolent dictator model means quality control. Be kind but firm about standards.

### Promoting Contributors to Maintainers

The human specified a benevolent dictator model with gradual trust-building:

1. **Phase 1** — Human reviews all PRs. Contributors submit through standard PR process.
2. **Phase 2** — After 3-5 quality PRs, offer "triage" permissions (label issues, close duplicates).
3. **Phase 3** — After sustained contribution (several months, deep understanding of the system), offer "write" access for specific areas (e.g., a sub-skill maintainer).
4. **Phase 4** — Core maintainer status for deeply trusted contributors. Can approve PRs, but human retains final say on architectural decisions.

Document this path explicitly in CONTRIBUTING.md so contributors know what the progression looks like.

---

## 7. Sub-skill Marketplace / Extension Model

### How Third-Party Sub-Skills Should Work

SquidSquad's sub-skill architecture (FEAT-SKILL-030, `references/sub-skills/`) already provides the composition model. Community sub-skills need:

**Install:**
1. User downloads the sub-skill `.md` file(s) to `references/sub-skills/community/` (new directory)
2. User adds the include directive to the relevant role entry file (or a config toggle)
3. User runs "upgrade squidsquad" to recompose templates

**Simpler alternative — config-driven:**
1. Add a `Community Sub-skills` section to `config.md` listing enabled sub-skills
2. During setup/upgrade, the composition engine checks for community sub-skills and includes them
3. No manual file editing needed

**Register:**
- Each community sub-skill has a manifest entry: name, description, author, roles it applies to, composition point (after which existing sub-skill), version, dependencies
- A central `community-skills-registry.md` or `community-skills.json` in the repo (or a separate registry repo)

**Compose:**
- Community sub-skills follow the same `{{include: path}}` format
- They are composed after core sub-skills at their declared composition point
- They can reference existing sub-skill sections but cannot modify them

### Marketplace vs Curated List

**Recommendation: Start with a curated list, evolve to a registry.**

A full marketplace is premature at launch. Instead:

1. **Phase 1 (Launch)**: A `COMMUNITY-SKILLS.md` file in the repo listing known community sub-skills with links to their repos/gists. Curated by the human.

2. **Phase 2 (Growing)**: A separate `squidsquad-community-skills` GitHub repo that serves as a registry. Sub-skill authors submit PRs to add their skill. Basic quality bar: must include a README, must work with the current SquidSquad version, must follow the sub-skill format.

3. **Phase 3 (Mature)**: Potentially integrate with Claude Code's skill marketplace ecosystem (SkillsMP, etc.) or build a simple CLI command: `squidsquad install-skill <name>`.

### Ensuring Quality of Community Sub-Skills

1. **Format validation** — CI check that verifies sub-skill files follow the expected format (markdown structure, section markers, no prohibited patterns)
2. **Composition testing** — Automated check that the sub-skill composes correctly with the current template set without breaking existing functionality
3. **Peer review** — Community sub-skill PRs require at least one review from a maintainer
4. **Version compatibility** — Sub-skills declare which SquidSquad version(s) they support
5. **"Verified" badge** — Sub-skills tested by the core team get a verified label in the registry

### Versioning and Compatibility

1. **SquidSquad version compatibility** — Sub-skills declare a minimum and maximum supported version in their manifest
2. **Sub-skill versioning** — Each community sub-skill has its own semver. Breaking changes in a sub-skill require a major version bump.
3. **Composition point stability** — Core sub-skills define stable composition points (named anchors) that community sub-skills attach to. Moving or removing a composition point is a breaking change in SquidSquad's own versioning.
4. **Architecture version** — `config.md` already has `Architecture Version: 1`. Bumping this signals that the composition model changed and community sub-skills may need updates.

### Sub-skill Ideas to Seed the Community

Suggest these as "good first sub-skills" to encourage early contributions:

- **Linting sub-skill** — Dev agent runs a configurable linter during the test step
- **Documentation sub-skill** — Dev agent generates/updates JSDoc/docstrings after feature implementation
- **Security scanning sub-skill** — QA agent runs a security scanner during verification
- **Performance testing sub-skill** — QA agent runs benchmarks and flags regressions
- **Deployment sub-skill** — DM agent triggers deployment after version bump
- **Notification sub-skill** — PM agent sends notifications (Slack, Discord webhook) on key events
- **Code review sub-skill** — Dev agent self-reviews changes against a checklist before marking Pending Test

---

## Key Open Questions for Human Decision

1. **Version number for public launch** — Ship as v0.8.0 (current) or bump to v1.0.0? The "1.0" signals stability and readiness. The "0.x" signals "early but working." Given the instruction to test on another project first, shipping as v0.9.0 after the test and v1.0.0 when going public could work.

2. **`.squidsquad/` in this repo's `.gitignore`** — Should the SquidSquad repo itself gitignore `.squidsquad/` (clean public face) or keep it tracked (dogfooding evidence)? Recommendation: remove from tracking before going public, keep history as proof.

3. **Example project** — What project to use for the "test on another project first" phase? This becomes the showcase.

4. **Discord server** — Create before launch or wait to see demand?

5. **Community sub-skill format** — Finalize before launch or iterate after feedback?

6. **README rewrite scope** — How much of the current README structure to keep vs redesign from scratch? (Addressed by FEAT-SKILL-056)

---

## Sources

- [AGPL License — Non-starter for Most Companies (Open Core Ventures)](https://www.opencoreventures.com/blog/agpl-license-is-a-non-starter-for-most-companies)
- [AGPL Policy (Google Open Source)](https://opensource.google/documentation/reference/using/agpl-policy)
- [Guide to AGPL Compliance (Vaultinum)](https://vaultinum.com/blog/essential-guide-to-agpl-compliance-for-tech-companies)
- [Understanding the AGPL (Medium/The Startup)](https://medium.com/swlh/understanding-the-agpl-the-most-misunderstood-license-86fd1fe91275)
- [The Fundamentals of the AGPLv3 (FSF)](https://www.fsf.org/bulletin/2021/fall/the-fundamentals-of-the-agplv3)
- [Providing Source Under AGPLv3 (Opensource.com)](https://opensource.com/article/17/1/providing-corresponding-source-agplv3-license)
- [oh-my-claudecode (GitHub)](https://github.com/yeachan-heo/oh-my-claudecode)
- [Everything Claude Code (GitHub)](https://github.com/affaan-m/everything-claude-code)
- [Agent Skills — Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Extend Claude with Skills — Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Open Source AI Agent Frameworks Compared (OpenAgents)](https://openagents.org/blog/posts/2026-02-23-open-source-ai-agent-frameworks-compared)
- [Growing Your Open Source Community (DEV Community)](https://dev.to/axrisi/growing-your-open-source-community-in-2025-strategies-for-sustainable-projects-2lln)
- [Four Steps Toward Building an Open Source Community (GitHub Blog)](https://github.blog/open-source/maintainers/four-steps-toward-building-an-open-source-community/)
- [Open Source Guides (opensource.guide)](https://opensource.guide/)
- [Promote Your Open Source Project (daily.dev)](https://business.daily.dev/resources/promote-open-source-project-step-by-step-launch-guide/)
- [10 Proven Ways to Boost GitHub Stars (ScrapeGraphAI)](https://scrapegraphai.com/blog/gh-stars)
- [Claude Code Skills Marketplace (SkillsMP)](https://skillsmp.com/)
- [awesome-claude-skills (GitHub)](https://github.com/travisvn/awesome-claude-skills)
