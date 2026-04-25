# FEAT-PM-2724 Context — Move agent boot detection to cycle_pre.py and create start-squad script

## Scope

Move mechanical agent boot detection out of PM's creative loop into cycle_pre.py. Remove the Auto Boot Agents config toggle. Create start-squad wrapper scripts. PM retains deliberate lifecycle governance (reboot, start, stop).

## Locked Decisions (human decided)
- **Sub-skill stays, template step removed**: Keep `references/sub-skills/common/boot-remote-agents.md` as documentation/reference. Remove the "Boot Remote Agents" step from the PM template entirely — cycle_pre.py handles boot detection mechanically, PM reads results from cycle-input.json without a dedicated step.
- **start-squad calls boot_remote.py --all**: Reuses existing liveness detection, .stop sentinel checks, clone path resolution. Does not call start-role scripts directly.
- **Static start-squad files**: Hand-written .ps1 and .sh scripts. No compose.py target needed (no {{ROLE}} substitution).
- **Remove config guard entirely**: Delete the `Auto Boot Agents` section from config.md and the config guard from boot_remote.py. `.stop` sentinel is the per-role opt-out mechanism.

## Dev Discretion (dev agent can choose)
- Implementation order within the task (scripts first, then config, then template — or whatever makes testing easiest)
- How boot_results field is structured in cycle-input.json (follow boot_remote.py's existing --json output format)
- Where start-squad scripts live (repo root or .squidsquad/ — wherever makes most sense for user discoverability)
- Whether to add a code comment about future watchdog.py replacing the cycle_pre boot call

## Side Effect Mitigations (required)
- **Compose rerun**: After sub-skill/template changes, must run `python references/scripts/compose.py deploy pm` to regenerate `.squidsquad/pm/CLAUDE.md`. QA must verify the composed output, not just the source files.
- **auto_boot_agents field removal**: Remove from `_build_pm_input()` in cycle_pre.py at the same time as adding `boot_results`. These must be in the same commit to avoid PM reading stale field.
- **agent-instructions.md sync**: Update `references/agent-instructions.md` to remove any Auto Boot Agents config check reference.
- **Existing installs**: Users who had `Auto Boot Agents: no` will see agents start booting after upgrade. This is intentional — document in CHANGELOG.

## Upgrade Path (required)
- Remove `## Auto Boot Agents` section from config.md
- No new config values added
- start-squad scripts are new files — upgrade copies them in
- /squidsquad-upgrade should handle config section removal

## Out of Scope
- watchdog.py implementation (vault decision exists, not built yet)
- Changes to reboot_agent.py (PM retains governance access as-is)
- Changes to start-role wrapper scripts (already handle pull, auth, heartbeat)
- Changes to boot_remote.py logic beyond removing the config guard (liveness detection, .stop sentinel, spawn logic all stay)
