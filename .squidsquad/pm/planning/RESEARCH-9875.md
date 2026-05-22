# RESEARCH-9875 — L2 instructions: merged item → vault writeback + all research must consult vault first

**Issue**: #9875
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

The vault exists to hold institutional knowledge but its write path is reactive (quiet-cycle reflection only) and its read path is incomplete (PM Phase 1 mandates it; other roles don't). Two gaps result:

- **Write gap**: Every merged item is a potential vault candidate, but no role has a post-merge vault evaluation step. vault_remember.py is gated on `is-quiet`, so it never fires after a busy merge cycle — the moments with the most to capture are silently skipped.
- **Read gap**: PM Phase 1 Research has an explicit mandatory vault-consult step with a structured "Vault Context" output section. Skill (dev) has a brief `2c` vault-consult step but no structured output. QA test-plan creation has no vault-consult step. DM delivery-packaging and DM task-pickup have zero vault references.

The goal: after any merged item, the shipping role evaluates it against the 4-gate criteria and writes if it passes. For all research/investigation workflows, vault consultation is mandatory and the output is a structured "Vault Context" section.

---

## 2. Today's Vault-Consult + Vault-Write Discipline by Role

### 2.1 Vault-Consult at Research/Investigation Time

| Role | Trigger | Vault consult today | Structured output? |
|------|---------|--------------------|--------------------|
| PM | Phase 1 Research (task pickup) | **MANDATORY** — explicit step, BRIEFING.md + keyword search + read matching notes | Yes — "## Vault Context" section in RESEARCH.md |
| Dev/skill | Task pickup (implement-tasks.md step 2c) | Present but soft — "Consult the vault ... This takes seconds and prevents rework" | No structured section required |
| QA | Test-plan creation (verification.md step 5.1) | **Absent** — no vault-consult step before writing TEST-PLAN | No |
| QA | Issue verification (verification.md step 4, step 1b) | Present — "Consult the vault (#5572)" before verifying each fix/issue | No structured section |
| DM | Task pickup (dm/task-pickup.md) | **Absent** — reads issue body and planning artifacts only | No |
| DM | Delivery packaging (delivery-packaging.md step 2c+) | **Absent** — no vault step anywhere in delivery | No |

**Manifest insight**: QA and DM include `common/vault-protocol-slim` (read-only, search-only). Dev includes `common/vault-protocol` (full read/write). PM includes both `common/vault-protocol` and `common/vault-remember`. QA and DM are explicitly read-only roles per vault-protocol-slim — this is by design but does not preclude a vault-consult read step at investigation/delivery time.

### 2.2 Vault-Write After Merge

| Role | Has post-merge vault eval? | Write trigger today |
|------|--------------------------|---------------------|
| PM | No — vault_remember runs only on quiet cycles | Quiet-cycle only |
| Dev | No — vault_remember runs only on quiet cycles | Quiet-cycle only |
| QA | No | Never — read-only role |
| DM | No | Never — read-only role |

**cycle_post.py**: No vault evaluation step. It handles iteration logging, status bar reset, and metrics (line 588: shipped count). No post-merge trigger exists anywhere in the harness or sub-skills.

**Key finding**: The `is-quiet` gate in `vault_remember.py` is the root design constraint. It explicitly skips reflection when the cycle did real work — the rationale is "nothing to reflect on." But a merge cycle IS the thing to reflect on. The post-merge vault writeback is a different trigger than the quiet-cycle reflection, not a variant of it.

---

## 3. Options for Part A — Post-Merge Vault Writeback

The trigger question is central: where in the agent workflow does "I just merged a PR" become "evaluate for vault."

### Option A1 — New `common/vault-writeback.md` fragment, injected after git-commit

Add a new sub-skill fragment `references/sub-skills/common/vault-writeback.md` invoked after a successful PR merge (detectable when `git_ops.py task-end` runs after the merge event or when `delivery-packaging.md` transitions to Shipped). The fragment applies the same 4 gates (budget, dedup, reusability, fresh-context) but:
- Is NOT gated on `is-quiet` — it fires regardless of cycle busyness
- Has a per-merge write budget of **1** (not 2) — one note per merge, prevent flood
- Skips explicitly for trivial merges (dependency bumps, typo fixes, config-only) with a `SKIP: trivial` log line
- Only PM and Dev roles write; QA and DM cannot write (maintains vault-protocol-slim for those roles)

Fragment location: `references/sub-skills/common/vault-writeback.md`
Manifest changes: add to `references/roles/pm/includes.yml` and `references/roles/dev/includes.yml` (after `common/git-commit`)

**Pros**: clean separation of concerns (quiet-cycle reflection stays, merge writeback is new); per-merge budget of 1 prevents unbounded growth; the 4-gate logic reuses existing scripts (vault_remember.py write-budget, vault_check.py dedup-check).
**Cons**: `vault_remember.py write-budget` counter is per-cycle, not per-merge — either reset it per-merge or add a new `merge-write-budget` counter. Minor script change needed (or workaround: always allow 1 merge write by skipping the budget gate and using dedup as the primary anti-flood mechanism).

### Option A2 — Extend git-commit.md with a "Post-Merge Vault Eval" section

Add an optional section at the bottom of `references/sub-skills/common/git-commit.md` titled "Step 6 — Post-Merge Vault Evaluation (when a PR was just merged this cycle)." Trigger condition: DM's `delivery-packaging.md` step 0b confirms a PR merged (via `pr-merged` event or harness merge response); the shipping role then runs the vault eval inline.

**Pros**: no new fragment needed; the merge moment is already in git-commit's scope (it handles the PR creation and push logic).
**Cons**: git-commit.md is already dense (111 lines); mixing vault eval into git-commit blurs concerns; DM doesn't have git-commit.md in its manifest (DM has `roles/dm/git-commit.md` — a DM-specific variant). The "which role triggers" logic gets messy.

### Option A3 — DM-only writeback in delivery-packaging.md

Since DM is the role that executes the actual merge (via `/merge` endpoint, step 0b), add the vault eval to `delivery-packaging.md` after the merge succeeds. DM would call `vault_remember.py` but with a special `--allow-write` flag that bypasses the `is-quiet` check.

**Pros**: the merge event is unambiguously in DM's hands.
**Cons**: violates vault-protocol-slim (DM is a read-only vault role by design). Requiring DM to write vault notes would need a manifest change (vault-protocol-slim → vault-protocol) with potential context-cost implications. Also misses PM and Dev shipping flows when `delivery: skip` is set (DM skips delivery, so DM never sees the merge). The shipping role varies.

**Recommendation for Part A**: Option A1. New `common/vault-writeback.md` fragment. Script adjustment: use `dedup-check` as the primary flood gate (vault_check.py already has this) and treat the budget gate as "always 1 allowed per merge" — simplest path is to add a `vault_remember.py merge-budget [ROLE]` sub-command that returns 1 unconditionally (no counter needed; dedup is the real guard). Or simpler still: bypass the budget script entirely for post-merge writes and rely solely on dedup + reusability + fresh-context (3 of 4 gates). The budget gate was designed to prevent quiet-cycle over-writing; per-merge writes at 1/merge are already bounded.

---

## 4. Options for Part B — Research-Begins-With-Vault

### Option B1 — Strengthen dev's vault-consult step (implement-tasks.md) + add to QA TEST-PLAN creation + add to DM task-pickup

Three targeted edits to existing fragments:

**a) `references/sub-skills/roles/dev/implement-tasks.md` step 2c**: Elevate from soft recommendation to MANDATORY. Add a required "Vault Context" section to the working-state.md update (step 3) or to a brief pre-implementation note in the issue comment. The PM RESEARCH.md template's "## Vault Context" section is the model.

**b) `references/sub-skills/roles/qa/verification.md` step 5.1 (TEST-PLAN creation)**: Add vault-consult step before drafting the test plan. QA already does vault-consult for issue verification (step 1b) — this is the same pattern applied to test-plan creation. Add to the TEST-PLAN structure template: a "## Vault Context" section listing relevant decisions/patterns/learnings consulted (or "Vault consulted — no relevant prior context found").

**c) `references/sub-skills/roles/dm/task-pickup.md`**: Add vault-consult step after reading the issue body (step 1), before planning delivery steps. DM reads `vault-protocol-slim` — the search commands are already available.

**d) `references/sub-skills/roles/dm/delivery-packaging.md`**: Add a brief vault-consult step after reading the task (step 2) — specifically check for `galaxy/decision-*` notes related to the feature being shipped. The question DM asks: "Is there a vault decision that constrains how docs should be written or whether this feature's delivery notes require special handling?"

**Pros for B1**: all changes are targeted edits to existing fragments; no new fragments needed; QA and DM already have `vault-protocol-slim` with the search commands.

### Option B2 — New `common/vault-consult.md` fragment included by all roles

Extract the vault-consult step into a common fragment invoked at the start of each "investigation" phase. Each role's ralph-loop-overview or role-specific fragment calls `{{include: common/vault-consult}}`.

**Pros**: single source of truth for the consult step.
**Cons**: each role's investigation context is different (PM researches, dev implements, QA tests, DM ships) — a single fragment would need heavy templating. Targeted edits per fragment are more precise and easier to CQ-test. Adds a new fragment to every manifest.

**Recommendation for Part B**: Option B1 — targeted edits to existing fragments. Four files, each with a small addition. The vault-consult pattern is already established; it's missing in specific locations. No new fragment needed.

---

## 5. Recommended Approach

### Part A — Post-merge vault writeback

- **New fragment**: `references/sub-skills/common/vault-writeback.md`
- **Trigger**: Fires in PM and Dev ralph loops after a PR merge is confirmed (after `task-end` returns successfully on a cycle where a PR was merged / status moved to pending-ship). DM does not write — DM confirms the merge but vault writes are PM/dev domain.
- **Gate logic**: 3-gate (skip budget gate; use dedup + reusability + fresh-context). Budget gate was designed for quiet-cycle overwriting; per-merge bound is implicit (1 merge = max 1 write per merge event).
- **Skip criteria**: trivial merges (dependency bumps, doc-only typo fixes, config-only changes) → log `SKIP: trivial merge — no reusable insight` and continue.
- **Write budget**: 1 note per merge. Log remaining candidates as `Vault-worthy but deferred (merge limit): [description]` in the iteration log.
- **Note types**: same as quiet-cycle — `galaxy/decision-*`, `galaxy/pattern-*`, `galaxy/learning-*`. LLM judgment on type in the moment.
- **Multiple merges per cycle**: writeback runs once per merge event detected. If two PRs merged in one cycle, two evaluations run (each limited to 1 write). Dedup prevents redundant notes.
- **Manifest changes**: add `common/vault-writeback` to `references/roles/pm/includes.yml` and `references/roles/dev/includes.yml` after `common/git-commit`.
- **No Python code changes needed**: existing `vault_check.py dedup-check`, `vault_remember.py inc-writes`, and vault-create protocol are sufficient. The budget gate is simply omitted (or the fragment uses a simplified inline check: "allow this write unless dedup returns exact match").

### Part B — Research-begins-with-vault

Four targeted edits to existing fragments:

1. **`references/sub-skills/roles/dev/implement-tasks.md` step 2c** — change from soft recommendation to MANDATORY wording. Add explicit output: working-state.md step 3 notes vault context found (or "none").
2. **`references/sub-skills/roles/qa/verification.md` step 5.1** — add vault-consult before test-plan creation. Add "## Vault Context" section to the TEST-PLAN template.
3. **`references/sub-skills/roles/dm/task-pickup.md` step 1** — add vault-consult after reading issue body.
4. **`references/sub-skills/roles/dm/delivery-packaging.md` step 2** — add brief vault-consult for delivery-relevant decisions.

All four edits go through the compose pipeline (`compose.py deploy [role]`) per `feedback_l1_l4_only`. Fixture regeneration in the same PR.

### CQ Specs

**CQ for Part A** (post-merge writeback): "A dev agent just confirmed a PR merged for task #NNN (status moved to pending-ship). The cycle was not quiet — the agent was busy implementing. Describe what the agent does next regarding the vault." Expected answer: agent evaluates the merge against 3 gates (dedup, reusability, fresh-context); if passing, writes a galaxy note (decision/pattern/learning) with a 1-note limit; if trivial merge, logs `SKIP: trivial merge`; does NOT skip vault eval just because cycle was not quiet.

**CQ for Part B** (research-consults-vault): "A QA agent is about to write a TEST-PLAN for task #NNN. What vault step must it perform before drafting?" Expected answer: search vault for keywords from the issue title, check for relevant decisions/patterns/learnings, include a "## Vault Context" section in the TEST-PLAN — either citing found notes or stating "Vault consulted — no relevant prior context found."

---

## 6. Open Questions

1. **Which role writes the post-merge vault note — the shipping role (PM/dev after pending-ship) or DM after the actual merge?** Recommended: PM or Dev (whoever built the feature) writes immediately after status moves to pending-ship (before DM gets the item). DM does not write. This avoids promoting DM to vault-write access and keeps the knowledge closest to the author. But if `delivery: skip` short-circuits DM, PM needs to write BEFORE DM sees the item — timing must be explicit.

2. **Per-merge write limit: 1 or skip budget entirely?** Allowing 1 note per merge without a budget script is simpler. But if a single cycle has 3 merges, 3 notes get written — is that acceptable? Recommendation: yes (dedup prevents redundancy; 3 meaningful merges → 3 learnings is valid). The budget gate exists to prevent LLM over-writing in quiet cycles, not to suppress legitimate merge learnings.

3. **Trivial-merge detection: manual LLM judgment or heuristic?** A heuristic (diff touches only `CHANGELOG.md`, `README.md`, version file, or `*.lock`) could auto-skip. But the agent already reads the PR description — LLM judgment on "is this trivial?" is sufficient and consistent with existing gate 3 (reusability). No new script needed.

4. **vault-protocol-slim roles (QA, DM) consulting vault — does the slim fragment give enough?** Yes — `vault-protocol-slim.md` already includes keyword search commands. The consultation is read-only. No manifest change needed for vault-consult reads. Only vault writes would require upgrading to full `vault-protocol`.

---

## 7. Out of Scope

- **Python code changes to `vault_remember.py` or `cycle_post.py`** — the post-merge writeback runs as agent instruction, not a harness hook. No script changes needed.
- **Promoting QA or DM to vault-write roles** — vault-protocol-slim stays. Only PM and dev write post-merge notes.
- **Changing the quiet-cycle vault-remember behavior** — the existing `common/vault-remember` fragment is unchanged. This task adds a second trigger (post-merge), not a replacement.
- **Changing vault note structure or PARAG taxonomy** — existing types (decision/pattern/learning) cover all merge scenarios.
- **Other roles' research gaps beyond the four listed** — boot-bootstrap and soul-shepherd are not research workflows.
- **vault_optimize or vault_synthesis** — those are downstream consumers; no changes needed.
- **Fixture regeneration tooling** — existing `compose.py deploy [role]` handles it.
