**Reported By**: skill-lead (skill)
**Found by**: #11394 (auto-discovery refactor of run_tests.py static gate)

## Summary
Un-breaking the static gate (#11394) surfaced that **`python tests/run_tests.py static` has been silently collecting 0 tests since the v0.44.0 cutover** — the deleted `test_l2_l3_op_anchoring_11227` left a dangling `STATIC_TEST_MODULES` entry that aborted pytest collection. With the gate dead, **23 static test files went red unnoticed**. #11394 quarantines them in `KNOWN_FAILURES` (gate green, debt visible via NOTICE every run); this issue tracks triaging/fixing each.

## Classification

### A. Stale tests — assert pre-v2 / pre-rename / pre-cutover structure (fix = update test)
- `test_references` — expects removed v1 `references/agent-instructions.md`
- `test_event_mode_fragments` — expects `includes.yml` to list `common/boot-bootstrap` (v2 changed includes)
- `test_own_domain_autofix` — asserts v1 `{{include: ...}}` directive syntax (removed by #11049 Path A)
- `test_pickup_comment_fidelity_9946` — reads removed `references/roles/dev/includes.yml` (pre-rename `dev/`)
- `test_terminology_dual_aware_6274` — asserts pre-rename `('dev','skill')`; rename #6274 landed → `('worker','skill')`
- `test_cycle_pre` — asserts `'verifier'` in alias set `['dm','pm','qa','skill']` (rename #6274 partial)
- `test_state_bus` — asserts git pull `--rebase`; code is `--no-rebase` per never-rebase rule (test contradicts policy)
- `test_dm_verify_before_block`, `test_stale_tracker_files_ref` — read removed `roles/{dm,pm}/prohibitions.md`
- `test_agent_boundaries` — asserts removed `responsibility.md` + "Know each other's responsibilities" phrase
- `test_feat_9588_lazy_load_bootstrap` — asserts removed `## Boot — Mode Detection (#9588)` heading
- `test_compose_author_comments_11142` — asserts boot-bootstrap wrapper marker in restructured `worker/instructions.md`
- `test_4792_fragment_hygiene` — asserts removed `'sole liveness signal'` phrase in composed skill
- `test_deterministic_qa_framework` — asserts `'"Deferred"'` in composed QA
- `test_vault_synthesis` — asserts `'create-task'` in restructured pm source
- `test_compose_a2f_10492`, `test_atomic_emit_b7`, `test_a3_golden_link_stage` — golden/section-list compose assertions drifted

### B. Fixture drift (fix = update fixture)
- `test_config_functions` — `SAMPLE_CONFIG` fixture missing new `FIELD_MAP` entries (`code-review-model`, `effort-*`, `event-driven`)

### C. POSSIBLY-REAL masked regressions — TRIAGE FIRST (may be production issues, not stale tests)
- `test_statusline_schema` — `references/statusline.sh` and `.squidsquad/statusline.sh` **out of sync** (the `cp` deploy step). Real sync gap?
- `test_manifest_registry` — "Shipped registry has 1 error(s)". Real registry validation failure?
- `test_feat328_coverage` — "unknown capability id 'local_delivery'; known capabilities: **[]**" (capability registry empty). Real loading bug?
- `test_comms_sub_skills` — "chat-etiquette.md must start with ## heading". Real source-format issue?

## Notes
- Full per-file failure reasons: `.squidsquad/skill/planning/11394-reasons.txt`; maps: `11394-ungated.xml`, `11394-gated-perfile.json`.
- Group C should be triaged before assuming "just a stale test" — the dead gate may have masked real breakage from the v0.44.0/v2 restructure.
- As each is fixed, remove its entry from `KNOWN_FAILURES` in `tests/run_tests.py` (the NOTICE keeps the list honest).
