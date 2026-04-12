# QA Results — Feature #4: PM auto-boots entire team on startup

**Date**: 2026-04-11
**Verified by**: QA agent

---

### Check-1: boot_remote.py exists and has required capabilities
- **Result**: PASS
- **Notes**: File exists at `references/scripts/boot_remote.py` (469 lines). Verified all sub-requirements:
  - **health_check.py integration**: `_run_health_check()` calls `health_check.py --json` and parses output (lines 45-57). `_needs_boot()` interprets health states (stopped/healthy/stalled/unknown) on lines 60-78.
  - **.stop sentinel respect**: `_needs_boot()` returns `False` for `health == "stopped"` with message "explicitly stopped (.stop sentinel)" (line 71). Stop check comes FIRST before other states.
  - **Cooldown logic**: `_check_cooldown()` on lines 111-119 reads `boot-attempts.log` and enforces 600-second (10 min) cooldown per role.
  - **Lock file support**: `_acquire_lock()` / `_release_lock()` on lines 127-148 use `boot-lock` file with 30-second TTL and stale-lock cleanup.
  - **Windows support (OS-aware)**: `_detect_os()` returns windows/macos/linux. `_spawn_windows()` (lines 208-245) uses `wt.exe` (Windows Terminal) with fallback to `cmd /c start`. Also has `_spawn_macos()` (osascript) and `_spawn_linux()` (tmux). Uses `subprocess.DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` creation flags on Windows.

### Check-2: boot-remote-agents.md sub-skill exists and is proper
- **Result**: PASS
- **Notes**: File exists at `references/sub-skills/common/boot-remote-agents.md` (25 lines). Contains clear agent instructions: check config, run `python references/scripts/boot_remote.py --all --json`, interpret output (action/success fields), log spawn failures, print boot summary. Silent pass when all agents healthy.

### Check-3: Sub-skill composed into ALL agent CLAUDE.md templates
- **Result**: PASS
- **Notes**: Verified `{{include: common/boot-remote-agents}}` directive present in all 5 role templates:
  - `references/roles/dev/CLAUDE.md` (line 178)
  - `references/roles/pm/CLAUDE.md` (line 245)
  - `references/roles/qa/CLAUDE.md` (line 109)
  - `references/roles/designer/CLAUDE.md` (line 114)
  - `references/roles/dm/CLAUDE.md` (line 108)
  - Additionally confirmed composed output in installed agents: `.squidsquad/pm/CLAUDE.md` (line 548), `.squidsquad/skill/CLAUDE.md` (line 428), `.squidsquad/dm/CLAUDE.md` (line 436) all have `<!-- sub-skill: boot-remote-agents -->` markers.
  - QA and Designer roles are not currently installed (no `.squidsquad/qa/` or `.squidsquad/designer/` dirs), but their reference templates DO include the directive. This is expected — they compose on install.

### Check-4: config.md has "Auto Boot Agents" field
- **Result**: PASS
- **Notes**: `.squidsquad/config.md` contains `## Auto Boot Agents` section (line 45) with `- **Enabled**: yes` (line 47). The script reads this at startup and respects `no` to disable (lines 432-444 of boot_remote.py).

### Check-5: config.py FIELD_MAP updated with auto-boot
- **Result**: PASS
- **Notes**: `references/scripts/config.py` line 52 has `"auto-boot": ("Auto Boot Agents", "Enabled")` in FIELD_MAP. This allows programmatic read/write via `python config.py get auto-boot` and `python config.py set auto-boot no`.

### Check-6: manifest.md updated with boot-remote entry
- **Result**: PARTIAL PASS
- **Notes**: The Dev Agent composition order in manifest.md lists `common/boot-remote-agents` at position 6 (line 26). However, the PM, QA, Designer, and DM composition order sections do NOT list `boot-remote-agents` even though all five role templates include it. Additionally, `boot-remote-agents.md` is missing from the Sub-skill File Inventory tree (the `common/` directory listing at lines 154-170). The actual templates and sub-skill file are correct — only the manifest documentation is out of sync.

### Check-7: Script runs without errors (--help and --dry-run)
- **Result**: PASS
- **Notes**: `python references/scripts/boot_remote.py --help` exits 0 with correct usage text. `python references/scripts/boot_remote.py --dry-run --all --json` exits 0 with valid JSON output showing 2 agents (dm, skill) both skipped as healthy. The script correctly integrates with the live health_check.py and config.md.

---

## Summary

| Check | Title | Result |
|-------|-------|--------|
| 1 | boot_remote.py capabilities | PASS |
| 2 | boot-remote-agents.md sub-skill | PASS |
| 3 | Composed into all agent templates | PASS |
| 4 | config.md Auto Boot Agents field | PASS |
| 5 | config.py FIELD_MAP auto-boot | PASS |
| 6 | manifest.md updated | PARTIAL PASS |
| 7 | Script runs without errors | PASS |

**Overall**: 6/7 PASS, 1 PARTIAL PASS

**Blocking issue**: None. All functional deliverables work correctly.

**Non-blocking gap**: `manifest.md` composition order sections for PM, QA, Designer, and DM do not list `boot-remote-agents`, and the file inventory tree is missing `boot-remote-agents.md`. This is a documentation-only gap — the actual templates and runtime behavior are correct.
