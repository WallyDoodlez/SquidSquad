# TEST-PLAN #12419 — Installer migration-walk (INSTALLER-ARCH §10)

Derived independently from the issue's 6 ACs + AC-CQ, against INSTALLER-ARCH §10/§4.3 (locked
upgrade model: upgrade = fresh-install flow + migration-walk). PR #12533, branch task/12419.

## ACs → Test Cases

| AC | TC | Method | Expected |
|----|----|--------|----------|
| AC1 existing reads version + selects chain; fresh skips | TC1 | own fixture: dir with/without `.squidsquad/` + stamped config.md | fresh → is_fresh, no walk; existing → reads stamp, builds chain |
| AC2 per-version files applied in version order | TC2 | own fixture: out-of-order migration files on disk, one below-installed, one above-target | chain sorted ascending by target; out-of-range excluded; missing step absent (silent) |
| AC3 three-gate model per §10 | TC3 | read WIZARD Step 0b.1 prose | Gate1 DeepSeek audit (no write) → Gate2 mini-CQ (no write) → apply atomically → Gate3 compose dry-run (revert-on-fail); abort-clean at any gate |
| AC4 non-migrated preserved; installer stamps, not migration files | TC4 | own fixture: stamp_version + preservation; WIZARD prose | exactly one version line written, other config preserved; prose states migrations MUST NOT set version |
| AC5 WIZARD Step 0b updated (doc+runbook in sync) | TC5 | read WIZARD Step 0b | flat 3-way prompt replaced by Upgrade-default / Full-rebuild / Abort + Step 0b.1 walk |
| AC6 tests: fresh vs existing; sample migration; preservation | TC6 | pytest | green |
| AC-CQ comprehension (WIZARD LLM-consumed) | TC7 | author `tests/comprehension/12419_spec.json`; fresh sonnet agent quiz on Step 0b/0b.1 prose | zero branch-semantics misreads |

## Comprehension gate
REQUIRED — WIZARD.md is the LLM-consumed installer runbook. Verifier authors the spec
(`tests/comprehension/12419_spec.json`, 6 CQs covering branch presentation, three-gate walk,
version-order apply, installer-stamps-not-migrations, full-rebuild typed-confirm + deferred
deletion, preservation), quizzes a fresh sonnet agent given ONLY the Step 0b/0b.1 prose.
