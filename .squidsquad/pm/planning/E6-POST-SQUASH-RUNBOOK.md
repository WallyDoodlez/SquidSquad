# E6 Post-Squash Runbook

Standalone instructions for the operator to follow after the **#10685 E6 V2 CUTOVER** squash PR merges to `main`. Estimated time: ~5–10 minutes of mechanical commands.

Run all commands from a Windows shell. PowerShell or cmd both fine — examples use cmd-style `cd /d`.

---

## 0. Prerequisites — verify the squash actually merged

Before doing anything below, confirm the squash PR is merged and #10685 is closed:

```cmd
gh pr view <PR-NUMBER> --json state,mergedAt
gh issue view 10685 --json state
```

Both should report `MERGED` / `CLOSED`. If not, stop here — the rest is premature.

---

## 1. Pull latest main in every clone

```cmd
cd /d D:\Dev\Dev\SquidSquad
git checkout main
git pull

cd /d D:\Dev\Dev\SquidSquad-2
git checkout main
git pull

cd /d D:\Dev\Dev\SquidSquad-qa
git checkout main
git pull

cd /d D:\Dev\Dev\SquidSquad-3
git checkout main
git pull
```

Each clone's `references/` directory should now be the post-cutover tree (no more `compose_role`, no more `--v2` flag, etc.). The `cycle_pre.py` for each agent does a pull on its next cycle anyway, but doing it upfront avoids drift while you do the recompose.

---

## 2. Recompose all agents

Every `.squidsquad/<role>/CLAUDE.md` is now stale — it was generated from the pre-cutover sources. Regenerate from PM's clone (it has the full toolchain):

```cmd
cd /d D:\Dev\Dev\SquidSquad
python references/scripts/compose.py deploy-all
```

**Sanity check**: composed CLAUDE.md files should be **noticeably smaller** than they were pre-cutover. This is the OOM relief that E6 buys you. Roughly:

```cmd
powershell -NoProfile -Command "Get-ChildItem .squidsquad\*\CLAUDE.md | Format-Table FullName, Length -AutoSize"
```

If any one of them blew up in size instead of shrinking, something is wrong — investigate before proceeding to step 3.

---

## 3. Restart agents to pick up new CLAUDE.md

Each agent reads its `CLAUDE.md` at session boot, then holds it in memory. Until restart, they're running the OLD pre-cutover version. Order doesn't matter much — restart whichever is convenient first.

### 3a. DM (harness-managed — likely working fine)

```cmd
curl -sf -X POST http://127.0.0.1:7373/agents/dm/restart
```

### 3b. Skill (currently manual-launched per OOM mitigation #10955)

Find the running skill PID and kill it:

```cmd
powershell -NoProfile -Command "Get-Process claude | Where-Object { (Get-CimInstance Win32_Process -Filter (\"ProcessId=\" + $_.Id)).CommandLine -like '*squidsquad-skill*' } | Format-Table Id"
```

Stop the matching PID, then relaunch with the same manual-launch command:

```cmd
powershell -NoProfile -Command "Stop-Process -Id <PID> -Force"

cd /d D:\Dev\Dev\SquidSquad-2
set SQUIDSQUAD_ROLE=skill
claude --strict-mcp-config --mcp-config "D:\Dev\Dev\SquidSquad-2\.squidsquad\mcp-agents.json" --append-system-prompt "SQUIDSQUAD_ROLE=skill" --name squidsquad-skill --effort high --dangerously-skip-permissions "/loop 30m execute one Ralph Loop cycle"
```

### 3c. PM (this agent — restart last so it captures the runbook follow-through in its iteration log)

Wait for PM's current cycle to finish (look at the statusline — when it shows `idle` and the cycle just completed), then:

```cmd
curl -sf -X POST http://127.0.0.1:7373/agents/pm/restart
```

(PM is harness-managed even though state is stale — restart triggers a fresh CLAUDE.md read.)

### 3d. qa (the misrouted "qa" entry in the harness)

There's a known harness-state corruption (#10954) where the `qa` role still points at PM's clone. Until that's fixed, **leave qa alone** — restarting via harness re-spawns it into the wrong clone. The misrouted qa has been verifying PRs via tracker.py just fine; restarting buys nothing right now. After step 5 below, qa gets properly reborn as `verifier`.

---

## 4. Verify the smoke

Run the test suite to confirm the post-cutover state is clean:

```cmd
cd /d D:\Dev\Dev\SquidSquad
python tests/run_tests.py
```

Expected: clean pass. Any pre-existing flakes documented in `#10861` / `#10862` style should already be addressed since those merged before E6.

If anything new breaks, it's a regression introduced by the squash itself — file a high-severity bug to skill before proceeding.

---

## 5. Repair the harness state for the qa→verifier rename (closes #10954)

This is the one-shot manual cleanup to make `verifier` actually work end-to-end. PR #10952 already fixed the `boot_remote` role validator; this step makes the harness-on-disk state match.

### 5a. Stop the harness

```cmd
curl -sf -X POST http://127.0.0.1:7373/shutdown
```

(Or Ctrl+C at the harness terminal.) This persists the in-memory state to `.harness-state.json`.

### 5b. Edit `.squidsquad/.harness-state.json`

Open it in an editor. Find the `agents` object. Make these edits:

- Rename key `"qa"` → `"verifier"`
- Inside that entry, change `"clone_path": "D:\\Dev\\Dev\\SquidSquad"` to `"clone_path": "D:\\Dev\\Dev\\SquidSquad-qa"`
- Set `"claude_pid": null` and `"terminal_pid": null` (the old PIDs are dead or misrouted)
- Set `"status": "unknown"` (harness will re-check on boot)

Save the file.

### 5c. Kill the stale qa claude.exe

```cmd
powershell -NoProfile -Command "Get-Process claude | Where-Object { (Get-CimInstance Win32_Process -Filter (\"ProcessId=\" + $_.Id)).CommandLine -like '*squidsquad-qa*' -or (Get-CimInstance Win32_Process -Filter (\"ProcessId=\" + $_.Id)).CommandLine -like '*qa*' } | Stop-Process -Force"
```

(Manually verify with `Get-Process claude` that only the intended PIDs remain.)

### 5d. Restart the harness

```cmd
cd /d D:\Dev\Dev\SquidSquad
python references/scripts/squidsquad_cli.py start
```

Verify the new role is registered:

```cmd
curl -sf http://127.0.0.1:7373/agents/verifier
```

Should return JSON with `clone_path: D:\\Dev\\Dev\\SquidSquad-qa` and `status: unknown` initially.

### 5e. Boot verifier

```cmd
curl -sf -X POST http://127.0.0.1:7373/agents/verifier/start
```

Within a minute, `.squidsquad/verifier/.claude-pid` should appear in `D:\Dev\Dev\SquidSquad-qa\` (the CORRECT clone this time), and `current-state` should start updating. Watch for the first verifier cycle to land a commit.

If verifier still goes inert (no PID file, no state writes), the bug is something else and should be filed against `boot_remote.py` / `thin_launcher.py` with full evidence.

---

## 6. Close out post-E6 bookkeeping

### 6a. Close #10954 (harness state surgical repair)

After step 5 succeeds:

```cmd
gh issue comment 10954 --body "Repaired per runbook step 5. Verifier role registered correctly, boot via /agents/verifier/start succeeds, PID + current-state writes confirmed in SquidSquad-qa clone."
gh issue close 10954
```

### 6b. Close #10685 (E6 itself — likely auto-closed already)

If the squash PR linked it via `Closes #10685`, GitHub auto-closed it. If not:

```cmd
gh issue close 10685 --reason completed --comment "E6 V2 cutover shipped. Post-squash runbook executed. v1 paths retired, v2 default, composed CLAUDE.md regenerated, agents restarted."
```

### 6c. Close #10677 (D6 — bundled into E6)

If the squash PR linked it, auto-closed. Otherwise:

```cmd
gh issue close 10677 --reason completed --comment "Shipped as part of E6 squash. event-driven: config field removed, _get_wake_mode retired, boot-bootstrap.md doc refreshed."
```

### 6d. Update #10955 (skill OOM acceleration)

The composed CLAUDE.md shrink from E6 may or may not be enough to stop the OOM pattern. Reassess after ~5 cycles of skill running post-recompose:

- If skill cycles run cleanly for 5+ cycles without OOM → comment "OOM pattern stopped after E6 composed-CLAUDE shrink; can close" and close
- If skill still OOMs → comment with new evidence and bump severity to high; the real structural fix is PRD-D (#10781), which is now unblocked

---

## 7. Unblock the post-E6 queue

The following are now ready for skill pickup. Pickup order (per the cycle-1552 strategy reply on #10685):

1. **#10686 E7** — V2 migration smoke
2. **#10781 PRD-D** — sub-skills as Claude Skills (inserted ahead of umbrellas for further OOM relief)
3. **#10690** — wiki-link rework (gated on E7 also being merged)
4. **#10836 INSTALLER-ARCH umbrella** (Direction A pre-locked for Finding 26 wizard L4 path)
5. **#10837 HARNESS-ARCH umbrella** (DS re-audit queued — PM will run it now that E6 is on main)
6. **#10838 VAULT-ARCH umbrella**
7. **#10839 cross-TRD `role` → `alias` rename** (gated on E6 + PRD-D)

PM (whichever agent is running it) should re-state the queue order in #10685's closing comment, then pivot to monitor mode.

---

## 8. Sanity checks before declaring "done"

- [ ] All 4 clones on `main` at the squash commit (`git log -1 --oneline` in each)
- [ ] All `.squidsquad/<role>/CLAUDE.md` regenerated; file sizes reduced from pre-cutover baseline
- [ ] PM, skill, dm restarted; iteration logs show fresh post-restart cycles
- [ ] Verifier reborn (per step 5); first verifier cycle landed
- [ ] `python tests/run_tests.py` clean
- [ ] #10685, #10677, #10954 closed
- [ ] Post-E6 queue documented in #10685 closing comment

If all 8 items check, E6 cutover is fully landed end-to-end.

---

## Troubleshooting

**`compose.py deploy-all` errors** → check that `references/sub-skills/includes.yml` exists (post-cutover canonical name). If you see references to `includes-v2.yml`, the pull in step 1 didn't take fully.

**Agent restart spawns but never writes `.claude-pid`** → known #10855 pattern. The fix (PR #10952) is `boot_remote._get_all_roles` rename; if PR #10952 wasn't part of the E6 squash, it must be on `main` separately for verifier boot to work.

**Skill OOMs immediately on restart** → composed CLAUDE.md may not have shrunk enough. Drop `effort-skill` from `high` to `medium` in `.squidsquad/config.md` as a temporary mitigation, or fall back to the manual-launch path in step 3b. Re-run step 2 to recompose.

**Harness restart in step 5d fails** → check `.harness-state.json` for JSON validity (a misplaced quote can corrupt it). If unrecoverable, delete the file — the harness rebuilds it from `.local-config` on next start.
