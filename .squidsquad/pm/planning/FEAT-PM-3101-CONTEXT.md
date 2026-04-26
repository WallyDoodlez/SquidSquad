# FEAT-PM-3101 Context — Upgrade startup logo

## Scope
Replace the current simple squid ASCII art in startup scripts with a blocky letter banner spelling "SQUIDSQUAD" (figlet/toilet style). Keep it clean and readable in a terminal.

## Locked Decisions (human decided)
- Blocky letter banner, NOT a squid character drawing
- Use a figlet/toilet-style ASCII art font generator for clean letter shapes — don't hand-draw
- ANSI color is nice-to-have, not required
- Focus on getting the letter shapes right

## Dev Discretion (dev agent can choose)
- Which figlet font to use (block, banner, slant, etc.)
- Whether to add ANSI color (red/orange to match README branding)
- Whether to keep the small squid icon alongside the text or replace entirely
- Exact spacing and alignment

## Side Effect Mitigations (required)
- PowerShell encoding: ensure .ps1 version renders correctly (see archived BUG-SKILL-003 for prior encoding issues)
- Run compose.py deploy-all after updating templates to propagate to all start scripts

## Upgrade Path (required)
- N/A — cosmetic change, no config or behavior impact

## Out of Scope
- Multi-character squid lineup from README
- Animated or interactive logos
