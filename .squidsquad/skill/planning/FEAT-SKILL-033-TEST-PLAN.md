# FEAT-SKILL-033 Test Plan — Heartbeat Branches

## QA Verification (PM will check these)

### T1 — heartbeat.sh exists and is standalone
- [ ] `references/heartbeat.sh` exists as standalone file
- [ ] Script takes role and interval as arguments
- [ ] Script does not require agent context to run

### T2 — Boot scripts launch heartbeat
- [ ] `start-skill.sh` launches heartbeat.sh in background
- [ ] `start-pm.sh` launches heartbeat.sh in background
- [ ] Heartbeat PID is managed (not orphaned)

### T3 — Config populated
- [ ] Fresh setup creates `Heartbeat Interval Seconds: 10` in config.md
- [ ] SKILL.md setup includes step explaining heartbeat to user

### T4 — Upgrade migration
- [ ] Upgrade flow adds `Heartbeat Interval Seconds: 10` to existing config.md if missing
- [ ] Upgrade flow does NOT overwrite existing custom value
- [ ] Upgrade regenerates boot scripts with heartbeat launch

### T5 — PM health check uses heartbeat
- [ ] PM CLAUDE.md Step 7 reads heartbeat branches instead of git log --grep
- [ ] PM correctly detects healthy agent (heartbeat within interval)
- [ ] PM correctly detects stalled agent (heartbeat older than interval)

### T6 — No main branch pollution
- [ ] Heartbeat pushes only to `heartbeat/<role>` branches
- [ ] No heartbeat-related commits on main

### T7 — statusline.sh updated
- [ ] Health icons in statusline.sh read heartbeat branches
- [ ] Consistent with PM Step 7 logic

### T8 — SKILL.md and templates coherent
- [ ] agent-instructions.md PM template Step 7 updated
- [ ] Dev agent template has NO heartbeat references
- [ ] SKILL.md setup step numbers sequential
