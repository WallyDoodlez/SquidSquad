# FEAT-PM-3465 Test Plan — Layered Role Definition Architecture (Re-scoped)

> **Scope note**: This plan reflects the revised scope confirmed in CONTEXT.md.
> Layer 2 IS the concrete role (dev, pm, qa, dm, designer) — there is no "role family" intermediary.
> Layer 3 = role customization via `<base>-<variant>` hyphen naming (e.g., pm-skill, dev-ios).
> The primary code change is generalizing `_load_manifest()` and `_get_entry_file_for_role()`
> from dev-only fallback to `<base>-<variant>` suffix-strip for all roles.
> Presets shipped as full-team compositions (all roles per preset):
> Skill: dev-skill, pm-skill, qa-skill, dm-skill
> iOS: dev-ios, pm-ios, qa-ios, dm-ios
> Web: dev-web, pm-web, qa-web, dm-web
> Android: dev-android, pm-android, qa-android, dm-android
> Full-stack: dev-fullstack, pm-fullstack, qa-fullstack, dm-fullstack

---

## Test Cases

### TC-1: Happy path — deploy-all produces valid output for all base roles
- **Precondition**: Feature branch applied (compose.py generalized, preset files created). No stale `.squidsquad/<role>/CLAUDE.md` or `SOUL.md` from a previous run.
- **Steps**: Run `python references/scripts/compose.py deploy-all`.
- **Expected**: `.squidsquad/<role>/CLAUDE.md` and `.squidsquad/<role>/SOUL.md` are written for all base roles (pm, qa, dev/skill, dm, designer). Each file is non-empty. compose.py exits 0 with no errors or warnings.
- **Verification**: `python references/scripts/compose.py deploy-all && echo OK`. For each base role: `test -s .squidsquad/<role>/CLAUDE.md && test -s .squidsquad/<role>/SOUL.md && echo "<role> OK"`. Confirm all roles produce non-zero file sizes.

---

### TC-2: Existing dev variants unchanged — skill/be/fe compose identically before and after migration
- **Precondition**: A baseline artifact checksum (or line count) exists for `.squidsquad/skill/CLAUDE.md` and `.squidsquad/skill/SOUL.md` from the pre-migration compose run. `be` and `fe` variant directories exist in `references/roles/`.
- **Steps**:
  1. Record pre-migration checksums: `md5sum .squidsquad/skill/CLAUDE.md .squidsquad/skill/SOUL.md` (or `wc -l` if checksums are not practical).
  2. Apply the feature branch (generalizing `_load_manifest()`).
  3. Run `python references/scripts/compose.py deploy-all`.
  4. Compare post-migration checksums/line counts.
- **Expected**: The composed output for `skill`, `be`, and `fe` is byte-for-byte identical to pre-migration output. The generalized fallback must not alter existing dev variant composition.
- **Verification**: `diff <(pre-migration .squidsquad/skill/CLAUDE.md) <(post-migration .squidsquad/skill/CLAUDE.md)` — zero diff. Same for SOUL.md. Same for `be` and `fe`. If byte-identical comparison is impractical (e.g., timestamps embedded), verify that all key content strings match and no new content appears.

---

### TC-3: New non-dev variant — pm-skill composes correctly
- **Precondition**: `references/roles/pm-skill/CLAUDE.md` and `references/roles/pm-skill/SOUL.md` exist (preset files). `pm-skill` has no `includes.yml` of its own (inherits from `pm`). The generalized `_load_manifest()` is in place.
- **Steps**: Run `python references/scripts/compose.py deploy pm-skill` (or deploy-all and inspect the pm-skill output).
- **Expected**:
  - `.squidsquad/pm-skill/CLAUDE.md` exists and contains pm Layer 2 content (e.g., PM-specific workflow instructions from `pm/includes.yml` sub-skills) PLUS pm-skill Layer 3 customization content (e.g., deterministic vs probabilistic boundary awareness from `pm-skill/CLAUDE.md`).
  - `.squidsquad/pm-skill/SOUL.md` contains pm identity content PLUS pm-skill-specific personality content.
  - compose.py correctly resolved `pm-skill` → base role `pm` via suffix-strip.
- **Verification**: `grep "<pm-layer2-unique-string>" .squidsquad/pm-skill/CLAUDE.md` — match found. `grep "<pm-skill-layer3-unique-string>" .squidsquad/pm-skill/CLAUDE.md` — match found. Cross-check: `grep "<pm-skill-layer3-unique-string>" .squidsquad/pm/CLAUDE.md` — no match (Layer 3 content is NOT in the base pm output).

---

### TC-4: SOUL.md flat assembly — deployed file is single flat file for all variants including new ones
- **Precondition**: `deploy-all` has run, producing outputs for all base roles and all presets (pm-skill, qa-skill, dm-skill, dev-ios, dev-web, dev-android, dev-fullstack).
- **Steps**:
  1. For each deployed SOUL.md (base roles + presets), confirm it is a single regular file (not a symlink, not a directory).
  2. Confirm no multi-document markers (`---`) that would indicate YAML multi-doc or concatenation artifacts.
  3. Confirm the file contains recognizable role-identity content (not empty, not a stub).
- **Expected**: Every `.squidsquad/<role>/SOUL.md` and `.squidsquad/<preset>/SOUL.md` is a single flat text file with all content from Layer 1 + Layer 2 + Layer 3 assembled into one document.
- **Verification**: `file .squidsquad/pm-skill/SOUL.md` — "ASCII text" (not symlink, not binary). `wc -l .squidsquad/pm-skill/SOUL.md` — greater than `wc -l references/roles/pm-skill/SOUL.md` (assembly added content from base pm). `ls .squidsquad/pm-skill/` — only one SOUL.md present (no SOUL-base.md, no SOUL-layer2.md).

---

### TC-5: soul_adaptation.py unchanged — Project Adaptation works on a Layer 3 variant SOUL.md
- **Precondition**: `.squidsquad/pm-skill/SOUL.md` exists from TC-3/TC-4. `soul_adaptation.py` is unmodified.
- **Steps**:
  1. Run `python references/scripts/soul_adaptation.py render pm-skill` (or the equivalent command for pm-skill role).
  2. Confirm the command exits 0.
  3. Confirm the `## Project Adaptation` section in `.squidsquad/pm-skill/SOUL.md` is found and rendered without error.
- **Expected**: `soul_adaptation.py` operates identically on a Layer 3 variant SOUL.md as on a base role SOUL.md. No code changes to `soul_adaptation.py` are needed. The `## Project Adaptation` marker and `<!-- /project-adaptation -->` end-marker are present and parseable.
- **Verification**: `python references/scripts/soul_adaptation.py render pm-skill && echo OK`. `grep "## Project Adaptation" .squidsquad/pm-skill/SOUL.md | wc -l` — exactly 1. `grep "<!-- /project-adaptation -->" .squidsquad/pm-skill/SOUL.md | wc -l` — exactly 1.

---

### TC-6: Layer 3 naming convention — _load_manifest() strips hyphen suffix to find base role
- **Precondition**: Feature branch applied. `_load_manifest()` has been generalized. Base role `pm` exists in `references/roles/pm/`. Variant `pm-skill` exists in `references/roles/pm-skill/` with no `includes.yml`.
- **Steps**: Trigger `_load_manifest("pm-skill")` (directly via test or indirectly via `compose.py deploy pm-skill`). Observe which `includes.yml` is loaded.
- **Expected**: `_load_manifest("pm-skill")` strips the `-skill` suffix, resolves to base role `pm`, and loads `references/roles/pm/includes.yml`. No error is raised about missing manifest. The loaded manifest is pm's, not a non-existent pm-skill manifest.
- **Verification**: Add a debug print or inspect compose.py log output showing the manifest path resolved to `references/roles/pm/includes.yml`. Alternatively: `grep "includes" references/roles/pm-skill/` yields no `includes.yml` (confirming variant has none), while the composed pm-skill output contains pm sub-skill content (confirming inheritance from pm's manifest).

---

### TC-7: Unknown variant fallback — variant with no matching Layer 3 gracefully handles the absence
- **Precondition**: Feature branch applied. `references/roles/pm-nonexistent/CLAUDE.md` does NOT exist. No `includes.yml` for `pm-nonexistent`.
- **Steps**: Attempt `python references/scripts/compose.py deploy pm-nonexistent`.
- **Expected**: compose.py either (a) exits with a clear, human-readable error message identifying that the role/variant directory does not exist, OR (b) if the variant name resolves to a valid base role, deploys using only the base role's content with a warning. No silent failure, no silent empty output, no Python traceback.
- **Verification**: The command produces a non-zero exit code with an error message containing the role name, OR produces a warning + valid output using base role pm's content. `python references/scripts/compose.py deploy pm-nonexistent 2>&1 | grep -iE "error|not found|unknown|warning"` — match found. In no case does the command silently produce an empty CLAUDE.md or SOUL.md.

---

### TC-8: Full suite regression — all existing tests pass after migration
- **Precondition**: All base roles migrated (no behavioral change to existing roles). `deploy-all` has run.
- **Steps**: Run `python tests/run_tests.py`.
- **Expected**: Zero failures. Zero errors. The test count is equal to or greater than pre-migration (new tests may be added; none may be removed).
- **Verification**: `python tests/run_tests.py` exits 0. No `FAIL` or `ERROR` lines in output. Confirm compose.py-specific tests (if any exist) pass.

---

### TC-9: Preset content — all shipped presets (full-team compositions) compose without errors
- **Precondition**: Feature branch applied. All 20 preset directories exist under `references/roles/` (5 presets × 4 roles each): skill (dev-skill, pm-skill, qa-skill, dm-skill), ios (dev-ios, pm-ios, qa-ios, dm-ios), web (dev-web, pm-web, qa-web, dm-web), android (dev-android, pm-android, qa-android, dm-android), fullstack (dev-fullstack, pm-fullstack, qa-fullstack, dm-fullstack).
- **Steps**:
  1. For each of 20 presets, verify `references/roles/<preset>/CLAUDE.md` exists and is non-empty.
  2. For each of 20 presets, verify `references/roles/<preset>/SOUL.md` exists and is non-empty.
  3. Run `python references/scripts/compose.py deploy-all` and confirm each preset produces a valid `.squidsquad/<preset>/CLAUDE.md` and `.squidsquad/<preset>/SOUL.md`.
- **Expected**:
  - All 20 preset source files exist and are non-empty.
  - All 20 presets compose without errors (exit 0).
  - Each composed SOUL.md is a flat file containing both base role content and preset-specific content.
  - Each preset inherits from its base role: dev-ios from dev, pm-ios from pm, qa-ios from qa, dm-ios from dm.
  - Each preset within a team composition shares domain vocabulary (e.g., all `-ios` presets reference iOS-specific concepts).
- **Verification**: `for p in dev-skill pm-skill qa-skill dm-skill dev-ios pm-ios qa-ios dm-ios dev-web pm-web qa-web dm-web dev-android pm-android qa-android dm-android dev-fullstack pm-fullstack qa-fullstack dm-fullstack; do test -s references/roles/$p/CLAUDE.md && test -s references/roles/$p/SOUL.md && echo "$p source OK"; done`. Then: `for p in dev-skill pm-skill qa-skill dm-skill dev-ios pm-ios qa-ios dm-ios dev-web pm-web qa-web dm-web dev-android pm-android qa-android dm-android dev-fullstack pm-fullstack qa-fullstack dm-fullstack; do test -s .squidsquad/$p/CLAUDE.md && test -s .squidsquad/$p/SOUL.md && echo "$p deployed OK"; done`.

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` exits 0 with no errors or warnings
- [ ] All 5 base role directories under `.squidsquad/` contain both `CLAUDE.md` and `SOUL.md` after deploy
- [ ] All 20 preset directories under `.squidsquad/` contain both `CLAUDE.md` and `SOUL.md` after deploy
- [ ] Each deployed `SOUL.md` (base roles + presets) is a regular non-empty file
- [ ] `python references/scripts/soul_adaptation.py render pm` exits 0
- [ ] `python references/scripts/soul_adaptation.py render pm-skill` exits 0
- [ ] `python tests/run_tests.py` exits 0
- [ ] `.squidsquad/skill/SOUL.md` is byte-for-byte identical to pre-migration output (no regression)
- [ ] `grep "<pm-skill-layer3-unique-string>" .squidsquad/pm-skill/CLAUDE.md` returns a match
- [ ] `grep "<pm-skill-layer3-unique-string>" .squidsquad/pm/CLAUDE.md` returns no match (not leaked into base)
- [ ] `grep "includes.yml" references/roles/pm-skill/` — no `includes.yml` present (variant inherits from base)
- [ ] `python references/scripts/compose.py deploy pm-nonexistent` exits non-zero with a clear error message

---

## Regression Risks

- **Existing dev variant silently broken**: The suffix-strip generalization in `_load_manifest()` must not alter the existing fallback path for `skill`, `be`, and `fe`. If the new logic resolves `skill` to a non-`dev` base role (e.g., because a `skill` directory exists at a different level), these variants silently lose their dev content. Watch for: `skill/SOUL.md` missing code-change protocol or other dev-only content.
- **soul_adaptation.py marker collision**: A preset SOUL.md that happens to include the string `## Project Adaptation` in its Layer 3 content would create two markers in the assembled file, corrupting soul_adaptation.py rendering. Watch for: duplicate `## Project Adaptation` headers in any assembled SOUL.md.
- **Suffix-strip false positive**: A base role whose name contains a hyphen (e.g., a future `skill-senior` role that IS a base role, not a variant) would be incorrectly resolved as a variant of `skill`. Watch for: any new base role names with hyphens failing to compose or inheriting the wrong includes.yml.
- **Preset SOUL.md token budget growth**: Each preset's SOUL.md includes full base role content plus Layer 3. For roles with longer SOUL.md files (e.g., pm), the preset SOUL.md may be notably larger. Watch for: pm-skill SOUL.md substantially larger than pm SOUL.md; verify both are under a sane line count (e.g., <250 lines).
- **deploy-all missing preset roles**: If `_list_known_role_identities()` does not pick up preset directories, deploy-all silently skips them. Watch for: deploy-all completing without producing `.squidsquad/pm-skill/` etc.
- **SOUL.md fallback to base role when preset has no SOUL.md**: If a preset has CLAUDE.md but no SOUL.md, the fallback behavior must be documented and tested. Silent inheritance of the base SOUL.md is acceptable; silent empty SOUL.md is not.
- **Atomic write not applied to preset outputs**: If compose.py's `.tmp`→`mv` atomic write pattern is not applied to the new preset deploy paths, partial writes on failure leave corrupt SOUL.md files. Watch for: deploy failure leaving a zero-byte or truncated `.squidsquad/<preset>/SOUL.md`.

---

## Comprehension Questions

### CQ-1: What are the three layers, and what does each one own in the revised architecture?
- **Files**: `references/docs/layer-model.md` (or `references/sub-skills/manifest.md` layer documentation) and/or `.squidsquad/pm/planning/FEAT-PM-3465-CONTEXT.md`.
- **Expected**: Layer 1 = agent definition — what any SquidSquad agent IS, regardless of role (Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity). Layer 2 = role definition — the concrete role: dev, pm, qa, dm, designer. Layer 3 = role customization — specialization of a role for a specific domain or use case (e.g., pm-skill, dev-ios). A fresh agent must name all three layers with correct descriptions and must NOT mention any "role family" or intermediate grouping concept — that concept was explicitly removed from scope.

### CQ-2: What is the Layer 3 naming convention, and how does compose.py use it to resolve the base role?
- **Files**: `references/scripts/compose.py` (specifically `_load_manifest()` and `_get_entry_file_for_role()`), `references/docs/layer-model.md` (or equivalent documentation).
- **Expected**: Layer 3 variants use hyphen naming: `<base>-<variant>` (e.g., `pm-skill`, `dev-ios`, `qa-skill`). compose.py strips the hyphen suffix to find the base role: `"pm-skill".split("-")[0]` → `"pm"`. `_load_manifest()` then loads `references/roles/pm/includes.yml` for the variant because `pm-skill` has no `includes.yml` of its own. A fresh agent must state both the convention (`<base>-<variant>`) and the resolution mechanism (suffix-strip to find base role, fallback to base role's `includes.yml`).

### CQ-3: How is SOUL.md assembled for a Layer 3 variant, and what does the variant's SOUL.md source file contain?
- **Files**: `references/roles/pm-skill/SOUL.md` (preset source file), `references/scripts/compose.py` (`deploy_role()` function), `.squidsquad/pm-skill/SOUL.md` (deployed output).
- **Expected**: A Layer 3 variant has its own full SOUL.md source file in `references/roles/<preset>/SOUL.md`. This file is a FULL file, not an overlay or patch — the Layer 3 author starts from the base role's SOUL.md as their base and modifies it to add variant-specific personality and domain vocabulary. At deploy time, compose.py assembles Layer 1 + Layer 2 SOUL sources plus this full Layer 3 SOUL.md into a single flat `.squidsquad/<preset>/SOUL.md`. No new merge or patch mechanism exists — same concatenation as base roles. A fresh agent must state "full file" (not "patch" or "overlay") and "deploy-time concatenation into one flat file".
