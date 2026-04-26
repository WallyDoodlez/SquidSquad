# FEAT-PM-3100 Test Plan — Remove global clones fallback

## Test Cases

### TC-1: Normal operation with .local-config present
- **Precondition**: `.squidsquad/.local-config` exists with valid entries
- **Steps**: Run `python references/scripts/boot_remote.py --dry-run --all --json`
- **Expected**: Scripts resolve clone paths from `.local-config`, no reference to `~/.squidsquad/clones/`
- **Verification**: Output shows correct paths matching `.local-config` entries

### TC-2: Hard error when .local-config missing
- **Precondition**: Temporarily rename `.local-config` to `.local-config.bak`
- **Steps**: Run `python references/scripts/boot_remote.py --dry-run --all`
- **Expected**: Script exits with non-zero code and a clear error message mentioning `.local-config` and setup
- **Verification**: Exit code != 0, stderr contains actionable error message
- **Cleanup**: Rename `.local-config.bak` back

### TC-3: Hard error when .local-config missing (health_check)
- **Precondition**: Temporarily rename `.local-config` to `.local-config.bak`
- **Steps**: Run `python references/scripts/health_check.py`
- **Expected**: Script exits with non-zero code and clear error message
- **Verification**: Exit code != 0, stderr contains actionable error message
- **Cleanup**: Rename `.local-config.bak` back

### TC-4: No global clones references in code
- **Precondition**: Changes applied
- **Steps**: `grep -r "squidsquad/clones" references/scripts/`
- **Expected**: Zero matches (all references removed)
- **Verification**: grep returns no results

### TC-5: reboot_agent.py inherits fix
- **Precondition**: `.local-config` present
- **Steps**: Run `python references/scripts/reboot_agent.py --help` (or dry test)
- **Expected**: Works normally — delegates to `boot_remote._get_clone_path()` which now requires `.local-config`
- **Verification**: No errors when `.local-config` exists

### TC-6: Full test suite passes
- **Steps**: `python tests/run_tests.py`
- **Expected**: No regressions
- **Verification**: Exit code 0 or same pre-existing failures only

## Smoke Tests
- [ ] `boot_remote.py --dry-run --all` works with `.local-config` present
- [ ] `health_check.py` works with `.local-config` present
- [ ] Both scripts fail clearly when `.local-config` is missing

## Regression Risks
- Any script that imports `boot_remote._parse_local_config()` or `health_check._parse_local_config()` will now get hard errors instead of fallback — verify no unexpected callers
