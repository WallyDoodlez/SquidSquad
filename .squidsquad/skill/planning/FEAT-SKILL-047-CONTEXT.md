# FEAT-SKILL-047 Context — Cross-Clone Health Detection + Guided Agent Setup

## Scope
Replace heartbeat branches with direct cross-clone file reads for real-time health detection. Add guided setup flow that clones repos and launches agents. Store agent paths in gitignored `.local-config`.

## Locked Decisions (human decided)
- **No GitHub API for health**: Don't consume user's API rate limit for status checks
- **Cross-clone file reads**: Read other agents' `current-state` files directly via absolute path
- **`.local-config` gitignored**: Paths are machine-specific, can't go in repo (multiple users may share same repo)
- **Guided setup**: Setup asks for path, clones repo, opens terminal, runs boot script — one flow
- **Health icons**: 🦑 healthy, 👻 stalled, ❓ unknown (replaces 🥚)
- **Stale threshold**: 2x iteration interval
- **Philosophy**: GitHub is the bus for all content/audit trail. Local file reads are the one exception for real-time operational status.

## Dev Discretion (dev agent can choose)
- `.local-config` file format (markdown like config.md, or simpler key=value)
- How to open a new terminal cross-platform (PowerShell `Start-Process`, bash `gnome-terminal`/`open -a Terminal`, etc.)
- Default clone path suggestion logic (e.g. sibling directory `../SquidSquad-<role>`)
- How statusline parses `.local-config` to get paths
- Whether PM also writes its own path to `.local-config` on boot (so other agents can find PM)

## Side Effect Mitigations (required)
- `.local-config` must be in `.gitignore` — never committed
- If `.local-config` is missing or a path is unreachable, show ❓ — don't crash or error
- Remove heartbeat.sh from both `references/` and `.squidsquad/`
- Remove `Heartbeat Interval Seconds` from config.md template
- Clean up remote heartbeat branches during upgrade (`git push origin --delete heartbeat/<role>`)
- Boot scripts must stop launching heartbeat background process

## Upgrade Path (required)
- Remove heartbeat.sh
- Regenerate boot scripts (no heartbeat launch)
- Remove Heartbeat Interval Seconds from config.md
- Delete remote heartbeat branches
- Regenerate statusline.sh (read .local-config instead of git fetch)
- User must manually create `.local-config` with agent paths (upgrade can prompt)

## Out of Scope
- GitHub API commit statuses (replaced by local file reads)
- Cross-machine health detection (local file reads are same-machine only — cross-machine is a future enhancement)
- Changing how agents communicate content (still via git)
