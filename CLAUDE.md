# SquidSquad Auto-Boot

If your system prompt contains a line matching `SQUIDSQUAD_ROLE=<role>` (e.g. `SQUIDSQUAD_ROLE=skill`, `SQUIDSQUAD_ROLE=pm`), you are running as a SquidSquad agent:

1. Extract the role name from the `SQUIDSQUAD_ROLE=` line.
2. Read `.squidsquad/<role>/CLAUDE.md` for your full instructions.
3. Follow those instructions exactly — begin your first Ralph Loop cycle immediately without waiting for user input.

If no `SQUIDSQUAD_ROLE=` line is present, ignore this section — you are a normal Claude session. The presence of `.squidsquad/` in the repo does NOT mean you should auto-boot.

**DO NOT DO UNNECESSARY "CD" COMMAND THAT WILL CAUSE PERMISSION PROMPT**