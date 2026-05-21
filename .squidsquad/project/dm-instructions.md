## DM Project Operations — SquidSquad

These instructions apply to the DM agent on this project.

### Boot & Pre-flight

- **Run `tracker.py check-gh` and `capability_check.py` at boot.** If either fails, report and halt — do not proceed with a broken environment.
- **Verify commands before declaring human-blocked.** Run the command yourself first. If it works, it's not blocked. Only mark `blocked:human-action` after confirming the command actually fails.

### Delivery Flow

- **Check `delivery:skip` before any delivery work.** If the task's Discussion contains `delivery: skip`, mark Shipped immediately — no packaging needed.
- **Increment `Shipped Since Last Bump` in config.md** after every ship.
- **Enable feature flags after delivery.** If the task introduced a config feature flag (e.g. `Cycle Runner: no`), enable it on this project via `python references/scripts/config.py set`.

### Branch + PR Workflow (#9478)

- **Use `git_ops.py task-begin` / `task-end`** for branch checkout — same as dev agents.
- **Skip draft PRs** — only process PRs that are ready for review.

### Version Bumps

- **Version bump sequence**: increment minor version, update `config.md` + `SKILL.md` frontmatter + `CHANGELOG.md`, create git tag, push, reset ship counter to 0.
- **CHANGELOG uses user-value framing.** Describe what users GET, not what was changed internally. Non-technical language.

### Documentation

- **Doc improvement loop**: after 3 quiet cycles, scan user-facing docs (README, SKILL.md, CHANGELOG). Max 3 fixes per scan. Rotate between files.
- **Post-ship reboots**: when a shipped task changes templates or sub-skills, trigger `reboot_agent.py` for affected agents so they pick up the new CLAUDE.md.

### Model & Fallback

- **Use `model: "sonnet"` for subagents** — Opus unnecessary for directed subtasks.
- **DM is always present.** Fixed team architecture — PM + QA + DM + workers.
