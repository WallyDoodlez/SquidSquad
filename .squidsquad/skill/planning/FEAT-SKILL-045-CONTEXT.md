# FEAT-SKILL-045 Context — Overdue Emoji

## Scope
Add an overdue emoji indicator to the statusline countdown timer area. When an agent's current Ralph Loop cycle has been running longer than the configured iteration interval (default 30 minutes), an emoji appears next to the timer. This is a statusline.sh-only change — no agent template or loop logic changes required.

## Locked Decisions (human decided)
- **All agents**: applies to PM, dev, and future DM/QA — every role that uses the statusline
- **Position**: overdue emoji appears at/near the countdown timer in the statusline
- **Trigger**: immediately when elapsed time exceeds the iteration interval (no grace period)
- **No indicator when not overdue**: clean default state — nothing extra shown when within interval

## Dev Discretion (dev agent can choose)
- Which emoji to use for the overdue indicator (e.g. hourglass, warning, alarm clock)
- Exact placement relative to the timer string (prepend, append, or replace the timer emoji)
- Whether to use color/ANSI formatting on the overdue indicator
- Whether the overdue state changes the existing timer text (e.g. show "+Nm" overage) or only adds the emoji

## Side Effect Mitigations (required)
- statusline.sh must not break when elapsed time exactly equals the interval (boundary condition)
- The overdue emoji must not shift or break the layout of other statusline segments (git sync, context, work status)
- PM statusline and dev statusline both include `TIMER_STR` in their output — the fix must apply to the shared timer computation section, not duplicated per-role
- Timer string length increase (from added emoji) must not cause line wrapping on typical terminal widths (>=80 cols)

## Upgrade Path (required)
- N/A — statusline.sh-only change. The script is copied from `references/statusline.sh` to `.squidsquad/statusline.sh` during setup and by dev agents after edits. Existing installs get the update when the dev agent copies the file in Step 3.9 of the Ralph Loop. No agent template changes needed.

## Out of Scope
- Grace period or configurable delay before showing overdue
- Configurable overdue emoji via config.md
- Notifications, alerts, or any action beyond a visual indicator
- Changes to agent loop timing or behavior when overdue
- Overdue indicator on line 2 (hint/status line) — this is line 1 only
