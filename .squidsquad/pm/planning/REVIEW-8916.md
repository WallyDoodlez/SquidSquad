I have thoroughly reviewed the TEST-PLAN document against the relevant files. Here are my findings:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: AC-3 (lines ~35-37), the verification command block
- **Severity**: error
- **Issue**: AC-3 specifies `python references/scripts/compose.py deploy-all --diff-only --mode loop` as a verification command, but `compose.py` does not support `--diff-only` or `--mode` flags. The script uses a simple positional-argument command dispatch (`deploy-all`, `deploy`, `all`, `upgrade-soul` — lines 1235-1298) with no argparse-based flag parsing. These flags don't exist anywhere in the codebase (confirmed via grep for `diff.only|diff_only|mode.loop|--mode` in `compose.py` — zero matches).
- **Evidence**: `compose.py` lines 1235-1298 show the command dispatch is purely positional (`cmd = args[0]`). The script has no argparse usage and no `--diff-only` or `--mode` arguments. The verification command is not executable.
- **Suggested fix**: Either (a) drop `--diff-only --mode loop` from the verification command and instead specify: run `compose.py deploy-all`, then verify that non-dev roles (PM, QA, DM) have byte-identical CLAUDE.md output via `git diff` against a pre-change deploy, OR (b) explicitly note that adding `--diff-only` / `--mode` support to `compose.py` is in scope for #8916 (though that would be a scope creep beyond the single `implement-tasks.md` fragment edit described in the Scope section).

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: R1 (lines ~53-54)
- **Severity**: warning
- **Issue**: R1 states "no change expected since the new step is in common-dev/ or roles/dev/, not mode-gated." This premise is incorrect. The fragment `roles/dev/implement-tasks` is included in **both** the /loop manifest (`references/roles/dev/includes.yml` line 12) **and** the events-mode manifest (`references/roles/dev/includes-events.yml` line 18). Because both manifests reference the same fragment file, editing `implement-tasks.md` WILL change the composed output for the skill/dev role in /loop mode. The /loop output will NOT be byte-identical — it will contain the new step.
- **Evidence**: `includes.yml` line 12: `- roles/dev/implement-tasks`; `includes-events.yml` line 18: `- roles/dev/implement-tasks`. Both manifests include the same fragment.
- **Suggested fix**: Rewrite R1 to acknowledge that the /loop mode skill CLAUDE.md WILL change (the new planning-artifact step is mode-agnostic and should appear in both modes). The real regression risk to test is that non-dev roles (PM, QA, DM) must remain byte-identical — their manifests do not include `roles/dev/implement-tasks`. The AC-3 text partially captures this ("/loop output unchanged for non-skill roles") but R1's reasoning contradicts it.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: Scope section (lines ~8-19) — the behavior specification for the new step
- **Severity**: warning
- **Issue**: The TEST-PLAN's Scope block describes a new step to be added "BEFORE implementation starts," but the existing `implement-tasks.md` already has a "Read planning artifacts" step at lines 13-18 (step 2 in the current flow) that partially covers the same ground — it already directs the dev to check `.squidsquad/pm/planning/`, look for CONTEXT.md and TEST-PLAN.md, and "respect locked decisions." The TEST-PLAN does not specify whether the new step **replaces** the existing step 2, **augments** it, or is inserted as an additional step. If both coexist, the agent gets redundant (and potentially contradictory) instructions — e.g., the existing step 2 says to check `.squidsquad/[ROLE]/planning/` as a fallback location, while the new step only mentions `.squidsquad/pm/planning/`.
- **Evidence**: Current `implement-tasks.md` lines 13-18 already handle planning artifact discovery. The TEST-PLAN Scope adds authority rules ("planning artifact is the authoritative scope", "CONTEXT.md wins") that the existing step lacks, but doesn't address the overlap.
- **Suggested fix**: Add an explicit directive to the Scope section: either "replace the existing step 2 (lines 13-18) with the new block" or "insert the new block as step 2, remove the old Read planning artifacts step, and fold its fallback-location logic into the new step." AC-1 should verify that the old file-pattern guidance (`.squidsquad/[ROLE]/planning/` fallback) is either preserved or intentionally removed.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: R2 (lines ~55-56) and CQ list (CQ-1 through CQ-3)
- **Severity**: warning
- **Issue**: R2 identifies a regression risk: "Skill might flag divergence on every PR even when bodies are in sync." The mitigation is "phrasing should be 'if divergence exists, flag it' not 'always note CONTEXT.md ref.'" However, no comprehension test (CQ) verifies the *non-divergence* case. CQ-1 tests that the agent picks CONTEXT.md over a conflicting issue body, and CQ-2 checks what files to look for, but none asks "If issue body and CONTEXT.md agree, what do you do?" Without a CQ for the agreement case, there is no verification that the conditional "flag only on divergence" behavior is correctly encoded in the fragment. The same incident pattern (lazy implementation that flags every time regardless) could recur at the fragment level.
- **Evidence**: The three CQs test the authority rule, the file patterns, and the code-review input files — but none test the non-divergence path specified by R2's mitigation.
- **Suggested fix**: Add a CQ-4: "You are implementing task #1234. The GitHub issue body says 'thin harness, no dispatch logic' and CONTEXT.md §5.4 also says 'thin harness, no dispatch logic.' After reading CONTEXT.md, what do you put in the PR description about planning artifacts?" Expected answer: nothing (or a brief note that scope matches — not a divergence flag). The key is that the agent does NOT flag a non-existent divergence.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: Scope section, line ~14 (`## 5.X #<NUMBER>`)
- **Severity**: warning
- **Issue**: The Scope section instructs the agent to read the relevant CONTEXT.md section identified as `## 5.X #<NUMBER> — ...` (h2 heading). However, the actual `CONTEXT.md` file uses `### 5.X #<NUMBER> — ...` (h3 headings) for per-task sections (confirmed at lines 329, 432, 477, 550, 589, 629, 666 of CONTEXT.md). If the implementer copies the `##` heading level from the TEST-PLAN into the fragment text, agents will search for an h2 heading that doesn't exist and may fail to locate the correct section.
- **Evidence**: CONTEXT.md uses `### 5.1 #8694 — Event-Mode L1 Base Agent Definition (lead)` (line 329), `### 5.2 #8695 — ...` (line 432), etc. The TEST-PLAN specifies `## 5.X`.
- **Suggested fix**: Change `## 5.X` to `### 5.X` in the Scope section's inline fragment text. The actual CONTEXT.md format is the ground truth.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8916.md`
- **Line**: Scope section — §9c change description (lines ~17-18)
- **Severity**: warning
- **Issue**: The scope says to "feed the CONTEXT.md section as part of the review input-files." This is imprecise about *which* section and *how* to resolve it. The §9c code-review loop runs on changed files (`git diff --cached --name-only`). The CONTEXT.md / TEST-PLAN files are planning artifacts — they are not typically part of the git diff for a PR. The implementer must determine: (a) how to locate the correct CONTEXT.md section (by parsing the task number from CONTEXT.md headings, or using CONTEXT-<NUMBER>.md), (b) whether to pass the entire CONTEXT.md or extract the relevant section, and (c) how to pass files outside the diff to `--input-files`. AC-2 partially addresses this by saying the invocation must list `CONTEXT*.md` in `--input-files`, but the Scope's "feed the CONTEXT.md section" language is misleading if the implementation actually passes the whole file via glob. The TEST-PLAN should make the implementation contract explicit.
- **Evidence**: Current §9c at lines 44-51 shows `$CHANGED_FILES` derived from `git diff --cached --name-only`. Planning artifacts live under `.squidsquad/pm/planning/` and are not in the diff. The Scope text "feed the CONTEXT.md section" suggests extracting a subsection; AC-2 says "list CONTEXT*.md in --input-files" which suggests passing the whole file.
- **Suggested fix**: Align Scope and AC-2. Either explicitly say "pass the full `.squidsquad/pm/planning/CONTEXT.md` and `.squidsquad/pm/planning/TEST-PLAN-<NUMBER>.md` as additional `--input-files` arguments beyond `$CHANGED_FILES`" or specify how to extract and pass only the relevant section. The current tension between "section" (Scope) and "CONTEXT*.md glob" (AC-2) creates implementation ambiguity.

---

### Summary

The TEST-PLAN has two hard issues that block clean verification: (1) AC-3's verification command literally doesn't exist, and (2) R1's "no change expected" claim is factually wrong because the fragment is included in both manifests. Three additional warnings cover gaps that could let the same incident pattern recur (no CQ for non-divergence, missing replacement-vs-augmentation guidance for the existing step 2, and a heading-level mismatch that could cause agents to miss the correct CONTEXT.md section). Finding 6 is a specification precision issue between Scope and AC-2 that could lead to inconsistent implementation.