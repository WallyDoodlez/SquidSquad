# FEAT-SKILL-055 — Phase 2 Prep: Open Questions Analysis

**Feature**: Proposal: take SquidSquad public as a community-driven skill
**Prepared by**: analysis-agent
**Date**: 2026-04-02
**Source**: FEAT-SKILL-055-RESEARCH.md, Section "Key Open Questions for Human Decision"

---

## Optimal Question Order

Questions are reordered by dependency (upstream decisions first, controversial/preference-based last):

| Order | Question | Rationale for Position |
|-------|----------|----------------------|
| 1 | Q3: Example project | Upstream dependency: chosen project affects test timeline, README content, and launch readiness |
| 2 | Q2: `.squidsquad/` in gitignore | Must be decided before cleanup work begins; blocks repo cleanup PR |
| 3 | Q5: Community sub-skill format | Architectural decision that affects CONTRIBUTING.md, README, and marketplace strategy |
| 4 | Q1: Version number | Depends on Q3 (test results) and Q5 (format stability); easy to decide late |
| 5 | Q6: README rewrite scope | Already scoped to FEAT-SKILL-056; low controversy, can proceed in parallel |
| 6 | Q4: Discord server | Pure preference, no dependencies, easily reversible |

---

## Question Analysis

---

### Q3: Example Project (Category: Strategy / Content)

> What project to use for the "test on another project first" phase? This becomes the showcase.

#### Option A: Purpose-built demo project (e.g., a CLI tool or small API)
**Recommended**

| Pros | Cons |
|------|------|
| Fully controlled scope -- can ensure it exercises all SquidSquad features (bugs, features, QA, vault) | Feels artificial; skeptics may dismiss it as cherry-picked |
| Can be completed quickly (days, not weeks) | Requires effort to create something believable |
| Clean git history from day one -- perfect showcase | Does not prove SquidSquad works on "real" codebases |

#### Option B: Existing personal/side project

| Pros | Cons |
|------|------|
| Proves SquidSquad works on real, messy codebases | May contain private code, secrets, or embarrassing history |
| Zero effort to create the project itself | Scope may be too large or too niche to serve as a universal showcase |
| Authenticity -- community respects real usage | Git history may be confusing to newcomers browsing the example |

#### Option C: Community-familiar project type (e.g., fork of a TODO MVC, contribute to an existing OSS repo)

| Pros | Cons |
|------|------|
| Immediately recognizable domain -- low cognitive load for new users | Overdone; "yet another TODO app" may not excite anyone |
| Easy for others to replicate and compare | May not exercise SquidSquad's unique strengths (multi-agent coordination, vault) |
| Can link to the well-known original for context | Fork licensing may create complications |

**Recommendation: Option A.** Build a small but real CLI tool or API server from scratch using SquidSquad. This gives full control over the showcase narrative, exercises all agent roles, and produces a clean git history that demonstrates the value proposition. Keep it small enough to complete in 2-3 days.

---

### Q2: `.squidsquad/` in This Repo's `.gitignore` (Category: Repo Architecture)

> Should the SquidSquad repo itself gitignore `.squidsquad/` (clean public face) or keep it tracked (dogfooding evidence)?

#### Option A: Remove from tracking, add to `.gitignore`
**Recommended**

| Pros | Cons |
|------|------|
| Clean public face -- new users see exactly what they will get | Loses the live dogfooding evidence in the working tree |
| No confusion about "is this my data or the project's?" | Developers working on SquidSquad itself need to un-ignore locally |
| Signals the correct pattern for consumer repos | History is still in git log, but harder to browse casually |

#### Option B: Keep tracked, add clear documentation

| Pros | Cons |
|------|------|
| Dogfooding evidence is front and center | Confusing for new users -- "why is there stale tracker data here?" |
| Contributors can see real-world agent coordination artifacts | Merge conflicts when multiple contributors have different tracker state |
| No special local config needed for SquidSquad development | Sends the wrong signal about whether `.squidsquad/` should be committed |

#### Option C: Hybrid -- gitignore everything except a `_example/` snapshot

| Pros | Cons |
|------|------|
| Clean working tree + browsable example of the structure | Maintenance burden -- example can go stale |
| Best of both worlds for onboarding | Extra directory to explain in docs |
| New users can see the folder structure without running setup | May confuse agents that scan for `.squidsquad/` contents |

**Recommendation: Option A.** Remove from tracking and gitignore. The git history preserves all dogfooding evidence (link to interesting commits in README). The example project (Q3) serves as the live demonstration. For SquidSquad development itself, developers can use `git update-index --assume-unchanged` or a local `.git/info/exclude` override.

---

### Q5: Community Sub-skill Format (Category: Architecture / Standards)

> Finalize before launch or iterate after feedback?

#### Option A: Ship a minimal spec, iterate after feedback
**Recommended**

| Pros | Cons |
|------|------|
| Faster to launch -- avoids analysis paralysis on format details | Early adopters may build sub-skills that break when the format changes |
| Real community feedback produces better design than guessing | Creates migration pain if format changes significantly |
| Signals openness to community input | May appear unfinished or amateurish to framework-savvy developers |

#### Option B: Finalize a complete spec before launch

| Pros | Cons |
|------|------|
| Stable contract from day one -- early adopters trust it | Delays launch for a feature that may see zero community usage initially |
| No migration pain for early sub-skill authors | Design in a vacuum tends to over-engineer or miss real needs |
| Professional impression -- "they thought this through" | Opportunity cost -- time spent on spec is time not spent on core stability |

#### Option C: Launch without community sub-skill support, add later

| Pros | Cons |
|------|------|
| Simplest launch -- fewer docs, fewer edge cases | Misses the key differentiator (extensibility) |
| Can observe what people actually want before building | Contributors who want to extend SquidSquad have no path forward |
| No format stability concerns | May lose early enthusiasts who want to contribute |

**Recommendation: Option A.** Ship a minimal spec (manifest fields, composition point, file naming convention) with a "v0 -- subject to change" label. Seed 2-3 example sub-skills to demonstrate the pattern. Iterate based on real feedback. The sub-skill architecture (FEAT-SKILL-030) already exists internally; exposing it with a "beta" label is low risk.

---

### Q1: Version Number for Public Launch (Category: Marketing / Signaling)

> Ship as v0.8.0 (current) or bump to v1.0.0?

#### Option A: Launch as v0.9.0, promote to v1.0.0 after community stabilization

| Pros | Cons |
|------|------|
| Honest signal: "working but still maturing" | Sub-1.0 may deter risk-averse adopters |
| Sets expectation that breaking changes are possible | Extra version bump ceremony later |
| The "road to 1.0" narrative can drive community engagement | Semantic versioning purists may nitpick |

#### Option B: Launch as v1.0.0
**Recommended**

| Pros | Cons |
|------|------|
| Strong signal of confidence and readiness | Sets high expectations -- any rough edges feel like broken promises |
| More likely to attract attention (people notice 1.0 launches) | Harder to justify breaking changes post-1.0 under semver |
| "Built by its own agents" narrative supports the maturity claim | If the test-on-another-project phase reveals major issues, 1.0 feels premature |

#### Option C: Stay at v0.8.0

| Pros | Cons |
|------|------|
| No version ceremony needed -- just flip the repo to public | Feels like an afterthought, not a launch |
| Accurately reflects current state | No news hook -- "project goes public at v0.8" is not exciting |
| Simplest option | Misses the marketing opportunity of a version milestone |

**Recommendation: Option B, conditional on Q3.** If the test-on-another-project phase succeeds cleanly, launch as v1.0.0. The dogfooding history and successful external test justify the confidence signal. If the test reveals significant issues, fall back to Option A (v0.9.0) and use the 1.0 milestone as a community goal.

---

### Q6: README Rewrite Scope (Category: Content / Design)

> How much of the current README structure to keep vs redesign from scratch?

#### Option A: Full redesign from scratch
**Recommended**

| Pros | Cons |
|------|------|
| Clean slate optimized for the public audience (not internal devs) | More work; risk of losing useful content that existed in the old version |
| Can follow best practices from high-star repos (hero section, GIF, quick start, why section) | Requires strong copywriting to match the elevator pitch quality in the research |
| No legacy structure constraining the layout | Must be careful not to lose SEO-relevant keywords from old README |

#### Option B: Restructure and rewrite in place

| Pros | Cons |
|------|------|
| Preserves any content that is already good | Old structure may constrain new thinking |
| Less work -- edit rather than recreate | Risk of Frankenstein README -- half old, half new |
| Git diff shows exactly what changed | May carry forward internal-facing language or assumptions |

#### Option C: Keep current structure, polish language only

| Pros | Cons |
|------|------|
| Minimal effort | Current README is written for internal development, not public adoption |
| Low risk of regression | Misses the opportunity to create a compelling landing page |
| Quick to execute | Does not address the fundamental audience shift |

**Recommendation: Option A.** The current README serves internal development. The public README needs to be a landing page: hero section, elevator pitch, demo GIF placeholder, quick start, "why SquidSquad" section, comparison table, contributing link. Write from scratch using the research's pitch material as the foundation. FEAT-SKILL-056 already scopes this work.

---

### Q4: Discord Server (Category: Community / Infrastructure)

> Create before launch or wait to see demand?

#### Option A: Create before launch, link from README

| Pros | Cons |
|------|------|
| Ready for the first wave -- enthusiasts who want to chat can find the community immediately | Empty Discord is worse than no Discord -- creates a ghost town impression |
| Shows commitment to community building | Moderation overhead from day one |
| Captures early adopters who prefer real-time chat over GitHub Issues | Splits conversation between Discord and GitHub Discussions |

#### Option B: Wait for demand, create when GitHub Discussions get active
**Recommended**

| Pros | Cons |
|------|------|
| Avoids empty server problem | Misses early adopters who prefer Discord over GitHub |
| GitHub Discussions are sufficient for initial community size | Creating Discord reactively means scrambling during a growth spike |
| Lower maintenance burden at launch | No real-time community presence |

#### Option C: Use an existing community Discord (e.g., Claude Code community) instead of creating a dedicated one

| Pros | Cons |
|------|------|
| Instant audience -- people are already there | No control over the space; dependent on someone else's server |
| Zero maintenance | SquidSquad discussions get lost in general noise |
| Cross-pollination with Claude Code users | Cannot customize channels, roles, or bots for SquidSquad workflows |

**Recommendation: Option B.** Launch with GitHub Discussions only. Monitor engagement. If Discussions consistently get 5+ active threads per week or users explicitly ask for Discord, create it then. A Discord link can be added to README at any time -- there is no advantage to having it on day one if nobody is in it.

---

## Summary Table

| # | Question | Category | Recommended Option | Confidence |
|---|----------|----------|-------------------|------------|
| 1 | Example project | Strategy | A: Purpose-built demo project | High |
| 2 | `.squidsquad/` gitignore | Repo Architecture | A: Remove from tracking | High |
| 3 | Community sub-skill format | Architecture | A: Minimal spec, iterate | High |
| 4 | Version number | Marketing | B: v1.0.0 (conditional on test success) | Medium |
| 5 | README rewrite scope | Content | A: Full redesign | High |
| 6 | Discord server | Community | B: Wait for demand | Medium |
