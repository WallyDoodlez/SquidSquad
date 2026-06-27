# TEST-PLAN-13042 — decay() must not rewrite `updated:` (VAULT-ARCH §4.4)

- **Issue**: #13042 (type:issue, severity:medium, role:skill) — `vault_optimize.py` decay() rewrites `updated:` to today in the same op as the confidence change, contradicting VAULT-ARCH §4.4 ("Decay steps do NOT modify `updated:`").
- **PR**: #13065, branch `squidsquad/task/13042`, HEAD `1f441506f`. Files: `vault_optimize.py` (+9/-3), `tests/test_vault_optimize.py` (+29/-0). `Fixes #13042` (closing keyword).
- **Derived**: 2026-06-21 00:30 from observed/impact/spec. Deterministic code → **NO CQ**.
- **Method**: isolated worktree; regression suite; **independent negative-verify** of the new test against main's pre-fix code; full static gate.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | decay() no longer rewrites `updated:` — both the frontmatter-path `re.sub` and the fallback `re.sub` are removed. | Diff: both `re.sub(r"updated: \S+", ...)` lines gone. |
| AC2 | decay() still rewrites `confidence:` (the decay itself still applies). | Diff: `header.replace(confidence...)` retained. |
| AC3 | The decay event is still recorded via the changelog entry (correct audit trail; `today` is consumed there, not orphaned). | Diff: changelog entry retained. |
| AC4 | A regression test locks the fix and would have caught the original bug. | `test_decay_preserves_updated_field` passes on branch AND fails against main's pre-fix code (negative-verified). |
| AC5 | No regression. | `run_tests.py static`. |
