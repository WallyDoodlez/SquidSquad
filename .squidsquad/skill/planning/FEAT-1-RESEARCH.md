# FEAT-1 Research: Templatize Boot Scripts

**Feature**: Replace 6 separate boot scripts (start-*.ps1 / start-*.sh) with a single template per platform, parameterized by role. A generator produces role-specific scripts from the template.

**Date**: 2026-04-05

---

## Current State Analysis

### Diff Summary: What Differs Per Role

All 3 `.sh` scripts and all 3 `.ps1` scripts are structurally identical. The only intentional per-role differences are:

| Parameter | skill | pm | dm |
|-----------|-------|----|----|
| config.py alias arg | `alias skill` | `alias pm` | `alias dm` |
| Default fallback name | `squidsquad-skill` | `squidsquad-pm` | `squidsquad-dm` |
| .active-role value | `skill` | `pm` | `dm` |
| current-state path | `.squidsquad/skill/current-state` | `.squidsquad/pm/current-state` | `.squidsquad/dm/current-state` |
| SQUIDSQUAD_ROLE | `skill` | `pm` | `dm` |
| Logo display name | `$AGENT_NAME` | `$AGENT_NAME` | `$AGENT_NAME` |
| Init message (sh) | `"Skill dev - start the loop"` | `"start the loop"` | `"start the loop"` |
| Init message (ps1) | `"Skill dev - start the loop"` | `"PM - start the loop"` | `"start the loop"` |

That's it. Every other line is identical across roles within the same platform.

### Accidental Drift (bugs from separate maintenance)

These are differences that exist in the actual scripts but should not:

1. **`start-skill.ps1` missing `Test-Path` guard** (lines 27-35): `start-pm.ps1` and `start-dm.ps1` wrap the logo block in `if (Test-Path .squidsquad) { ... }`. `start-skill.ps1` does not — it reads `config.md` unconditionally. If `.squidsquad/` were missing, skill would error while pm/dm would silently skip.

2. **`start-skill.ps1` missing `-ErrorAction SilentlyContinue`**: `start-pm.ps1` line 25 and `start-dm.ps1` line 25 use `Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue`. `start-skill.ps1` line 24 omits `-ErrorAction SilentlyContinue`.

3. **Init messages are inconsistent**: `start-skill.sh` says `"Skill dev - start the loop"`, `start-skill.ps1` says `"Skill dev - start the loop"`, `start-pm.sh` says `"start the loop"`, `start-pm.ps1` says `"PM - start the loop"`, `start-dm.sh`/`start-dm.ps1` both say `"start the loop"`. There is no principled reason for these to differ.

4. **SKILL.md templates are outdated**: The templates in SKILL.md Step 5 (lines 595-658 for generic, 660-725 for PM, 729-794 for DM) do NOT include the `--name` flag parsing block or the `config.py alias` fallback. These were added to the actual scripts later but never back-ported to the SKILL.md templates. This means any new setup from SKILL.md produces scripts without `--name` support.

### Template Parameters Needed

Based on the analysis, the template needs exactly these parameters:

| Parameter | Example | Source |
|-----------|---------|--------|
| `ROLE` | `skill`, `pm`, `dm`, `fe` | Role name from config.md |
| `DEFAULT_ALIAS` | `squidsquad-skill` | Always `squidsquad-{ROLE}` |
| `INIT_MESSAGE` | `start the loop` | Could standardize to `"start the loop"` for all |

`DEFAULT_ALIAS` is always `squidsquad-{ROLE}`, so it can be derived. `INIT_MESSAGE` could be standardized. That reduces the template to a **single parameter: `ROLE`**.

---

## 1. Codebase Impact

### Files That Change

| File | Action | Notes |
|------|--------|-------|
| `references/templates/start-role.sh` | **NEW** | Bash template with `{{ROLE}}` placeholders |
| `references/templates/start-role.ps1` | **NEW** | PowerShell template with `{{ROLE}}` placeholders |
| `references/scripts/generate_boot.py` | **NEW** | Generator script (or extend compose.py) |
| `.squidsquad/start-skill.sh` | **GENERATED** | Output of generator |
| `.squidsquad/start-skill.ps1` | **GENERATED** | Output of generator |
| `.squidsquad/start-pm.sh` | **GENERATED** | Output of generator |
| `.squidsquad/start-pm.ps1` | **GENERATED** | Output of generator |
| `.squidsquad/start-dm.sh` | **GENERATED** | Output of generator |
| `.squidsquad/start-dm.ps1` | **GENERATED** | Output of generator |
| `SKILL.md` | **MODIFY** | Step 5 templates replaced with generator invocation |
| `tests/test_start_scripts.py` | **MODIFY** | Add template tests, keep output tests |
| `references/scripts/compose.py` | **POSSIBLY MODIFY** | If we extend it instead of new script |

### Generation Approach: Extend compose.py vs. New Script

**Option A — Extend `compose.py`**: compose.py already does `{{include: path}}` resolution and `[ROLE]`-style placeholder substitution (lines 100-134). Adding a `generate-boot` command that reads `references/templates/start-role.{sh,ps1}` and substitutes `{{ROLE}}` is natural. The `deploy_role()` function (line 137) is the closest pattern.

**Option B — New `generate_boot.py`**: Keeps compose.py focused on CLAUDE.md composition. Boot scripts are a different artifact type (shell scripts vs markdown). A dedicated 50-line script is simpler to understand.

**Recommendation**: Option A (extend compose.py). The substitution logic already exists, and compose.py is the established "generate artifacts from templates" tool. Adding a `boot` subcommand keeps the tool surface small.

### Impact on Setup Flow (SKILL.md)

SKILL.md Step 5 (lines 589-933) currently contains 6 complete script bodies that the setup agent copies verbatim. This would change to:

```
# Step 5 — Generate Boot Scripts
For each role (dev agents + pm + qa + dm + designer as applicable):
  python references/scripts/compose.py boot <role>
```

The 340 lines of inline script templates in SKILL.md (lines 595-933) collapse to ~10 lines of generator invocation.

### Impact on Existing Tests (test_start_scripts.py)

The 51 test cases in `tests/test_start_scripts.py` test the **output** scripts, not templates. They verify:
- Scripts exist (6 TCs)
- Bash has shebang (3 TCs)
- --name flag parsing present (6 TCs)
- shift 2 in bash (3 TCs)
- config.py alias fallback (6 TCs)
- Correct SQUIDSQUAD_ROLE (6 TCs)
- --append-system-prompt used (6 TCs)
- --name variable passed to claude (6 TCs)
- active-role written (3 TCs)
- inject-permissions called (3 TCs)
- current-state initialized (3 TCs)

All 51 TCs remain valid and should still pass after generation. They become **regression tests** ensuring the generator produces correct output. Additionally, new tests should verify:
- Templates exist in `references/templates/`
- Generator produces identical output to committed scripts
- Template contains all required placeholders
- No placeholder leaks (no `{{ROLE}}` in generated output)

---

## 2. Template Design

### Bash Template (`references/templates/start-role.sh`)

```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

# Parse --name flag (optional override for agent alias)
AGENT_NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) AGENT_NAME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Read alias from config if no --name override
if [ -z "$AGENT_NAME" ]; then
  AGENT_NAME=$(python references/scripts/config.py alias {{ROLE}} 2>/dev/null || echo "squidsquad-{{ROLE}}")
fi

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D   v${V:-?}  —  ${AGENT_NAME}

LOGO
fi

# Inject permissions from template into settings.json
bash .squidsquad/inject-permissions.sh

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "{{ROLE}}" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/{{ROLE}}/current-state
echo "idle|Initializing..." > .squidsquad/{{ROLE}}/current-state

claude --dangerously-skip-permissions --name "$AGENT_NAME" --append-system-prompt "SQUIDSQUAD_ROLE={{ROLE}}" "start the loop"
```

### PowerShell Template (`references/templates/start-role.ps1`)

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

# Parse --name flag (optional override for agent alias)
$AgentName = ""
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq "--name" -and ($i + 1) -lt $args.Count) {
        $AgentName = $args[$i + 1]
        break
    }
}

# Read alias from config if no --name override
if (-not $AgentName) {
    try {
        $AgentName = (python references/scripts/config.py alias {{ROLE}} 2>$null).Trim()
    } catch {
        $AgentName = "squidsquad-{{ROLE}}"
    }
    if (-not $AgentName) { $AgentName = "squidsquad-{{ROLE}}" }
}

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

    Write-Host ""
    Write-Host "      ▗▄▖"
    Write-Host "     ▟█ █▙"
    Write-Host "    ▐█• •█▌"
    Write-Host "   ███████"
    Write-Host "   ▐█████▌"
    Write-Host "    ▐▌▐▌▐▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  $AgentName"
    Write-Host ""
}

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"{{ROLE}}" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/{{ROLE}}/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/{{ROLE}}/current-state -NoNewline

$sysPrompt = "SQUIDSQUAD_ROLE={{ROLE}}"
$initMsg = "start the loop"
claude --dangerously-skip-permissions --name "$AgentName" --append-system-prompt $sysPrompt $initMsg
```

### Template Location

`references/templates/` — parallel to `references/scripts/` and `references/sub-skills/`. This directory does not exist yet.

### Generation Trigger

| Trigger | When | How |
|---------|------|-----|
| `/squidsquad-setup` | Step 5 | `python references/scripts/compose.py boot <role>` for each role |
| `/squidsquad-upgrade` | Per-role agent | Same command, regenerates from updated template |
| Manual | Developer runs directly | `python references/scripts/compose.py boot skill` |
| `compose.py boot-all` | Convenience | Iterates all roles from config.md |

---

## 3. Side Effects

### What Breaks if Generation Fails

If `compose.py boot <role>` fails (template missing, Python error, etc.):
- The `.squidsquad/start-<role>.{sh,ps1}` files will not be written
- If this is a fresh setup: agents cannot be launched. User sees clear error.
- If this is an upgrade: old scripts remain in place (safe — they just won't get the fix). But the upgrade agent should detect this and report it.

**Mitigation**: Generator should validate the template exists and all `{{ROLE}}` placeholders are substituted before writing. If substitution leaves any `{{...}}` in output, fail loudly.

### Boot Script Permissions (chmod +x)

The `.sh` scripts need `chmod +x`. Currently, `git` preserves the execute bit. The generator must either:
- Run `chmod +x` after writing (Unix only)
- Set the git filemode bit

Current scripts in the repo already have the execute bit set. The generator should call `os.chmod(path, 0o755)` on Unix, and `subprocess.run(["git", "update-index", "--chmod=+x", path])` on Windows (where filesystem doesn't track it).

### BOM Handling for .ps1

Checking the current `.ps1` files: they do NOT have a UTF-8 BOM (verified by the `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` line being the first line, and the files being read cleanly by test_start_scripts.py with `encoding="utf-8"`). The generator should write UTF-8 without BOM, matching current behavior.

### Line Endings

- `.sh` files MUST use LF (`\n`). CRLF in bash scripts causes `\r` errors.
- `.ps1` files work with either, but CRLF is conventional on Windows.

The generator should:
- Write `.sh` with `newline='\n'` (explicit LF)
- Write `.ps1` with default platform line endings (or CRLF explicitly)

The `.gitattributes` file (if present) may also handle this. Current repo likely uses `git config core.autocrlf` — the generator should write with explicit line endings to avoid surprises.

### Impact on Existing Clones

Existing clones already have working boot scripts. The first `upgrade` after this feature will regenerate them from template. If the generated output matches current scripts (minus the drift bugs), `git diff` shows only the bug fixes. This is a clean upgrade path.

---

## 4. Edge Cases

### Custom Roles Beyond skill/pm/dm

SKILL.md already defines templates for: `fe`, `be`, `qa`, `designer` (lines 595-933). The template approach inherently supports any role name — the `{{ROLE}}` placeholder is the only variable. No special-casing needed.

Config.md's `Dev Agents` field lists active dev roles. The generator reads this to know which roles to generate for. PM is always present. QA is present when dev/designer agents exist. DM is present when `dm/` directory exists.

### Human Has Manually Edited a Boot Script

Risk: user added custom logic (e.g., environment variable setup, conda activation). Regeneration would overwrite it.

**Mitigation options**:
1. **Generated header comment**: Add `# GENERATED by compose.py — DO NOT EDIT. Regenerate: python references/scripts/compose.py boot <role>` at the top (matching the pattern used in CLAUDE.md generation, see compose.py line 146-147).
2. **Diff check before overwrite**: If the existing file doesn't match the expected generated output for the OLD template, warn that manual edits will be lost. This is complex and fragile.
3. **`--force` flag**: Generator skips files that exist unless `--force` is passed. Setup always uses `--force`, upgrade uses `--force` (since the whole point is to update scripts).

**Recommendation**: Option 1 (header comment). It's the pattern already used for generated CLAUDE.md files. Users who ignore the warning and edit anyway are making a conscious choice.

### Role Added After Initial Setup

User starts with `skill` only, later adds `fe`. They run `/squidsquad-setup` again or manually invoke `compose.py boot fe`. The generator creates `start-fe.sh` and `start-fe.ps1`. No conflict with existing scripts.

### Template Changes During Upgrade

When SKILL.md is updated with a new boot script feature (e.g., adding `--name` flag parsing), the upgrade flow regenerates all boot scripts from the updated template. This is the exact problem this feature solves — instead of manually patching 6 files, the template is patched once and all scripts are regenerated.

---

## 5. Integration Risks

### /squidsquad-upgrade

Current upgrade flow (SKILL.md lines 1193-1207) says: "Also regenerate `.squidsquad/start-[role].sh` and `.squidsquad/start-[role].ps1`" for each role agent. Currently, upgrade agents copy the inline templates from SKILL.md. After this feature, they call `compose.py boot <role>` instead.

**Risk**: The upgrade agent needs to know to call `compose.py boot` instead of copying templates. This is controlled by SKILL.md Step 5 instructions. As long as SKILL.md is updated, the upgrade agents will use the new approach.

**Risk**: If the template file (`references/templates/start-role.sh`) doesn't exist in an older skill version being upgraded FROM, the generator will fail. Mitigation: the upgrade copies the new `references/` files first (they come from the skill repo), then generates.

### /squidsquad-setup

Setup (SKILL.md Step 5) currently has the agent write boot scripts by copying inline templates. After this feature, Step 5 instructions change to invoke the generator. The setup agent reads SKILL.md at runtime, so it automatically picks up the new instructions.

### compose.py Changes

Adding a `boot` subcommand to compose.py:

```python
elif cmd == "boot":
    if len(args) < 2:
        print("Usage: compose.py boot <role>", file=sys.stderr)
        sys.exit(1)
    role = args[1]
    generate_boot_scripts(role)
```

The `generate_boot_scripts()` function:
1. Reads `references/templates/start-role.sh` and `references/templates/start-role.ps1`
2. Replaces `{{ROLE}}` with the role name
3. Writes to `.squidsquad/start-{role}.sh` and `.squidsquad/start-{role}.ps1`
4. Sets execute permission on `.sh`

This is ~30 lines of new code. compose.py currently has 200 lines. Low risk.

A `boot-all` subcommand reads `config.md` for dev-agents, always includes pm, conditionally includes qa/dm/designer, and generates all.

---

## 6. Upgrade & Migration

### How Existing Installs Get Templatized Scripts

1. User runs `/squidsquad-upgrade`
2. Upgrade detects version gap (SKILL.md version > config.md version)
3. Each role agent now calls `compose.py boot <role>` instead of copying inline templates
4. Generated scripts overwrite existing scripts
5. `git diff` shows the changes (mostly drift fixes + generated header comment)

### What Happens if They Don't Upgrade

Nothing breaks. Existing scripts continue to work. They just don't get fixes automatically. This is the current behavior anyway — manual patches are required.

### Migration Checklist

1. Create `references/templates/` directory
2. Write `references/templates/start-role.sh` and `references/templates/start-role.ps1`
3. Add `boot` and `boot-all` commands to `compose.py`
4. Update SKILL.md Step 5 to use generator instead of inline templates
5. Update SKILL.md Upgrade Instructions to reference generator
6. Regenerate all 6 scripts (3 roles x 2 platforms) to fix drift bugs
7. Update `tests/test_start_scripts.py` to add template validation tests
8. Run all 51 existing TCs to confirm generated output passes

---

## 7. Open Questions

1. **Should init messages be standardized?** Currently skill says `"Skill dev - start the loop"`, pm says `"PM - start the loop"` (ps1) or `"start the loop"` (sh), dm says `"start the loop"`. Should all roles use the same message (e.g., `"start the loop"`)? Or should the template support a `{{INIT_MESSAGE}}` parameter? **Why this matters**: If standardized, the template has exactly 1 parameter (ROLE). If per-role, we need a second parameter or a config lookup.

2. **Should generated scripts have a "DO NOT EDIT" header?** This is the pattern used for generated CLAUDE.md files. Adding it is low-cost and signals intent. **Why this matters**: Without it, users may edit generated scripts and lose changes on upgrade.

3. **Should `references/templates/` also hold the SKILL.md inline template blocks for QA, Designer?** Currently SKILL.md has templates for qa and designer that don't exist as actual scripts in this repo (SquidSquad is its own test case with only skill/pm/dm). **Why this matters**: Keeping templates in one place vs. keeping them in SKILL.md affects where upgrade agents look.

4. **Should the `.sh` template include `2>/dev/null || true` on `inject-permissions.sh`?** The SKILL.md template has it (line 616), but the actual `start-skill.sh` does not (line 34). PM and DM actual scripts also lack it. **Why this matters**: Without it, a missing inject-permissions.sh produces a visible error.

---

## 8. Recommendation

**Do this feature.** It's low-risk, high-value, and straightforward.

**Implementation plan**:

1. **Create `references/templates/start-role.sh` and `start-role.ps1`** using the templates shown in Section 2. Use `{{ROLE}}` as the single placeholder. Standardize init message to `"start the loop"` for all roles.

2. **Add `boot` command to `references/scripts/compose.py`** (~30 lines). Read template, substitute `{{ROLE}}`, write output, set permissions.

3. **Add `boot-all` command** that reads config.md for active roles and generates all scripts.

4. **Update SKILL.md Step 5** to call `compose.py boot <role>` instead of inline templates. Remove the ~340 lines of inline script bodies. Keep one example showing what the generated output looks like.

5. **Update SKILL.md Upgrade Instructions** (lines 1196-1207) to reference `compose.py boot` instead of "regenerate start scripts".

6. **Regenerate all 6 current scripts** to fix drift bugs (missing Test-Path guard in skill.ps1, missing -ErrorAction, inconsistent init messages).

7. **Add template tests** to `tests/test_start_scripts.py`:
   - Templates exist in `references/templates/`
   - Templates contain `{{ROLE}}` placeholder
   - Generated output has no remaining `{{...}}` placeholders
   - Generated output matches committed scripts (detect manual edits)

8. **Run existing 51 TCs** — all should pass with generated scripts.

**Estimated scope**: ~5 changed files, ~2 new files, ~80 new lines of Python, ~340 lines removed from SKILL.md, net reduction in maintained code.

**Risk**: Low. The templates are simple text substitution. compose.py already has the pattern. Tests already validate the output.
