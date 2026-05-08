Now I have a comprehensive view of the codebase. Let me finalize with a careful synthesis of all findings.

---

# FEAT-PM-5932 Research — L2 External Code Review Loop Before Pending-Test

## Summary
This task adds an external-model code review step between self-review (step 9b in `implement-tasks.md`) and pending-test (step 10). The dev agent runs `model_router.py` with a new `code-review` task type, passing changed files + ACs + project philosophy; an external model (configurable per-project via `config.md`, e.g. `deepseek-v4-pro`) returns findings. The dev must disposition every finding (fix / file to PM / justify ignore) before re-running review, looping until clean or 5-iteration cap.

The primary work is: (a) adding a `code-review` task type to `model_router.py` with a new prompt template, (b) adding a `Code Review Model` key to the `## Model Routing` config section, (c) modifying `implement-tasks.md` to define the new loop step, and (d) defining the disposition-tracking artifact. The biggest risk is **workflow friction**: if the external model produces false positives or low-value findings, the mandatory-disposition loop becomes busywork. The prototype in `REVIEW-5622-DEEPSEEK.md` shows a manual run produced 6 actionable issues — but that was a skilled agent running it, not a mechanical step. Mitigation: the disposition format must allow `justified-ignore` as a first-class outcome, not a guilt-ridden exception.

## Vault Context
- **BRIEFING.md priorities**: #5932 is itself the active task (pending, high). #5170 is the L4-variant predecessor (pending, medium). Human preference: "Dev agent disagreements with external code review escalate to human."
- **Related decisions**: [[decision-self-healing-sentinel]] — two-tier self-healing (detect gap → file root-cause bug) applies: if the code review loop itself reveals a process gap, the dev should file a bug. [[decision-vault-remember-source-agnostic]] — code review findings are valid signals for vault reflection (patterns, learnings).
- **Related patterns**: [[pattern-model-router-architecture]] — thin adapter, plugin manifests, exit-code contract (0=success, 1=fallback), agentic tool-use loop. The new `code-review` task type follows the same mold. [[pattern-deterministic-scripts-over-prose]] — the code review step in implement-tasks.md must be a concrete, scriptable procedure, not a prose suggestion.
- **Human preferences**: "Systems should self-heal" — the loop must self-terminate at 5 iterations with a clear outcome. "Prefers direct/mechanical checks" — the review should check concrete criteria (regression, AC coverage, philosophy violations), not subjective code aesthetics. "Never ship with failed TCs" — code review must not bypass failing tests. "Documents live on forge, not chat" — findings must be tracked in an artifact, not just scrollback.
- **Related learnings**: None directly on point. The `REVIEW-5622-DEEPSEEK.md` prototype is an implicit learning — external review found 6 concrete issues that self-review missed, validating the concept.

## Impact Analysis
- **Files touched**:
  - `references/scripts/model_router.py` — add `code-review` task type (not Claude-locked), add to `key_map` and CLI choices (lines ~137-150, ~989-998)
  - `references/prompts/code-review.md.j2` — NEW: prompt template for code review
  - `.squidsquad/config.md` — NEW key `Code Review Model` under `## Model Routing` (default: `claude`)
  - `references/sub-skills/roles/dev/implement-tasks.md` — insert new step between current 9b (self-review) and 10 (pending-test transition), replace existing steps 10-11 numbering
  - `references/sub-skills/common/working-state.md` — add optional disposition-tracking section to template (or define standalone artifact)
  - `tests/test_model_router.py` — add tests for code-review task type, config key parsing
- **Behavior changes**:
  - Dev agent gains a mandatory external model invocation before transitioning to pending-test
  - Dev agent must interpret and disposition structured findings from external model
  - Loop: fix/review cycle can iterate up to 5 times
  - If external model unavailable (exit code 1/2/3): falls back to Claude via Agent tool (standard model_router contract)
  - If `Code Review Model` is `claude`: spawns Claude subagent via Agent tool (exit code 1 → parent handles)
- **Dependencies**:
  - `model_router.py` code-review task type (must exist before implement-tasks.md can reference it)
  - Provider API key must be configured for whichever model is chosen (e.g. `DEEPSEEK_API_KEY`)
  - `capability_check.py` may need update if `code-review` requires capabilities not in dev manifest
  - No new Python packages required — model_router's existing `openai>=1.0.0` handles DeepSeek/OpenAI-compatible APIs

## Side Effects
- **Risk 1: False positives erode trust — dev ignores review entirely** — Severity: **H** — Mitigation: The `justified-ignore` disposition is explicitly documented as valid. The prompt template must emphasize concrete, evidence-backed findings (file:line, test failure, AC gap), not style opinions. If the dev disagrees with >50% of findings across 3+ reviews, escalate to human — the model or prompt needs tuning.
- **Risk 2: 5-iteration cap reached with unresolved findings — pipeline stalls** — Severity: **M** — Mitigation: At iteration cap, dev transitions to pending-test with a comment listing unresolved findings and justification. QA can then decide whether to reject back or accept with noted gaps. The cap is a safety valve, not a failure.
- **Risk 3: External model burns tokens on irrelevant files** — Severity: **M** — Mitigation: The `--input-files` parameter should include only actually-changed files (via `git diff --name-only HEAD~1` or similar), plus ACs and philosophy context as `--context`. Not the entire repo. The prompt template must scope the review tightly.
- **Risk 4: Self-review (9b) and external review (new step) overlap confusingly** — Severity: **L** — Mitigation: Self-review checks: regression, integration, philosophy, personas. External review checks the *same things* but from an independent-model perspective, plus AC coverage. The steps are complementary, not redundant. Document the distinction in implement-tasks.md.

## Edge Cases
- **External model unavailable (no API key, network down, quota exceeded)**: model_router exits 1 or 2. Per existing contract, dev spawns Claude subagent via Agent tool. The loop still runs — it just uses Claude for the external perspective. This is fallback, not failure. If even Claude Agent tool fails, escalate to human.
- **No files changed (config-only task, doc-only)**: The review still runs but may produce zero findings. Dev marks "no code changes to review" in dispositions and exits loop after first iteration. The prompt should detect this and produce a short "no code findings" output.
- **Changed files exceed model context window**: Need to decide truncation strategy. Options: (a) review files individually in sequence, (b) truncate large files at MAX_FILE_READ_BYTES (500KB, already in model_router line 82), (c) sample critical files. Recommendation: cap at first 10 changed files + ACs + philosophy, with a note "N files omitted due to context limits."
- **Concurrent edits during review loop**: If another agent pushes changes while dev is iterating on review, the changed-files list is stale. Mitigation: `git pull` at start of each review iteration before determining changed files. If new changes appear mid-loop, re-base the review on latest.
- **Dev agent context window pressure during loop**: Each iteration adds review findings → disposition → re-review to scrollback. After 3+ iterations, context pressure could exceed threshold (70%). Mitigation: Summarize prior dispositions compactly in the re-review context. The loop is bounded at 5 — worst case, agent exits at context pressure and resumes from working-state.md.
- **External model's findings reference files it shouldn't access**: The 4-layer security model (tool whitelist, path sandbox, no shell, sensitive deny-list) in model_router.py lines 252-279 applies. If the model requests `.env` or `~/.ssh/`, it gets "ERROR: Access to sensitive file denied." This is tested in `test_model_router.py` lines 87-121.

## Integration Risks
- **model_router.py currently only called by PM agents**: Dev agents (`skill`, `qa`) have no model_router invocation pattern in their composed CLAUDE.md. The `implement-tasks.md` sub-skill must include the full invocation syntax. This is fine — the compose system inlines it. Risk: if the dev agent's composed template doesn't include the model_router invocation, the review step silently skips. Mitigation: the implement-tasks.md step must include the exact `python references/scripts/model_router.py code-review ...` command with all required flags.
- **`Code Review Model` config key must be parsed by `_parse_model_routing()`**: Currently, `model_router.py` line 137-150 maps task types to config keys via `key_map`. The key transformation is: `code-review` → `code-review-model` → config field `Code Review Model`. The parser at line 112 matches `- **Key**: value` and lowercases/replaces-spaces. So `- **Code Review Model**: deepseek-v4-pro` → `code-review-model: deepseek-v4-pro`. This works without parser changes. Verified: existing test at `test_model_router.py:24-32` confirms the parsing pattern.
- **`CLAUDE_LOCKED_TASKS` set at line 49**: `{"comprehension", "qa-execution"}`. Code review is NOT Claude-locked (it's an advisory review, not safety-critical like QA execution). If a project wants Claude for code review, they set `Code Review Model: claude` in config.md, and model_router returns exit 1 → dev spawns Claude Agent tool.
- **QA's existing verification pipeline (Step 5 in `verification.md`)**: QA already does code review during pending-test verification (lines 132-285). The external review by dev before pending-test is a *pre-filter* to reduce QA rejection churn. It does not replace QA. If dev's review loop catches 80% of issues, QA gets cleaner submissions.
- **Working-state.md format**: Current template (`references/sub-skills/common/working-state.md`) has `Task`, `Status`, `Started`, `Completed Steps`, `Remaining Steps`, `Key Decisions`. Adding disposition tracking here is natural — the working-state file is already the dev's context-reset safety net. New field: `## Code Review Dispositions` with per-finding entries.
- **PR flow interaction**: If PR flow is enabled, the code review findings may reference files that haven't been pushed to the PR yet (they're staged or in the working tree). The `--input-files` must use the working tree state (`git diff --name-only HEAD` or `git diff --cached --name-only`), not the last pushed commit.

## Upgrade & Migration
- **New config values**:
  - `Code Review Model` under `## Model Routing` — default: `claude` (no behavior change for existing installs)
- **New files**:
  - `references/prompts/code-review.md.j2` — prompt template for code review
  - _Possibly_: `references/sub-skills/roles/dev/code-review-disposition.md` — if disposition format is a separate sub-skill (alternative: inline in implement-tasks.md)
- **Template changes**:
  - `implement-tasks.md`: new step inserted between 9b and 10, renumbering existing 10→11 etc.
  - `working-state.md`: optional `## Code Review Dispositions` section
  - `dev/includes.yml`: no change needed (implement-tasks.md is already included)
  - `dev/instructions.md`: no change needed (includes are resolved via manifest)
- **Upgrade steps**: `compose.py deploy-all` to regenerate dev agent CLAUDE.md templates. Config.md gets new key with default `claude` — existing installs are unaffected. Users who want external review set `Code Review Model: deepseek-v4-pro` and provide `DEEPSEEK_API_KEY`.
- **Graceful degradation**: If config.md has no `Code Review Model` key, `_parse_model_routing()` returns empty `{}`, `get_model_for_task("code-review")` falls through to `routing.get("default-model", "claude")` → `claude` (line 147-148). Dev spawns Claude Agent tool — review still runs, just with Claude. Zero pipeline blockage. If user sets an external model but no API key: exit code 2, falls back to Claude. Fully degraded path works.

## Open Questions
- **Q1**: Should the dev commit dispositions to the repo (audit trail) or keep them in working-state.md (ephemeral)? — **Why**: Dispositions are audit evidence that review was performed. If someone later asks "was this reviewed?", the disposition file is the answer. But committing adds git noise. Recommendation: dispositions file stays in `.squidsquad/[ROLE]/planning/` (like QA-RESULTS.md) and is committed to the state branch. Human preference: "Git = audit trail."
- **Q2**: What happens when dev's disposition is `file-to-PM` — does the loop pause until PM acts? — **Why**: If the dev files a follow-up and continues the loop, the PM filing hasn't been triaged yet. The finding is dispositioned but unresolved. Recommendation: `file-to-PM` counts as dispositioned for loop-exit purposes. The PM issue is the tracking mechanism.
- **Q3**: Should the review use `git diff` (unstaged + staged) or `git diff --cached` (staged only) to determine changed files? — **Why**: Per implement-tasks.md step 9 "Verify changes exist" runs `git_ops.py has-changes` (which checks `git status --porcelain`), so there are uncommitted changes. If dev hasn't staged yet, `--cached` is empty. Recommendation: use `git diff --name-only HEAD` (all changes since last commit) at the time review starts, then `git add -A` before first review to include everything.
- **Q4**: Is the 5-iteration cap configurable or hardcoded? — **Why**: Per task spec it's locked at 5. But projects with higher quality bars might want 3, and faster-moving projects might want 2. Recommendation: hardcode 5 as per LOCKED DECISIONS. If demand emerges, make it configurable in a follow-up.

## Recommendation
**Feasible with caveats.** The model_router architecture already supports the pattern — adding a `code-review` task type is ~50 lines of code (config key, prompt template, CLI choice) plus template changes to implement-tasks.md. The primary caveat is designing the disposition format and loop mechanics to be lightweight enough that devs don't resent the process. The prototype REVIEW-5622-DEEPSEEK.md demonstrates that external review finds real issues self-review misses (6 concrete findings), validating the approach. The fallback-to-Claude path ensures zero pipeline blockage.

Key implementation priorities:
1. Code-review prompt template must emphasize evidence-backed findings (file:line, AC gap, test failure), not style opinions
2. Disposition format must explicitly permit `justified-ignore` as a valid outcome
3. Loop must self-terminate cleanly at cap with a "review incomplete — noted gaps" flag
4. The step in implement-tasks.md must be a concrete, copy-paste-able procedure with exact commands

## Vault Candidates
- **Type**: learning — "REVIEW-5622-DEEPSEEK.md prototype: external DeepSeek review found 6 actionable issues that self-review (implement-tasks.md step 9b) missed. External models catch different failure modes than the implementing agent." — **Why**: Validates the core premise of #5932. Preserve as evidence that external review adds value beyond self-review.
- **Type**: pattern — "Code review disposition format: every finding must be addressed as fix / file-to-PM / justified-ignore. Un-dispositioned findings block pending-test transition. This is the same pattern as QA's zero-gap gate (verification.md line 194-197)." — **Why**: Reusable pattern for any future review-gate step. The "disposition everything before proceeding" pattern is a general quality gate.
- **Type**: decision — "External code review uses working-tree state (`git diff HEAD`), not staged-only or last-pushed. Changed-files list is captured at review-start to prevent drift during the fix/review loop. Concurrent remote changes trigger re-base." — **Why**: The timing of file capture matters for correctness. If the review sees stale files, findings are invalid. This should be a locked decision.
- **Type**: pattern — "External model review loop: run → get findings → disposition all → fix → re-run → exit when clean OR 5 iterations. Same loop structure applies to any L2/L3 review gate (design review, security review, accessibility review)." — **Why**: The loop structure (run, disposition, fix, re-run) is generic. Vault it so future review gates can be bolted on without redesigning the loop mechanics.