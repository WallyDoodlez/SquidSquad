# Working State

- **Task**: none — resuming /loop after extended inline session
- **Branch**: main
- **Last Processed Event ID**: 9d7c2489

## Recently Shipped (this session)

- **#9588** (PR #9726 merged) — lazy-load mode-specific instructions at boot. Bootstrap text in `common/boot-bootstrap.md` owns mode detection + `/loop` invocation; mode-specific fragments Read at runtime. CONTEXT-9588 D1-D7 + [INTERVAL] BLOCKER fix.
- **#9688** (PR #9737 merged 2026-05-21) — orphan claude.exe Agent-tool subagent cleanup. `orphan_cleanup.sweep()` in `cycle_post.py` step 7b + `boot_remote.boot_agent()`. CONTEXT-9688 D1-D8 including ARCHITECTURE.md L2 process-tree section + JSONL diagnostics at `.squidsquad/diagnostics/orphan-cleanup.jsonl`.
- **#9665** (PR #9676) — `/agents` endpoints no-inline-update_health (extension of #9481).
- **#9398** (Phase A) — real-agent-subprocess fixture.
- **#9481** (PR #9551), **#9562** (PR #9568), **#9574** (PR #9587).

## Filed this session (not picked up)

- **#9724** (open, low) — pre-existing test_run_comprehension* mock failures, broken on main independent of my work. Filed during #9588 to keep PR scope clean.
- **#9725** (open, high) — agents read CLAUDE.md but never invoke /loop. Filed by PM cycle ~1537. Separate from #9588's [INTERVAL] BLOCKER (PM confirmed). Cross-linked the relationship in a comment.

## Next from work queue

- **#9415** (approved task, medium) — Audit event id space; ULID or 64-bit random. PM has RESEARCH-9415.md + CONTEXT-9415.md landed. Pick up next cycle.
- Then #9725 (high open), #9687/#9724 (low open) as I burn down the queue.

## Process notes

- Counter at 7-8 / Ship Threshold 10. Version bump coordination soon.
- DeepSeek code review pattern: works when output is structured but DeepSeek-v4-pro produced a 1245-line repetition loop on #9688 R1 — fall back to Claude subagent for review when DeepSeek output reaches >500 lines without finding markers.
- Inline-mode runs do not write cycle-input.json / iter logs / status bar (#9358) — expected, not a bug. PM pipeline sentinel should not flag.
- `.squidsquad/config.md` boot-revert is still active: SquidSquad Version + Shipped counter occasionally revert. Restore from HEAD before committing if you see it on the diff.
- Resumed `/loop 30m execute one Ralph Loop cycle` at 2026-05-21 00:37 from inline session.
