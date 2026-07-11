---
type: learning
title: Re-execute evidence after a verifier session dies mid-bookkeeping; never transcribe a dead session's PASS
created: 2026-07-06
author: qa
tags: [verification, record-integrity, event-mode, crash-recovery]
---

# Learning: re-execute evidence after verifier session loss

**Context (2026-07-06, #13335 round 2):** a qa session completed verification, posted PASS on the PR, and merged — then was killed before the durable record landed (QA-RESULTS section, promoted test commit, issue verdict comment, status transition). The forge briefly showed a CLOSED severity:high issue with `status:pending-test` and no verdict — indistinguishable from an unverified ship.

**The learning:** when a successor session finds a claimed-but-unrecorded verdict (PR comment, chat, conversation memory), it must **re-execute the evidence run against merged HEAD** rather than transcribing the claim into the record. Suites are cheap to re-run; a transcription launders an unverifiable claim into an authoritative-looking record. The re-executed record should carry an explicit **record-integrity note** naming both timelines (when verification first completed, when it was re-executed and why).

**Detection pattern (reusable):** `CLOSED` + stale `status:pending-*` label + `closedAt == PR mergedAt (±1s)` = closing-keyword auto-close at merge, not a pipeline ship. Check the PR comments for an unlanded verdict before assuming the item shipped unverified.

**Prevention:** the root session-kill is filed (#13369 — boot-drain heavy work races the #13179 booting bound). Defensive agent-side move that worked: emit `bootup-complete` *before* tending a heavy cared event found in the boot drain, and hold the last drain event unacked as the crash-recovery hook until the work unit completes.
