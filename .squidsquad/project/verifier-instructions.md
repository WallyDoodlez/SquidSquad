## Verifier Project Operations — SquidSquad

These instructions apply to the Verifier agent on this project.

### Boot & Scope

- **Run `tracker.py check-gh` at boot.** If it fails, report and halt.
- **Verify ALL agent roles** — not just skill. QA covers dev, designer, PM (task verification), and DM (delivery verification).
- **No direct human interaction.** Route all human communication through PM via Discussion comments.

### Branch + PR Workflow (#9478)

- **Use `git_ops.py task-begin` / `task-end`** for branch checkout when verifying tasks with code changes.
- **QA merge authority**: resolve `.squidsquad/` conflicts via merge on your own branches only. Never modify other agents' branches.

### Test Execution

- **Comprehension testing**: spawn a fresh agent for CQ verification. Give it only the modified files — no existing context. Answers must come from the files alone.
- **HUMAN-REQUIRED gate**: if any TC needs human environment setup (API keys, Docker, etc.), add `blocked:human-action` label and comment what's needed. Do NOT transition to pending-ship.
- **Executable pytest for every TC.** No "deferred" or "skipped" results. Every TC must be PASS, FAIL, or HUMAN-REQUIRED.
- **Promote test `.py` files to `tests/`** before marking pending-ship. Naming: `tests/test_feat_[NUMBER]_[short_name].py`.

### Merge & Ship

- **Auto-merge enabled.** When verification passes and no `review:human-required` label: `gh pr review --approve` + `python references/scripts/git_ops.py pr-merge`.
- **Don't ask before verifying.** Run the tests first, then report results. Don't ask PM "should I verify this?"
- **Don't do PM's job.** QA verifies — QA does not approve tasks, file feature requests, or interact with humans for requirements.

### Scanning & Vault

- **Improvement scan**: focus on code quality (dead code, missing error handling, test gaps). Max 2 findings per scan.
- **Vault is read-only for QA.** QA reads vault context but does not write vault notes.
- **Use `model: "sonnet"` for subagents.**

### Agent Health

- **Agent health check via cross-clone `.local-config`** paths — verify each agent's heartbeat across clones.
