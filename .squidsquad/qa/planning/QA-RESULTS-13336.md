# QA-RESULTS-13336 — Retire WIZARD.md; INSTALLER-RUNTIME.md as installer operating manual

**Issue**: #13336 (operator-filed task, priority:high, keystone of the INSTALLER-RUNTIME set)
**PR**: #13358 `squidsquad/task/13336` (5 commits, 16 files, +537/−1337)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13336.md` (ACs from issue body + PM-locked Discussion amendments)
**Verdict**: **FAIL — 1 finding (AC3: README). Back to In Progress.** Everything else passes; this is a #13318-round-1-class doc-only gap.

## THE FINDING (AC3 FAIL) — README.md untouched; describes the retired flow and contradicts the §3 PR invariant

**Finding**: issue-body AC3 enumerates the repoint surfaces: "wizard.py docstring/header, references/installer-files.txt, **README**, docs/INSTALLER-ARCH.md, tests, sub-skills". The PR touches no README. Root `README.md` still describes the retired installer:

1. **README.md:67** — "…launches an intent-driven setup wizard. The wizard asks 3 quick questions — what your project does, then 2 adaptive follow-ups based on your answers…" — this is the adaptive Q1/Q2/Q3 questionnaire that THIS task's coverage checklist declares **OBSOLETE** (bucket 3, operator-confirmed) and that no longer exists on this branch.
2. **README.md:67 (same paragraph)** — "…walks you through setup including whether you want **PR Flow (human review gate on every change) or direct commits**." — direct contradiction of the §3 invariant this same PR enshrines ("committing straight to the main line is **never offered**"; test bans `pr-flow-prompt` from the manual; PM's correction: "the only surviving related question is the merge gate"). A doc-vs-spec contradiction on exactly the point PM corrected mid-task.

**Why the AC6 grep gate missed it**: README never contained the literal string `WIZARD.md`, so the zero-stray-reference grep passes — but AC3 names README as a surface, and the *content* describes the deleted runbook's flow. Same failure shape as #13318 round 1 (README stale after script deletion).

**Evidence**: `git diff main...HEAD --stat` (no README in the 16 files); `grep -ni "wizard" README.md` lines 33/41/48/67/69/82/133/139 — lines 67's two claims above are the stale ones (33/41/48/82/133/139 remain accurate: soul-filling, model routing, per-agent clones, worker-variant ask, `setup-yes` verified still dispatched at wizard.py:3842).

**Required for re-verification**: update README's setup description (the line-67 paragraph) to the describe-and-confirm model — no fixed 3-question script, and PR-review framing without a "or direct commits" choice (merge gate = the variable). Nothing else reblocks; all other ACs stand (doc-only delta → re-verify will be README + suite re-run only, per the #13318 round-2 pattern).

## AC walk

| AC | Result | Evidence |
|---|---|---|
| AC1 coverage checklist, no mechanic dropped | PASS | Checklist posted + PM-reviewed; §9 spot-audit: all 16 ABSORBED mechanics physically present with semantics intact (3-gate migration walk + stamp-version, gather/provision/re-verify + hard/soft split, check-existing 3-way + typed `delete and rebuild` + deferred deletion, setup_requirements walker incl. only_in_presets/repo_hints/per_installed_agent/variant→roster, restart-agents 3 branches + never-auto-spawn, L4 enrich never-overwrite, error recovery targeted-retry/push-failure, ensure-labels no-rollback, model-routing silent-skip + graceful degrade, forgejo flow). OBSOLETE artifacts absent from the manual ([P/V/E/A], Q1-Q3 script, loop-interval ask, pr-flow choice) |
| AC2 WIZARD.md deleted | PASS | `references/wizard/` gone; diff-filter=D = exactly `references/wizard/WIZARD.md` |
| AC3 every reference repointed | **FAIL** | README untouched + stale (see THE FINDING). All OTHER named surfaces clean: wizard.py docstrings, installer-files.txt:14, SKILL.md:313, INSTALLER-ARCH (11 live sites + historical §14 declared), COMPOSE-ARCHITECTURE, migrations/README, tests, packages/cli |
| AC4 installer boots on the manual (HARD GATE) | PASS | cli/index.js:316 setupCommand reads `docs/INSTALLER-RUNTIME.md` top-to-bottom; L363 seed commit stages the manual; installer-files.txt ships it; Read-targets-exist test shipped; helper trio named in prose exists on disk |
| AC5 depth-weighted step 6 + profession shift | PASS | §4 step 6 "go deep" (PM/DM) vs "lighter/confirm, don't excavate" (Workers/Verifier); §4 step 3 "from here on speak their profession's language" |
| AC6 zero stray refs + checklist reviewed | PASS* | Repo-wide sweep: every hit = live repoint, declared-historical (ARCH §14 below new entry; comprehension specs 11613/12419/12420 — runner verified strictly per-spec-path at run_comprehension_test.py:451-458, no all-specs walk, stale source_file inert), or qa-lane iteration logs. *Literal-grep passes; the README content gap is filed under AC3 |
| AC7 consent verbatim + exact test | PASS | § Consent wording — verbatim + §4 step-0 "do not paraphrase" binding; `test_consent_wording_is_verbatim_scripted` locks the script line-by-line |
| AC8 tests rewritten + gates green + CQ | PASS | test_wizard_runbook.py rewritten to narrative contract (_WIZARD_COMMANDS kept + extended), test_installer_wiring.py + no-resurrection guard, 3 files = 69/69 standalone; **static gate on branch: 5210 passed, 0 failures, 0 errors**; CQ spec 13336_spec.json (6 Qs, verifier-reviewed) |

## Comprehension test (fresh sonnet agent, INSTALLER-RUNTIME.md + SKILL.md decl only)

**11/11 PASS, zero misreads** — my CQ-A..E (manual-first + dep sequence, consent-verbatim refusal, no loop-interval question + defaults 30m/70, PR-invariant + merge-gate-only, depth weighting) and worker's CQ1-6 scenarios (write discipline + 3 exceptions, one-consent provisioning + hard/soft, check-existing choices + deferred deletion, migration-gate failure = git restore + no stamp + clean stop, restart-agents branches + never-self-start, ephemeral exit).

## Landing safety

Base main; 11 behind (all qa/skill state + merge commits, benign); only deletion = WIZARD.md itself; no fleet/state artifacts.

---

# ROUND 2 — 2026-07-06 ~19:55 — **PASS, zero gaps**

**Scope** (per the round-1 rejection): README + suite re-run only.

- **AC3 fix confirmed** (commit e504ff52b on PR #13358): README.md Quick Start paragraph repointed to the describe-and-confirm model (reads docs/code, describes back, user corrects before write) and the SS3 invariant framing — every change lands via reviewable PR; the merge gate (approve-each vs self-merge-on-verification) is the ONLY variable. Wording cross-checked 1:1 against docs/INSTALLER-RUNTIME.md §3 (L41: "The pull request is always there — only the human gate is optional") and §9 (L204: "never a question ... no 'PR flow on/off' choice").
- **Residual sweep clean**: zero README hits for `quick questions` / `adaptive follow` / `direct commits` / `PR Flow` / `WIZARD.md` on branch HEAD.
- **Delta discipline**: fix commit = 1 file, +1/−1 (the README paragraph). Branch total delta vs main (17 files, +538/−1338, sole deletion = WIZARD.md) unchanged from the round-1-verified scope.
- **Static gate independently re-run on branch HEAD e504ff52b: 5246 passed / 0 failures / 0 errors.**

**Process notes**: verdict-before-merge ordering applied (learning from the #13335 record-gap incident) — issue verdict comment posted BEFORE the squash-merge (7f21facde). Approve-review blocked by GitHub's same-author rule (all agents share one account); verdict recorded on the issue + here instead. `git_ops.py pr-merge` explicitly delegates issue closure to GitHub auto-close ("PR linked to #13336 — GitHub auto-close will handle issue state") — fact added to #13371's triage.

**Verdict: PASS — zero gaps. #13336 → pending-ship** (transition executed post-merge; DM woken for ship bookkeeping).
