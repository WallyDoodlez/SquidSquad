## #13212 — stage verifier-authored comprehension specs in the post-cycle commit

(qa-filed improvement-scan; cluster root, front-loaded plan on the issue.)

### RCA — two distinct findings, disentangled
1. **DURABLE BUG (fixed here):** `git_ops._role_owned_patterns` had **no** entry matching `tests/comprehension/`. `commit_role_scoped` reads `git status --porcelain` (which *does* list untracked `??` files) and stages by role pattern — so every new comprehension spec was classified **foreign** and left untracked, landing only via qa's manual "recover N-behind" rescue commits (e.g. `304a0990e`). These are verifier-authored **permanent regression assets** (#9184) that must land automatically.
2. **NOT a staging bug (out of this slice):** the `.squidsquad/qa/planning/` accumulation + 99-behind clone. Those paths **already** match `.squidsquad/qa/`, so they stage fine *when post-cycle runs*. Their accumulation = post-cycle **did not run** during the qa wedge (a liveness symptom tracked by **#12271**, recovered manually) — out of `cycle_post`'s control. Folding a liveness fix into this commit would be scope-creep.

### Fix
Add `tests/comprehension/` to the **qa (verifier)** `role_specific` patterns. Scoped to qa only — the verifier authors comprehension specs; skill never self-authors them (skill-cq). Purely **additive**: only expands what qa stages; foreign-file skip, the #11083 branch-guard, and push-role propagation are untouched.

### Verification
- +3 tests: `test_qa_extras` (positive + boundary), `test_comprehension_specs_are_qa_only` (qa-only isolation across pm/dm/skill), `test_qa_stages_untracked_comprehension_spec_13212` (behavioral — the exact `??` untracked porcelain status staged, not foreign-warned).
- Full static gate: **4965 passed, 0 failures, 0 errors**.
- DS code-review: **NO_FINDINGS** (DS-REVIEW-13212.md on main).
- No CQ (deterministic code, not LLM-consumed). No manifest (no new tracked files).

### Cluster context
Part of the deploy-path-fragility cluster (#13212 ⊃ #13215; #13211 separate). Sibling slices (per the strategy posted on this issue): **#13215** = make deploy-pull robust to a *pre-existing* dirty tree (belt to this fix's suspenders); **#13211** = move `_FRESHEN_LOCK` into `git_ops.ensure_main_and_pull`. Shipped as independent slices, not batched.
