# TEST-PLAN-13336 — Retire WIZARD.md; INSTALLER-RUNTIME.md becomes the installer operating manual

**Source**: issue #13336 body ACs + PM-locked amendments in Discussion (bucket-3-obsolete confirmation, consent verbatim carve-out, cli/index.js hard gate, threshold-70 + pr-flow-prompt corrections). Locked spec artifact: `docs/INSTALLER-RUNTIME.md` (PR #13331, merged).
**Derived from ACs + Discussion contract — not from the PR #13358 diff.**
Deletion-task class → apply [[learning-verify-deletion-task-by-repo-wide-consumer-sweep]] (repo-wide consumer sweep, #13318 precedent: stale-ref rejection).

## ACs (issue body + PM amendments)

- AC1: coverage checklist maps every WIZARD.md section → new home or explicit obsolete note; **no mechanic silently dropped** (PM reviewed; 2 corrections must be landed: silent defaults 30m/**70**; pr-flow-prompt **OBSOLETE**, merge-gate only).
- AC2: `references/wizard/WIZARD.md` deleted.
- AC3: every WIZARD.md reference repointed → INSTALLER-RUNTIME.md (wizard.py docstrings, installer-files.txt, README, INSTALLER-ARCH.md, COMPOSE-ARCHITECTURE.md, SKILL.md, migrations/README, tests, sub-skills).
- AC4: installer session boots following INSTALLER-RUNTIME.md top-to-bottom — **HARD GATE (PM)**: `packages/cli/index.js` spawn-time setupCommand reads the manual, not the deleted file; every Read target in setupCommand exists on disk; installer-files.txt ships `docs/INSTALLER-RUNTIME.md`.
- AC5: depth-weighted step 6 (PM/DM deep, Worker/Verifier lighter) + post-step-3 profession-language shift reflected in the wiring (manual the session reads).
- AC6: gate — grep shows **zero stray** WIZARD.md references on live surfaces; retained-historical mentions must be itemized/justified.
- AC7 (PM): consent wording stays **verbatim** + an exact-consent-script test exists.
- AC8 (standard): tests rewritten to the new narrative contract (test_wizard_runbook.py RUNBOOK path + invariants, `_WIZARD_COMMANDS` allowlist kept; test_installer_wiring.py incl. no-resurrection guard), full static gate green, CQ spec `tests/comprehension/13336_spec.json`.

## Test cases

- **TC-1 (AC2)**: branch has no `references/wizard/WIZARD.md`; deletion present in diff.
- **TC-2 (AC6)**: repo-wide sweep `grep -rn "WIZARD"` (case-insensitive variants + `wizard.md`) over live surfaces: references/scripts+sub-skills+wizard, docs/, tests/, packages/, SKILL.md, README, migrations/. Every hit must be (a) repointed, (b) an itemized retained-historical (ARCH §14 revision log below the new entry, comprehension specs 11613/12419/12420, teammate `.squidsquad/` artifacts), or (c) a FAIL. Cross-check each claimed-historical is genuinely non-live (no automated reader consumes it).
- **TC-3 (AC1)**: coverage-checklist spot-audit — sample ABSORBED rows physically present in INSTALLER-RUNTIME.md §9: migration walk (3 gates + stamp-version), setup_requirements walker semantics, restart-agents (#12420 reachable/partial/unreachable + never auto-spawn), build-config-md preview + never-touch-real-.squidsquad, error-recovery (targeted retry past commit, push-failure), gather-deps/provision-deps + re-verify, shared_fs init, ensure-labels no-rollback, L4 enrichment (never overwrite Stack/Test Command). OBSOLETE rows absent from the manual: verbatim intent-classifier prompt, [P/V/E/A] menu, adaptive Q1/Q2/Q3 questionnaire, Step-5 loop-interval ask, pr-flow on/off choice.
- **TC-4 (AC4 hard gate)**: `packages/cli/index.js` setupCommand mentions INSTALLER-RUNTIME.md and no WIZARD.md; every `Read`-target path named in the setupCommand prose exists on disk (run the shipped test + independent check); `references/installer-files.txt` lists `docs/INSTALLER-RUNTIME.md` and not `references/wizard/WIZARD.md`.
- **TC-5 (AC7)**: consent wording present verbatim in the manual; a test asserts the exact consent script; consent NOT declared obsolete anywhere.
- **TC-6 (AC1 corrections)**: §9 silent defaults = 30m / 70 (zero "80" for threshold); merge gate (Auto Merge) is the only PR-related variable; a test bans `pr-flow-prompt` in the manual.
- **TC-7 (AC5)**: manual carries depth-weighted step-6 + profession-language shift (IR §4 steps 3/6, §2); SKILL.md source-of-truth declaration points at the manual.
- **TC-8 (AC8)**: run rewritten test files + full static gate — all green; `_WIZARD_COMMANDS` allowlist retained.
- **TC-9 (landing safety)**: `git diff main...HEAD --diff-filter=D` = ONLY `references/wizard/WIZARD.md`; behind-count sane; no fleet/state artifacts touched.
- **TC-10 (regression sanity)**: worker suite relevant files pass standalone.

## Coverage matrix
AC1→TC-3,TC-6 · AC2→TC-1 · AC3→TC-2 · AC4→TC-4 · AC5→TC-7 · AC6→TC-2 · AC7→TC-5 · AC8→TC-8,TC-10 · meta→TC-9

## Comprehension Questions (LLM-consumed installer instructions)

Files: `docs/INSTALLER-RUNTIME.md` (+ SKILL.md repointed declaration). Worker spec at `tests/comprehension/13336_spec.json` (6 Qs over §9) — verifier reviews it, then runs fresh-agent CQ with my own derived questions:

- **CQ-A**: A fresh installer session starts. What document do you follow, top-to-bottom, and where is the exact wizard.py call sequence for dependency provisioning? (Expect: INSTALLER-RUNTIME.md; §9 playbook gather-deps → present → consent → provision-deps → re-verify.)
- **CQ-B**: May you rephrase the step-0 consent wording to sound friendlier? (Expect: NO — consent is the verbatim carve-out; adapt everything except consent.)
- **CQ-C**: What loop-interval question do you ask the user at step 5, and what threshold default applies? (Expect: none — silent defaults 30m / 70.)
- **CQ-D**: The user wants direct commits to main instead of PRs. What do you offer? (Expect: nothing to offer — PR flow is an invariant; only the merge gate / Auto Merge is a variable.)
- **CQ-E**: How deep do you go when confirming each agent at step 6? (Expect: depth-weighted — PM/DM deep, Worker/Verifier lighter.)
