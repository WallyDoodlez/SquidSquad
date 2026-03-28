# SquidSquad Auto-Boot

If the file `.squidsquad/.active-role` exists, you are running as a SquidSquad agent:

1. Read `.squidsquad/.active-role` to get your role name (e.g. `fe`, `be`, `skill`, `pm`).
2. Read `.squidsquad/<role>/CLAUDE.md` for your full instructions.
3. Follow those instructions exactly — begin your first Ralph Loop cycle immediately without waiting for user input.

If `.squidsquad/.active-role` does not exist, ignore this section — you are a normal Claude session.

**DO NOT DO UNNECESSARY "CD" COMMAND THAT WILL CAUSE PERMISSION PROMPT**