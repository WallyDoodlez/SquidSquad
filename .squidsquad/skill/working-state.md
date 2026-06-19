# Working State

- **Task**: #12820 (in-progress) — RCA COMPLETE + fix-design recorded; **implementation DEFERRED for safety** (harness-startup blast radius + restart-path interaction). Resume = mechanical per the #12820 comments. (#12825 + #12511 both SHIPPED/CLOSED this session.)
- **Updated**: 2026-06-19 (skill — resumed/inline session)
- **Quiet Cycle Counter**: 0

## Shipped this session (DONE)
- **#12825** (HIGH) — supervised harness launcher + agent-triggerable harness restart. AC1-AC8. PR **#12860 MERGED**, issue SHIPPED/CLOSED. (qa verified cy345 8/8 ACs.)
- **#12511** (HIGH bug) — test-isolation leak. Fix = autouse `_block_live_harness_egress` guard in tests/conftest.py + regression test. PR **#12867**, issue SHIPPED/CLOSED. (qa verified cy346 with on-the-wire A/B proof.)

## Filed / deduped
- **#12861** (LOW) — installer-files.txt omits shipped shared sub-skills (l4-curation/pr-protocol/tracker-protocol/common/task-pickup). Overlaps **#12821** (no manifest-completeness test); consolidated finding onto #12821, flagged #12861 for PM dedup.

## QA agent — CORRECTION: never inert; healthy in POLLING (#12820 misread)
Initial /status read (bootup_complete=false, stale last_activity) led me to conclude qa was inert + reboot it. WRONG — that's the #12820 polling artifact: qa boots POLLING (dead ephemeral .harness-port) and doesn't heartbeat the event bus, so /status can't see it. Clone ground truth (SquidSquad-qa working-state/current-state) shows qa ALIVE and verifying — it PASSED #12825 (cy345) + #12511 (cy346) in polling. My reboot was an unnecessary disruption (operator's first "I don't think QA is inert" was right).
**RCA root (#12820): harness.py find_free_port (3786-3800) silently binds an ephemeral port when 7373 is taken** → a 2nd harness (run with SQUIDSQUAD_DIR=qa's real clone) self-writes (harness.py:1836) that dead port to qa's clone .harness-port → permanent polling. Posted evidenced RCA on #12820; corrected misdiagnosis on #10855/#12409; #11600 RESOLVED. Vault: [[learning-polling-agent-reads-as-inert-on-status]].
**#12820 fix DESIGN (recorded on issue, deferred):** ephemeral fallback + self-write are LOAD-BEARING for the integration suite (real_harness fixture spawns harness in tmp dir, reads self-written .harness-port to discover port — breaks if disabled). Fix must DISTINGUISH prod-singleton (default 7373, real clones) from test (tmp dir, explicit --port 0). Candidate: on default-port path, if find_free_port falls back to ephemeral (7373 held), refuse-to-start OR skip self-write+distribute — BUT must probe /status (live singleton=refuse vs stale/TIME_WAIT=proceed+SO_REUSEADDR) to NOT break the #12825 exit-42 restart relaunch. Coordinated harness.py + fixture change + full integration-suite verify + regression test. Untraced trigger: what runs a harness w/ SQUIDSQUAD_DIR=qa real clone (not boot_remote/thin_launcher).
Separately noted (#11600 comment): cross-clone .local-config divergence (skill clone lists skill→../SquidSquad-skill, dm→../SquidSquad-2-dm vs running harness skill=SquidSquad-2, dm=SquidSquad-3) — low-impact (only PM-clone's .local-config is consequential), can file if not tracked.

## In-flight / held (unchanged)
- **#12450** S1+S2 done; S3 (WIZARD.md + PM CQ AC) + S4 (L3 placement, PM-gated) pending. Next feature after current burndown.
- **#12801** HELD (false-premise TUI; awaiting PM/operator). **#12800** HIGH approved ungated. **#12837** HIGH open (harness evicted:true/null oldest_id). **#12846** LOW (mine, wizard unguarded read). **#12823** medium (.gitattributes config.md merge=ours).
- **#12824** SHIPPED (closed).

## Queue note
Next approved: #12853 (L1 Soul Never-Block→Never-Stop), #12800 (human as non-agent role), then HIGH open bugs (#12837, #12409, #12397, #11600). Several qa/reboot-health bugs open (#10855/#12409/#11600/#12820) — cluster worth front-loaded planning if picked up.

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
