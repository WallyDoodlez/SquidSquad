# FEAT-PM-2493 Test Plan — Per-Agent Working Directories (Minimal Scope)

## Scope

Two changes only:
1. `scaffold_install` in `wizard.py` clones the repo for each non-PM agent into sibling directories
2. `generate_local_config` in `compose.py` writes relative paths instead of absolute paths

## Test Cases

### TC-1: Wizard creates sibling clones for non-PM agents
- **Precondition**: Primary repo at `/tmp/test-project/` with `origin` remote configured. Install spec includes agents: `pm`, `skill`, `qa`.
- **Steps**: Run `scaffold_install(spec, "/tmp/test-project/")`.
- **Expected**: Directories `../test-project-skill/` and `../test-project-qa/` exist as full git clones alongside the primary repo.
- **Verification**: `ls -d /tmp/test-project-skill /tmp/test-project-qa && git -C /tmp/test-project-skill rev-parse --git-dir && git -C /tmp/test-project-qa rev-parse --git-dir`

### TC-2: PM does NOT get a clone
- **Precondition**: Same as TC-1. Install spec includes `pm`, `skill`, `qa`.
- **Steps**: Run `scaffold_install(spec, "/tmp/test-project/")`.
- **Expected**: No `../test-project-pm/` directory is created. PM agent data stays in the primary repo at `.squidsquad/pm/`.
- **Verification**: `test ! -d /tmp/test-project-pm && test -d /tmp/test-project/.squidsquad/pm`

### TC-3: .local-config written with relative paths
- **Precondition**: Same as TC-1. Scaffold completes successfully.
- **Steps**: Read `.squidsquad/.local-config` in the primary repo.
- **Expected**: PM entry points to `.` (current directory). Non-PM entries use relative paths (e.g., `../test-project-skill`, `../test-project-qa`). No absolute paths present.
- **Verification**: `cat /tmp/test-project/.squidsquad/.local-config | grep -v '^#' | grep -v '^$'` — each line matches `- **role**: ../` or `- **role**: .`

### TC-4: Relative paths resolve correctly from primary repo
- **Precondition**: Scaffold completed. `.local-config` contains relative paths.
- **Steps**: From the primary repo directory, resolve each path in `.local-config` and check that it points to a valid directory containing `.git/`.
- **Expected**: `Path(primary_repo / relative_path).resolve()` exists and is a git repo for every entry.
- **Verification**: Parse `.local-config`, for each entry run `cd /tmp/test-project && test -d "<relative_path>/.git"`

### TC-5: Clones have correct remote URL
- **Precondition**: Primary repo has `origin` set to `https://github.com/user/test-project.git`.
- **Steps**: Run scaffold. Check `git remote get-url origin` in each clone.
- **Expected**: Every clone's `origin` URL matches the primary repo's `origin` URL exactly.
- **Verification**: `diff <(git -C /tmp/test-project remote get-url origin) <(git -C /tmp/test-project-skill remote get-url origin)`

### TC-6: Clones are on the correct branch
- **Precondition**: Primary repo is on branch `main`.
- **Steps**: Run scaffold. Check `git branch --show-current` in each clone.
- **Expected**: Each clone is checked out on the same branch as the primary repo (`main`).
- **Verification**: `git -C /tmp/test-project-skill branch --show-current` outputs `main`

### TC-7: Idempotent — running setup again does not break existing clones
- **Precondition**: Scaffold already ran once. Clones exist with local modifications (e.g., a file created in the clone's `.squidsquad/skill/working-state.md`).
- **Steps**: Run `scaffold_install(spec, "/tmp/test-project/", overwrite_existing=True)` a second time.
- **Expected**: Existing clones are not deleted or re-cloned. The local modifications in the clone survive. `.local-config` is regenerated with the same relative paths. No errors raised.
- **Verification**: Check that the local modification file still exists in the clone. Check `.local-config` content matches expected format. Check clone's git log is unchanged.

### TC-8: Single-agent setup (PM only) — no clones created
- **Precondition**: Install spec contains only `pm` agent: `{"agents": [{"id": "pm", "role": "pm"}], ...}`.
- **Steps**: Run `scaffold_install(spec, "/tmp/test-project/")`.
- **Expected**: No sibling directories created. `.local-config` contains only PM entry pointing to `.`. Scaffold completes without error.
- **Verification**: `ls /tmp/ | grep test-project` shows only `test-project/`. `.local-config` has exactly one non-comment line.

### TC-9: Windows path compatibility — spaces in paths
- **Precondition**: Primary repo at `D:\My Projects\test project\` (path with spaces in two segments).
- **Steps**: Run `scaffold_install(spec, "D:\\My Projects\\test project\\")`.
- **Expected**: Clones created at `D:\My Projects\test project-skill\` and `D:\My Projects\test project-qa\`. Relative paths in `.local-config` are correctly quoted or escaped if needed. Git operations in the clones succeed.
- **Verification**: `git -C "D:\My Projects\test project-skill" status` exits 0. `.local-config` paths resolve correctly when passed to `Path()`.

### TC-10: health_check.py reads agent state via relative paths in .local-config
- **Precondition**: Scaffold completed with relative paths in `.local-config`. Each clone has `.squidsquad/<role>/.health` file with a recent epoch. No `~/.squidsquad/clones/` directory (force fallback to `.local-config`).
- **Steps**: Run `python references/scripts/health_check.py` from the primary repo directory.
- **Expected**: Health check resolves relative paths from `.local-config`, finds `.health` files in each clone, and reports agent health status without errors. Each agent shows as alive (green) or has a valid status.
- **Verification**: `python references/scripts/health_check.py --json` returns valid JSON with entries for each configured agent. No "path not found" or resolution errors in stderr.

### TC-11: boot_remote.py spawns agents in correct clone dirs via .local-config
- **Precondition**: Scaffold completed with relative paths in `.local-config`. No `~/.squidsquad/clones/` directory. Boot scripts exist in each clone.
- **Steps**: Run `python references/scripts/boot_remote.py --all --dry-run` (or `--json`) from the primary repo directory.
- **Expected**: boot_remote.py resolves relative paths from `.local-config` to the correct clone directories. Dry-run output shows the correct absolute paths for each agent's working directory. PM's path resolves to the primary repo.
- **Verification**: `python references/scripts/boot_remote.py --all --json` output shows correct resolved paths for each agent. The `clone_path` for `skill` resolves to the sibling clone, not the primary repo.

## Smoke Tests

- [ ] Fresh install with 3 agents (pm, skill, qa): scaffold completes, 2 clones created, `.local-config` has relative paths
- [ ] `git status` in each clone shows clean working tree after scaffold
- [ ] `health_check.py --json` runs without errors from primary repo
- [ ] Re-running scaffold on an existing setup produces no errors and preserves clone state

## Regression Risks

- **health_check.py absolute path assumption**: `_parse_local_config()` currently wraps paths with `Path()` but may not resolve relative paths against the correct base directory. The parser at `health_check.py:93-105` does `Path(m.group(2).strip())` which will treat relative paths as relative to CWD, not relative to the repo root. This must be verified.
- **boot_remote.py same issue**: `_parse_local_config()` at `boot_remote.py:69-80` has the identical pattern. Relative paths will only resolve correctly if the script is run from the primary repo directory.
- **Existing single-repo installs**: Must not break. If no clones exist and `.local-config` points to `.`, all agents should fall back to primary repo (current behavior with collisions).
- **generate_local_config callers**: `compose.py deploy-all` at line 539 also calls `generate_local_config()`. After this change, `deploy-all` must also emit relative paths (or accept that it will be overridden by the wizard).
- **Path separator on Windows**: Relative paths like `../project-skill` use forward slashes. Python's `Path` handles this on Windows, but any shell scripts consuming `.local-config` directly must handle both separators.
