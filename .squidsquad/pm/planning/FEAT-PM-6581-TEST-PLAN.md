# FEAT-PM-6581 Test Plan — Wizard Reframing

## Test Cases

### TC-1: Preset manifest domain_variants resolved per role (happy path)
- **Precondition**: A preset manifest (e.g. `references/presets/software-dev/manifest.yaml`) has a `domain_variants` field mapping each role to a variant (e.g. `dev: web`, `pm: web`, `qa: web`, `dm: web`). The corresponding L3 variant directories exist under `references/roles/`.
- **Steps**: Call `apply_project_type(spec, "web")` (or the post-refactor equivalent manifest-resolution function) with a spec containing all four core roles.
- **Expected**: Each agent in the spec receives the variant declared in the manifest for its role. The return value reflects the per-agent mapping, not a single uniform string.
- **Verification**: Assert `spec["agents"][i]["variant"]` equals the manifest-declared variant for each role. No role receives a variant from the old hardcoded `PROJECT_TYPE_PRESETS` dict.

---

### TC-2: All roles receive domain variant — no role is skipped (happy path)
- **Precondition**: Preset manifest declares variants for dev, pm, qa, and dm. Spec contains one agent of each role.
- **Steps**: Run manifest-driven domain resolution for the preset.
- **Expected**: All four agents have `variant` set (none are `None` or absent). Matches the locked decision "All roles get domain variant."
- **Verification**: Assert `agent["variant"]` is non-None for every agent in `spec["agents"]`.

---

### TC-3: scaffold_install writes L4 project files with structured data (happy path)
- **Precondition**: A valid install spec is built with scan_data containing `test_command`, `stack`, and at least one detected config file. `.squidsquad/project/` does not yet exist.
- **Steps**: Call `scaffold_install(spec, tmp_path, overwrite_existing=True)`. Inspect `.squidsquad/project/` in `tmp_path`.
- **Expected**: `.squidsquad/project/` is created. At minimum one structured L4 file (e.g. `stack-details.md` or `project-conventions.md`) is written with mechanically-populated content derived from scan data (stack, test command, detected config).
- **Verification**:
  ```bash
  ls .squidsquad/project/
  grep -l "test_command\|stack\|Stack" .squidsquad/project/*.md
  ```
  Assert the file exists and contains the values that were in `scan_data`.

---

### TC-4: WIZARD.md runbook adds qualitative notes to L4 files (happy path)
- **Precondition**: `scaffold_install()` has written structured L4 files. WIZARD.md runbook instructs the installer agent to scan the repo and add qualitative notes (conventions, patterns).
- **Steps**: Read WIZARD.md and confirm it contains instructions directing the installer agent to (a) read existing L4 files written by scaffold_install, and (b) append qualitative project-specific notes to those files after the mechanical scaffold step completes.
- **Expected**: WIZARD.md clearly distinguishes the two authorship modes: structured data written by `scaffold_install()` vs. qualitative enrichment written by the LLM agent following the runbook. Instructions are explicit about which sections the agent should populate and which are already machine-written.
- **Verification**: Read WIZARD.md. Confirm presence of instructions referencing `.squidsquad/project/` L4 files and directing the agent to add qualitative content (conventions, domain patterns) after the scaffold step.

---

### TC-5: "custom" project type — no domain variant, agents get L1+L2 only (edge case)
- **Precondition**: Spec contains pm, dev, qa, dm agents. Project type resolved to "custom" (no domain variants declared or user selects custom).
- **Steps**: Run the manifest-driven resolution path with no `domain_variants` declared in the preset (or custom preset selected).
- **Expected**: No agent receives a `variant` field. `spec["project_type"]` is set to `"custom"` (or equivalent). All agents compose from base L1+L2 only.
- **Verification**: Assert `"variant" not in agent` for every agent. Assert `spec.get("project_type") == "custom"` (or the manifest-equivalent field). Run `compose_role("pm")` and confirm no L3 variant file is included in the assembled output.

---

### TC-6: Deprecated design preset with empty role_install_order (edge case)
- **Precondition**: `references/presets/design/manifest.yaml` exists with `role_install_order: []`. Wizard attempts to resolve domain variants for this preset.
- **Steps**: Attempt to build a spec using the design preset (as in `--yes` mode or interactive selection of "design"). Invoke the manifest-driven variant resolution with the design preset.
- **Expected**: No specialist agents are installed (only pm + dm + qa as always-installed roles). No variant is applied (empty `role_install_order` means no L3 assignment loop runs). `scaffold_install()` completes without error; the summary reports only the infrastructure roles.
- **Verification**: Assert `summary["agents"]` contains only infrastructure roles (pm, qa, dm). Assert no `"FAILED"` entries. Assert no `domain_variants` key is referenced (manifest has none).

---

### TC-7: generate_default_spec uses manifest instead of hardcoded preset (regression)
- **Precondition**: Current `generate_default_spec()` hardcodes `"preset": "software-dev"` and sets `"variant": "skill"` directly on the dev agent. After this task, the spec should derive its default variant from the `software-dev` manifest's `domain_variants` field, not from hardcoded strings.
- **Steps**: Call `generate_default_spec()` with no arguments (simulating `--yes` / `cmd_setup_yes` path). Inspect the returned spec.
- **Expected**: The spec's `"preset"` field is `"software-dev"`. The agent variant(s) are derived from the manifest's `domain_variants` field (not hardcoded `"skill"`). If the manifest declares `dev: skill`, the result matches; if changed, the spec reflects the manifest value.
- **Verification**:
  ```python
  spec = wizard.generate_default_spec()
  assert spec["preset"] == "software-dev"
  # Load the manifest and compare variants
  import yaml
  manifest = yaml.safe_load(open("references/presets/software-dev/manifest.yaml"))
  declared = manifest.get("domain_variants", {})
  for agent in spec["agents"]:
      role = agent["role"]
      if role in declared:
          assert agent.get("variant") == declared[role]
  ```

---

### TC-8: scaffold_install overwrite_existing guards still work for L4 files (regression)
- **Precondition**: A previous install has already written `.squidsquad/project/stack-details.md` with custom content. `overwrite_existing=False` (the default).
- **Steps**: Call `scaffold_install(spec, target_root, overwrite_existing=False)` with an updated spec.
- **Expected**: The existing `stack-details.md` (and any other existing L4 files) are not overwritten. They appear in `summary["preserved"]`. New L4 files that did not exist before are still created.
- **Verification**: Assert the content of `.squidsquad/project/stack-details.md` is unchanged after the second scaffold run. Assert the path appears in `summary["preserved"]`.

---

### TC-9: compose.py L4 auto-include path works with new L4 file format (regression)
- **Precondition**: `.squidsquad/project/` contains L4 files written by the new wizard: one `shared-*.md` file (all roles) and one `dev-*.md` file (dev role only). The files use the format scaffold_install will write post-refactor.
- **Steps**: Call `compose_role("dev")` and `compose_role("pm")` against a target root containing those L4 files.
- **Expected**: Both the `shared-*.md` file appears in both assembled outputs. The `dev-*.md` file appears only in the dev agent's output, not the pm agent's output. L4 content is wrapped in `<!-- sub-skill: project-* -->` markers as per current compose.py behavior.
- **Verification**:
  ```python
  dev_out = compose_role("dev")
  pm_out = compose_role("pm")
  assert "sub-skill: project-shared-" in dev_out
  assert "sub-skill: project-shared-" in pm_out
  assert "sub-skill: project-dev-" in dev_out
  assert "sub-skill: project-dev-" not in pm_out
  ```

---

### TC-10: TestApplyProjectType tests replaced with equivalent coverage for new path (side effect)
- **Precondition**: `tests/test_wizard.py` currently contains `TestApplyProjectType` (lines 2013–2046) testing the old uniform-variant path via `PROJECT_TYPE_PRESETS`.
- **Steps**: After the refactor, confirm the old `TestApplyProjectType` class is replaced (not merely supplemented) by new tests that exercise the manifest-driven per-agent variant assignment. Run `python tests/run_tests.py`.
- **Expected**: No test in `TestApplyProjectType` references the old `PROJECT_TYPE_PRESETS` dict or the old `apply_project_type()` signature (uniform variant). New tests exercise: (a) preset manifest declares variants → each agent gets the correct variant, (b) empty/missing domain_variants → no variant assigned, (c) partial role mapping → only declared roles get variants. All new tests pass.
- **Verification**: `python tests/run_tests.py` exits 0. `grep -n "PROJECT_TYPE_PRESETS" tests/test_wizard.py` returns no results (old constant removed or no longer referenced in tests).

---

### TC-11: Fresh install with default preset produces working agent setup (smoke)
- **Precondition**: Empty temp directory. Network access available for `gh` auth check (or mock). `references/presets/software-dev/manifest.yaml` is the resolved preset.
- **Steps**: Run `wizard.generate_default_spec()`, then `scaffold_install(spec, tmp_path, overwrite_existing=True)`.
- **Expected**: `.squidsquad/` tree is created with at minimum pm and skill (dev) agent directories. Each directory contains a valid `CLAUDE.md`. `.squidsquad/project/` exists (may be empty or contain L4 seed files). No `"FAILED"` entries in summary.
- **Verification**:
  ```bash
  python references/scripts/wizard.py --yes --dry-run  # or test harness equivalent
  ls .squidsquad/
  ls .squidsquad/pm/
  ls .squidsquad/skill/
  ls .squidsquad/project/
  ```
  Assert summary `agents` list has no `"FAILED"` entry.

---

## Smoke Tests

- [ ] `python tests/run_tests.py` passes with no failures after the refactor
- [ ] `python references/scripts/wizard.py --help` exits 0 (wizard.py parses without import error)
- [ ] `python references/scripts/compose.py deploy pm` completes without error against a post-refactor install
- [ ] `.squidsquad/project/` is created by scaffold_install even when empty (compose.py L4 directory iteration is a no-op — no error)
- [ ] `generate_default_spec()` returns a spec with `"preset": "software-dev"` and at least one agent with a `variant` field matching the manifest
- [ ] Running `scaffold_install` twice with `overwrite_existing=False` on the same directory raises `FileExistsError` (existing safety net preserved)

---

## Regression Risks

- **Hardcoded PROJECT_TYPE_PRESETS removed prematurely**: If `apply_project_type()` is refactored away before the manifest's `domain_variants` field is wired up, `generate_default_spec()` and `--yes` mode silently produce specs with no variants. Watch for agents composing from L1+L2 only when they should have a variant.
- **Compose merge conflict at line 1071**: `references/scripts/compose.py` currently has an unresolved merge conflict marker at line 1071. This will cause a SyntaxError on import if not resolved before or as part of this task. Any test that imports compose.py will fail until fixed.
- **L4 overwrite guard regression**: The new L4 file write logic must integrate with the existing `overwrite_existing` guard pattern used for `config.md` and `SOUL.md`. If the L4 write path bypasses the guard, re-running setup will clobber PM-curated project conventions.
- **Role-prefix filtering in compose.py**: The `_assemble_claude` L4 filter distinguishes `shared-*.md`, `<role>-*.md`, and unprefixed files. New L4 file names from scaffold_install must follow this convention exactly — a naming deviation silently excludes files from the assembled output.
- **generate_default_spec variant hardcode**: The current code hardcodes `"variant": "skill"` on the dev agent. After refactor, if the manifest does not declare a `domain_variants` field for `software-dev`, the non-interactive `--yes` path produces an agent with no variant. Ensure the manifest is updated alongside the wizard code.
- **Empty project directory**: If `scaffold_install` no longer creates `.squidsquad/project/` at all (e.g., early return on error), compose.py's L4 loop silently finds nothing — no error, but also no L4 content. Smoke test must verify directory creation is unconditional.

---

## Comprehension Questions (task touches LLM-consumed instructions)

### CQ-1: How does the wizard determine which L3 variant to assign to each agent?
- **Files**: `references/scripts/wizard.py` (manifest-resolution path, post-refactor), `references/presets/software-dev/manifest.yaml`
- **Expected**: The wizard reads the preset's `domain_variants` field from the preset manifest YAML. Each agent's role is looked up in that map, and the declared variant is written into the spec's agent entry. There is no hardcoded fallback in `PROJECT_TYPE_PRESETS` — the manifest is the single authority. A missing or null entry in `domain_variants` means that role gets no variant (L1+L2 only).

### CQ-2: What files does scaffold_install write to .squidsquad/project/, and which ones does the LLM agent (WIZARD.md runbook) add to?
- **Files**: `references/scripts/wizard.py` (`scaffold_install` function), WIZARD.md runbook
- **Expected**: `scaffold_install()` mechanically writes structured L4 files (e.g. stack details, test command, detected config) derived from scan_data. The WIZARD.md runbook instructs the installer agent to subsequently open those same files and append qualitative notes (project conventions, domain patterns, team context). The installer agent never overwrites the structured sections; it adds to designated qualitative sections. This is the "hybrid L4 writer" model from the locked decisions.

### CQ-3: What happens when compose.py assembles a CLAUDE.md for a dev agent versus a pm agent, given L4 files in .squidsquad/project/?
- **Files**: `references/scripts/compose.py` (`_assemble_claude` function, lines 314–341)
- **Expected**: compose.py iterates `.squidsquad/project/*.md` in sorted order. Files prefixed `shared-` are included for all roles. Files prefixed with a known role identity (e.g. `dev-`) are included only for agents whose role identity matches that prefix. Files prefixed `pm-` are excluded from the dev agent's output and vice versa. Unprefixed files are included for all roles. The content is wrapped in `<!-- sub-skill: project-<stem> -->` markers.

### CQ-4: Why is overwrite_existing=False the safe default for L4 files, and what does it protect?
- **Files**: `references/scripts/wizard.py` (`scaffold_install` function, overwrite_existing guard)
- **Expected**: `overwrite_existing=False` prevents scaffold_install from clobbering L4 files that were written by a previous install or subsequently edited by PM or the human. L4 files represent accumulated project knowledge (conventions, stack details, team directives). Destroying them on re-run would erase institutional context. The guard places them in `summary["preserved"]` rather than overwriting them, consistent with the pattern used for `SOUL.md` and `working-state.md`.
