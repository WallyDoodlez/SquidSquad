# FEAT-SKILL-037 Discussion Prep

## Q1: Should the PM line 2 health icons move or stay in place when step text is shown?
**Category**: behavior (layout/UX)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Health icons stay right-aligned; step text is left-aligned with a max width, padding fills the gap | No visual jitter — icons never move. Clean separation of dynamic (left) and stable (right) content. Easy to scan health status at a glance since it is always in the same spot. | Step text must be truncated if it exceeds the budget. Requires calculating available width (terminal width minus icon area minus padding). |
| B | Health icons follow immediately after step text, separated by a spacer | Uses space efficiently — short step text leaves no dead whitespace. No truncation needed for short steps. | Icons jump around as step text length changes, creating visual jitter every few seconds. Hard to quickly scan health status since it moves. |
| C | Health icons move to line 1 (right side); line 2 is fully dedicated to step/hint text | Line 2 has full width for step text — generous truncation budget. Health icons on line 1 are always visible and stable. | Changes line 1 layout, which is currently well-defined. May crowd line 1 if role name + iteration + health icons compete for space. Bigger scope change than needed. |

**Recommended**: A — Right-aligned health icons with left-aligned step text and a fixed max width is the standard terminal UI pattern. It eliminates jitter, keeps the layout predictable, and the truncation cost is minimal since step descriptions rarely need more than 50 chars. The research already proposes this layout (`[step/hint] [padding] [health] [rest]`), and the existing statusline already right-aligns the rest nudge, so the pattern is established.

## Q2: Should hints rotate on every statusline refresh or only on cycle boundaries?
**Category**: behavior (timing/UX)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Rotate on cycle boundaries using `(timestamp / (INTERVAL * 60)) % hint_count` | Hints are stable for the full cycle duration (e.g., 5 minutes). Human can actually read them. Matches acceptance criteria ("rotate each cycle"). Low cognitive load. | A hint that is irrelevant to the current moment stays visible for the full cycle. Less dynamic feel. |
| B | Rotate on every statusline refresh (after each assistant message) | Maximum variety — hints change frequently. Always feels "alive." | Hints flash too fast during active work (multiple messages per second). Unreadable. Distracting. Defeats the purpose of hints as ambient guidance. |
| C | Rotate on a fixed sub-cycle interval (e.g., every 60 seconds) using `(timestamp / 60) % hint_count` | More frequent rotation than full cycles but still readable. Feels responsive without being distracting. Decoupled from cycle length — works the same whether cycles are 3 or 10 minutes. | Adds a second timing constant to configure/maintain. Does not match the "rotate each cycle" wording in acceptance criteria. Slightly more complex than option A. |

**Recommended**: A — Cycle-boundary rotation is the simplest, matches the acceptance criteria language, and ensures hints are stable long enough to be useful. Hints are ambient background text, not a live feed. If the cycle interval is 5 minutes, seeing the same hint for 5 minutes is fine — the human is focused on their own work, not watching the status bar. Option C is a reasonable fallback if cycle intervals grow very long (15+ minutes), but at current intervals (3-5 min) option A is ideal.

## Q3: What is the maximum character width for step descriptions before truncation?
**Category**: scope (layout sizing)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Fixed 50-character max for step text on all line 2 variants | Simple to implement — one constant. Works for most terminals (80+ cols). Leaves ~25-30 chars for health icons + rest nudge on PM line 2. Dev line 2 (no health icons) gets extra breathing room. | Wastes space on wide terminals. PM line 2 with 3+ agent health icons could get tight at exactly 80 cols. |
| B | Dynamic width: `terminal_width - health_icon_width - rest_nudge_width - padding` | Uses all available space. Adapts to terminal size. No wasted space. | Requires `tput cols` or `$COLUMNS` in statusline — adds complexity. Health icon width varies with agent count. More logic, more edge cases, harder to test. |
| C | Fixed 40-character max for PM, fixed 60-character max for dev agents | Tailored to each role's line 2 content. PM gets a conservative budget that safely accommodates health icons. Dev agents get a generous budget since their line 2 is simpler. | Two constants instead of one. Must remember to update if PM line 2 layout changes. Slightly more complex. |

**Recommended**: C — Role-specific fixed widths are the best balance of simplicity and correctness. PM line 2 carries more content (health icons, rest nudge) so it needs a tighter budget. Dev line 2 is simpler and can afford more space. Fixed values avoid the complexity of dynamic terminal width detection while still being tuned per role. The values (40 for PM, 60 for dev) can be defined as constants at the top of statusline.sh.

## Q4: Should the DM role (FEAT-SKILL-035) get its own hint pool now or later?
**Category**: scope (timing/dependencies)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Create `references/hints-dm.txt` now with placeholder/generic hints | One upgrade cycle handles everything. No future churn. File exists and the system works end-to-end for DM from day one. | DM role is not approved yet — hints would be speculative. If DM design changes, hints need rewriting. Shipping unused content adds noise to the repo. |
| B | Defer entirely until DM ships (FEAT-SKILL-035 is approved and implemented) | No speculative work. Hints are written with full knowledge of DM steps and behavior. Clean separation of concerns. | Requires a second upgrade cycle when DM ships. If forgotten, DM launches without hints (falls back to empty line 2 — acceptable but not ideal). |
| C | Create the empty file structure now (`references/hints-dm.txt` with only comments explaining the format) but no actual hints | Establishes the pattern so the DM implementer knows exactly where to add hints. Zero speculative content. Trivial to fill in later. | Still ships an empty file that does nothing. Marginal value over option B — the format is documented in the research file and in the other hint pool files. |

**Recommended**: B — Defer until DM ships. The research file already notes this recommendation and the reasoning is sound: DM steps are not defined yet, so any hints written now would be guesses. The fallback behavior (no hint file = no hints on line 2) is graceful and acceptable. When FEAT-SKILL-035 ships, adding `hints-dm.txt` is a trivial one-file addition. No reason to create speculative content.

## Q5: Should current-state files be cleared when the boot script starts (before the agent launches)?
**Category**: compatibility (startup/crash recovery)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Add `rm -f .squidsquad/$ROLE/current-state` to each boot script (`start-*.sh`) before launching the agent | Clean slate on every boot. No stale state from a previous crash is ever shown. Simple one-liner. Boot scripts are the natural place for cleanup. | If boot script itself fails after clearing the file but before the agent starts, line 2 is blank (acceptable — same as pre-feature behavior). |
| B | Do not clear on boot; rely on staleness detection in statusline.sh | Less code — no boot script changes needed. Staleness detection already handles this case (stale timestamp = fall through to hints). | Brief window between boot and first agent step where stale state from a crash is visible. Staleness threshold (e.g., 2x interval = 10 min) could mean the stale step shows for several minutes before expiring. |
| C | Agent writes an "initializing" state as its very first action, before Step 1 | Stale state is overwritten immediately when the agent starts. Line 2 shows "Initializing..." which is informative. No boot script changes needed. | Depends on the agent template being correct — if the agent crashes before this write, stale state persists. Does not handle the case where the boot script fails before the agent even starts. |

**Recommended**: A — Clearing in the boot script is the safest and simplest approach. It is a single `rm -f` line, it runs before the agent process starts, and it guarantees no stale state survives a restart regardless of how the previous instance died. Option C is a nice complement (showing "Initializing..." is informative), but it should not replace the boot script cleanup. Consider doing both A and C together: boot script clears the file, then the agent's first action writes an initializing state.
