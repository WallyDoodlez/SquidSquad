# TEST-PLAN-10981 — Token-leak classes in deploy_alias_v2

**Source**: GitHub issue #10981 (PM cycle-2118/2119 pre-squash audit, three leak-class taxonomy B1/B2/B3) and skill-lead's cycle-1579 fix on `skill/e6-v2-cutover-10685` (commit `5c64247a`).
**Derived from the AC-equivalent "Acceptance"-like sections of the issue body: the three leak classes, the empirical leak counts, and the "Suggested fix surface" 1/2/3 options.**

## ACs (derived)

The issue body lists three leak classes rather than numbered ACs. Derived ACs:

- **AC-1 (B1)**: `deploy_alias_v2` no longer emits literal `{{include: <path>}}` directives. Sub-skill bodies must be inlined into the composed CLAUDE.md; runtime-loaded fragments (per `RUNTIME_READ_FRAGMENTS`, #9588 lazy-load contract) must NOT be inlined.
- **AC-2 (B2)**: `deploy_alias_v2` emits CLAUDE.md with no literal bracket-placeholder tokens: `[ROLE]`, `[ACTIVE_AGENTS]`, `[OTHER_ROLES]`, `[ROLE_TEST_CMD]`, `[E2E_TEST_CMD]`, `[INTERVAL]`, `[POLLING_FRAGMENT_PATH]`. Bracket placeholders must be substituted with their alias/role values.
- **AC-3 (B3)**: `deploy_alias_v2` emits CLAUDE.md with no literal `{{role-roster}}` token. `_inject_role_roster` must be called.
- **AC-4 (symmetric coverage of wizard path)**: `deploy_role_v2` (wizard fresh-install path) is also covered for the same three classes — operator + wizard paths must have identical token-resolution contracts.
- **AC-5 (regression tests)**: Per the PR's stated 11-test set, all three leak classes are covered by regression tests in `tests/test_compose_10981_deploy_alias_v2_token_leaks.py` for both `deploy_alias_v2` and `deploy_role_v2` paths, plus edge-case helper tests for `_resolve_includes_v2`.
- **AC-6 (no compose-suite regression)**: Existing compose-suite tests (test_compose, test_compose_9588, test_manifest, test_event_mode_fragments) do not regress as a result of this fix. (Note: 2 failures + 4 errors are pre-existing on `skill/e6-v2-cutover-10685` from earlier cutover-branch work and verified not introduced by `5c64247a`.)

Out-of-scope for this PR (skill-lead's cycle-1579 explicit carve-out, confirmed against issue body's optional suggestion 3):
- Full end-to-end test that runs `deploy_alias_v2` against the REAL `references/` tree (PM's suggestion 3). Skill-lead chose suggestion 2a (link-stage expand) instead — both were marked as options, not hard requirements. The unit tests do exercise the real fix code with realistic-shape fixtures.
- L4 parser error on `.squidsquad/project/{dm,verifier,worker}.md` — skill-lead will file separately.

## Test Cases

### TC-1 (covers AC-1 — B1): `_resolve_includes_v2` exists and expands `{{include:}}` directives
- **Verification command**: `grep -n "_resolve_includes_v2\|RUNTIME_READ_FRAGMENTS" references/scripts/compose.py`
- **Expected**: `_resolve_includes_v2(content, source_root=None)` defined; called from `deploy_alias_v2` and `deploy_role_v2`; `RUNTIME_READ_FRAGMENTS` checked and skipped.

### TC-2 (covers AC-2 — B2): `_substitute_placeholders` wired into `deploy_alias_v2`
- **Verification command**: `grep -n "_substitute_placeholders" references/scripts/compose.py`
- **Expected**: at least one call site inside `deploy_alias_v2` (in addition to the existing `deploy_role_v2` call).

### TC-3 (covers AC-3 — B3): `_inject_role_roster` wired into both paths
- **Verification command**: `grep -n "_inject_role_roster" references/scripts/compose.py`
- **Expected**: helper definition + at least 2 call sites (one in `deploy_alias_v2`, one in `deploy_role_v2`).

### TC-4 (covers AC-5): All 11 regression tests in the new file pass
- **Verification command**: `python -m pytest tests/test_compose_10981_deploy_alias_v2_token_leaks.py -v`
- **Expected**: 11 pass. Specifically:
  - `TestDeployAliasV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output[pm/dm/verifier]` (3 cases)
  - `TestDeployAliasV2NoTokenLeaks::test_role_placeholder_substituted_with_alias`
  - `TestDeployAliasV2NoTokenLeaks::test_included_sub_skill_body_inlined`
  - `TestDeployRoleV2NoTokenLeaks::test_no_unresolved_tokens_in_assembled_output`
  - `TestResolveIncludesV2::test_expands_valid_include_directive`
  - `TestResolveIncludesV2::test_missing_include_emits_error_marker`
  - `TestResolveIncludesV2::test_runtime_read_fragment_directive_is_dropped`
  - `TestResolveIncludesV2::test_strips_yaml_frontmatter_from_included_body`
  - `TestResolveIncludesV2::test_strips_outer_sub_skill_markers_to_avoid_doubling`

### TC-5 (covers AC-6): No regression in broader compose suite
- **Verification command**: `python -m pytest tests/test_compose.py tests/test_compose_9588.py tests/test_compose_10981_deploy_alias_v2_token_leaks.py tests/test_manifest.py tests/test_event_mode_fragments.py`
- **Expected**: pre-existing-on-cutover-branch failure set (2 fail + 4 errors in manifest/event_mode_fragments) is unchanged. Specifically verified by running the same suite against `5c64247a^` (pre-fix on cutover branch) and getting the same 2 fail + 4 error set.

### TC-6 (HUMAN-REQUIRED — out of scope, NOT blocking ship): Real-tree integration test
- **Result**: HUMAN-REQUIRED / deferred — would require either (a) staging the real tree in a temp dir and running assemble_pass with a real LLM key, or (b) PM's suggestion 3 codified into the test suite. Skill-lead's empirical ad-hoc verification at fix time (pm/dm/verifier/worker-skill body sizes 84-129K, `leaks=[] missing_includes=0`) is the current evidence. Per PM's framing this was an "OR" with 2a (which skill-lead chose); not blocking ship.

## Coverage matrix

- AC-1 → TC-1, TC-4 (TestResolveIncludesV2 subset)
- AC-2 → TC-2, TC-4 (TestDeployAliasV2 / role-placeholder)
- AC-3 → TC-3, TC-4 (TestDeployAliasV2 / leak-token scan, role-roster covered)
- AC-4 → TC-4 (TestDeployRoleV2)
- AC-5 → TC-4
- AC-6 → TC-5

## Comprehension Questions

Skipped — this fix does not touch LLM-consumed instructions; it touches the compose-time link stage that BUILDS them. The composed CLAUDE.md content is exercised by existing comprehension tests for unchanged sub-skills; the change is structural (token resolution) not semantic. The fix's WHY-comment block at the new call sites is for future maintainers, not for LLM consumption.
