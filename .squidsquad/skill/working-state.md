# Working State

- **Task**: none. Updated 2026-09-26 14:25. Halting for the held deploy-signal 91d8f8c70e690935 (ack-stop deploy-halted sent right after this write).
- Next on respawn: #14131 (HIGH, harness: an agent alive at intent=deploying is never recovered) together with #14132 (/restart of an idle agent held up to 30 min by the 'waiting' pause-guard). Same health-poller area, one PR. The #14131 plan is posted on the issue:
  - alive + idle (no activity heartbeat within the window) + past `_DEPLOY_WINDOW_SECONDS` + no deploy in flight -> `_run_deploy_sequence(role, None)`;
  - alive + active past a ceiling -> one deploy-error to pm;
  - module-level in-flight set guards double starts (register at every deploy-thread start).
  - For #14132, exempt the /restart's own requested kill from active_pause (e.g. an `operator_force_at`-style stamp consulted by the reboot decision).
- Pending-test (verifier): #14109 (PR #14111), #14124 + #14125 (PR #14134). SHIPPED: #13860 (PR #14126); its receipts file is committed on main.

## Queue after
- #14127 (vault schema upgrade merge; unblocked now #13860 merged), #14114 (after #14109 merges; same file), #14130 (flaky PS1 launcher test).
- Approved: #13861 P5 (P4 gate now satisfied), #13862 M-track, #10690, #10686.

## Notes
- gh active account Naahtec is pull-only: push with a `gh auth token --user WallyDoodlez` credential helper; for gh calls use git_ops/tracker (pinned GH_TOKEN).
- Before switching branches, `git restore` the composed .squidsquad/*/CLAUDE*.md if dirty (stale recompose from branch source).

## Improvement Scan
Status: idle. Last scan 2026-07-19 05:52.

## Quiet Cycle Counter: 0
