# FEAT-149 Context — Extract SOUL.md as Runtime-Injectable Files

## Scope

Extract agent souls from compile-time inclusion in CLAUDE.md to runtime-injectable `.squidsquad/[role]/SOUL.md` files. Agents read their soul at session start. Humans can customize agent personality by editing SOUL.md directly without redeploying templates.

**Delivers:**
1. `{{runtime:}}` directive in compose.py — emits "Read SOUL.md" instruction instead of inlining soul content
2. `.squidsquad/[role]/SOUL.md` files per installed role — created from default templates during deploy
3. Default soul templates shipped with each role sub-skill (`references/sub-skills/souls/`)
4. Updated role entry files using `{{runtime: souls/[role]}}` instead of `{{include: souls/[role]}}`
5. Setup/upgrade flow creates SOUL.md from defaults if missing

## Locked Decisions (human decided)

- **{{runtime:}} directive**: compose.py gets a new directive type. `{{runtime: souls/dev}}` emits a "Read .squidsquad/skill/SOUL.md and follow its instructions" block into CLAUDE.md instead of inlining the content. Why: clean separation of personality from template.

- **Every role ships a default SOUL.md**: Each role sub-skill includes a default soul template. The sub-skill directory website will also require this — every listed sub-skill must include a default SOUL.md. Why: agents must always have a personality, even on fresh installs.

- **Deploy creates if missing, never overwrites**: `compose.py deploy [role]` copies the default soul template to `.squidsquad/[role]/SOUL.md` only if the file doesn't exist. Human customizations are preserved across deploys. Why: customization is the whole point — overwriting defeats it.

- **Git-tracked**: SOUL.md is committed to the repo. Team members share the same agent personality. Changes are visible in PRs. Why: consistency across the team. Personal overrides can be added later via a `.local` pattern if needed.

- **Read once at session start**: Agent reads SOUL.md when it boots, not every cycle. Changes require agent restart. Why: ~800 tokens read once is negligible; reading every 30 min cycle is wasteful for content that rarely changes. Matches coleam00 SOUL.md pattern.

## Dev Discretion (dev agent can choose)

- Exact format of the {{runtime:}} directive output (the "Read SOUL.md" instruction text)
- How compose.py detects and processes {{runtime:}} vs {{include:}} directives
- Whether to add a compose.py soul subcommand for standalone soul management
- SOUL.md file format (keep existing markdown structure or add frontmatter)
- Error handling when SOUL.md is missing at boot (fallback to inline default?)

## Side Effect Mitigations (required)

- **Missing SOUL.md**: If SOUL.md doesn't exist at boot, CLAUDE.md's runtime instruction should include a fallback: "If SOUL.md is missing, use these defaults: [abbreviated personality]." This prevents personality-less agents.
- **Transition period**: Existing CLAUDE.md files have inline souls. After deploy, they'll have runtime instructions instead. The soul content moves to SOUL.md. Old CLAUDE.md files continue to work until redeployed.
- **compose.py deploy must create SOUL.md**: If deploy generates a CLAUDE.md with {{runtime:}} but doesn't create SOUL.md, the agent has no personality. Deploy MUST create SOUL.md if missing.
- **Manifest update**: Update manifest.md to note that soul sub-skills are now runtime-injected, not compile-time included.

## Upgrade Path (required)

- **New files**: `.squidsquad/[role]/SOUL.md` per installed role
- **Modified files**: role entry files (replace {{include:}} with {{runtime:}}), compose.py (add {{runtime:}} handler), manifest.md
- **Regenerate**: `compose.py deploy` for all roles after upgrade
- **Idempotent**: SOUL.md created from default if missing, never overwritten
- **Graceful degradation**: Non-upgraded installs keep inline souls in CLAUDE.md. No breakage.

## Out of Scope

- Per-user .local override files (future enhancement)
- SOUL.md editor UI (future)
- Dynamic personality switching mid-session
- Sub-skill directory website SOUL.md requirements (separate project)
