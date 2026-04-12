# FEAT-SKILL-401 Test Plan — Capability Sub-Skills

## Test Cases

### TC-1: Directory rename references/tools/ to references/sub-skills/capabilities/
- **Precondition**: Pre-rename repo state with `references/tools/` containing figma, google_stitch, local_html, local_delivery subdirectories.
- **Steps**:
  1. Run the rename (git mv or equivalent).
  2. Verify new directory structure exists at `references/sub-skills/capabilities/`.
  3. Verify old `references/tools/` no longer exists.
  4. Verify all 4 capability sub-skill directories are present under the new path.
- **Expected**: `references/sub-skills/capabilities/{figma,google_stitch,local_html,local_delivery}/` each contain manifest.yaml, sub-skill.md, and setup.md.
- **Verification**:
  ```bash
  ls references/sub-skills/capabilities/
  # Must list: figma, google_stitch, local_html, local_delivery
  test ! -d references/tools/ && echo "PASS: old dir removed"
  for d in figma google_stitch local_html local_delivery; do
    test -f "references/sub-skills/capabilities/$d/manifest.yaml" && echo "PASS: $d/manifest.yaml"
    test -f "references/sub-skills/capabilities/$d/sub-skill.md" && echo "PASS: $d/sub-skill.md"
    test -f "references/sub-skills/capabilities/$d/setup.md" && echo "PASS: $d/setup.md"
  done
  ```

### TC-2: Manifest schema v2 bump — all manifests valid
- **Precondition**: All role and capability manifests updated with `schema_version: 2`. manifest.py updated to accept v2.
- **Steps**:
  1. Run `python references/scripts/manifest.py validate`.
  2. Confirm exit code 0 and no errors.
- **Expected**: All manifests pass validation. Zero errors, zero warnings (aside from any pre-existing warnings).
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate
  echo "Exit code: $?"
  # Must be 0
  ```

### TC-3: Manifest schema v2 — old v1 manifests rejected
- **Precondition**: manifest.py `SUPPORTED_SCHEMA_VERSIONS` updated to `{2}` only.
- **Steps**:
  1. Create a temporary manifest with `schema_version: 1`.
  2. Run manifest.py validation against it (or place it in the capabilities dir and run full validate).
- **Expected**: Validation emits an error: "unknown schema_version 1; supported: [2]".
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate 2>&1 | grep -i "schema_version"
  # Should NOT find any v1 manifests passing. If a v1 test manifest is injected, it must fail.
  ```

### TC-4: Role manifests — requires_tools renamed to requires_sub_skills
- **Precondition**: All 5 role manifests updated: `requires_tools` field renamed to `requires_sub_skills`.
- **Steps**:
  1. Inspect each role manifest for `requires_sub_skills` field.
  2. Verify no manifest contains `requires_tools`.
  3. Run `python references/scripts/manifest.py validate`.
- **Expected**: All role manifests contain `requires_sub_skills` (not `requires_tools`). Validation passes.
- **Verification**:
  ```bash
  grep -r "requires_tools" references/roles/*/manifest.yaml
  # Must return empty (no matches)
  grep -r "requires_sub_skills" references/roles/*/manifest.yaml
  # Must match designer (any_of), dm (any_of), dev ({}), pm ({}), qa ({})
  python references/scripts/manifest.py validate
  ```

### TC-5: compose.py {{capability:}} directive inlines capability sub-skill content
- **Precondition**: compose.py updated with `{{capability:}}` directive handler. A role entry file (e.g., designer CLAUDE.md) uses `{{capability: figma}}`.
- **Steps**:
  1. Add `{{capability: figma}}` directive to a test entry file (or the designer CLAUDE.md).
  2. Run `python references/scripts/compose.py designer-agent`.
  3. Inspect the composed output for inlined figma sub-skill.md content.
- **Expected**: Output contains the figma sub-skill.md content wrapped in `<!-- sub-skill: sub-skill -->` (or similar capability markers). The content is read from `references/sub-skills/capabilities/figma/sub-skill.md`.
- **Verification**:
  ```bash
  python references/scripts/compose.py designer-agent 2>&1 | grep -c "figma"
  # Must find figma-related content inlined
  ```

### TC-6: compose.py {{capability:}} — missing capability ID
- **Precondition**: compose.py has the `{{capability:}}` handler.
- **Steps**:
  1. Add `{{capability: nonexistent_tool}}` to a test entry file.
  2. Run compose.py on that role.
- **Expected**: compose.py emits an error comment in output (e.g., `<!-- ERROR: Missing capability: nonexistent_tool -->`) rather than crashing.
- **Verification**:
  ```bash
  # Temporarily add bad directive, compose, check for error marker
  python references/scripts/compose.py designer-agent 2>&1 | grep "ERROR.*Missing capability"
  ```

### TC-7: capability_check.py — reads manifest, checks MCP availability
- **Precondition**: `references/scripts/capability_check.py` exists. Designer manifest declares `requires_sub_skills: any_of: [figma, google_stitch, local_html]`. At least one of the three is available in the environment.
- **Steps**:
  1. Run `python references/scripts/capability_check.py designer`.
  2. Inspect output for per-capability status.
- **Expected**: Script reads `references/roles/designer/manifest.yaml`, extracts `requires_sub_skills`, checks each capability's availability (MCP server_name for mcp provider, check_command for CLI provider), and reports status per capability. Exit code 0 if `any_of` semantics are satisfied (at least one available).
- **Verification**:
  ```bash
  python references/scripts/capability_check.py designer
  echo "Exit code: $?"
  # Exit code 0 = at least one any_of capability is available
  ```

### TC-8: capability_check.py — all required capabilities missing
- **Precondition**: capability_check.py exists. No MCP servers configured, no CLI tools installed for the target role.
- **Steps**:
  1. Run capability_check.py for a role whose `any_of` capabilities are all unavailable.
- **Expected**: Script reports each capability as unavailable. Exit code non-zero. Output includes a clear warning listing missing capabilities.
- **Verification**:
  ```bash
  python references/scripts/capability_check.py designer
  echo "Exit code: $?"
  # Exit code non-zero when none of any_of are available
  ```

### TC-9: capability_check.py — role with empty requires_sub_skills
- **Precondition**: Dev role manifest has `requires_sub_skills: {}`.
- **Steps**:
  1. Run `python references/scripts/capability_check.py dev`.
- **Expected**: Script reports no capabilities required. Exit code 0. No warnings.
- **Verification**:
  ```bash
  python references/scripts/capability_check.py dev
  echo "Exit code: $?"
  # Must be 0
  ```

### TC-10: PM Phase 1 Research — capability gap analysis
- **Precondition**: PM feature-intake sub-skill (`references/sub-skills/pm-specific/feature-intake.md`) updated with capability gap analysis instructions. A target agent role manifest exists with `requires_sub_skills`.
- **Steps**:
  1. Simulate a PM Phase 1 Research cycle targeting the designer role.
  2. Verify the RESEARCH.md output includes a "Capability Gaps" section.
  3. The section should list each required capability and whether it is satisfied.
- **Expected**: RESEARCH.md contains a "Capability Gaps" heading. Each required sub-skill is listed with its availability status. Missing capabilities are flagged as non-blocking.
- **Verification**:
  ```bash
  # After a Phase 1 run, check the research artifact:
  grep -c "Capability Gaps" .squidsquad/pm/planning/FEAT-*-RESEARCH.md
  # Must be >= 1
  ```

### TC-11: Agent runtime self-check on startup
- **Precondition**: Agent CLAUDE.md templates updated with a startup self-check section that calls `capability_check.py`. capability_check.py is deployed.
- **Steps**:
  1. Inspect a composed agent CLAUDE.md (e.g., designer) for the self-check instructions.
  2. Verify the instructions reference `python references/scripts/capability_check.py [ROLE]`.
- **Expected**: The composed CLAUDE.md contains startup instructions that invoke capability_check.py. The instructions specify: run check, log warnings for missing capabilities, continue with fallback if available.
- **Verification**:
  ```bash
  python references/scripts/compose.py designer-agent 2>&1 | grep "capability_check"
  # Must find capability_check reference in composed output
  ```

### TC-12: Designer design-tools.md renamed to design-capabilities.md
- **Precondition**: File `references/sub-skills/designer-specific/design-tools.md` renamed to `design-capabilities.md`. All references updated.
- **Steps**:
  1. Verify `design-capabilities.md` exists and `design-tools.md` does not.
  2. Verify designer CLAUDE.md entry file uses `{{include: designer-specific/design-capabilities}}`.
  3. Run compose.py for designer and verify output includes the design capabilities content.
- **Expected**: File renamed, include directive updated, compose succeeds without errors.
- **Verification**:
  ```bash
  test -f references/sub-skills/designer-specific/design-capabilities.md && echo "PASS: new file exists"
  test ! -f references/sub-skills/designer-specific/design-tools.md && echo "PASS: old file removed"
  grep "design-capabilities" references/roles/designer/CLAUDE.md
  # Must match the include directive
  python references/scripts/compose.py designer-agent > /dev/null 2>&1
  echo "Compose exit code: $?"
  # Must be 0
  ```

### TC-13: design-capabilities.md terminology — no "tool" references
- **Precondition**: design-capabilities.md has all "tool" references replaced with "capability sub-skill" or "sub-skill" as appropriate.
- **Steps**:
  1. Search design-capabilities.md for the word "tool" (case-insensitive).
  2. Exclude false positives (e.g., "tooltip", "toolchain" if present).
- **Expected**: No standalone occurrences of "tool" or "tools" as the primary noun for external integrations. Acceptable: "tooltip", "Figma is a tool" in quoted descriptions.
- **Verification**:
  ```bash
  grep -iw "tools\?\b" references/sub-skills/designer-specific/design-capabilities.md | grep -v tooltip | grep -v "# Tool manifest"
  # Ideally zero matches for standalone "tool"/"tools" referring to the old concept
  ```

### TC-14: WIZARD.md references updated from "tool" to "capability sub-skill"
- **Precondition**: `references/wizard/WIZARD.md` updated.
- **Steps**:
  1. Search WIZARD.md for "tool" references that should now say "capability sub-skill" or "sub-skill".
  2. Verify manifest.py CLI kind argument accepts the new naming.
- **Expected**: WIZARD.md uses unified "sub-skill" terminology. No references to `references/tools/` path.
- **Verification**:
  ```bash
  grep -n "references/tools" references/wizard/WIZARD.md
  # Must return empty
  grep -c "sub-skill" references/wizard/WIZARD.md
  # Should be > 0
  ```

### TC-15: SKILL.md references updated
- **Precondition**: `SKILL.md` updated with new directory paths and terminology.
- **Steps**:
  1. Search SKILL.md for `references/tools/` path references.
  2. Search for "tool" as a standalone concept (not "tooltip" etc.).
- **Expected**: No references to the old `references/tools/` path. Architecture section describes capability sub-skills under `references/sub-skills/capabilities/`.
- **Verification**:
  ```bash
  grep -n "references/tools" SKILL.md
  # Must return empty
  ```

### TC-16: manifest.py validator — kind rename from "tools" to "capabilities"
- **Precondition**: manifest.py updated: validator function renamed/updated, CLI `list` and `load` commands accept the new kind name.
- **Steps**:
  1. Run `python references/scripts/manifest.py list capabilities`.
  2. Run `python references/scripts/manifest.py load capabilities figma`.
- **Expected**: `list capabilities` returns all 4 capability IDs. `load capabilities figma` returns the figma manifest as JSON.
- **Verification**:
  ```bash
  python references/scripts/manifest.py list capabilities
  # Must list: figma, google_stitch, local_html, local_delivery
  python references/scripts/manifest.py load capabilities figma
  # Must output valid JSON with figma manifest data
  ```

### TC-17: manifest.py cross-reference — requires_sub_skills IDs resolve
- **Precondition**: Role manifests use `requires_sub_skills`. Capability manifests live under new path.
- **Steps**:
  1. Run full validation: `python references/scripts/manifest.py validate`.
  2. Check that cross-reference checks resolve `any_of` and `all_of` IDs against the capabilities registry (not the old tools registry).
- **Expected**: Designer's `any_of: [figma, google_stitch, local_html]` resolves. DM's `any_of: [local_delivery]` resolves. No "unknown tool ID" errors.
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate 2>&1 | grep -i "unknown"
  # Must return empty (no unresolved references)
  ```

### TC-18: manifest.py cross-reference — capability applicable_roles resolve
- **Precondition**: Capability manifests still have `applicable_roles` referencing role IDs.
- **Steps**:
  1. Run full validation.
  2. Check that each capability's `applicable_roles` entries exist in the role registry.
- **Expected**: No "unknown role" errors for applicable_roles fields.
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate 2>&1 | grep -i "applicable_roles"
  # Must return empty (no errors)
  ```

### TC-19: Behavioral sub-skills unaffected — common/ includes still work
- **Precondition**: `references/sub-skills/common/` directory unchanged. All `{{include: common/*}}` directives in role entry files intact.
- **Steps**:
  1. Run `python references/scripts/compose.py all`.
  2. Verify compose succeeds for all roles.
  3. Spot-check that tracker-protocol, vault-protocol, pull-latest content appears in composed output.
- **Expected**: All behavioral sub-skills compose correctly. No missing include errors.
- **Verification**:
  ```bash
  python references/scripts/compose.py all 2>&1
  echo "Exit code: $?"
  # Must be 0
  grep -c "ERROR.*Missing include" references/agent-instructions.md
  # Must be 0
  ```

### TC-20: Behavioral sub-skills unaffected — role-specific includes still work
- **Precondition**: `references/sub-skills/pm-specific/`, `references/sub-skills/designer-specific/` (except rename), `references/sub-skills/dev-specific/` directories unchanged (except design-tools rename).
- **Steps**:
  1. Run compose for each role that uses role-specific includes.
  2. Verify no missing include errors.
- **Expected**: All role-specific behavioral sub-skills compose correctly.
- **Verification**:
  ```bash
  python references/scripts/compose.py all 2>&1 | grep "ERROR"
  # Must return empty
  ```

### TC-21: Test suite passes — test_manifest.py
- **Precondition**: `tests/test_manifest.py` updated to reference new paths, field names, and schema version.
- **Steps**:
  1. Run `python -m pytest tests/test_manifest.py -v`.
- **Expected**: All tests pass.
- **Verification**:
  ```bash
  python -m pytest tests/test_manifest.py -v
  echo "Exit code: $?"
  # Must be 0
  ```

### TC-22: Test suite passes — test_manifest_registry.py
- **Precondition**: `tests/test_manifest_registry.py` updated to reference new paths, field names, and schema version.
- **Steps**:
  1. Run `python -m pytest tests/test_manifest_registry.py -v`.
- **Expected**: All tests pass.
- **Verification**:
  ```bash
  python -m pytest tests/test_manifest_registry.py -v
  echo "Exit code: $?"
  # Must be 0
  ```

### TC-23: Full test suite passes
- **Precondition**: All code changes complete.
- **Steps**:
  1. Run `python -m pytest tests/ -v`.
- **Expected**: All tests pass. No regressions.
- **Verification**:
  ```bash
  python -m pytest tests/ -v
  echo "Exit code: $?"
  # Must be 0
  ```

### TC-24: manifest.py DOMAIN_ONLY_BLOCKLIST — no false positives from rename
- **Precondition**: DOMAIN_ONLY_BLOCKLIST in manifest.py may contain "sub-skill" as a blocked phrase. Capability manifest descriptions should NOT be flagged.
- **Steps**:
  1. Check if "sub-skill" is in the DOMAIN_ONLY_BLOCKLIST.
  2. If yes, verify capability manifests' `description` and `display_name` fields do not trigger false domain-only violations.
  3. Run validation.
- **Expected**: No domain-only violations for capability manifests that use "sub-skill" terminology appropriately. If "sub-skill" is in the blocklist, capability manifests must avoid using it in their free-text fields (they describe the tool in domain terms, not SquidSquad-internal terms).
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate 2>&1 | grep "domain-only"
  # Must return empty
  ```

### TC-25: Two capability sub-skills with any_of — no conflict
- **Precondition**: Designer manifest has `any_of: [figma, google_stitch, local_html]`. All three exist in the capabilities directory.
- **Steps**:
  1. Run validation.
  2. Verify no conflict warnings between overlapping any_of capabilities.
- **Expected**: Validation passes. any_of semantics mean "at least one" — all three coexisting is valid.
- **Verification**:
  ```bash
  python references/scripts/manifest.py validate 2>&1 | grep -i "conflict"
  # Must return empty
  ```

### TC-26: Capability sub-skill removed from directory but still referenced in manifest
- **Precondition**: Role manifest references a capability ID that does not exist in the capabilities directory (simulate by temporarily renaming one).
- **Steps**:
  1. Temporarily rename `references/sub-skills/capabilities/figma/` to `references/sub-skills/capabilities/figma_bak/`.
  2. Run `python references/scripts/manifest.py validate`.
  3. Restore the directory.
- **Expected**: Validation emits an error for the unresolved `figma` reference in designer's `requires_sub_skills.any_of`.
- **Verification**:
  ```bash
  # Manual test — rename, validate, check for error, restore
  python references/scripts/manifest.py validate 2>&1 | grep "figma"
  # Must find an unresolved reference error
  ```

## Upgrade Verification Tests

### TC-27: Upgrade path — /squidsquad-upgrade re-deploys agent CLAUDE.md files
- **Precondition**: An existing SquidSquad install with old "tools" vocabulary. Upgrade mechanism available.
- **Steps**:
  1. Run the upgrade process (compose all roles).
  2. Verify recomposed agent CLAUDE.md files contain new terminology.
- **Expected**: After upgrade, agent instructions reference "capability sub-skill" / "sub-skill" instead of "tool". Self-check instructions are present. `design-capabilities` is included (not `design-tools`).
- **Verification**:
  ```bash
  python references/scripts/compose.py all
  grep -c "capability_check" references/agent-instructions.md
  # Must be > 0 (self-check is present)
  grep "design-tools" references/agent-instructions.md
  # Must return empty (old name gone)
  ```

### TC-28: Graceful degradation — non-upgraded install continues working
- **Precondition**: A hypothetical install that still has `references/tools/` and old manifest.py (v1 schema).
- **Steps**:
  1. Verify that the old code paths (reading `references/tools/`, `requires_tools`, `schema_version: 1`) would still function with old manifest.py.
  2. This is a design verification, not a runtime test — confirm that no backward-incompatible change was made to the data format that would cause old code to crash.
- **Expected**: Old manifest.py (pre-upgrade) can still read old manifests. Agents using old vocabulary continue to function. The capability gap analysis simply does not exist — PM researches features without checking capabilities.
- **Verification**: Design review. Confirm that the old `references/tools/` directory is only read by `manifest.py` (which gets upgraded together). No external consumers.

### TC-29: config.md — no new required config values
- **Precondition**: Feature does not introduce required config.md fields.
- **Steps**:
  1. Inspect config.md for any new required fields related to capabilities.
- **Expected**: No new mandatory config fields. Capability tracking is via role manifests, not config.md.
- **Verification**:
  ```bash
  grep -i "capabilities\|sub.skill" .squidsquad/config.md
  # Should be empty or only informational (no required fields)
  ```

## Smoke Tests

- [ ] `python references/scripts/manifest.py validate` exits 0
- [ ] `python references/scripts/manifest.py list capabilities` returns 4 IDs
- [ ] `python references/scripts/compose.py all` exits 0 with no ERROR markers
- [ ] `python references/scripts/capability_check.py dev` exits 0 (no requirements)
- [ ] `python -m pytest tests/ -v` all pass
- [ ] `references/tools/` directory does not exist
- [ ] `references/sub-skills/capabilities/` directory contains 4 subdirectories
- [ ] `grep -r "requires_tools" references/roles/` returns empty
- [ ] `grep -r "schema_version: 1" references/roles/*/manifest.yaml references/sub-skills/capabilities/*/manifest.yaml` returns empty
- [ ] `design-capabilities.md` exists, `design-tools.md` does not

## Regression Risks

- **Behavioral sub-skill composition breakage**: The rename and new `{{capability:}}` directive in compose.py must not interfere with existing `{{include:}}` directive resolution. Watch for path resolution bugs where compose.py confuses `references/sub-skills/common/` paths with `references/sub-skills/capabilities/` paths.
- **DOMAIN_ONLY_BLOCKLIST false positives**: The blocklist contains `"sub-skill"` as a blocked phrase. If capability manifest descriptions or display_names use the word "sub-skill", they will be flagged. Capability manifests must describe the integration in domain terms only (which is already the case).
- **manifest.py CLI kind argument**: If the CLI still accepts `tools` as a kind argument (backward compat), it must be tested. If it only accepts `capabilities`, all callers (wizard, tests, CI) must be updated.
- **Cross-reference validator path change**: The validator resolves `requires_sub_skills` IDs by looking up manifest files on disk. The path changed from `references/tools/<id>/manifest.yaml` to `references/sub-skills/capabilities/<id>/manifest.yaml`. If the path resolution is wrong, all cross-reference checks silently fail or produce false positives.
- **compose.py SUB_SKILLS_DIR constant**: compose.py currently sets `SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills"`. The `{{capability:}}` directive must resolve from `SUB_SKILLS_DIR / "capabilities" / <id> / "sub-skill.md"`, not from `SUB_SKILLS_DIR / <id>.md` (which is how behavioral includes resolve).
- **Designer CLAUDE.md include path**: The `{{include: designer-specific/design-tools}}` line must be updated to `{{include: designer-specific/design-capabilities}}`. If missed, compose.py will emit a `<!-- ERROR: Missing include -->` marker that silently degrades the designer agent.
- **Test fixture paths**: test_manifest.py and test_manifest_registry.py may hardcode paths like `references/tools/` or field names like `requires_tools`. All must be updated or tests will fail.
- **PM feature-intake sub-skill**: The capability gap analysis adds new prose instructions to `references/sub-skills/pm-specific/feature-intake.md`. If these instructions reference the wrong path (`references/tools/` instead of `references/sub-skills/capabilities/`), the PM agent will fail to find capability manifests.
- **capability_check.py provider-specific checks**: MCP checks look for server availability; CLI checks look for command existence. If the check mechanism is wrong (e.g., checking for a process name instead of MCP config), it will produce false negatives (report unavailable when available).
- **Git history**: The directory rename via `git mv` preserves history. If done via delete + create, history is lost. Verify with `git log --follow references/sub-skills/capabilities/figma/manifest.yaml`.
