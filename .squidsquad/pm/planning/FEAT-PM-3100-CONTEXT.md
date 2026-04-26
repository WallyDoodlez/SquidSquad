# FEAT-PM-3100 Context — Remove global clones fallback

## Scope
Remove `~/.squidsquad/clones/` fallback from `boot_remote.py` and `health_check.py`. Make `.local-config` mandatory — if missing, hard error with clear message.

## Locked Decisions (human decided)
- Missing `.local-config` → hard error + exit (no silent fallback, no auto-generation)

## Dev Discretion (dev agent can choose)
- Error message wording
- Exit code choice
- Whether to log a warning before exiting or just exit

## Side Effect Mitigations (required)
- Ensure setup flow (`/squidsquad-setup`) creates `.local-config` — if it doesn't already, that's a prerequisite
- Do not delete `~/.squidsquad/clones/` — user may use it for other projects

## Upgrade Path (required)
- N/A — existing installs already have `.local-config`. The fallback removal only affects setups that somehow lost their `.local-config`.

## Out of Scope
- Deleting `~/.squidsquad/clones/` directory
- Agent template documentation about clone philosophy
- Changes to `reboot_agent.py` (it delegates to `boot_remote._get_clone_path()` so it inherits the fix)
