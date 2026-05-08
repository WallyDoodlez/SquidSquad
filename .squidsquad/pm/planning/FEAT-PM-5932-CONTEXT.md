# FEAT-PM-5932 Context — L2 External Code Review Loop Before Pending-Test

## Scope

Add a mandatory external code review step between self-review (step 9b) and pending-test (step 10) in the dev agent Ralph Loop. The external model reviews changed files against ACs and project philosophy. Dev must disposition every finding before proceeding. Loop iterates until clean or 5-iteration cap.

## Locked Decisions (human decided)

- **Model**: Configurable per-project via config.md `Code Review Model` field under `## Model Routing`
- **Review scope**: Full changed files (`git diff --name-only HEAD`) + task ACs + project philosophy. Not just the diff — full file context
- **Loop cap**: Hardcoded at 5 iterations. Not configurable
- **Layer**: L2 — applies to all projects, not opt-in
- **Follow-up routing**: Filed to PM for triage, not to dev's own backlog
- **Disposition tracking**: Mandatory for every finding. Posted as PR comment (audit trail on the PR itself)
- **Disposition types**: Fix (apply the fix), File-to-PM (design flaw — reject and re-plan), Justified-ignore (document why not applicable)
- **File-to-PM = rejection**: When dev dispositions a finding as file-to-PM, it means the external reviewer found a design-level flaw (AC gap, philosophy violation, wrong approach). The review loop EXITS immediately. Dev's implementation is rejected — status transitions to `planning` (new transition: `in-progress → planning`, see #6057). PM receives the filed issue and decides: (a) re-plan — update ACs/CONTEXT.md, go `planned → approved`, dev picks up fresh, or (b) redirect to human review — `planning → pending-human-review` if human input needed. This is not a minor follow-up — it's a full re-plan signal
- **Git state**: All changes since HEAD captured at review-start. Dev stages before first review
- **Fallback**: If external model unavailable (exit code 1/2), falls back to Claude via Agent tool. Review still runs

## Dev Discretion (dev agent can choose)

- Internal structure of the model_router code-review task type
- Prompt template wording (must emphasize evidence-backed findings, not style opinions)
- How to format the PR comment (structured findings table vs prose)
- Whether to batch all dispositions in one PR comment or post incrementally

## Side Effect Mitigations (required)

- Self-review (step 9b) and external review are complementary, not redundant — document the distinction in implement-tasks.md
- The `justified-ignore` disposition must be explicitly documented as a valid, non-shameful outcome
- If >50% of findings across 3+ reviews are justified-ignore, escalate to human — the model or prompt needs tuning
- At 5-iteration cap with unresolved findings (all fix/justified-ignore, no file-to-PM), dev transitions to pending-test with findings noted. QA decides whether to accept or reject
- Review prompt must scope tightly to changed files — not entire repo

## Upgrade Path (required)

- New config.md field: `Code Review Model` under `## Model Routing` — default `claude` (zero behavior change for existing installs)
- New prompt template: `references/prompts/code-review.md.j2`
- Template change: `implement-tasks.md` gets new step between 9b and 10
- `compose.py deploy-all` regenerates dev agent CLAUDE.md
- Graceful degradation: if config.md has no `Code Review Model`, falls through to `claude` default

## Out of Scope

- Configurable loop cap (hardcoded at 5)
- QA running its own external code review (QA has its own verification flow)
- Security-specific review (future L3 concern)
- Design review (future designer-specific concern)
