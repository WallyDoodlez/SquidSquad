# QA-RESULTS-13318 — VERDICT: FAIL (AC7) → back to in-progress (skill)

**Issue**: #13318 — consolidate to ONE start script per platform.
**PR**: #13320 (base main, head squidsquad/task/13318).
**Verifier**: qa | **Date**: 2026-06-28 ~15:43 | **Verified at**: PR head b5b18de29

## AC walk

| AC | Verdict | Evidence |
|----|---------|----------|
| AC1 single entrypoint per platform | **PASS** | `git ls-tree` branch: only `.squidsquad/start.ps1` + `.squidsquad/start.sh` exist; diff D's all 7 old scripts (start.{sh,ps1,bat}, start-harness.{sh,bat}, restart-harness.{sh,bat}); repo root has no launchers. Matches operator location-refinement. |
| AC2 full bring-up preserved | **PASS** | start.sh `ensure_deps` (python3/pip, requirements.txt import probe, requirements-tui.txt, claude warn) + `sync_clones` (`git checkout main && git pull --no-rebase` for primary + every `.local-config` clone) → supervised harness launch. |
| AC3 TUI bundled | **PASS** | full mode: `harness_up` python3-urllib probe (M1 fix — no curl-less false-down); if up → attach; else `nohup … start.sh --bare … & disown` then `exec python3 references/tui/app.py`. Singleton-safe. |
| AC4 self-restart (folds #12825) | **PASS** | `run_supervised`: exit-42→relaunch (crash_count reset), exit-0→stop, other→crash-loop guard (threshold 3, 60s healthy-reset), INT/TERM trap→no relaunch. Detached harness + foreground TUI. Verbatim-faithful to #12825. |
| AC5 bare/no-setup (folds #12525) | **PASS** | `--bare`/`--no-setup` → `run_supervised` only, no deps/sync/TUI. #12527 reference updated (per skill; squidsquad_cli RESTART_WRAPPER --bare). |
| AC6 quit-TUI leaves fleet up | **PASS** | harness detached via nohup+disown; TUI foreground via exec. Quitting TUI does not tear down the backgrounded harness/fleet; re-run re-attaches. |
| **AC7 repoint ALL consumers** | **FAIL** | See below. |
| AC8 tests retargeted + new coverage | **PASS** | `test_13318_consolidated_launcher.py` + retargeted `test_12525/12526/12825` → **47 passed**. New coverage for single-entrypoint/TUI/singleton/supervised. |
| Comprehension (harness-restart.md CQ) | DEFERRED to clean re-submission | `harness-restart.md` correctly repointed; CQ spec `13318_spec.json` well-authored (3 CQs). Will run the fresh-agent CQ once the full doc surface is final post-AC7-fix. |

## AC7 FAIL — specific evidence

AC7 explicitly enumerates "README #13277 'Harness Dashboard' launch lines, INSTALLER-ARCH/HARNESS-ARCH launch references" as consumers to repoint. The PR touched **none** of README.md / INSTALLER-ARCH.md / HARNESS-ARCH.md, and skill's delivery comment does not list them or flag them to PM/DM. Live, now-broken references remain:

1. **README.md:86** — still presents `restart-harness.sh` / `restart-harness.bat` as "the documented default for running the harness directly," and `start-harness.sh` / `start-harness.bat` as the one-shot option. **All four are deleted by this PR** → the paragraph documents nonexistent scripts.
2. **docs/INSTALLER-ARCH.md:557** — cold-start instruction: "the user runs `./start.sh` from the repo root." Script moved to `.squidsquad/start.sh` → **stale path** (no `./start.sh` at root). Also **:545** (`./start.sh` cold-start) and **:620** broken doc link `[start.sh](../start.sh)`.

HARNESS-ARCH.md: clean (no stale refs found).

What were correctly repointed (PASS portion of AC7): `squidsquad_cli.py`, `installer-files.txt`, `packages/cli/index.js`, `wizard.py` (cold_start_cmd), `harness.py` comment, `references/sub-skills/common/harness-restart.md`, `WIZARD.md`.

**Required to clear AC7**: repoint the mechanical launch refs in INSTALLER-ARCH.md (`./start.sh` → `.squidsquad/start.sh`; fix the §620 link) and the README:86 script names; for any deeper narrative rewrite of the README launcher paragraph that is DM/PM-owned (#13277), **flag it to PM/DM via a tracked transition/issue** per AC7's lane-split clause (skill must do one or the other — neither was done).

## Landing safety

Branch 0-behind/6-ahead; deletions are the task's explicit goal; +701/-436 additions-dominant; no agent-state files in diff. (Not a blocker; recorded for the eventual clean merge.)

**VERDICT (round 1): FAIL on AC7. Transition pending-test → in-progress (skill). All other ACs PASS; fixing AC7 (+ then the deferred comprehension CQ) should clear it in one cycle.**

---

## RE-VERIFICATION (round 2) — 2026-06-28 ~20:20, verified at head 24b08336c — VERDICT: PASS (zero gaps)

Skill fixed AC7. **Delta since round-1 head (b5b18de29) = exactly 3 doc files** (README.md, docs/HARNESS-ARCH.md, docs/INSTALLER-ARCH.md) — no script/code/test change → AC1-6 + AC8 remain PASS (surface unchanged, re-verification not required for the unchanged code per "code already verified").

- **AC7 now PASS**: README.md:86 repointed to `.squidsquad/start.{sh,ps1} --bare` (deleted restart-harness.*/start-harness.* refs removed); HARNESS-ARCH §2 `start.sh at repo root` → `.squidsquad/start.{sh,ps1}` + repo-root note (a prose ref my round-1 grep didn't flag — skill caught it); INSTALLER-ARCH §4.12/§10.3:545/:557/§620-link all repointed to `.squidsquad/start.sh`. Re-grep clean except INSTALLER-ARCH:630 — a **dated 2026-06-15 doc-honesty historical entry** quoting Step 7.6's then-behavior (frozen record; repointing would falsify history) — correctly left untouched.
- **Comprehension (harness-restart.md CQ) now PASS**: fresh sonnet agent given ONLY the modified prose → **3/3 correct, zero misreads** (CQ1 fully-dead→no-restart/human-handoff/.squidsquad launcher; CQ2 supervised-launcher vs direct-harness.py unsupervised; CQ3 no-flag/empirical-post-restart-check). No reference to deleted scripts; no claim a separate one-shot launcher survives → drift-free per spec pass criteria.
- **Landing safety**: 0-behind/7-ahead; doc-only delta; no state files.

**VERDICT: PASS — zero gaps. Approve + auto-merge (Lane A) → pending-ship.**
