# Research — INSTALLER-ARCH Dependency Provisioning (#11537 R2)

**Date**: 2026-06-12 | **Author**: PM (sonnet research subagent + PM synthesis)
**Operator direction**: option (b) auto-provision, but **gather all missing → ask permission → proceed**. Research current func first.
**Status**: research complete; design proposed; awaiting operator confirm before writing the §dep-provisioning section.

---

## Current state — dep handling is scattered across 4 places, inconsistent

| Dependency | Where handled | Behavior today | fail-fast / gather-all |
|---|---|---|---|
| `gh` installed | `wizard.py:166` | check + instruct (returns JSON `fix` list w/ per-OS cmds) | fail-fast |
| `gh` authed | `wizard.py:181-193` | check + instruct (`gh auth login`) | fail-fast |
| Python 3 | `start.sh:10-17` (runtime only) | **auto-install** apt/brew, else print+exit. NOT checked in wizard. | n/a |
| pip | `start.sh:21-27` (runtime only) | auto-install apt/ensurepip. NOT in wizard. | n/a |
| `claude` CLI | `start.sh:33` warn-only; `thin_launcher.py:484` fail at spawn | warn / runtime-fail. NOT checked at install. | n/a |
| py pkgs (fastapi,uvicorn) | `start.sh:30` | auto `pip3 install fastapi uvicorn` (HARD-CODED 2 of 4) | n/a |
| py pkgs (all 4) | `WIZARD.md:665-681` Step 7.5b | `pip install -r requirements.txt` post-commit | n/a |

**requirements.txt** (runtime): fastapi, starlette, uvicorn, watchdog. **requirements-dev.txt**: pytest, pyyaml.

## Key findings

1. **Install-time wizard checks ONLY `gh`** (fail-fast). No Python/pip/claude check at install. Everything else is deferred to `start.sh` (runtime boot) or post-commit Step 7.5b.
2. **Auto-provision already EXISTS but only in `start.sh`** (Python/pip/fastapi+uvicorn), bash-only, apt/brew branches, **no Windows path** (a referenced `start.ps1` does not exist in repo).
3. **DRIFT (doc vs code)**: INSTALLER-ARCH §4.1 + §3.1 claim Phase 0 checks Python3+pip+claude — it does NOT (only gh). Doc overstates. (R1 didn't touch this — it's new for R2.)
4. **Real code bugs surfaced** (skill-domain, file separately from the docs section):
   - `pyyaml` needed at runtime (manifest.py/capability_check.py/source_frontmatter.py) but only in requirements-dev.txt.
   - `start.sh` installs only fastapi+uvicorn (2 of 4 runtime pkgs); skips starlette+watchdog (though fastapi pulls starlette transitively).
   - No Windows `start.ps1` despite WIZARD.md §7.6 referencing it.

## Gaps to implement option-(b) (gather-all → consent → provision)

1. No **gather-all collector** — wizard check_gh is fail-fast; nothing enumerates ALL missing deps in one pass.
2. No Python/pip/claude check function in the wizard at all.
3. No **per-platform installer dispatch** in the wizard (fix strings exist as display text only; start.sh has apt/brew but unreachable from wizard, no Windows).
4. No **consent prompt** before provisioning anywhere.
5. No **unified dep manifest** consumed by a provision flow (start.sh hard-codes; requirements.txt unused by start.sh).

## Proposed R2 design (option b + consent) — for the INSTALLER-ARCH section

**Flow** (new Phase 0 behavior the section documents):
1. **Gather-all detect**: single pass enumerates EVERY missing/unsatisfied dep — gh (install+auth), Python3, pip, claude CLI, runtime py packages (from requirements.txt) — without bailing on the first.
2. **Present + consent**: show the human the full missing-set with the exact per-OS provisioning actions; ask one permission ("install these N items?").
3. **Provision on approval**: per-platform dispatch (winget/choco on Windows, brew on macOS, apt/dnf on Linux for system deps; `pip install -r requirements.txt` for packages; `gh auth login` interactive for auth). Items that can't be auto-installed (e.g. claude CLI via npm, gh auth) fall back to instruct.
4. **Re-verify** after provisioning; anything still missing → instruct + stop.

**Doc vs code split**: R2 (this task, PM) writes the INSTALLER-ARCH dep-provisioning **section** (the target design above + correct the §4.1/§3.1 drift to describe gather-all). The **implementation** (gather-all collector, per-platform dispatch, consent prompt, unified manifest, start.ps1) is a separate **skill** task — file post-section-approval.

**#11412 reconcile**: #11412 (low-sev, "document dep-provisioning, follow-up to #11403") is the same scope — fold into #11537, close #11412 as superseded.

## Open design questions for operator
- Q1: Does auto-provision run at **install time** (Phase 0, inside the wizard) or stay at **start.sh** (runtime boot), or both? (Research shows today it's split: gh-check at install, system-deps at boot.)
- Q2: For deps that genuinely can't be silently auto-installed (claude CLI = npm global; gh auth = interactive login) — confirm those stay **instruct/guided**, not forced.
- Q3: Scope of "provision": system tools (gh/python/claude) AND py packages, or py packages only (system tools = instruct)?
