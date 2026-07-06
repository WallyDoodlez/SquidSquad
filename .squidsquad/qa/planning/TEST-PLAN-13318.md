# TEST-PLAN-13318 — Consolidate to ONE start script per platform

**Issue**: #13318 (type:task, priority:high, role:skill) — consolidate to a single launcher per platform; remove all others.
**PR**: #13320 (base main, head squidsquad/task/13318), +701/-436, 24 files.
**Authoritative contract**: issue body ACs 1-8 **+ operator location-refinement comment** (scripts live at `.squidsquad/start.{ps1,sh}`, repo root has NO launchers; script resolves repo-root as its own parent dir / git rev-parse). The operator comment supersedes the body's "remain at repo root."
**Verifier**: qa. Derived independently from the AC list + operator comment, not from skill's diff.

## Acceptance criteria

- **AC1** Single entrypoint per platform — only `.squidsquad/start.ps1` + `start.sh` remain; identical behavior/flags across both; repo root has no launchers.
- **AC2** Full bring-up preserved: dep check+install (requirements.txt), sync all clones to main (`--no-rebase`), launch harness (harness spawns the fleet).
- **AC3** TUI bundled: after harness up, launch `references/tui/app.py` foreground; attach (not double-start) if harness already running (singleton-safe).
- **AC4** Self-restart preserved (folds restart-harness.*, #12825) — supervised auto-relaunch loop: exit-42→relaunch, exit-0→clean stop, crash-loop guard. NON-NEGOTIABLE. Harness+supervisor detached/background, TUI foreground.
- **AC5** Bare/no-setup path preserved (folds start-harness.*, #12525) — `--bare`/`--no-setup` flag OR #12527 invokes harness.py directly; #12527 reference updated.
- **AC6** Quitting TUI leaves harness + fleet running; re-running re-attaches TUI.
- **AC7** Repoint ALL consumers of removed scripts — tests, sub-skills (incl. harness-restart), **README #13277 'Harness Dashboard' launch lines, INSTALLER-ARCH/HARNESS-ARCH launch references**, squidsquad_cli. Mechanical launch-command refs updated in-task; deeper narrative doc rewrite flagged to PM/DM (lane split).
- **AC8** Tests retargeted (not orphaned) + new coverage for AC3/AC4/AC5.

## Test method

1. AC1 — `git ls-tree` launcher inventory on branch + diff name-status (deletions complete, only 2 scripts in `.squidsquad/`).
2. AC2-AC6 — static inspection of `.squidsquad/start.sh` (and ps1 parity) for each behavior; supervised-loop semantics; repo-root resolution.
3. AC7 — repo-wide grep for references to deleted/moved scripts (`start-harness`, `restart-harness`, `./start.sh`, `start.bat`); confirm each live consumer repointed OR flagged to PM/DM.
4. AC8 — run `test_13318_consolidated_launcher.py` + retargeted `test_12525/12526/12825`.
5. Comprehension — task touches LLM-consumed instructions (`harness-restart.md`, WIZARD.md); CQ spec `tests/comprehension/13318_spec.json`; fresh sonnet agent on the changed prose. (Run on clean re-submission once the doc surface is final.)
6. Landing safety — branch behind/ahead; deletions intended; additions-dominant.
