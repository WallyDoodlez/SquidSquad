# FEAT-SKILL-021 Research — Status Bar Append (Last Line Only)

## Executive Summary

SquidSquad's setup completely replaces the user's `statusLine` config. The user wants SquidSquad info on the **last line only**, preserving their existing status bar above. Three approaches analyzed; key blocker is whether Claude Code supports multi-line status bar output.

## Current State

- **Project statusline**: `.squidsquad/statusline.sh` — reads JSON stdin, outputs single line with squid emoji, role, iteration, health, context %
- **User's statusline**: `~/.claude/hooks/gsd-statusline.js` — outputs model name, task, directory, context progress bar
- **Config hierarchy**: Project-level `.claude/settings.json` completely overrides user-level. No chaining mechanism.
- **Setup (Step 7)**: BUG-009 added replace/skip prompt, but no merge option

## Approaches

### Option A: Chain User Command (Recommended if multi-line works)
Save user's existing statusLine command during setup to `.squidsquad/.user-statusline`. statusline.sh runs their command first, captures output, appends SquidSquad line below.
- **Pros**: Preserves exact user customizations
- **Cons**: Multi-line output risk, eval security, two processes per update, cross-platform fragility

### Option B: Reproduce Default Info + Append
statusline.sh parses JSON stdin and reconstructs default Claude status, then appends SquidSquad line.
- **Pros**: Self-contained, no saved state
- **Cons**: Loses user customizations (GSD features, task names, styling)

### Option C: Request Claude Code Feature
Ask Claude Code team to support `"mode": "append"` in statusLine config.
- **Pros**: Cleanest solution
- **Cons**: Blocking dependency on Claude Code team

## Key Risk

**Multi-line output**: Neither gsd-statusline.js nor statusline.sh outputs newlines. Unknown if Claude Code status bar supports multi-line. Must test before committing to Option A or B.

## Side Effects & Edge Cases

| Edge Case | Impact | Mitigation |
|-----------|--------|------------|
| User's command is Node script | eval must handle node invocation | Store full resolved command |
| No existing statusLine | Just show SquidSquad line | Check if .user-statusline exists |
| User command times out | SquidSquad line never appears | 1s timeout on user command |
| Performance (2 processes) | Slight delay per status update | Acceptable for status bar |
| Windows paths | Backslashes, spaces in paths | Resolve to absolute paths at setup |
| Relative path commands | cwd may vary at runtime | Resolve during setup |

## Open Questions

1. **Does Claude Code support multi-line status bar output?** — Must test. Blocks approach decision.
2. **Setup merge strategy**: Auto-merge (default) vs ask user? Recommend: merge default, replace/skip as fallbacks.
3. **Supported command types**: bash, node, exe — all via eval? Recommend: store as-is, eval, trust user.
4. **Path resolution**: Resolve $HOME/relative paths at setup time? Recommend: yes, store absolute paths.
5. **Timeout/error handling**: Silent failure (skip user output, show SquidSquad only)? Recommend: yes, 1s timeout.
6. **Position customization**: Always last line, or configurable? Recommend: always last, out of scope for v1.
7. **Claude Code parent config reference**: Can project-level statusLine reference user-level? Recommend: test/ask.
