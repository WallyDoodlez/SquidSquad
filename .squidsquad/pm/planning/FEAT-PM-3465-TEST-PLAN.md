# FEAT-PM-3465 Test Plan — Layered Role Definition Architecture

## Test Cases

### TC-1: Happy path — deploy-all produces valid layered artifacts for all 5 roles
- **Precondition**: Layer 1 base sources, Layer 2 general-role sources, and Layer 3 role-specific sources all exist under the chosen directory layout. No `.squidsquad/<role>/CLAUDE.md` or `SOUL.md` files exist (clean deploy).
- **Steps**: Run `python references/scripts/compose.py deploy-all`.
- **Expected**: `.squidsquad/<role>/CLAUDE.md` and `.squidsquad/<role>/SOUL.md` are written for all 5 roles (pm, qa, skill, dm, designer). Each CLAUDE.md contains content from Layer 1 (base agent), Layer 2 (general role), and Layer 3 (role-specific) in that order. Each SOUL.md is a single flat file containing content from all three SOUL source layers.
- **Verification**: For each role, `grep` for a Layer-1-only string (e.g., the Ralph Loop preamble that lives only in the base template), a Layer-2-only string (e.g., "code-change protocol" for developer roles, "pipeline oversight" for coordinator), and a Layer-3-only string (a role-specific section header that cannot appear in Layer 1 or 2). All three must be present in the same output file. `wc -l .squidsquad/<role>/SOUL.md` must be greater than any single source layer alone.

---

### TC-2: SOUL.md flat assembly — deployed file is a single flat file; soul_adaptation.py works unchanged
- **Precondition**: `deploy-all` has run successfully (TC-1 passed). `.squidsquad/pm/SOUL.md` exists as a flat assembled file.
- **Steps**:
  1. Confirm `.squidsquad/pm/SOUL.md` is a single file (not a symlink, not a directory, not a multi-document YAML).
  2. Run `python references/scripts/soul_adaptation.py render pm` (or equivalent invocation).
  3. Confirm the command exits 0 without modification to soul_adaptation.py itself.
- **Expected**: `soul_adaptation.py render` locates the `## Project Adaptation` section and `<!-- /project-adaptation -->` marker in the flat SOUL.md and renders successfully. The output file still contains all Layer 1+2+3 content alongside the adaptation section. No error is raised about missing sections or unexpected file structure.
- **Verification**: `python references/scripts/soul_adaptation.py render pm && echo OK`. Check that `grep "## Project Adaptation" .squidsquad/pm/SOUL.md` returns exactly one match. Check that the Layer 1 identity string still appears above the adaptation section.

---

### TC-3: Dev variant Layer 2 inheritance — `skill` agent receives "developer" Layer 2 content
- **Precondition**: `dev/manifest.yaml` contains `general_role: developer`. No `references/roles/skill/manifest.yaml` exists (skill is a pure variant). Clean deploy state.
- **Steps**: Run `python references/scripts/compose.py deploy skill` (or equivalent single-role deploy).
- **Expected**: `.squidsquad/skill/SOUL.md` contains the Layer 2 "developer" identity content (e.g., code-change protocol, PR conventions) that originates from the general role source — not from anything in skill's own role directory. `.squidsquad/skill/CLAUDE.md` likewise contains the Layer 2 developer instructions.
- **Verification**: `grep "<layer2-developer-unique-string>" .squidsquad/skill/SOUL.md` returns a match. `grep "<layer2-developer-unique-string>" .squidsquad/skill/CLAUDE.md` returns a match. Cross-check: `grep "<layer2-developer-unique-string>" references/roles/skill/` returns no matches (confirming content came from parent, not skill's own sources).

---

### TC-4: PM dual Layer 2 — deployed PM SOUL.md contains both coordinator AND verifier identity content
- **Precondition**: PM's Layer 2 is configured as coordinator + verifier dual (per locked decisions). `deploy-all` or `deploy pm` has run.
- **Steps**: Inspect `.squidsquad/pm/SOUL.md` and `.squidsquad/pm/CLAUDE.md`.
- **Expected**: Both files contain coordinator identity content (e.g., pipeline oversight, human check-in language) AND verifier identity content (e.g., zero-gap gate, coverage requirements). Both sets of content are present in the same flat file. Neither set is absent.
- **Verification**: `grep "<coordinator-unique-string>" .squidsquad/pm/SOUL.md` — match found. `grep "<verifier-unique-string>" .squidsquad/pm/SOUL.md` — match found. Compare against `.squidsquad/qa/SOUL.md`: QA's verifier content originates from the same Layer 2 source — if dev chose shared extraction, both files share an identical passage; if dev chose duplication, PM and QA each contain equivalent but independently stored verifier text.

---

### TC-5: upgrade_soul() preservation — Layer 3 content and Project Adaptation section survive upgrade
- **Precondition**: `.squidsquad/pm/SOUL.md` exists from a prior deploy. It has been modified by `soul_adaptation.py` to contain non-empty `## Project Adaptation` content (simulate a project-adapted install). Layer 3 content unique to PM (not present in Layer 1 or Layer 2) is also present.
- **Steps**:
  1. Record the current `## Project Adaptation` section content.
  2. Record a Layer-3-only string present in SOUL.md.
  3. Simulate an upgrade: modify the Layer 1 base SOUL source (e.g., bump a version string in the Layer 1 template) and run `python references/scripts/compose.py upgrade-soul pm` (or `compose.py deploy-all` using the new `upgrade_soul()` path).
- **Expected**: After the upgrade, `.squidsquad/pm/SOUL.md` contains the updated Layer 1 content (the bumped version string). The `## Project Adaptation` section is unchanged — same content as before the upgrade. The Layer-3-only string is also present and unchanged.
- **Verification**: `grep "<updated-layer1-string>" .squidsquad/pm/SOUL.md` — match. `diff <(before-adaptation-section) <(after-adaptation-section)` — zero diff. `grep "<layer3-unique-string>" .squidsquad/pm/SOUL.md` — match.

---

### TC-6: Atomic write — SOUL.md generation uses .tmp + mv pattern
- **Precondition**: Developer implementation complete. Source is readable.
- **Steps**: Inspect the compose.py `deploy_role()` and/or `upgrade_soul()` code path that writes `.squidsquad/<role>/SOUL.md`.
- **Expected**: The write path creates a `.tmp` file (e.g., `.squidsquad/<role>/SOUL.md.tmp`) and then renames/moves it to the final path. The final file is never written via a direct open-and-write to the target path.
- **Verification**: `grep -n "\.tmp" references/scripts/compose.py` — find the temp file creation line. `grep -n "os.rename\|shutil.move\|mv\b" references/scripts/compose.py` (or equivalent Python rename call) — find the atomic move. Confirm the rename target is the final SOUL.md path. No direct `open(".squidsquad/<role>/SOUL.md", "w")` write without a prior `.tmp` intermediate.

---

### TC-7: Full suite regression — all existing tests pass after migration
- **Precondition**: All 5 roles have been migrated to the new layered source structure. `deploy-all` has run and produced fresh artifacts.
- **Steps**: Run the full test suite: `python tests/run_tests.py`.
- **Expected**: Zero failures. Zero errors. All tests that passed before the migration continue to pass.
- **Verification**: `python tests/run_tests.py` exits 0. No new `FAIL` or `ERROR` lines in output. If any tests specifically check compose.py behavior or SOUL.md structure, they must also pass.

---

### TC-8: Comms independence — comms sub-skills remain in common/, unaffected by Layer 2
- **Precondition**: Migration complete. `deploy-all` has run.
- **Steps**:
  1. Confirm that `references/sub-skills/common/chat-etiquette`, `mention-protocol`, and `consensus-protocol` still exist at their existing paths and have not been moved into any Layer 2 general-role directory.
  2. Deploy a role that uses comms sub-skills (e.g., any role with comms feature-flag enabled in its includes.yml).
  3. Confirm the composed CLAUDE.md includes the comms content at the correct position (after Layer 2, as a common include — not as part of Layer 2 itself).
- **Expected**: Comms sub-skill paths are unchanged. Their inclusion position in composed output is unchanged. No Layer 2 general-role file references comms sub-skills by path.
- **Verification**: `ls references/sub-skills/common/ | grep -E "chat-etiquette|mention-protocol|consensus-protocol"` — all three present. `grep -r "chat-etiquette\|mention-protocol\|consensus-protocol" references/roles/general/` — zero matches (comms are not embedded in Layer 2 sources).

---

### TC-9: No runtime change — agent boot reads exactly one SOUL.md file
- **Precondition**: `deploy-all` has run. `.squidsquad/<role>/SOUL.md` exists as a flat file.
- **Steps**: Inspect the deployed `.squidsquad/<role>/CLAUDE.md` for the `{{runtime:}}` directive that references the SOUL.md. Count how many `{{runtime:}}` directives for SOUL files are present. Also confirm the agent template's boot instruction references a single SOUL.md path.
- **Expected**: Exactly one `{{runtime: souls/<role>}}` directive (or equivalent single-file reference) per composed CLAUDE.md. No new `{{runtime:}}` entries for Layer 1 or Layer 2 SOUL sources. The agent reads one file at boot, not three.
- **Verification**: `grep "runtime.*soul\|runtime.*SOUL" .squidsquad/<role>/CLAUDE.md | wc -l` — output is `1`. `ls .squidsquad/<role>/` — only one SOUL.md file present (no `SOUL-layer1.md`, `SOUL-base.md`, etc.).

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy-all` exits 0 with no errors or warnings
- [ ] All 5 role directories under `.squidsquad/` contain both `CLAUDE.md` and `SOUL.md` after deploy
- [ ] Each deployed `SOUL.md` is a regular file (not empty, not a symlink, not a directory)
- [ ] `python references/scripts/soul_adaptation.py render pm` exits 0
- [ ] `python references/scripts/soul_adaptation.py render qa` exits 0
- [ ] `grep "## Project Adaptation" .squidsquad/pm/SOUL.md` returns exactly one match
- [ ] `python tests/run_tests.py` exits 0
- [ ] `ls references/sub-skills/common/ | grep chat-etiquette` returns a match
- [ ] `.squidsquad/skill/SOUL.md` exists and contains developer Layer 2 content (confirm via grep)
- [ ] No `references/roles/general/` directory contains any comms sub-skill files

---

## Regression Risks

- **soul_adaptation.py marker parsing**: If the assembled SOUL.md has two `## Project Adaptation` section headers (one from a Layer 2 source that accidentally reuses the marker name), soul_adaptation.py will corrupt the file. Watch for: adaptation rendering producing duplicate sections or clobbering non-adaptation content.
- **Dev variant fallback silently missing Layer 2**: If `_load_manifest()` fallback resolves the Layer 3 manifest but does not walk up to inject Layer 2 content, `skill`/`be`/`fe` variants silently deploy without developer identity. Watch for: composed SOUL.md for skill that contains only Layer 1 + Layer 3 with no Layer 2 strings.
- **PM SOUL.md size inflation**: With dual Layer 2 (coordinator + verifier) plus Layer 1 and Layer 3, PM's SOUL.md may grow significantly. Watch for: token budget impact — PM's SOUL.md substantially larger than QA's; verify both are under a sane size limit (e.g., <200 lines).
- **upgrade_soul() clobbering Layer 3**: If the upgrade function re-renders Layer 3 from the template source (instead of preserving the deployed Layer 3 section), project-customized Layer 3 content is lost silently. Watch for: upgrade that overwrites any content below the Layer 2 boundary.
- **Atomic write leaving .tmp on failure**: If compose.py crashes mid-write, a stale `.tmp` file may remain. Watch for: leftover `.squidsquad/<role>/SOUL.md.tmp` files after a failed run that could be mistakenly read on a subsequent partial run.
- **Manifest schema backward-compat**: If `_load_manifest()` now expects `general_role` and it is absent on legacy manifests (e.g., custom roles added before this migration), compose.py may error or silently produce no Layer 2 content. Watch for: any role that does not have `general_role` in its manifest failing to deploy or deploying with missing Layer 2 identity.
- **Compose output size regression**: Larger composed CLAUDE.md files may hit Claude's context window earlier in long sessions. Watch for: notable increase in composed file size vs. pre-migration baselines.

---

## Comprehension Questions (task touches LLM-consumed instructions)

### CQ-1: What are the three layers in the new architecture, and what does each layer own?
- **Files**: Deployed `.squidsquad/<role>/CLAUDE.md` (composed output), or the Layer 1 base source and Layer 2 general-role source files created during implementation.
- **Expected**: Layer 1 = base SquidSquad agent identity (Ralph Loop, boot instructions, timestamp discipline, atomic writes, subagent model preference — shared by all roles). Layer 2 = role-family identity (coordinator, verifier, developer, delivery, creative — content genuinely not present in common/ today, e.g. code-change protocol for developer, zero-gap gate for verifier, pipeline oversight for coordinator). Layer 3 = specific role instructions and personality (the existing per-role CLAUDE.md and SOUL.md content that is not shared). A fresh agent must name all three layers and give at least one concrete content example for each.

### CQ-2: Where and when is SOUL.md assembled from its three layers?
- **Files**: `references/scripts/compose.py` (the `deploy_role()` or `upgrade_soul()` function), the Layer 1/2/3 SOUL source files, and the deployed `.squidsquad/<role>/SOUL.md`.
- **Expected**: Assembly happens at deploy time (i.e., when `compose.py deploy-all` or `deploy <role>` runs), not at agent boot time. The three SOUL source files are concatenated by compose.py into a single flat `.squidsquad/<role>/SOUL.md`. At runtime, the agent reads exactly one file. `soul_adaptation.py` and the `{{runtime:}}` directive are unchanged — they see the same single-file structure as before. A fresh agent must state "deploy-time" (not "runtime" or "boot-time") and "single flat file".

### CQ-3: How does the `skill` agent (a dev variant with no own role directory) get its Layer 2 content?
- **Files**: `references/roles/dev/manifest.yaml` (contains `general_role: developer`), `references/scripts/compose.py` (`_load_manifest()` fallback logic), deployed `.squidsquad/skill/SOUL.md`.
- **Expected**: The `skill` agent has no `references/roles/skill/manifest.yaml`. The existing `_load_manifest()` fallback resolves to `dev/manifest.yaml`. That manifest declares `general_role: developer`. compose.py uses this field to inject the Layer 2 "developer" general-role SOUL and CLAUDE content when assembling skill's output. No new inheritance logic was added — the existing parent-manifest fallback handles it. A fresh agent must identify the fallback mechanism and the `general_role` field in dev's manifest as the source of Layer 2 for skill.

### CQ-4: What does the PM role's Layer 2 contain that differs from a pure verifier role like QA?
- **Files**: The Layer 2 general-role sources for "coordinator" and "verifier" (under `references/roles/general/` or equivalent), deployed `.squidsquad/pm/SOUL.md`, deployed `.squidsquad/qa/SOUL.md`.
- **Expected**: PM's Layer 2 carries both coordinator identity (pipeline oversight, human check-in, routing work to agents) AND verifier identity (zero-gap gate, coverage requirements). QA's Layer 2 carries only verifier identity. PM has more Layer 2 content than QA as a result of the dual assignment. A fresh agent must identify that PM's Layer 2 = coordinator + verifier (not just one), and explain that this was a locked decision because PM falls back to combined PM/QA duties when QA is absent.

### CQ-5: What must upgrade_soul() preserve, and what is it allowed to update?
- **Files**: `references/scripts/compose.py` (`upgrade_soul()` function), `.squidsquad/<role>/SOUL.md` (live deployed file), the Layer 1 and Layer 2 SOUL source templates.
- **Expected**: `upgrade_soul()` is allowed to update Layer 1 and Layer 2 sections of the deployed SOUL.md (re-rendering them from the current source templates, so agents pick up improvements to base and general-role identity). It must NOT modify Layer 3 content (the role-specific identity) and must NOT modify the `## Project Adaptation` section or anything between that marker and `<!-- /project-adaptation -->`. These two regions are treated as immutable by the upgrade function. A fresh agent must state both the "allowed" (L1+L2) and the "forbidden" (L3 + Project Adaptation) parts explicitly.
