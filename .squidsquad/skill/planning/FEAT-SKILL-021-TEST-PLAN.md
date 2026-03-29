# FEAT-SKILL-021 Test Plan — Status Bar Append

## Verification Criteria

### Setup Behavior
- [ ] Setup detects existing statusLine in user's `.claude/settings.json`
- [ ] Existing command saved to `.squidsquad/.user-statusline` (exact string, as-is)
- [ ] If no existing statusLine, no `.user-statusline` file created
- [ ] Setup does NOT prompt user about statusLine (auto-merge)
- [ ] SKILL.md setup steps updated to document the chaining behavior

### statusline.sh Chaining
- [ ] statusline.sh checks for `.squidsquad/.user-statusline` file
- [ ] If file exists: runs saved command with JSON stdin piped in, captures output
- [ ] User's output appears first (line 1+), SquidSquad line appears last
- [ ] If file doesn't exist: only SquidSquad line output
- [ ] 1-second timeout on user command execution
- [ ] Silent fallback: if user command fails/times out, only SquidSquad line shown (no error)

### Template Updates
- [ ] `references/agent-instructions.md` statusline template updated with chaining logic
- [ ] SKILL.md statusline.sh template updated
- [ ] Generated `.squidsquad/statusline.sh` includes chaining logic

### Edge Cases (manual read-through)
- [ ] User command is node script (e.g. `node "$HOME/.claude/hooks/gsd-statusline.js"`)
- [ ] User command uses $HOME or other env variables (resolved at runtime, not setup)
- [ ] User command outputs multiple lines (all preserved, SquidSquad still last)
- [ ] Empty .user-statusline file handled gracefully (skip, show SquidSquad only)
