# New Project Setup — SquidSquad Skill Marketplace

Hey Claude, I want to start a new project and use SquidSquad to help me build it.

## The Project

I'm building a **skill marketplace** for SquidSquad — a website where people can browse, search, and discover community-created sub-skills for SquidSquad. Think of it like a plugin directory. Sub-skills live in their own GitHub repos, and this site is the public catalog.

Eventually this becomes the monetization layer too — featured listings, verified badges, premium sub-skills. But start with the core browsing experience.

## What I Need You To Do

1. Create a new GitHub repo called `squidsquad-market` under my account (WallyDoodlez). Public repo.

2. Install the SquidSquad skill from `github.com/WallyDoodlez/SquidSquad`. Follow the installation docs in that repo's SKILL.md — it explains how to set up SquidSquad on a new project.

3. Run through the setup flow. Here's what I want:
   - Project name: squidsquad-market
   - One dev agent: `skill` (full-stack)
   - Default aliases
   - 30 minute cycles
   - No E2E tests yet

4. Seed these as initial features to build:

   **Core (build first)**
   - **Browse skills**: landing page with a grid/list of available sub-skills. Each card shows: name, description, author, install count, tags, compatibility
   - **Skill detail page**: full README rendered, install instructions (`claude install-skill <repo-url>`), compatibility info, version history, author profile link
   - **Search and filter**: search by name/description, filter by tags (dev, qa, pm, designer, dm), filter by compatibility (SquidSquad version)
   - **Submit your skill**: form to register a new sub-skill. Provide GitHub repo URL, the site pulls metadata (README, SKILL.md frontmatter, tags). Requires GitHub OAuth.

   **Auth**
   - **GitHub OAuth**: sign in with GitHub. Required for submitting skills. Profile shows your published skills.

   **Monetization (build after core)**
   - **Featured listings**: paid placement at the top of browse/search results
   - **Verified badge**: paid certification that the sub-skill meets quality/security standards
   - **Premium sub-skills**: authors can set a price, marketplace handles payment (Stripe)

5. For tech stack — I want the agents to discuss and recommend something. Include it as an open question during the planning phase. My only requirement is it should be modern, deployable to Vercel or similar, and the agents should be able to build it autonomously.

6. Boot the agents and let them start building.

## Important

- Follow the SquidSquad docs in the repo, don't make up how it works
- If anything in the setup is confusing or breaks, note it — those are bugs I need to fix in SquidSquad itself
- This is also a test of the SquidSquad setup experience, so be honest about friction points
- The agents should plan features properly (research, discussion, test plan) before implementing — that's how SquidSquad works
