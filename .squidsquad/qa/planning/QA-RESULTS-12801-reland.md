# QA-RESULTS-12801 (RE-LAND) — Harness TUI reboot action bar, clean re-land

**Verdict: PASS — zero gaps (within the 8 ACs).** PR #13274 merged (squash). Re-verification of the clean re-land after the #13271 SEV-1 revert. Supersedes the landing of QA-RESULTS-12801.md (the original 8/8 AC verification stands; this confirms the clean re-land).

## Landing safety (the #13271 lesson — the NEW critical gate)
- `git diff origin/main <branch> --diff-filter=D` = **EMPTY** → +additions-only, **zero file deletions**. The `-11` in the stat is within-file edits (harness.py, HARNESS-ARCH), not removals.
- Diff is **+TUI-only**: references/tui/app.py (+232), harness_client.py (+281), harness.py TUI endpoints (+131), HARNESS-ARCH (+5), tests (+491). 7 files.
- Fleet artifacts **preserved on the branch**: config.md present, all 4 composed CLAUDE.md Verbose Mode=6. No mass-revert.
- `behind_by` = **1** (effectively current; well under the now-live #13271 guard's 50 threshold).

## AC re-confirmation (feature code identical to the verified-8/8 original)
| AC | Result |
|----|--------|
| AC1 action bar (reboot) | PASS — my promoted headless render test (test_feat_12801_render_contract_qa.py) active on branch + reboot_action_bar tests |
| AC2 specific + all reboot | PASS |
| AC3 busy indicator | PASS |
| AC4 graceful vs force | PASS — 48 harness restart/force tests |
| AC5 force distinct + confirm | PASS |
| AC6 crash-streak exclusion | PASS — operator_force tests |
| AC7 tests (dispatch/busy/graceful-vs-force) | PASS — consolidated test_feat_12801_reboot_action_bar.py (394) |
| AC8 HARNESS-ARCH updated | PASS |

Tests: test_feat_12801_reboot_action_bar.py + test_tui_app_12801.py + test_harness_route_contract.py + my render test = 39; harness endpoint tests = 48. All PASS.

## Divergence flagged (NOT a reblock — outside the 8 ACs)
- `requirements-tui.txt` (S1.4 `textual` dep declaration) was NOT re-landed (reverted in the incident, not in the cherry-picked action-bar commit). **Install-readiness gap**: textual is installed fleet-wide (the feature runs), but a fresh install wouldn't provision it. PM had said "S1.4 dep-declaration stays skill's call" — outside the 8 ACs. Filed as a low follow-up. Does NOT block this ship.
- The original 6 test files collapsed to 3 (render→my test; harness_client→TestHarnessClientPost in the consolidated test; requirements→tied to the un-relanded S1.4). AC coverage intact.

Status: pending-test → pending-ship.
