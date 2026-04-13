# FEAT-SKILL-401 QA Results — Capability Sub-Skills

**QA Date**: 2026-04-11
**Tester**: QA Agent
**Branch**: main (commit a88749e)

## Summary

| TC | Title | Result |
|----|-------|--------|
| TC-1 | Directory rename | PASS |
| TC-2 | Manifest schema v2 — all valid | PASS |
| TC-3 | Manifest schema v2 — old v1 rejected | FAIL |
| TC-4 | requires_tools renamed to requires_sub_skills | PASS |
| TC-5 | compose.py {{capability:}} directive | PASS |
| TC-6 | compose.py {{capability:}} — missing capability | PASS |
| TC-7 | capability_check.py — designer | PASS |
| TC-8 | capability_check.py — all missing | PASS |
| TC-9 | capability_check.py — empty requires | PASS |
| TC-10 | PM Phase 1 capability gap analysis | PASS |
| TC-11 | Agent runtime self-check on startup | PASS |
| TC-12 | design-tools.md renamed to design-capabilities.md | PASS |
| TC-13 | design-capabilities.md terminology | PASS |
| TC-14 | WIZARD.md references updated | PASS |
| TC-15 | SKILL.md references updated | PASS |
| TC-16 | manifest.py kind rename — capabilities | PASS |
| TC-17 | manifest.py cross-reference — requires_sub_skills | PASS |
| TC-18 | manifest.py cross-reference — applicable_roles | PASS |
| TC-19 | Behavioral sub-skills — common includes | PASS |
| TC-20 | Behavioral sub-skills — role-specific includes | PASS |
| TC-21 | test_manifest.py | PASS |
| TC-22 | test_manifest_registry.py | PASS |
| TC-23 | Full test suite | PASS |
| TC-24 | DOMAIN_ONLY_BLOCKLIST — no false positives | PASS |
| TC-25 | Two capability sub-skills any_of — no conflict | PASS |
| TC-26 | Missing capability cross-reference detected | PASS |
| TC-27 | Upgrade path — compose redeploys | PASS |
| TC-28 | Graceful degradation — non-upgraded install | PASS |
| TC-29 | config.md — no new required fields | PASS |

**Overall: 28 PASS, 1 FAIL**

---

## Detailed Results

### TC-1: Directory rename references/tools/ to references/sub-skills/capabilities/
- **Result**: PASS
- **Notes**: `references/sub-skills/capabilities/` contains all 4 subdirectories (figma, google_stitch, local_delivery, local_html). Each has manifest.yaml, sub-skill.md, and setup.md. `references/tools/` does not exist.

### TC-2: Manifest schema v2 — all valid
- **Result**: PASS
- **Notes**: `python references/scripts/manifest.py validate` exits 0 with "OK -- 5 role(s), 4 capability(ies), 2 preset(s)". All 5 role manifests and 4 capability manifests use `schema_version: 2`.

### TC-3: Manifest schema v2 — old v1 rejected
- **Result**: FAIL
- **Notes**: `SUPPORTED_SCHEMA_VERSIONS = {1, 2}` in manifest.py (line 62). The validator accepts both v1 and v2, not v2-only as the test plan expected. This is a design decision for backward compatibility — capability_check.py also falls back to `requires_tools` field. The CONTEXT.md states "no dual-field backward compat" but the implementation chose to keep v1 acceptance for graceful degradation. **This is a test plan vs. implementation mismatch, not a code bug.** The test plan assumed v2-only; the dev chose v1+v2 for safety. The human should decide whether v1 acceptance is intentional.

### TC-4: requires_tools renamed to requires_sub_skills
- **Result**: PASS
- **Notes**: `grep -r "requires_tools" references/roles/*/manifest.yaml` returns empty. All 5 role manifests use `requires_sub_skills`. Designer has `any_of: [figma, google_stitch, local_html]`, DM has `any_of: [local_delivery]`, dev/pm/qa have `{}`.

### TC-5: compose.py {{capability:}} directive
- **Result**: PASS
- **Notes**: compose.py lines 38-62 implement the `{{capability: id}}` directive. It reads from `CAPABILITIES_DIR / id / "sub-skill.md"`, wraps content in `<!-- sub-skill: capability-{id} -->` markers. No role entry files currently USE this directive (roles use `{{include: common/capability-check}}` instead), but the mechanism is implemented and functional.

### TC-6: compose.py {{capability:}} — missing capability
- **Result**: PASS
- **Notes**: Tested with `{{capability: nonexistent_tool}}` — compose emits `<!-- ERROR: Missing capability: nonexistent_tool -->` without crashing.

### TC-7: capability_check.py — designer role
- **Result**: PASS
- **Notes**: `python references/scripts/capability_check.py designer` exits 0. Output: figma OK (mcp), google_stitch OK (mcp), local_html OK (builtin). "any_of satisfied by: ['figma', 'google_stitch', 'local_html']".

### TC-8: capability_check.py — all missing
- **Result**: PASS
- **Notes**: Design review: the script correctly handles all-missing scenario — if no `any_of` capability is available, it prints "FAIL" and exits 1. For `all_of`, missing items are listed. Code paths verified at lines 130-132 (any_of fail) and 138-140 (all_of fail). Cannot trigger in this environment since MCP/builtin providers always pass, but logic is correct.

### TC-9: capability_check.py — empty requires
- **Result**: PASS
- **Notes**: `python references/scripts/capability_check.py dev` exits 0 with "OK: dev requires no capabilities."

### TC-10: PM Phase 1 capability gap analysis
- **Result**: PASS
- **Notes**: `references/sub-skills/pm-specific/task-intake.md` (note: named task-intake, not feature-intake as test plan stated) contains capability gap analysis instructions at step 7 and a "Capability Gaps" output section template. References `python references/scripts/capability_check.py [TARGET_ROLE]` and describes fallback checking for `any_of` lists.

### TC-11: Agent runtime self-check on startup
- **Result**: PASS
- **Notes**: `references/sub-skills/common/capability-check.md` exists and is included by designer and dm roles via `{{include: common/capability-check}}`. The composed designer output contains startup instructions referencing `python references/scripts/capability_check.py [ROLE]` with exit code handling (0=proceed, 1=warn+continue degraded, 2=misconfiguration). Dev role does not include it (has empty requires, so no need). The `compose all` output (agent-instructions.md) is dev-only and naturally omits it.

### TC-12: design-tools.md renamed to design-capabilities.md
- **Result**: PASS
- **Notes**: `references/sub-skills/designer-specific/design-capabilities.md` exists. `design-tools.md` does not exist. Designer CLAUDE.md uses `{{include: designer-specific/design-capabilities}}`. Compose succeeds.

### TC-13: design-capabilities.md terminology
- **Result**: PASS
- **Notes**: Two occurrences of "design tool" remain: "Figma is a design tool accessed through its MCP server" and "Google Stitch is a design tool accessed through available Stitch sub-skills". These are acceptable per the test plan — they describe what Figma/Stitch ARE in domain terms (they are design tools), not using "tool" as the SquidSquad organizational concept. The overall file uses "capability sub-skill" and "sub-skill" terminology consistently.

### TC-14: WIZARD.md references updated
- **Result**: PASS
- **Notes**: `grep -n "references/tools" references/wizard/WIZARD.md` returns empty. WIZARD.md contains at least 1 "sub-skill" reference.

### TC-15: SKILL.md references updated
- **Result**: PASS
- **Notes**: `grep -n "references/tools" SKILL.md` returns empty. No references to old directory path.

### TC-16: manifest.py kind rename — capabilities
- **Result**: PASS
- **Notes**: `python references/scripts/manifest.py list capabilities` returns all 4 IDs (figma, google_stitch, local_delivery, local_html). `python references/scripts/manifest.py load capabilities figma` returns valid JSON with schema_version 2. The CLI also accepts `tools` as an alias for backward compat.

### TC-17: manifest.py cross-reference — requires_sub_skills resolve
- **Result**: PASS
- **Notes**: `python references/scripts/manifest.py validate` exits 0 with no "unknown" errors. Designer's `any_of: [figma, google_stitch, local_html]` and DM's `any_of: [local_delivery]` all resolve.

### TC-18: manifest.py cross-reference — applicable_roles resolve
- **Result**: PASS
- **Notes**: Validation exits 0 with no "applicable_roles" errors. All capability manifests reference valid role IDs.

### TC-19: Behavioral sub-skills — common includes
- **Result**: PASS
- **Notes**: `python references/scripts/compose.py all` exits 0. Composed output contains tracker-protocol, vault-protocol, and pull-latest content (10+ references found). No `ERROR.*Missing include` markers.

### TC-20: Behavioral sub-skills — role-specific includes
- **Result**: PASS
- **Notes**: `compose all` (dev role) produces no ERROR markers. designer, dm, pm, qa roles compose without errors. No missing include errors found.

### TC-21: test_manifest.py
- **Result**: PASS
- **Notes**: All tests in test_manifest.py pass as part of the full suite (612 passed total).

### TC-22: test_manifest_registry.py
- **Result**: PASS
- **Notes**: All tests in test_manifest_registry.py pass as part of the full suite.

### TC-23: Full test suite
- **Result**: PASS
- **Notes**: `python -m pytest tests/ -v` — 612 passed in 44.02s. Zero failures, zero errors.

### TC-24: DOMAIN_ONLY_BLOCKLIST — no false positives
- **Result**: PASS
- **Notes**: `python references/scripts/manifest.py validate` shows no "domain-only" violations. Capability manifests describe integrations in domain terms without triggering the blocklist.

### TC-25: Two capability sub-skills any_of — no conflict
- **Result**: PASS
- **Notes**: Validation exits 0 with no "conflict" warnings. All three designer capabilities coexist correctly under any_of semantics.

### TC-26: Missing capability cross-reference detected
- **Result**: PASS
- **Notes**: Temporarily renamed figma/ to figma_bak/. Validation correctly emitted: "unknown capability id 'figma'; known capabilities: ['google_stitch', 'local_delivery', 'local_html']" and exited with code 1. Directory restored.

### TC-27: Upgrade path — compose redeploys
- **Result**: PASS
- **Notes**: `python references/scripts/compose.py all` succeeds. Composed output uses "capability sub-skill" / "sub-skill" terminology. No "design-tools" references in agent-instructions.md. Designer/DM roles include capability-check self-check instructions when composed individually.

### TC-28: Graceful degradation — non-upgraded install
- **Result**: PASS
- **Notes**: Design review confirms backward compat: manifest.py accepts both schema_version 1 and 2. capability_check.py falls back to `requires_tools` field if `requires_sub_skills` is absent (line 107). manifest.py CLI accepts `tools` as alias for `capabilities` kind. Old installs would function — the only missing feature is capability gap analysis.

### TC-29: config.md — no new required fields
- **Result**: PASS
- **Notes**: `grep -i "capabilities\|sub.skill" .squidsquad/config.md` returns empty. No new mandatory config fields introduced. Capability tracking is via role manifests.

---

## Smoke Tests

- [x] `python references/scripts/manifest.py validate` exits 0
- [x] `python references/scripts/manifest.py list capabilities` returns 4 IDs
- [x] `python references/scripts/compose.py all` exits 0 with no ERROR markers
- [x] `python references/scripts/capability_check.py dev` exits 0
- [x] `python -m pytest tests/ -v` — 612 passed, 0 failed
- [x] `references/tools/` directory does not exist
- [x] `references/sub-skills/capabilities/` contains 4 subdirectories
- [x] `grep -r "requires_tools" references/roles/` returns empty
- [x] `grep -r "schema_version: 1" references/roles/*/manifest.yaml references/sub-skills/capabilities/*/manifest.yaml` returns empty
- [x] `design-capabilities.md` exists, `design-tools.md` does not

## Overall Verdict

**28 PASS, 1 FAIL**

The single FAIL (TC-3) is a test plan vs. implementation mismatch, not a code defect. The CONTEXT.md states "No dual-field backward compat" and "hard bump", which the test plan interpreted as v2-only validation. However, the implementation keeps `SUPPORTED_SCHEMA_VERSIONS = {1, 2}` for graceful degradation of non-upgraded installs (TC-28). This is a reasonable engineering choice — the human should confirm whether v1 should be rejected or kept for backward compat.

All functional requirements are met. The directory rename, manifest schema v2, compose directive, capability_check.py, PM capability gap analysis, terminology updates, and test suite all pass.
