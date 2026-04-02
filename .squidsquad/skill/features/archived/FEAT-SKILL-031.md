## FEAT-SKILL-031 — Status bar redesign (Emoji Rich style)

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: Redesign the status bar (`statusline.sh`) with an emoji-rich visual style. Replaces the current ANSI-only design with expressive emoji indicators. PM gets a two-line bar with team health and optional rest nudge on a separate line.

  **PM — all healthy, mid-planning, normal hours:**
  ```
  🦑 PM/QA v0.5.1 │ 📦 9/10 🚀 │ 📋 FEAT-017 P2 │ 🧠 [green]42%[/green] │ 🔄 2m
    🦑🦑🦑
  ```

  **PM — one stalled, no planning, late night (10pm-12am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 5/10 │ 🧠🔥 [yellow]62%[/yellow] │ 🔄 3m
    🦑🦑👻                                    🌙 late
  ```

  **PM — one never started, high context, very late (12am-2am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 7/10 │ 🧠💀 [red]85%[/red] │ 🔜 <1m
    🦑👻🥚                                    😴 rest?
  ```

  **PM — behind remote, bump ready, should be in bed (2am-6am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 10/10 🚀 │ ↓3 │ 🧠 [green]38%[/green] │ 🔄 4m
    🦑🦑                                      🛏️ sleep!
  ```

  **Dev — idle, bugs + features:**
  ```
  🦑 skill v0.5.1 │ 🐛3 ⭐2 │ 🧠 [green]25%[/green] │ 🔄 4m
  ```

  **Dev — working on feature:**
  ```
  🦑 skill v0.5.1 │ 🔨 FEAT-017 │ 🧠 [green]31%[/green] │ 🔄 3m
  ```

  **Dev — fixing bug, unpushed, caution context:**
  ```
  🦑 fe v0.5.1 │ ↑2 │ 🔨 BUG-FE-004 │ 🧠🔥 [yellow]68%[/yellow] │ 🔄 2m
  ```

  **Dev — danger context, cycle imminent:**
  ```
  🦑 skill v0.5.1 │ 🔨 FEAT-031 │ 🧠💀 [red]91%[/red] │ 🔜 <1m
  ```

  **Dev — backlog clear:**
  ```
  🦑 be v0.5.1 │ ✅ clear │ 🧠 [green]12%[/green] │ 🔄 5m
  ```

  **Locked design decisions:**
  - **Style**: Emoji Rich — emoji for all indicators, ANSI colors used for context percentage text
  - **Ship counter**: 📦 N/threshold shown on PM bar. 🚀 appears when counter >= 9 (one away from bump)
  - **Context display**: Brain emoji always shown. Stacked indicator emoji at higher tiers. Percentage text is ANSI-colored:
    - 🧠 `\033[32mNN%\033[0m` — <50% (green text)
    - 🧠🔥 `\033[33mNN%\033[0m` — 50-74% (yellow text)
    - 🧠💀 `\033[31mNN%\033[0m` — 75%+ (red text)
  - **Agent health**: 🦑 healthy, 👻 stalled (was alive, now gone), 🥚 never started — displayed on PM's **second line** as a row of icons (no agent names). User digs in if they see a 👻 or 🥚
  - **Rest nudge**: Right-aligned on PM line 2, time-based: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am). Hidden 6am-10pm
  - **Active task**: 🔨 FEAT-XXX or BUG-XXX shown on dev bar when working-state has an in-progress task, replaces backlog counts
  - **Version**: shown after role name, always present
  - **Ship counter position**: 📦 is position 2 (right after identity), before planning phase
  - **Git sync**: ↑N (unpushed) / ↓N (behind remote) — only shown when out of sync, hidden when clean
  - **Planning phase**: 📋 FEAT-XXX PN — shown on PM bar only during active feature intake, hidden otherwise
  - **Timer**: 🔄 Nm for normal countdown, 🔜 <1m when under 1 minute (replaces ⏳)
  - **Dropped**: iteration number (low value), "time since last" (replaced by countdown only)
  - **Emoji key** (for reference in docs):
    - 🦑 = SquidSquad brand + healthy agent
    - 👻 = stalled agent (was alive, now gone)
    - 🥚 = agent never started
    - 📦 = ship counter
    - 🚀 = version bump imminent
    - 🐛 = open bugs
    - ⭐ = actionable features
    - 🔨 = active task
    - 🧠 = context (always shown)
    - 🔥 = context caution (50-74%, stacked with 🧠)
    - 💀 = context danger (75%+, stacked with 🧠)
    - green/yellow/red ANSI = context percentage text color
    - 🔄 = next cycle countdown (normal)
    - 🔜 = next cycle imminent (<1m)
    - 📋 = planning phase in progress (PM only)
    - ↑N/↓N = git sync status (only when out of sync)
    - 🌙 = late night nudge (10pm-12am)
    - 😴 = rest nudge (12am-2am)
    - 🛏️ = sleep nudge (2am-6am)
    - ✅ = backlog clear (dev only)

- **Acceptance Criteria**:
  - [ ] `statusline.sh` rewritten with emoji-rich output matching the design above
  - [ ] PM bar outputs two lines: main info + team health (🦑/👻/🥚 icons, no names)
  - [ ] Rest nudge right-aligned on PM line 2: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am), hidden otherwise
  - [ ] Dev bar shows active task (from working-state.md) when in-progress, backlog counts otherwise
  - [ ] Ship counter reads from config.md `Shipped Since Last Bump` and `Ship Threshold`
  - [ ] 🚀 appears when ship counter >= threshold - 1
  - [ ] Context: 🧠 always shown, 🔥 stacked at 50-74%, 💀 stacked at 75%+
  - [ ] Context percentage text colored: green <50%, yellow 50-74%, red 75%+
  - [ ] Version read from config.md
  - [ ] Timer: 🔄 Nm for countdown, switches to 🔜 <1m when under 1 minute
  - [ ] Git sync: ↑N/↓N shown only when out of sync with remote
  - [ ] Planning phase: 📋 FEAT-XXX PN shown on PM bar during active intake
  - [ ] Ship counter at position 2 (after identity, before planning/git sync)
  - [ ] Iteration number removed from display
  - [ ] SKILL.md status bar documentation updated
  - [ ] README status bar section updated with new examples

### Discussion

> [2026-03-29 03:20] **pm/qa**: Filed with full design locked by human. Style: Emoji Rich. Key decisions: PM gets two-line bar with team health on line 2, ship counter with 🚀 at 9+, three-tier context emoji (🧠/⚠️/🔥), active task display replaces backlog when working, version always shown, iteration number dropped, timer condensed to countdown only. Status: Pending — awaiting human approval.
> [2026-03-29 03:30] **pm/qa**: Design refinement — context display updated: 🧠 always shown, 🔥 stacked at 50-74% (caution), 💀 stacked at 75%+ (danger). Percentage text ANSI-colored: green <50%, yellow 50-74%, red 75%+. Locked, not yet approved.
> [2026-03-29 03:40] **pm/qa**: Design refinement batch — added: git sync (↑N/↓N, hidden when clean), planning phase (📋 FEAT-XXX PN on PM bar), timer changed to 🔄 with 🔜 <1m when imminent, ship counter moved to position 2. All locked, not yet approved.
> [2026-03-29 04:00] **pm/qa**: Final design refinements — agent health: 🦑 healthy, 👻 stalled, 🥚 never started (no names, just icons). Rest nudge on PM line 2: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am). ✅ clear for empty dev backlog. Human approved. Status → Approved.
> [2026-03-29 04:05] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 04:15] **skill-lead**: Complete. Full rewrite of statusline.sh in SKILL.md with Emoji Rich design. PM two-line output with team health + rest nudge. Dev shows active task/backlog/clear. Ship counter, planning phase, git sync, context tiers, countdown timer all implemented. SKILL.md docs, README status line section, CHANGELOG updated. Status → Pending Test.
> [2026-03-29 04:20] **pm/qa**: QA verified — all acceptance criteria pass. Full Emoji Rich script in SKILL.md, PM two-line with 🦑/👻/🥚 health + rest nudge, dev shows 🔨/🐛⭐/✅, ship counter pos 2 with 🚀, 📋 planning phase, ↑↓ git sync, 🧠🔥💀 context tiers with ANSI colors, 🔄/🔜 timer. README and SKILL.md docs updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
