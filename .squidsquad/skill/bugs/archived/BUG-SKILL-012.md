## BUG-SKILL-012 — Step markers inconsistent and not visually distinct enough

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Two issues with the `[squidsquad]` step markers from FEAT-SKILL-008:

  1. **Not all actions are prefixed** — Some PM and dev actions (filing bugs, updating trackers, research spawning, discussion questions) happen without a marker. Every SquidSquad action should have one.

  2. **Not visually distinct** — Plain `[squidsquad]` text blends in with normal Claude output. The markers should use ANSI styling to stand out:
     - Replace `[squidsquad]` with `[🦑]`
     - Background: pink/magenta (`\033[45m`)
     - Foreground: black (`\033[30m`)
     - Reset after the prefix

  **Example output:**
  ```
  \033[45m\033[30m[🦑]\033[0m Pulling latest...
  \033[45m\033[30m[🦑]\033[0m Triaging bugs...
  \033[45m\033[30m[🦑]\033[0m Filing BUG-SKILL-012...
  ```

  The ANSI styling makes SquidSquad actions immediately scannable in scrollback — pink background with squid emoji is unmistakable.

- **Steps to Reproduce**:
  1. Run any SquidSquad agent
  2. Observe some actions have `[squidsquad]` prefix, others don't
  3. The prefixed ones blend in with normal text
- **Expected**: Every SquidSquad action prefixed with `[🦑]` in pink background / black foreground ANSI
- **Actual**: Inconsistent prefixing, plain text styling

### Discussion

> [2026-03-28 05:30] **pm/qa**: Reported by human. The markers need to be both complete (every action) and visually outstanding (ANSI pink bg + black fg + squid emoji). Shortening to `[🦑]` also saves horizontal space.
> [2026-03-28 05:58] **skill-lead**: Fixed. Replaced all `[squidsquad]` markers with ANSI-styled `\033[45m\033[30m[🦑]\033[0m` across: agent-instructions.md (both dev and PM templates), skill/CLAUDE.md, pm/CLAUDE.md, SKILL.md, and README.md. All step markers and sub-action markers now use the styled format. Status → Fixed.
> [2026-03-28 06:25] **pm/qa**: Verified. ANSI-styled markers confirmed: agent-instructions.md (38), skill/CLAUDE.md (10), pm/CLAUDE.md (16), SKILL.md (2). No old-style `[squidsquad]` markers remain in any file. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
