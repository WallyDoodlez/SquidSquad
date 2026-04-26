# FEAT-PM-3101 Test Plan — Upgrade startup logo

## Test Cases

### TC-1: Logo renders in bash
- **Precondition**: Updated start-role.sh template
- **Steps**: Source the logo section or run `bash -c` with the heredoc
- **Expected**: Blocky SQUIDSQUAD text renders cleanly, no garbled characters
- **Verification**: Visual inspection in terminal

### TC-2: Logo renders in PowerShell
- **Precondition**: Updated start-role.ps1 template
- **Steps**: Run the Write-Host logo section in PowerShell
- **Expected**: Same blocky text, no encoding artifacts (ref BUG-SKILL-003)
- **Verification**: Visual inspection in Windows Terminal / PowerShell

### TC-3: Version and agent name preserved
- **Precondition**: Logo includes version and agent name line
- **Steps**: Check template for `${V:-?}` and `${AGENT_NAME}` references
- **Expected**: Version and agent name still displayed alongside or below the logo
- **Verification**: grep for variable references in template

### TC-4: compose.py deploy-all propagates
- **Precondition**: Templates updated
- **Steps**: Run `python references/scripts/compose.py deploy-all`
- **Expected**: All start-*.sh and start-*.ps1 files updated with new logo
- **Verification**: diff any start script against template — logo section should match

### TC-5: Full test suite passes
- **Steps**: `python tests/run_tests.py`
- **Expected**: No regressions
- **Verification**: Same pass/fail as before

## Smoke Tests
- [ ] Logo visible and readable in Windows Terminal
- [ ] Logo visible and readable in bash
- [ ] Version number displays correctly
- [ ] Agent name displays correctly

## Regression Risks
- PowerShell Unicode encoding (prior bug BUG-SKILL-003)
- Logo width exceeding narrow terminal widths (keep under 60 chars wide)
