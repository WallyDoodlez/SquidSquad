# Code Review — #13172 (fail-closed wrong-type additional_includes)

Reviewer: Sonnet subagent (model_router/DeepSeek has been returning degenerate
sub-threshold output this session → direct Sonnet review per the auto-fallback rule).

## Verdict: NO_BLOCKING_FINDINGS

### Findings & disposition
- **MEDIUM (FIXED):** inline comment miscounted siblings — claimed it matches the base `includes` wrong-type path, but that path (Branch B) returns None, not sys.exit(1). Corrected to cite the correct same-branch siblings (base_role-missing + missing sub-skill file, both sys.exit(1)) and to note the base-includes path's different contract.
- **LOW (FIXED):** added test_null_additional_includes_is_valid — regression guard for the `... or []` idiom (null/absent → [] → valid).
- **LOW (FIXED):** isolated test_valid_list_additional_includes_still_resolves from the live sub-skill tree (stub file + patched SUB_SKILLS_DIR) so a future rename can't cause a misleading missing-file exit.
- **LOW (NOTED, out of scope):** the reviewer found `_load_manifest_v2_from_file` is not reachable from the production deploy path post-E6 (#10685) cutover — deploy-all/deploy/wizard go through v2_link_stage.emit_v2_linked, not _load_manifest_v2. So this hardens a path currently exercised only by tests + its own recursion. Tombstoning/retiring _load_manifest_v2 is a separate decision (PM/triage) — noted on the issue, not folded here (don't gold-plate; the guard is still correct + cheap, and matches sibling contracts if the path is ever re-wired). Also confirmed: even on the deploy-all route, each alias is wrapped in `except SystemExit: failed.append(alias)` — one bad manifest fails one alias, never wedges the fleet.

### Verified
- No false positives: absent/null/empty additional_includes → [] → passes (the `or []` short-circuit).
- Fail-closed matches same-branch sibling severity.
- Tests cover string→exit, dict→exit, valid-list→resolves, null→valid.
