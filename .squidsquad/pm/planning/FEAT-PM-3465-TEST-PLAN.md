# FEAT-PM-3465 Test Plan — Layered Role Definition Architecture (Updated: CLAUDE.md + SOUL.md)

> **Why this plan was rewritten**: The previous version was blocked because it covered only SOUL.md layering.
> Per CONTEXT.md locked decision "Both files layered": CLAUDE.md AND SOUL.md must both be layered.
> Layer 3 variants require their own `includes.yml` (with `base_role` + `additional_includes` schema),
> their own entry file (`CLAUDE.md` adding variant-specific prose), and their own `SOUL.md` (full file).
> All 20 presets (5 presets × 4 roles) need both files.
>
> **Scope**: 3-layer model formalized for all roles.
> - Layer 1 = agent definition (Ralph Loop, tracker, vault, heartbeat, cycle runner, context pressure, git, base identity)
> - Layer 2 = role definition (dev, pm, qa, dm, designer — concrete roles)
> - Layer 3 = role customization via `<base>-<variant>` hyphen naming (e.g., pm-skill, dev-ios)
>
> **Presets shipped (full-team compositions, all 4 roles each)**:
> Skill: dev-skill, pm-skill, qa-skill, dm-skill
> iOS: dev-ios, pm-ios, qa-ios, dm-ios
> Web: dev-web, pm-web, qa-web, dm-web
> Android: dev-android, pm-android, qa-android, dm-android
> Full-stack: dev-fullstack, pm-fullstack, qa-fullstack, dm-fullstack
>
> **compose.py changes**: `_load_manifest()` gains `base_role` + `additional_includes` support;
> `_get_entry_file_for_role()` gains suffix-strip fallback generalized to all roles;
> new `_strip_variant_suffix()` helper. Total: ~35 lines changed/added.

---

## Test Cases

### TC-1: CLAUDE.md happy path — deploy-all produces valid CLAUDE.md for all base roles AND all Layer 3 variants
- **Precondition**: Feature branch applied (compose.py generalized, all 20 preset directories created with `CLAUDE.md`, `SOUL.md`, and `includes.yml`). No stale `.squidsquad/` outputs from a previous run.
- **Steps**: Run `python references/scripts/compose.py deploy-all`.
- **Expected**: For all base roles (pm, qa, dev, dm, designer) AND all 20 presets, `.squidsquad/<role>/CLAUDE.md` is written, is non-empty, and contains recognizable role-instruction content. compose.py exits 0 with no errors or warnings.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all && echo OK
  for role in pm qa dev dm designer dev-skill pm-skill qa-skill dm-skill dev-ios pm-ios qa-ios dm-ios dev-web pm-web qa-web dm-web dev-android pm-android qa-android dm-android dev-fullstack pm-fullstack qa-fullstack dm-fullstack; do
    test -s .squidsquad/$role/CLAUDE.md && echo "$role CLAUDE.md OK" || echo "$role CLAUDE.md MISSING/EMPTY"
  done
  ```

---

### TC-2: CLAUDE.md Layer 3 inheritance — pm-skill CLAUDE.md contains pm L1+L2 sub-skills PLUS pm-skill-specific sub-skills
- **Precondition**: `references/roles/pm-skill/includes.yml` declares `base_role: pm` and `additional_includes` listing at least one pm-skill-specific sub-skill (e.g., `pm-skill-specific/deterministic-boundary`). `references/roles/pm/includes.yml` exists with the base pm manifest. Feature branch applied.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy pm-skill` (or deploy-all and inspect).
  2. Inspect `.squidsquad/pm-skill/CLAUDE.md`.
- **Expected**: The deployed `pm-skill/CLAUDE.md` contains:
  - Content from pm's Layer 2 sub-skills (e.g., a string unique to pm-specific sub-skills, such as the PM check-in protocol or tracker protocol wording).
  - Content from pm-skill's Layer 3 `additional_includes` sub-skill(s) (e.g., a string unique to the probabilistic boundary sub-skill).
  Both content blocks must be present in the single flat output file.
- **Verification**:
  ```bash
  # Pick a string uniquely from pm's base includes (Layer 2) — replace <PM_L2_UNIQUE> with actual string
  grep -c "<PM_L2_UNIQUE>" .squidsquad/pm-skill/CLAUDE.md  # must be >= 1
  # Pick a string uniquely from the pm-skill additional sub-skill (Layer 3) — replace <PM_SKILL_L3_UNIQUE>
  grep -c "<PM_SKILL_L3_UNIQUE>" .squidsquad/pm-skill/CLAUDE.md  # must be >= 1
  ```

---

### TC-3: CLAUDE.md Layer 3 isolation — pm-skill-specific content does NOT appear in base pm CLAUDE.md
- **Precondition**: Both `pm` and `pm-skill` have been composed (TC-1 or TC-2 has run). The string used for Layer 3 content in TC-2 is known.
- **Steps**: After deploy-all, inspect `.squidsquad/pm/CLAUDE.md` for the pm-skill Layer 3 unique string.
- **Expected**: The pm-skill Layer 3 content string does NOT appear in `.squidsquad/pm/CLAUDE.md`. Layer 3 additions are additive to the variant only — they must not leak into the base role's deployed output.
- **Verification**:
  ```bash
  # Same Layer 3 unique string from TC-2
  grep "<PM_SKILL_L3_UNIQUE>" .squidsquad/pm/CLAUDE.md  # must return no match (exit code 1)
  ```

---

### TC-4: SOUL.md happy path — deploy-all produces valid SOUL.md for all base roles AND all Layer 3 variants
- **Precondition**: Same as TC-1. All 20 preset `SOUL.md` source files exist in `references/roles/<preset>/SOUL.md`.
- **Steps**: Run `python references/scripts/compose.py deploy-all` (may reuse TC-1 run).
- **Expected**: For all base roles AND all 20 presets, `.squidsquad/<role>/SOUL.md` is written and is non-empty.
- **Verification**:
  ```bash
  for role in pm qa dev dm designer dev-skill pm-skill qa-skill dm-skill dev-ios pm-ios qa-ios dm-ios dev-web pm-web qa-web dm-web dev-android pm-android qa-android dm-android dev-fullstack pm-fullstack qa-fullstack dm-fullstack; do
    test -s .squidsquad/$role/SOUL.md && echo "$role SOUL.md OK" || echo "$role SOUL.md MISSING/EMPTY"
  done
  ```

---

### TC-5: SOUL.md flat assembly — every deployed SOUL.md is a single flat file (no multi-doc, no symlink, no stub)
- **Precondition**: deploy-all has run. Base roles + all 20 presets have SOUL.md outputs.
- **Steps**:
  1. For each deployed SOUL.md (base roles + presets), confirm it is a regular file, not a symlink.
  2. Confirm no multi-document YAML markers (`---`) that would indicate concatenation artifacts.
  3. Confirm the file contains recognizable identity content (not empty or whitespace-only).
  4. Confirm each preset SOUL.md is longer than its source file alone (verifying assembly added base role content).
- **Expected**: Every `.squidsquad/<role>/SOUL.md` is a single flat ASCII text file. Preset SOUL.md line count exceeds the source `references/roles/<preset>/SOUL.md` line count (base content was prepended/appended). No more than one `## Project Adaptation` marker per file.
- **Verification**:
  ```bash
  file .squidsquad/pm-skill/SOUL.md  # "ASCII text", not symlink
  wc -l .squidsquad/pm-skill/SOUL.md  # must be > wc -l references/roles/pm-skill/SOUL.md
  grep -c "## Project Adaptation" .squidsquad/pm-skill/SOUL.md  # must equal 1
  ls -la .squidsquad/pm-skill/  # confirm single SOUL.md, no SOUL-base.md or similar artifacts
  ```

---

### TC-6: soul_adaptation.py unchanged — works correctly on a Layer 3 variant SOUL.md
- **Precondition**: `.squidsquad/pm-skill/SOUL.md` exists from TC-4/TC-5. `soul_adaptation.py` is unmodified (no changes to this script are part of this feature).
- **Steps**:
  1. Run `python references/scripts/soul_adaptation.py render pm-skill`.
  2. Confirm exit code 0.
  3. Confirm the `## Project Adaptation` section is present and rendered without error.
- **Expected**: `soul_adaptation.py` operates identically on a Layer 3 variant SOUL.md as on a base role SOUL.md. The `## Project Adaptation` marker and end-marker are present and parseable. No code change to `soul_adaptation.py` was needed.
- **Verification**:
  ```bash
  python references/scripts/soul_adaptation.py render pm-skill && echo OK
  grep -c "## Project Adaptation" .squidsquad/pm-skill/SOUL.md  # exactly 1
  grep -c "<!-- /project-adaptation -->" .squidsquad/pm-skill/SOUL.md  # exactly 1
  ```

---

### TC-7: Existing dev variants unchanged — skill/be/fe compose identically before and after migration
- **Precondition**: Pre-migration checksums or line counts recorded for `.squidsquad/skill/CLAUDE.md` and `.squidsquad/skill/SOUL.md`. `be` and `fe` directories exist in `references/roles/`.
- **Steps**:
  1. Record pre-migration checksums: `md5sum .squidsquad/skill/CLAUDE.md .squidsquad/skill/SOUL.md`.
  2. Apply the feature branch.
  3. Run `python references/scripts/compose.py deploy-all`.
  4. Compare post-migration checksums to pre-migration.
- **Expected**: The composed output for `skill`, `be`, and `fe` is byte-for-byte identical to pre-migration output for both CLAUDE.md and SOUL.md. The generalized suffix-strip fallback must not alter existing dev variant composition.
- **Verification**:
  ```bash
  # Pre: md5sum .squidsquad/skill/CLAUDE.md > /tmp/skill-pre.md5
  # Post:
  md5sum .squidsquad/skill/CLAUDE.md  # compare to /tmp/skill-pre.md5
  md5sum .squidsquad/skill/SOUL.md    # compare to pre-migration
  # If byte-identical comparison impractical, verify key content strings match and no new content appears
  ```

---

### TC-8: Layer 3 naming convention — _load_manifest() strips hyphen suffix correctly to find base role
- **Precondition**: Feature branch applied. `_load_manifest()` generalized. `references/roles/pm/includes.yml` exists. `references/roles/pm-skill/includes.yml` uses the `base_role` + `additional_includes` schema (NOT the legacy `includes:` key).
- **Steps**: Trigger `_load_manifest("pm-skill")` indirectly via `python references/scripts/compose.py deploy pm-skill`. Observe which manifest is loaded for the base sub-skills.
- **Expected**: `_load_manifest("pm-skill")` reads pm-skill's `includes.yml`, sees `base_role: pm`, recursively loads `references/roles/pm/includes.yml`, and returns pm's manifest entries plus `additional_includes` entries. No error is raised. The composed pm-skill CLAUDE.md contains pm's Layer 2 sub-skill content (proving the correct manifest was used).
- **Verification**:
  ```bash
  # Verify pm-skill/includes.yml uses variant schema (has base_role, not includes:)
  grep "base_role" references/roles/pm-skill/includes.yml   # must match
  grep "^includes:" references/roles/pm-skill/includes.yml  # must NOT match
  # Verify composed output contains pm base content
  grep "<PM_L2_UNIQUE>" .squidsquad/pm-skill/CLAUDE.md  # must match
  ```

---

### TC-9: includes.yml variant schema — base_role + additional_includes merges correctly with base role's includes
- **Precondition**: `references/roles/pm-skill/includes.yml` exists with schema: `base_role: pm` and `additional_includes: [pm-skill-specific/deterministic-boundary]`. `references/roles/pm/includes.yml` exists with the legacy `includes:` schema listing pm's full sub-skill manifest.
- **Steps**:
  1. Manually read both YAML files.
  2. Run `python references/scripts/compose.py deploy pm-skill`.
  3. Inspect `.squidsquad/pm-skill/CLAUDE.md` to count total sub-skill sections present.
- **Expected**: The merged manifest used by compose.py equals: all entries from `pm/includes.yml` (in order) PLUS all entries in `pm-skill/includes.yml additional_includes` (appended). The composed CLAUDE.md contains content from every entry in this merged list. The variant schema (`base_role` + `additional_includes`) is backward-compatible — existing base roles using the `includes:` key are unaffected.
- **Verification**:
  ```bash
  # Count sub-skill sections in pm CLAUDE.md
  SECTIONS_PM=$(grep -c "^---" .squidsquad/pm/CLAUDE.md || true)
  # Count sub-skill sections in pm-skill CLAUDE.md — must be greater by the count of additional_includes
  SECTIONS_PMSKILL=$(grep -c "^---" .squidsquad/pm-skill/CLAUDE.md || true)
  echo "pm: $SECTIONS_PM, pm-skill: $SECTIONS_PMSKILL"
  # pm-skill must have exactly N more sections where N = count of additional_includes entries
  ```

---

### TC-10: Full suite regression — all existing tests pass after migration
- **Precondition**: All base roles migrated (no behavioral change to existing roles). deploy-all has run.
- **Steps**: Run `python tests/run_tests.py`.
- **Expected**: Zero failures. Zero errors. Test count equal to or greater than pre-migration (new tests may be added; none may be removed).
- **Verification**:
  ```bash
  python tests/run_tests.py  # exits 0, no FAIL or ERROR lines
  ```

---

### TC-11: All 20 presets valid — each preset has both CLAUDE.md and SOUL.md source files that compose without errors
- **Precondition**: Feature branch applied. All 20 preset directories exist under `references/roles/` with `CLAUDE.md`, `SOUL.md`, and `includes.yml` (variant schema) in each.
- **Steps**:
  1. For each of 20 presets, verify source files: `references/roles/<preset>/CLAUDE.md`, `SOUL.md`, `includes.yml` each exist and are non-empty.
  2. For each of 20 presets, verify `includes.yml` uses the variant schema (`base_role:` present, `includes:` NOT present).
  3. Run `python references/scripts/compose.py deploy-all` and confirm all 20 produce valid deployed output.
- **Expected**: All 20 preset source directories are complete (3 files each: CLAUDE.md, SOUL.md, includes.yml). All 20 compose without errors. Each deployed CLAUDE.md and SOUL.md is non-empty. compose.py exits 0.
- **Verification**:
  ```bash
  for p in dev-skill pm-skill qa-skill dm-skill dev-ios pm-ios qa-ios dm-ios dev-web pm-web qa-web dm-web dev-android pm-android qa-android dm-android dev-fullstack pm-fullstack qa-fullstack dm-fullstack; do
    test -s references/roles/$p/CLAUDE.md || echo "$p: MISSING source CLAUDE.md"
    test -s references/roles/$p/SOUL.md   || echo "$p: MISSING source SOUL.md"
    test -s references/roles/$p/includes.yml || echo "$p: MISSING includes.yml"
    grep -q "base_role" references/roles/$p/includes.yml || echo "$p: includes.yml missing base_role"
    test -s .squidsquad/$p/CLAUDE.md || echo "$p: MISSING deployed CLAUDE.md"
    test -s .squidsquad/$p/SOUL.md   || echo "$p: MISSING deployed SOUL.md"
    echo "$p OK"
  done
  ```

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` exits 0 with no errors or warnings
- [ ] All 5 base role directories under `.squidsquad/` contain both `CLAUDE.md` and `SOUL.md` after deploy
- [ ] All 20 preset directories under `.squidsquad/` contain both `CLAUDE.md` and `SOUL.md` after deploy
- [ ] Each preset `includes.yml` under `references/roles/<preset>/` uses `base_role:` key (not `includes:`)
- [ ] `.squidsquad/pm-skill/CLAUDE.md` contains pm Layer 2 content (inheritance confirmed)
- [ ] `.squidsquad/pm-skill/CLAUDE.md` contains pm-skill Layer 3 content (variant content confirmed)
- [ ] `.squidsquad/pm/CLAUDE.md` does NOT contain pm-skill Layer 3 content (no leakage)
- [ ] Each deployed `SOUL.md` for all 20 presets is a regular non-empty file (not symlink, not stub)
- [ ] `python references/scripts/soul_adaptation.py render pm` exits 0
- [ ] `python references/scripts/soul_adaptation.py render pm-skill` exits 0
- [ ] `python tests/run_tests.py` exits 0
- [ ] `.squidsquad/skill/CLAUDE.md` is byte-for-byte identical to pre-migration output (no regression)
- [ ] `.squidsquad/skill/SOUL.md` is byte-for-byte identical to pre-migration output (no regression)
- [ ] `grep "^includes:" references/roles/pm-skill/includes.yml` returns no match (variant schema enforced)
- [ ] `python references/scripts/compose.py deploy pm-nonexistent` exits non-zero with a clear error message

---

## Regression Risks

- **CLAUDE.md Layer 3 content missing from variant**: If `_load_manifest()` for a variant fails to append `additional_includes`, the variant's CLAUDE.md is identical to the base role. No error is raised — the failure is silent. Watch for: `pm-skill/CLAUDE.md` line count equal to `pm/CLAUDE.md` (missing the additional sub-skill content).
- **CLAUDE.md Layer 3 content leaking into base role**: If the merged manifest is written back to the base role's manifest or if compose.py uses the wrong manifest path, base role CLAUDE.md gains Layer 3 content unintentionally. Watch for: pm L3 content appearing in `pm/CLAUDE.md` after composing `pm-skill`.
- **Existing dev variant silently broken by suffix-strip**: The suffix-strip generalization in `_load_manifest()` must not alter the existing fallback path for `skill`, `be`, and `fe`. If the new logic resolves `skill` to a non-`dev` base role, these variants silently lose their dev content. Watch for: `skill/CLAUDE.md` missing dev-specific workflow instructions or `skill/SOUL.md` missing code-change protocol.
- **includes.yml schema collision**: A base role that accidentally includes a `base_role:` key in its `includes.yml` would be treated as a variant and recursively inherit from another base role. Watch for: compose errors or unexpected content in base role CLAUDE.md after the compose.py change.
- **soul_adaptation.py marker collision**: A preset SOUL.md containing the string `## Project Adaptation` in its Layer 3 content would create two markers in the assembled file, corrupting soul_adaptation.py rendering. Watch for: duplicate `## Project Adaptation` headers in any assembled SOUL.md.
- **Suffix-strip false positive on future base roles**: A future base role whose name contains a hyphen (e.g., `skill-senior` intended as a base role, not a variant) would be incorrectly resolved as a variant. Watch for: any new base role names with hyphens failing to compose or inheriting the wrong includes.yml.
- **deploy-all missing preset roles**: If `_list_known_role_identities()` does not return preset directories (e.g., because they have no `includes.yml` in the old sense), deploy-all silently skips them. Watch for: deploy-all completing without producing `.squidsquad/pm-skill/` etc.
- **Atomic write not applied to preset outputs**: If compose.py's `.tmp` → `mv` atomic write pattern is not applied to new preset deploy paths, a failure mid-write leaves a corrupt or zero-byte file. Watch for: deploy failure leaving a zero-byte or truncated `.squidsquad/<preset>/CLAUDE.md` or `SOUL.md`.
- **Preset SOUL.md token budget growth**: Each preset's SOUL.md includes full base role content plus Layer 3. PM SOUL.md is longer than dev SOUL.md — pm-skill SOUL.md may be notably large. Watch for: assembled SOUL.md exceeding a sane line count (warn if >250 lines; investigate if >300).

---

## Comprehension Questions

These questions are answered by a fresh agent reading only the files listed — the answer must be derivable from those files alone. They verify the implementing agent understood the architecture as shipped.

### CQ-1: What are the three layers and what does each one own?
- **Files**: `references/docs/layer-model.md` (or `references/sub-skills/manifest.md` layer documentation) and `.squidsquad/pm/planning/FEAT-PM-3465-CONTEXT.md`.
- **Expected**: Layer 1 = agent definition — what any SquidSquad agent IS regardless of role (Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity). Layer 2 = role definition — the concrete role: dev, pm, qa, dm, designer, with role-specific workflow, responsibilities, quality bar, decision style. Layer 3 = role customization — specialization of a role for a specific domain or use case (e.g., pm-skill, dev-ios), inheriting all L1+L2 behavior and adding/extending with variant-specific sub-skills and identity. The agent must NOT mention any "role family" or intermediate grouping concept — that concept was explicitly removed.

### CQ-2: How does CLAUDE.md layering work for a Layer 3 variant? What files are required and how does compose.py use them?
- **Files**: `references/scripts/compose.py` (`_load_manifest()`, `_get_entry_file_for_role()`, `_strip_variant_suffix()`), `references/roles/pm-skill/includes.yml`, `references/roles/pm-skill/CLAUDE.md`, `references/roles/pm/includes.yml`.
- **Expected**: A Layer 3 variant requires three source files: (1) `includes.yml` with `base_role: <base>` and `additional_includes: [<list>]` — the variant schema, distinct from the base role's `includes:` schema; (2) `CLAUDE.md` entry file containing variant-specific prose and `{{include:}}` directives for the additional sub-skills only; (3) `SOUL.md` — full file, not an overlay. compose.py's `_load_manifest()` reads the variant's `includes.yml`, sees `base_role: pm`, recursively loads pm's manifest, appends `additional_includes`, and returns the merged list. `_get_entry_file_for_role()` uses the variant's own `CLAUDE.md` if present, or strips the hyphen suffix to find the base role's entry file. The deployed `CLAUDE.md` is a single flat file containing all L1+L2+L3 content — layering is source-time only, not runtime.

### CQ-3: How is SOUL.md assembled for a Layer 3 variant, and what must the variant's SOUL.md source file contain?
- **Files**: `references/roles/pm-skill/SOUL.md` (preset source), `references/scripts/compose.py` (`deploy_role()`), `.squidsquad/pm-skill/SOUL.md` (deployed output).
- **Expected**: A Layer 3 variant has its own full SOUL.md source file. It is a FULL file — not an overlay, not a patch, not a diff. The Layer 3 author starts from the base role's SOUL.md as their base and writes a complete file that includes the base role's full identity plus variant-specific personality, domain vocabulary, and perspective. At deploy time, compose.py assembles L1 + L2 + L3 SOUL sources into a single flat `.squidsquad/<preset>/SOUL.md`. The assembled file has exactly one `## Project Adaptation` section. No new merge or patch mechanism exists — same build-time concatenation as base roles. If a variant has no SOUL.md, compose.py falls back to the base role's SOUL.md (silent inheritance, not silent empty file).

### CQ-4: What is the Layer 3 naming convention and how does compose.py resolve the base role from a variant name?
- **Files**: `references/scripts/compose.py` (`_strip_variant_suffix()`), `references/docs/layer-model.md` (or equivalent), `references/roles/pm-skill/includes.yml`.
- **Expected**: Layer 3 variants use the `<base>-<variant>` hyphen convention (e.g., `pm-skill`, `dev-ios`, `qa-android`). compose.py's `_strip_variant_suffix()` strips the last hyphen segment using `rsplit("-", 1)[0]` and checks if the result is a known base role identity. If it is, the base role's manifest is used as the starting point. The variant's own `includes.yml` declares `base_role: <base>` explicitly, making the inheritance unambiguous even without relying on the naming convention alone. A fresh agent must state both the convention AND that `includes.yml`'s `base_role` field is the authoritative source for inheritance — the suffix-strip is a fallback for variants that have no `includes.yml` of their own.
