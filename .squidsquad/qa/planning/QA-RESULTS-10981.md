# QA-RESULTS-10981

**Run**: 2026-06-03 21:17 (qa cycle 638)
**Branch**: `skill/e6-v2-cutover-10685` (commit `5c64247a`)
**PR**: none (#10685 E6 squash PR not yet open per PM's Phase 8 gate)
**Verdict**: **PASS** — all 6 ACs satisfied; routing `pending-test → pending-ship`.

## AC walk

| AC | Statement | TC | Result |
|----|-----------|----|--------|
| 1 (B1) | `{{include:}}` directives expanded in `deploy_alias_v2`; runtime fragments preserved per #9588 contract. | TC-1, TC-4 | PASS — `_resolve_includes_v2` defined; respects `RUNTIME_READ_FRAGMENTS` (test `test_runtime_read_fragment_directive_is_dropped` PASSES); missing-source markers visible (test `test_missing_include_emits_error_marker` PASSES). |
| 2 (B2) | Bracket placeholders (`[ROLE]`, `[ACTIVE_AGENTS]`, ...) substituted in `deploy_alias_v2` output. | TC-2, TC-4 | PASS — `_substitute_placeholders` now called from `deploy_alias_v2` (in addition to existing `deploy_role_v2` call); `test_role_placeholder_substituted_with_alias` PASSES (verifies `[ROLE]` → `pm` in actual output, sample `"This is the pm agent"`). |
| 3 (B3) | `{{role-roster}}` injected in BOTH paths. | TC-3, TC-4 | PASS — `_inject_role_roster` definition (compose.py:405-425) plus 2 new call sites (one in `deploy_alias_v2`, one added to `deploy_role_v2` which previously missed it); leak scan in `test_no_unresolved_tokens_in_assembled_output` includes `{{role-roster}}` and passes for pm/dm/verifier. |
| 4 | Wizard path (`deploy_role_v2`) symmetrically covered. | TC-4 | PASS — `TestDeployRoleV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output` PASSES against the same leak-token set. |
| 5 | 11 new regression tests in `tests/test_compose_10981_deploy_alias_v2_token_leaks.py`. | TC-4 | PASS — all 11 collected and pass in 0.36s. |
| 6 | No compose-suite regression introduced by `5c64247a`. | TC-5 | PASS — combined compose suite shows 204 pass + 2 fail + 4 error. Verified the 2 fail + 4 error set is **pre-existing on the cutover branch** by re-running the same suite after `git checkout 5c64247a^ -- references/scripts/compose.py tests/`: identical failure set (2 fail + 4 errors). Failures: `test_manifest.py::test_include_targets_exist` (regex matches `common/agent-boundaries.md` literal in some manifest fixture and appends `.md` twice — surface-level test bug, not introduced here), `test_manifest.py::test_no_orphan_sub_skills`, and 4 errors in `test_event_mode_fragments.py::TestAc6M62ManifestWiring` collection. |

## Test runs

### TC-4 — 11 new regression tests

```
$ python -m pytest tests/test_compose_10981_deploy_alias_v2_token_leaks.py -v
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployAliasV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output[pm] PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployAliasV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output[dm] PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployAliasV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output[verifier] PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployAliasV2NoTokenLeaks::test_role_placeholder_substituted_with_alias PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployAliasV2NoTokenLeaks::test_included_sub_skill_body_inlined PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestDeployRoleV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestResolveIncludesV2::test_expands_valid_include_directive PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestResolveIncludesV2::test_missing_include_emits_error_marker PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestResolveIncludesV2::test_runtime_read_fragment_directive_is_dropped PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestResolveIncludesV2::test_strips_yaml_frontmatter_from_included_body PASSED
tests/test_compose_10981_deploy_alias_v2_token_leaks.py::TestResolveIncludesV2::test_strips_outer_sub_skill_markers_to_avoid_doubling PASSED
11 passed in 0.36s
```

### TC-5 — compose-suite regression (pre-existing failure verification)

```
$ python -m pytest tests/test_compose.py tests/test_compose_9588.py tests/test_compose_10981_deploy_alias_v2_token_leaks.py tests/test_manifest.py tests/test_event_mode_fragments.py
2 failed, 204 passed, 4 errors in 2.41s
```

Same suite run against `5c64247a^` (pre-fix) — identical failure set (2 failed, 4 errors). Confirmed the failures are NOT introduced by this fix; they pre-existed on the cutover branch from earlier work and would persist with or without `5c64247a`. The cutover branch carries a different baseline than `main`; on `main` `test_include_targets_exist` PASSES (re-verified by `git checkout main` and re-running). These pre-existing failures are out of scope for this issue.

### TC-6 — real-tree integration (HUMAN-REQUIRED / deferred)

Attempted live `deploy_alias_v2` against the real `references/` tree via a staged temp install (copied real `references/` + `docs/` into a tmpdir, called `compose.deploy_alias_v2('pm', target_root=tmpdir)`). Failed at `assemble_and_emit` step because the QA cycle environment doesn't have an LLM provider configured for `model='sonnet'` — `model_router.route` returned exit code 1. This is the same reason the unit tests stub `assemble_and_write_soul` with a passthrough.

Skill-lead's ad-hoc empirical verification at fix time (cycle-1579 comment: pm/dm/verifier/worker-skill all produced bodies 84-129K with `leaks=[] missing_includes=0`) is the current real-tree evidence. Codifying this into the test suite would require either an LLM key in test infra or a deterministic assemble stub — not blocking ship per PM's framing of suggestion 3 as optional.

## Decision

All 6 ACs satisfied. Empirical evidence from skill-lead's fix-time verification matches the unit tests' invariants. Unit tests cover the THREE leak-class taxonomy comprehensively (per-role assertions + per-token-class assertions + edge cases of `_resolve_includes_v2`).

The pre-existing failure set on the cutover branch (`test_manifest.py::test_include_targets_exist`, `test_no_orphan_sub_skills`, 4 errors in `test_event_mode_fragments.py::TestAc6M62ManifestWiring`) is NOT introduced by this fix and is out of scope for #10981 — separate issues if not already filed under E6 prep work.

Transitioning #10981 `pending-test → pending-ship`. There is no separate PR for this fix (skill-lead committed directly to `skill/e6-v2-cutover-10685`); the eventual E6 squash PR (#10685) will fold this commit. PM holds the squash gate per their Phase 8 readiness statement; #10981 resolving unblocks that gate.

The L4 parser error on `.squidsquad/project/{dm,verifier,worker}.md` noted by skill-lead in their cycle-1579 comment is a separate finding for a separate filing (skill-lead committed to file under role:skill).
