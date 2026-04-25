```markdown
# FEAT-PM-2496 Research — Unify agent lifecycle (single wrapper for all start/restart/reboot paths)

## Summary
This research reviewed the current agent lifecycle mechanisms across the repo: per-role boot wrappers (`.squidsquad/start-*.ps1|.sh`), remote boot orchestration (`references/scripts/boot_remote.py`), health reporting (`references/scripts/health_check.py`), and reboot orchestration (`references/scripts/reboot_agent.py`). The key gap is that **reboot behavior assumes the per-role wrapper is running** (it writes `.restart` then kills the agent), but if the wrapper is *not* running (or the PID points at the wrapper itself), the agent can be killed without a guaranteed respawn path.

Recommendation: **make `reboot_agent.py` always go through the same wrapper entrypoint used for human start and PM auto-boot**. Concretely: after initiating a reboot (writing `.restart` and killing the running PID), `reboot_agent.py` should **ensure the wrapper is running** by calling the same boot mechanism as `boot_remote.py` (i.e., spawn `.squidsquad/start-<role>.ps1|.sh` in a terminal) when needed. This unifies “human start”, “PM auto-boot”, “PM reboot”, and “self-restart” around the wrapper as the single lifecycle authority.

Primary risks: (1) double-starting if PID semantics differ (wrapper PID vs child PID), (2) cross-clone path resolution inconsistencies (`reboot_agent.py` parses `.local-config` differently than `boot_remote.py`), and (3) platform-specific terminal spawning behavior.

## Vault Context
- **BRIEFING.md priorities**: #2353 reboot_agent.py --all dict bug — pending-test (high) (already reflected in `tests/test_reboot_agent.py`); no explicit FEAT-PM-2496 note yet.
- **Related decisions**: [[decision-watchdog-supervisor]] — centralize lifecycle in a standalone supervisor; avoid scattered restart logic across multiple scripts.
- **Related patterns**: none explicitly named for lifecycle unification, but aligns with “single deterministic script” direction in [[decision-watchdog-supervisor]].
- **Human preferences**: PID-first liveness checks (from [[decision-pid-primary-liveness]] and `human-profile.md` lines 33-34); prefer OS-truth over stale state files.
- **Related learnings**: none directly about reboot, but the general “self-heal + close the loop” approach in [[decision-self-healing-sentinel]] suggests we should eliminate the “agent dies permanently” failure mode rather than documenting it.

## Impact Analysis
- **Files touched**:
  - `references/scripts/reboot_agent.py` (core change: ensure wrapper respawn path; unify clone-path parsing)
  - `references/scripts/boot_remote.py` (likely refactor: expose a reusable “spawn wrapper for role” function or share clone-path parsing)
  - `tests/test_reboot_agent.py` (add coverage for “wrapper not running → reboot triggers spawn”)
  - Potentially templates/wrappers if PID semantics need adjustment:
    - `.squidsquad/start-*.ps1` and `.squidsquad/start-*.sh` (generated)
    - `references/templates/start-role.ps1`, `references/templates/start-role.sh` (source templates)
- **Behavior changes**:
  - `reboot_agent.py` will no longer be “kill-only”; it will **guarantee a wrapper-based respawn** when the wrapper is absent.
  - More consistent clone-path resolution (today `reboot_agent.py` uses a legacy `.local-config` markdown parse; `boot_remote.py` prefers `~/.squidsquad/clones/` then `.local-config`).
- **Dependencies**:
  - Terminal spawning behavior in `references/scripts/boot_remote.py` (`wt.exe` / `cmd start` / `osascript` / `tmux`)
  - `.squidsquad/start-<role>.*` wrapper contract: `.pid`, `.health`, `.restart`, `.stop`, `current-state`

## Side Effects
- **Risk 1**: Double-start / race if reboot triggers spawn while wrapper is still alive — Severity: M — Mitigation: before spawning, check PID liveness *and* whether PID corresponds to wrapper vs child; prefer PID-first per [[decision-pid-primary-liveness]]. If `.pid` is wrapper PID (as in `.squidsquad/start-skill.sh` line 97 writes `$$`), killing it will stop wrapper; spawning is correct. If `.pid` is child PID in some roles/versions, spawning could create a second wrapper; mitigate by standardizing `.pid` meaning (wrapper PID) in templates.
- **Risk 2**: Cross-clone mismatch (reboot writes `.restart` in one clone, boot spawns wrapper in another) — Severity: H — Mitigation: unify clone-path resolution by reusing `boot_remote._parse_local_config()` logic (shared filesystem `~/.squidsquad/clones/` first, then `.local-config`). Today `reboot_agent._get_clone_path()` only parses `.squidsquad/.local-config` markdown (reboot_agent.py lines 35-45).
- **Risk 3**: Platform spawn failures (no terminal available) — Severity: M — Mitigation: reuse `boot_remote._spawn_terminal()` fallback messaging; if spawn fails, return non-zero and print manual boot instructions (boot_remote.py lines 358-361 show manual boot guidance).

## Edge Cases
- **Agent busy and reboot times out**: `reboot_agent.py` cleans `.restart` on timeout (reboot_agent.py lines 123-129). If we add “ensure wrapper running”, do **not** spawn wrapper on timeout (would restart mid-cycle). Only spawn when we actually killed the process (or it was already dead).
- **PID file exists but process dead**: currently returns 0 and does nothing (reboot_agent.py lines 100-103). With unification, consider optionally spawning wrapper in this case (since agent is dead). This would align with “reboot means ensure running”.
- **`.restart` written but wrapper not present**: current failure mode. Fix by spawning wrapper after kill, or by spawning wrapper when `.restart` exists and PID is dead.
- **`.stop` sentinel present**: boot wrappers honor `.stop` (e.g., `.squidsquad/start-skill.sh` lines 218-225; `.ps1` similar around lines 207-214). Reboot should probably respect `.stop` (don’t respawn if explicitly stopped).

## Integration Risks
- **Health semantics mismatch**: `boot_remote.py` still documents `.health primary with PID fallback` (boot_remote.py docstring lines 4-8) and implements `.health` gating (boot_remote.py lines 201-214) despite vault decision [[decision-pid-primary-liveness]] stating PID should be primary. If reboot starts relying on boot_remote behavior, this inconsistency can reintroduce stale `.health` issues. Mitigation: adjust boot_remote `_needs_boot()` to be PID-primary (or at least not block boot when `.health=alive` but PID is dead—health_check already detects this stale case at health_check.py lines 312-317).
- **Wrapper generation drift**: `.squidsquad/start-skill.*` differs from `references/templates/start-role.*` (e.g., start-skill.sh is a full restart loop with `.restart` + context pressure watcher; template start-role.sh is a simpler single-run + optional respawn). Ensure the “single wrapper” concept is consistent across generated scripts and templates.

## Upgrade & Migration
- **New config values**: none required for minimal fix.
- **New files**: none required.
- **Template changes**: likely “yes” if standardizing `.pid` meaning and/or ensuring wrapper always owns restart logic. Source templates are:
  - `references/templates/start-role.ps1`
  - `references/templates/start-role.sh`
- **Upgrade steps**:
  - N/A if we only change `reboot_agent.py` to spawn wrapper via existing `boot_remote.py` logic.
  - If templates change, users must regenerate wrappers via compose (wrappers indicate regeneration command at top, e.g. `.squidsquad/start-skill.sh` lines 2-3).
- **Graceful degradation**:
  - If user doesn’t upgrade wrappers, `reboot_agent.py` can still spawn existing `.squidsquad/start-<role>.*` scripts; behavior improves without requiring wrapper regeneration.

## Open Questions
- **Q1**: What does `.squidsquad/<role>/.pid` represent across all roles/versions: wrapper PID or Claude child PID? — **Why**: reboot correctness depends on killing the right process and deciding whether a wrapper is already supervising.
- **Q2**: Should `reboot_agent.py` treat “agent not running” as “boot it” (i.e., reboot == ensure running), or keep current “no-op success”? — **Why**: affects operator expectations and whether reboot becomes a recovery tool.
- **Q3**: Should we refactor lifecycle into a dedicated Python “wrapper supervisor” (per [[decision-watchdog-supervisor]] referencing `references/scripts/watchdog.py`), given `references/scripts/watchdog.py` is currently missing from the repo (glob found only a vault note and `.squidsquad/watchdog-log.txt`)? — **Why**: if watchdog is intended to be the single authority, reboot should signal watchdog rather than spawning terminals directly.

## Recommendation
Feasible with caveats
```