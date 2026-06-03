# AUDIT — E6 #10685 Phase 3d.3: deploy --check post-cutover fate

**Cycle**: 1556
**Branch**: `skill/e6-v2-cutover-10685`
**Author**: skill-lead
**Question for PM**: How should the v1 `check_role` chain be retired? Three options below; recommendation is **Option B**.

## Why this audit exists

Cycle 1555 (Phase 3d.2) surfaced that the `compose.py` comment at lines 2407-2410 understates the v1/v2 asymmetry. The comment reads:

> Post-E6 (#10685) phase 4 suffix flip, ``deploy`` writes the canonical ``CLAUDE.md`` and ``check_role`` reads the same path — the cutover-window asymmetry from phases 2-3 no longer applies.

The PATHS are now symmetric, but the COMPOSE LOGIC is not.

## The mismatch

| | v1 (`compose_role` → `_compose_role_to_string` → `check_role`) | v2 (`deploy_alias_v2` → `assemble_and_emit`) |
|---|---|---|
| Link stage | `compose_role` walks v1 manifest, inlines `{{include:}}` via `_resolve_includes_with_manifest` | `v2_link_stage.emit_v2_linked` produces deterministic linked composite |
| LLM polish | None | `assemble_and_emit` runs `assemble_slot` per slot (real LLM, sonnet) |
| Output shape | Pre-LLM | Post-LLM (six `## <Slot>` polished + conflict reports) |
| Determinism | Yes | Link stage: yes. Assembled CLAUDE.md: no. |

`assemble_and_emit` at atomic_emit.py:103 calls `assemble_slot_fn` (default: real `assemble_slot` from `assemble_pass`). The output of `_build_claude_md(assembled_per_slot)` at atomic_emit.py:205 is post-LLM.

Meanwhile `check_role` at compose.py:1386 calls `_compose_role_to_string(role_name)` which calls `compose_role(role_name)` — a deterministic v1-shape walk with no LLM.

**Result**: `deploy --check` on any role that has been deployed via `deploy_alias_v2` post-cutover will report DRIFT for the entire CLAUDE.md, because the on-disk file is the v2 assembled output and the expected is the v1 pre-assemble output. The DIFFERENT SHAPES collide.

## Why the test suite hasn't surfaced this

`tests/test_compose_check_a4_10388.py::test_clean_when_compose_equals_disk` (line 66) and friends write `_compose_role_to_string("pm")` to disk then call `check_role("pm")` — so v1-expected vs v1-on-disk matches trivially. They never exercise `check_role` against a `deploy_alias_v2`-produced file. The bug is invisible to the existing test surface.

## Three options

### Option A — retire `deploy --check` entirely

Delete `check_role` + `_compose_role_to_string` + `_diff_compose_output` + the `--check` flag handling in compose.py:2382-2424 (deploy command's check branch) and 2444-2480 (deploy-all command's check branch). Net delete: ~150 lines. The `check_alias_staged_l4` path (the A4.5 staged-content check) stays — it's a different code path entirely (validates a to-be-committed L4 file against the v2 link stage, no on-disk diff).

**Pros**: Smallest blast radius. Removes 100% of the v1 chain that's blocking Phase 3d.4. No new code surface.

**Cons**: Operators lose the drift-detection convenience. Was this critical? Best evidence: pre-E6 the comment at 2406 says "A4 per-alias drift-check fallback" — wording suggests fallback, not primary workflow. The PRD comment doesn't list `deploy --check` as a critical SC.

### Option B — migrate `check_role` to v2 (compare against linked composite)

Rewrite `check_role` to compare the on-disk `CLAUDE.linked.md` (not `CLAUDE.md`) against a fresh `v2_link_stage.emit_v2_linked(...)` result. The LINKED composite IS deterministic — no LLM in the link stage — so a clean compare is possible.

Delete `_compose_role_to_string` (v1-only). Delete `compose_role` (only this caller chain left). Phase 3d.4 follows naturally.

The new `check_role` reads the on-disk `.squidsquad/<alias>/CLAUDE.linked.md` (the pre-LLM artifact), computes the same in-memory, diffs. Drift now means "the linked composite changed since last deploy" — a meaningful signal.

**Pros**: Preserves drift-detection. The check now actually corresponds to the canonical v2 artifact (linked composite). The CLAUDE.md polish is rightly excluded from the check (LLM polish drift is not a meaningful concept).

**Cons**: ~60 lines of new v2-flavored check code. Updates `tests/test_compose_check_a4_10388.py` (4 tests) to swap target file + swap expected computation. `_diff_compose_output` stays useful (it diffs `## ` sections; the linked composite has those too).

### Option C — leave as-is, accept always-drift

Status quo. `deploy --check` always reports drift post-cutover. Operators learn to ignore it or never use it.

**Pros**: Zero engineering work.

**Cons**: The CLI command becomes a footgun: it does the wrong thing reliably. Better to retire it (Option A) than leave it broken.

## Recommendation: Option B

Drift-detection against the **linked composite** is the architecturally cleanest answer:

- Matches v2's "link stage is the deterministic compose, assemble is the LLM stage" mental model. Drift-check belongs at the link layer.
- The `CLAUDE.linked.md` triple member exists specifically to be the canonical inspectable pre-LLM artifact (atomic_emit.py:206: `claude_linked_md = linked_composite`).
- Phase 3d.4 (delete `compose_role`) is unblocked by either A or B; B preserves a useful workflow at low extra cost (~60 LOC).
- Updates to `test_compose_check_a4_10388.py` are mechanical: target file → `CLAUDE.linked.md`, expected source → `emit_v2_linked(...)`.

If PM/human disagrees on Option B's necessity (drift-check not a critical workflow), Option A is the fallback — pure-deletion, lowest cost. Either way, Option C is not viable.

## Proposed next-cycle plan

- **Cycle 1557 (Phase 3d.3 execution)**: implement Option A or B per PM decision.
- **Cycle 1558+ (Phase 3d.4)**: delete `compose_role` + `_resolve_includes` + `_load_manifest` + `_resolve_includes_with_manifest` + `TestComposeRole` in test_compose.py + line-392 in test_manifest.py.
- **Cycle 1559+ (Phase 3d.5)**: delete `deploy_role` + its tests in test_compose_a6_v2.py:78-276, test_compose_a2f_10492.py, test_d2_link_stage_references.py B7.
- **Cycle 1560+ (Phase 7+8)**: AC10 cumulative DS review pre-merge; open squash PR.
