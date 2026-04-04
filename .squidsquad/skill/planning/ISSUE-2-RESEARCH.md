# ISSUE-2 — Research: README Redesign for Public Landing Page

**Feature**: Full README redesign (public-facing landing page)
**Researcher**: research-agent
**Date**: 2026-04-02
**Status**: Complete

---

## Table of Contents

1. [Current README Audit](#1-current-readme-audit)
2. [Best-in-Class Open Source READMEs](#2-best-in-class-open-source-readmes)
3. [README Structure Proposal](#3-readme-structure-proposal)
4. [The Hook](#4-the-hook)
5. [What to Keep vs Remove from Current README](#5-what-to-keep-vs-remove-from-current-readme)

---

## 1. Current README Audit

### What It Covers

The current README (366 lines) covers these sections:

| Section | Lines | Content |
|---------|-------|---------|
| ASCII art + title | 1-17 | Squid logo, one-liner tagline |
| What It Is | 19-25 | Two-paragraph explanation |
| How It Works | 27-163 | Agents table, team shapes, Ralph Loop (mermaid), architecture diagram (mermaid), `.squidsquad/` folder tree |
| Features | 167-225 | 16 feature descriptions (status line, step markers, working state, context pressure, health detection, quiet cycles, improvement scanning, iteration retention, PR flow, GitHub Issues, designer, subagent delegation, status bar chaining, auto versioning, vault, agent personalities, externalized templates, VS Code integration, `/squidsquad-status` command) |
| Philosophy | 227-245 | Git Is the Bus, Complete Audit Trail, No External Dependencies, One Exception: Real-Time Health |
| Quick Start | 248-308 | 4-step install + launch instructions (bash + PowerShell) |
| Cross-Team Bug Filing | 310-320 | Bug routing table |
| Requirements | 322-332 | Dependencies list |
| Git Protocol | 334-346 | Agent commit conventions |
| Versioning | 348-359 | Semver, upgrading instructions |
| License | 361-366 | AGPL-3.0 link |

### What's Good

1. **The one-liner tagline is strong**: "Your AI dev team that coordinates through markdown, not meetings." This is the pitch. Keep it.
2. **Team shapes table** is immediately understandable — shows the flexibility in 5 rows.
3. **Architecture diagram** (mermaid) is clear and informative.
4. **Philosophy section** articulates the "why" well — Git Is the Bus is a memorable framing.
5. **Requirements section** is honest and minimal.

### What's Missing for a Public Audience

1. **No badges** — No version badge, no license badge, no "works with Claude Code" badge. First impression for GitHub visitors is bare.
2. **No hero moment** — The ASCII art is cute but doesn't grab. No screenshot, no GIF, no demo video. Visitors need to SEE what this looks like running.
3. **No "why should I care" section** — Jumps straight from "what is this" to "how it works." Missing the emotional hook: "You're a solo dev with more ideas than time."
4. **No social proof or credibility signal** — No mention that SquidSquad was built by its own agents (the dogfooding story). No link to interesting git history.
5. **No comparison to alternatives** — Reader doesn't know how this differs from CrewAI, AutoGen, oh-my-claudecode.
6. **No FAQ** — Common questions (cost? model requirements? does it work with X?) are unanswered.
7. **Features section is a wall of text** — 16 features listed as paragraph-style descriptions with no visual hierarchy. Exhaustive but unscalable for scanning.
8. **Quick Start is buried** — Line 248 of 366. Most people scroll past or leave before reaching it.
9. **No contributing section** — No invitation to participate.

### Internal Noise That Should Be Removed or Moved

1. **`.squidsquad/` folder tree (lines 117-163)** — 46 lines of directory listing. This is reference documentation, not landing page material. Move to a docs file or collapse into a brief mention.
2. **Cross-Team Bug Filing section** — Internal operational detail. Remove from README entirely; this belongs in agent instructions.
3. **Git Protocol section** — Agent-facing commit conventions. Not relevant to someone deciding whether to install. Remove or move to CONTRIBUTING.md.
4. **16 detailed feature descriptions** — This reads like a changelog, not a feature showcase. Condense to 6-8 key features with one-liners, link to detailed docs for the rest.
5. **Dual bash/PowerShell examples** — Makes the Quick Start visually heavy. Show one primary (bash), note PowerShell is also supported.
6. **Ralph Loop mermaid diagram** — Cool but premature for a landing page. Save for an "Architecture" or "How It Works" deeper section.
7. **Context pressure, quiet cycle skipping, iteration retention** — Implementation details that matter to users but not to prospects. These are "discover later" features.

### Scannability Assessment

**Poor.** The README is 366 lines with no visual hierarchy beyond H2/H3 headers. The features section alone is ~60 lines of dense paragraphs. No icons, no bullet points for quick scanning, no bold keywords to anchor the eye. A developer skimming on GitHub will see a wall of text after the architecture diagram and bounce.

---

## 2. Best-in-Class Open Source READMEs

### Patterns from Top AI Tool READMEs

Based on analysis of successful AI tool projects (Cursor, Aider, CrewAI, AutoGen, Claude Code ecosystem tools, oh-my-claudecode):

#### What They All Have

1. **Hero section with visual** — Screenshot, GIF, or ASCII banner + badges. oh-my-claudecode leads with a demo GIF showing the HUD in action. CrewAI has a branded banner image.
2. **Badges row** — Version, license, stars, downloads, Discord/community link. Creates immediate "this is a real project" signal.
3. **One-sentence pitch above the fold** — Before scrolling. CrewAI: "Framework for orchestrating role-playing, autonomous AI agents." Aider: "AI pair programming in your terminal."
4. **Quick Start within first screenful** — Or a prominent link to it. Installation should be 1-3 commands. The faster someone can try it, the more likely they will.
5. **Feature bullets, not paragraphs** — Short, scannable, often with emoji/icons. 4-8 features max on the landing page.
6. **Architecture as a simple diagram** — One image/mermaid showing the high-level flow. Not exhaustive — just enough to build mental model.
7. **Comparison table** (optional but effective) — "How is this different from X?" Helps readers self-select.
8. **Contributing section** — Even if just "PRs welcome." Signals openness.
9. **License clearly stated** — Badge + footer.

#### What Hooks People in the First 10 Seconds

1. **A visual that shows the product running** — GIF > screenshot > diagram > nothing. People process images 60,000x faster than text.
2. **A problem statement they identify with** — "You're a solo dev who wants a team" hits harder than "multi-agent coordination framework."
3. **A clear "what you get"** — Not what the tool IS, but what it DOES for you. "Install one skill, get a dev team" > "orchestrates autonomous AI agents."
4. **Proof it works** — Star count, user testimonials, or (in SquidSquad's case) the dogfooding story.
5. **Low perceived effort** — "5-minute setup" or "one command" signals that trying it won't waste their afternoon.

#### Specific Observations

**oh-my-claudecode** (858+ stars, trending):
- Leads with a demo GIF — you immediately see what it looks like
- "Zero-config" is the first word after the title
- Feature list uses emoji bullets
- Quick start is 3 steps, fits in one screenful
- Comparison table vs vanilla Claude Code

**CrewAI** (44K+ stars):
- Branded banner image
- "Build multi-agent systems with ease" — value prop in subtitle
- Feature grid with icons
- Code example showing usage in <20 lines
- "Why CrewAI?" section directly addresses alternatives

**Aider** (popular AI coding tool):
- Terminal screenshot as hero
- "AI pair programming in your terminal" — 7 words, instantly understood
- Feature bullets with bold keywords
- Quick start: 2 commands (`pip install aider-chat`, `aider`)

### The Formula

```
Hero (visual + tagline + badges)
  -> What is this? (1 paragraph)
  -> Why? / The Problem (2-3 sentences)
  -> Key Features (6-8 bullets with icons)
  -> Quick Start (3-5 steps)
  -> How It Works (one diagram)
  -> Differentiators (comparison or unique story)
  -> Contributing
  -> License
```

---

## 3. README Structure Proposal

### Complete Section-by-Section Outline

#### 1. Hero Section (~15 lines)
- ASCII squid art (keep — it's distinctive and memorable)
- `# SquidSquad`
- **Tagline**: "Your AI dev team that coordinates through markdown, not meetings."
- **Badges row**: version (v1.0.0), license (AGPL-3.0), "works with Claude Code", GitHub stars
- **One-liner expansion**: "Install one skill. Run one command. Get a PM, devs, and QA — all autonomous, all coordinating through your git repo."

#### 2. Demo Visual (~5 lines)
- Screenshot or GIF placeholder showing agents running in split terminals
- Caption: "Three agents working in parallel — PM, Skill Lead, QA"
- This is the single most impactful thing missing from the current README

#### 3. The Problem (~8 lines)
- "You're a solo developer with more ideas than bandwidth."
- AI assistants help, but they're one-shot — you describe, they do, you describe the next
- You're still the bottleneck, still the PM, still the QA
- What if you could describe what you want and a team handles the rest?

#### 4. What Is SquidSquad (~10 lines)
- Elevator pitch paragraph (from FEAT-SKILL-055 research)
- Key differentiator: no infrastructure, no message queues, no API keys — just markdown and git
- "Every decision is traceable in `git log`. Your AI team gets better at being YOUR team over time."

#### 5. Key Features (~20 lines)
- 6-8 features as bullet points with emoji icons, one line each:
  - Autonomous agent loop (Ralph Loop) — agents work while you sleep
  - Flexible team shapes — define your roles, get PM + QA for free
  - GitHub Issues as tracker — bugs and features are real GitHub Issues
  - Shared memory vault — agents learn your preferences, conventions, style
  - Context pressure management — agents exit cleanly, resume from saved state
  - Agent personalities — PM is diplomatic, QA is skeptical, dev is pragmatic
  - Sub-skill architecture — extend agent behavior without forking
  - PR-based workflow (optional) — human reviews before merge

#### 6. Quick Start (~25 lines)
- **Step 1**: Install the skill (one command or file copy)
- **Step 2**: "Set up SquidSquad for my project" (one sentence to Claude)
- **Step 3**: Launch agents (show bash example, note PowerShell support)
- **Step 4**: Talk to the PM
- Entire section should feel achievable in 5 minutes

#### 7. Team Shapes (~10 lines)
- Keep the existing team shapes table — it's excellent
- Shows flexibility without verbose explanation
- 5 examples: `fe, be` / `fe, be, designer` / `be` / `api, worker` / `skill`

#### 8. How It Works (~25 lines)
- Keep the architecture mermaid diagram (the non-Ralph-Loop one)
- Brief explanation: "Each agent runs as a Claude Code CLI instance, looping autonomously"
- Mention the Ralph Loop by name with a one-sentence summary, link to detailed docs
- "All coordination is asynchronous through git — no direct agent-to-agent communication"

#### 9. Built By Its Own Agents (~10 lines)
- The dogfooding story: "SquidSquad was built by SquidSquad"
- "Browse the `.squidsquad/` folder and git history to see real multi-agent coordination"
- This is a unique credibility signal no competitor can claim
- Link to an interesting commit or planning artifact as proof

#### 10. Requirements (~8 lines)
- Keep existing requirements list
- Add estimated cost note (Claude Code usage) if applicable
- Clean formatting: bullet list

#### 11. Philosophy (~10 lines)
- Condense to 3-4 bullet points:
  - Git Is the Bus (all coordination through git)
  - Complete Audit Trail (every decision in git history)
  - No External Dependencies (just git + Claude Code)
  - Your Team, Your Way (flexible roles, extensible sub-skills)

#### 12. Contributing (~5 lines)
- "We welcome contributions! See CONTRIBUTING.md"
- Highlight sub-skills as the lowest-friction contribution path
- Link to good-first-issue label

#### 13. License (~3 lines)
- AGPL-3.0 badge + brief explanation
- "Free to use, even commercially. Modifications must stay open source if distributed."

### Total Estimated Length: ~155 lines

Down from 366. Less than half the current length, but more impactful. Details move to linked docs.

---

## 4. The Hook

### What Makes Someone Stop Scrolling

1. **Visual of agents running in split terminals** — Shows the product immediately. A GIF of three terminals with agents working simultaneously, with the squid emoji markers scrolling by. This is the #1 thing that will make people stop and look.

2. **"Your AI dev team"** — The word "team" is the hook. Solo devs don't want another tool. They want teammates. Framing SquidSquad as a team (not a framework, not a tool, not a library) is the emotional differentiator.

3. **"Built by its own agents"** — This is the "whoa" moment. Every AI tool claims to work well. SquidSquad can point to its own git history as proof. It's the most credible demo possible.

### The One-Liner

**Primary recommendation:**
> Your AI dev team that coordinates through markdown, not meetings.

This is already in the README and it's excellent. It communicates:
- "Your" — personal, not generic
- "AI dev team" — not a tool, a TEAM
- "markdown, not meetings" — the mechanism AND the anti-pattern it solves

**Alternatives (for badges, tweets, HN title):**
- "Install one skill. Get a dev team." (ultra-short)
- "An AI dev team in your git repo" (location-focused)
- "PM, devs, and QA — all AI, all autonomous, all in your repo" (specificity)
- "Show HN: SquidSquad — An AI dev team that coordinates through markdown, not meetings" (HN format)

**Recommendation**: Keep the current tagline. It's the strongest option.

### Visual Element That Grabs Attention

**Priority order:**

1. **Demo GIF** (highest impact) — 10-15 seconds showing:
   - Split terminal with 3 agents
   - PM printing a check-in
   - Dev agent fixing a bug with squid markers
   - QA verifying the fix
   - Caption: "Three agents, one repo, zero meetings"

2. **Hero screenshot** (medium impact) — Static image of the split terminal view, showing agent output with squid markers.

3. **ASCII art** (low but memorable) — The current squid ASCII. Distinctive, on-brand, zero-friction (no image hosting needed). Keep it regardless of whether a GIF/screenshot is also added.

The ASCII art should stay even if a GIF is added — it appears in terminal when the README is viewed via `cat` and is part of the brand identity.

---

## 5. What to Keep vs Remove from Current README

### Section-by-Section Assessment

| Current Section | Verdict | Rationale |
|----------------|---------|-----------|
| ASCII art + title | **KEEP** | Brand identity, distinctive, works in terminal |
| One-liner tagline | **KEEP** | Perfect hook — don't change it |
| "What It Is" (2 paragraphs) | **REWRITE** | Good content but needs to lead with the problem, not the solution. Restructure as Problem -> Solution |
| Agents table | **KEEP, condense** | Useful but move into "How It Works," trim descriptions |
| Team shapes table | **KEEP** | Excellent — shows flexibility instantly |
| Ralph Loop mermaid | **MOVE** | Too detailed for landing page. Link to it from "How It Works" section, or put in a separate ARCHITECTURE.md |
| Architecture mermaid | **KEEP** | Good high-level view. Keep one diagram on the landing page — this one |
| `.squidsquad/` folder tree | **REMOVE** | 46 lines of directory structure. This is reference docs, not landing page. Move to ARCHITECTURE.md or a wiki |
| Features (16 items) | **CONDENSE** | Pick 6-8 headline features, one line each. The rest become "discover later" in docs |
| Status Line description | **REMOVE from README** | Implementation detail. Mention "live status bar" as a feature bullet |
| Step Markers description | **REMOVE from README** | Implementation detail |
| Working State File | **CONDENSE** | Mention as part of "context pressure management" feature bullet |
| Context Pressure Detection | **CONDENSE** | One bullet: "Agents exit cleanly when context fills, resume from saved state" |
| Cross-Clone Health Detection | **REMOVE** | Operational detail |
| Quiet Cycle Skipping | **REMOVE** | Operational detail |
| Self-Improvement Scanning | **CONDENSE** | One bullet: "Agents proactively find code quality issues during idle time" |
| Iteration Log Retention | **REMOVE** | Operational detail |
| PR-Based Approval Flow | **CONDENSE** | One bullet: "Optional PR workflow for human review" |
| GitHub Issues as Tracker | **KEEP as bullet** | Key feature — "Bugs and features are real GitHub Issues" |
| Designer Agent | **CONDENSE** | One bullet: "Optional designer agent for design-to-code workflows" |
| Subagent Delegation | **REMOVE** | Implementation detail for the landing page |
| Status Bar Chaining | **REMOVE** | Implementation detail |
| Auto Versioning | **REMOVE from features** | Mention briefly in versioning section |
| Vault Memory Layer | **CONDENSE** | One bullet: "Shared knowledge vault — agents learn your preferences over time" |
| Agent Personalities | **CONDENSE** | One bullet: "Distinct agent personalities — PM is diplomatic, QA is skeptical" |
| Externalized Templates | **REMOVE** | Architecture detail |
| VS Code integration | **REMOVE** | Minor feature |
| `/squidsquad-status` | **REMOVE** | Minor feature |
| Philosophy (4 items) | **CONDENSE** | Keep all 4 points but as short bullets, not paragraphs |
| Quick Start | **KEEP, restructure** | Move MUCH higher (after features). Simplify to 4 clear steps. Show bash only, note PowerShell |
| Cross-Team Bug Filing | **REMOVE** | Internal operational detail |
| Requirements | **KEEP** | Essential info, already concise |
| Git Protocol | **REMOVE** | Agent-facing, not user-facing. Move to CONTRIBUTING.md |
| Versioning | **CONDENSE** | Keep upgrade instructions, cut to 3-4 lines |
| License | **KEEP** | Add badge, add brief AGPL explanation for clarity |

### Summary of Content Disposition

- **Keep as-is**: ASCII art, tagline, team shapes table, architecture diagram, requirements, license
- **Keep but rewrite/condense**: What It Is, features, philosophy, Quick Start, versioning
- **Move to separate docs**: Ralph Loop diagram, `.squidsquad/` folder tree, Git Protocol, detailed feature descriptions
- **Remove entirely from public docs**: Cross-Team Bug Filing, Cross-Clone Health Detection, Status Bar Chaining, Externalized Templates, Quiet Cycle Skipping, Iteration Log Retention

### New Content Needed

1. **Demo visual** (GIF or screenshot) — does not exist yet
2. **"The Problem" section** — emotional hook for solo devs
3. **"Built by its own agents" section** — dogfooding story
4. **Contributing section** — invitation to participate
5. **Badges** — version, license, Claude Code compatibility
6. **Comparison or "Why SquidSquad"** — optional but valuable for differentiation

---

## Key Recommendations

1. **The #1 priority is a demo visual.** A GIF of agents running in split terminals will do more for conversion than any amount of text. Without it, the README competes on words alone in a crowded space.

2. **Move Quick Start to position 6 (after features).** Currently at line 248 — most visitors never see it. It should be reachable within 2 scrolls on GitHub.

3. **Cut from 366 to ~155 lines.** Every line that doesn't help someone decide to install is noise on a landing page. Detail moves to ARCHITECTURE.md, CONTRIBUTING.md, or wiki.

4. **Lead with the problem, not the solution.** "You're a solo dev with more ideas than bandwidth" before "SquidSquad is a Claude Code skill that..."

5. **The dogfooding story is the credibility trump card.** No competitor was built by its own agents. Make this prominent — it's the "show, don't tell" proof that the system works.

6. **Keep the tagline.** "Your AI dev team that coordinates through markdown, not meetings" is the strongest single line in the entire project. It should survive every rewrite.

---

## Sources

- Current README.md analysis (366 lines, 11 sections)
- FEAT-SKILL-055-CONTEXT.md (locked decisions: AGPL, v1.0.0, dogfooding, pitch)
- FEAT-SKILL-055-RESEARCH.md (competitive landscape, pitch development, community strategy)
- Analysis of oh-my-claudecode, CrewAI, Aider, AutoGen README patterns
- Open source README best practices (opensource.guide, GitHub documentation)
