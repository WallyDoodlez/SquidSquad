# FEAT-SKILL-021 Context — Status Bar Append (Last Line Only)

## Scope
Modify SquidSquad's statusline setup to preserve the user's existing status bar. SquidSquad appends its info on the last line only. User's original statusLine command is saved and chained.

## Locked Decisions

### Q1: Approach — Option A (chain user command)
**Decision**: Multi-line status bar output confirmed working in Claude Code. Use Option A: save user's existing statusLine command during setup, chain it in statusline.sh (run their command first, append SquidSquad line below).
**Why**: Only approach that preserves exact user customizations.

### Q2: Setup merge strategy — auto-merge
**Decision**: Auto-merge by default. Setup detects existing statusLine, saves the command to `.squidsquad/.user-statusline`, and sets up chaining automatically. No prompt needed.
**Why**: Reduces setup friction. Replace/skip can be done manually via config.

### Q3: Path resolution — store as-is
**Decision**: Save the exact command string from the user's settings.json without resolving paths or variables. Let bash handle $HOME etc. at runtime.
**Why**: Simplest approach, works for most cases, preserves portability.

### Q4: Error handling — silent fallback
**Decision**: If user's saved command fails or times out (1-second timeout), skip user output and show only SquidSquad line. No warning displayed.
**Why**: Status bar is non-critical UI. Silent failure is least disruptive.

### Q5: Position — always last line
**Decision**: SquidSquad status info always appears on the last line of the status bar output.
**Why**: Simple, predictable. Configurable position can be added later if needed.

## Dev Discretion Areas
- Exact bash implementation for chaining (eval vs direct execution)
- Whether to also generate a .ps1 version for PowerShell
- How to handle edge case where .user-statusline file exists but is empty
- Whether to add a setup step to test the chained output works
