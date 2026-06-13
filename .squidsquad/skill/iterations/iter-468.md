# Iteration 468 — 2026-06-13 15:15

**Mode**: POLLING (/loop cron 71281ae5, 30m).

## Summary
No operator response on #11745 (still blocked). 4 prior PRs unchanged (no rejections). Deterministic work-queue next actionable = **#11511** (PR mergeability flaps). Investigated; **disproved both proposed fixes** with citations and identified the true root cause. Held for direction confirmation (high blast radius). Confirmed the rest of the queue is triage/operator-blocked.

## Work — #11511 root-cause investigation
- **Disproved candidate 2 (.gitattributes merge=union)**: GitHub does NOT honor user `.gitattributes` merge drivers for PR mergeability — `merge=union` is an open GitHub feature request since 2021 (community discussion #9288; GitHub: "doesn't consider user-defined .gitattributes files"). Confirmed `merge=ours` is doubly local-only (`merge.ours.driver=true` is in local `.git/config`, uncommitted). The existing `.gitattributes` strategies are therefore server-side no-ops — adding more won't help.
- **Disproved candidate 1 for working-state.md (gitignore)**: current-state / cycle-*.json / .backlog-cache already gitignored (don't flap). working-state.md is the remaining flap source, but gitignoring it breaks intentional cross-agent visibility — `cycle_post.py` deliberately splits state→working/main (read by health_check sentinel, state_bus, migrate_state_branch).
- **True root cause**: working-state.md flaps only when it lands on a FEATURE branch (both-sides-changed vs main). `cycle_post` already routes state to working/main, not the feature branch — leaks happen only when the wrapper is bypassed (harness-down manual commits) or branch races.

## Recommendation posted on #11511 (held for confirmation)
1. Treat GitHub CONFLICTING as advisory — verify real conflicts via `git merge-tree --write-tree base head`; merge locally when harness down (zero-risk, stops wasted hand-nudge cycles immediately).
2. Harden state routing so working-state.md can't land on a feature branch even on manual paths (extend #11083 guard intent).
3. Do NOT add `.gitattributes` entries (proven ineffective) and do NOT gitignore working-state.md (breaks visibility).

## Queue state (flagged to operator in working-state)
Every actionable item is triage/operator-blocked: #11745 (UX fork), #11505 (PM disambiguation), #11511 (direction), #10690 (E7-gated), #10686 (operator-manual), #11716 (untriaged own-scan finding — can't auto-fix). Implementable approved work shipped cycle 466. Cycles are investigation-only until operator triages.

## Next
- Await operator on #11745 (A vs B) and #11511 (direction confirm).
- If #11511 direction confirmed → implement (recommendation #1 is zero-risk and buildable immediately: a `git_ops` real-conflict check helper).
- Monitor 4 PRs → DM ships #11723/#11641.
