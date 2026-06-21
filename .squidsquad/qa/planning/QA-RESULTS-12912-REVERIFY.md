# QA-RESULTS-12912 (RE-VERIFY #1) — deploy-signal recompose model

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-20 02:56 · **Verifier:** qa · PR #12926 @ e8e3a9855 · branch `squidsquad/task/12912`.

Re-verification after the cy377 FAIL (see QA-RESULTS-12912.md). type:task/high/role:skill.
Verified in isolated worktree `D:\Dev\Dev\sq-12912-verify`. Append-only.

## Both FAIL items resolved
1. **BLOCKING — forbidden `cycle_pre` token (the no-regression FAIL basis): FIXED.**
   - Fix commit e8e3a9855 ("drop forbidden cycle_pre token from event-mode-contract; dedup manifest").
   - Delta since my prior-verified HEAD (7a857780e) is ONLY 2 files: event-mode-contract.md + installer-files.txt.
   - Case E loop-mode bullet now reads "…at its next session start's pull (AGENT-RUNTIME §7.8)" — the
     literal `cycle_pre` token is gone; no other forbidden token (`cycle_post`/`/loop`) present.
   - `test_event_mode_fragments.py::TestAc5NoModeConditional` → **36 passed** (was 1-failed/35 on the prior HEAD).
   - The reword is **meaning-preserving** ("cycle_pre.py's pull" == "next session start's pull (§7.8)" — loop-mode
     gets the committed CLAUDE.md at its next session's git pull), so the original CQ HARD GATE 5/5 still holds;
     no re-CQ required for a token-level reword that preserves semantics.
2. **AC12 §11 push-retry TRD reconciliation: DONE (by PM).**
   - PM landed the §11 doc-amend on main (commit e7f07bdd4; tracked as #13013, now CLOSED).
   - origin/main HARNESS-ARCH §11 push-rejection row now states the harness does NOT retry — recovers
     immediately (0 retries), matching the shipped code. The code↔TRD drift from my FAIL is GONE.
   - AC9 boot-path intent-sequencing: already disclosed by skill as a non-gap (functionally equivalent) —
     unchanged from the original verification.

## Manifest dedup (cross-PR overlap with #12915, which shipped this session)
- #12912's fix commit reverted its installer-files.txt additions (the 6 common-events fragments now ship via
  #12915) → #12912 is now **net-zero** on the manifest (Total back to 229 on-branch).
- **Test-merge of origin/main into the branch: CLEAN** (no conflicts; harness.py auto-merged). Merged manifest:
  **Total 250 == 250 actual, 0 duplicates, 0 dangling**. So post-merge the manifest is #12915's correct 250 with
  no common-events duplication. The duplicate risk I flagged is resolved.

## Carried-forward verification (prior HEAD, unaffected by the 2-file delta)
All functional ACs 1–12 PASS with live evidence (per QA-RESULTS-12912.md): deploy-signal emit (AC1),
ack-stop/halt/no-ack-cursor (AC2), pull-first (AC3), cursor-advance infinite-loop guard (AC4), boot
detect-only (AC5), failure recovery (AC6), loop-mode no-consume (AC7), sequential per-clone deploy (AC8),
intent-sequencing (AC9), manifest/consumption (AC10), #12519-stays-separate (AC11), DS-audit (AC12).
Independent CQ HARD GATE 5/5.

## No-regression
- Full static gate on branch HEAD e8e3a9855: **PASS — 4692 gated tests, 0 failures, 0 errors** (exit 0).
  The exact test that FAILed before now passes; only the 2 allowlisted #10360 known-failures.

## Disposition
pending-test → pending-ship (DM). PR #12926 — `Closes #12397` (folds in), no closing keyword for #12912 →
merge deferred to DM (post-merge L1/event-mode-contract recompose = restart-required, fleet-wide; clean
test-merge confirmed). Counter NOT bumped. Re-verify QA-RESULTS on main.
