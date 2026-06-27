## #13172 — fail-closed on wrong-type `additional_includes` in the v2 manifest loader

(skill-filed improvement-scan finding, triaged into the work queue.)

### Root cause
`compose._load_manifest_v2_from_file` silently reset a wrong-TYPE `additional_includes` (e.g. a bare string `additional_includes: common/cycle-runner` instead of a list) to `[]`. The variant's sub-skills then vanished from the composed `CLAUDE.md` with **zero diagnostic** — a manifest schema typo yields silently-incomplete agent instructions. This was the **only** swallowed case in the function: every sibling schema error in the same base_role/variant branch (`base_role` missing, a listed sub-skill file missing) does `sys.exit(1)`.

### Fix
Make the wrong-type case fail **closed** — `print(ERROR ... expected list, file=sys.stderr); sys.exit(1)` — matching its same-branch siblings. (The `isinstance` guard itself was already correct; it just must not be silent.)

### Verification
- +4 tests: bare-string→exit(1) with diagnostic, dict→exit, valid-list→resolves (isolated from the live sub-skill tree via stub + patched `SUB_SKILLS_DIR`), null/absent→valid (regression guard for the `… or []` idiom).
- Full static gate: **4971 passed, 0 failures, 0 errors**.
- Review: Sonnet (model_router/DeepSeek degenerate this session → auto-fallback): **NO_BLOCKING_FINDINGS**; 1 MEDIUM (an inline comment miscounted the siblings — the base `includes` wrong-type path returns `None`, not `sys.exit(1)`) + 2 LOW (null-case test, test isolation) all addressed. DS-REVIEW-13172.md on main.
- No CQ (deterministic code). No manifest (no new files).

### Out-of-scope note (on the issue)
The reviewer found `_load_manifest_v2` is **unreachable from the production deploy path** post-E6 (#10685) — deploy/deploy-all/wizard route through `v2_link_stage.emit_v2_linked`, not this loader. Retiring/tombstoning it is a separate triage decision; this guard is correct + cheap if the path is ever re-wired, and even on deploy-all each alias is wrapped in `except SystemExit` so a bad manifest fails one alias, never the fleet.
