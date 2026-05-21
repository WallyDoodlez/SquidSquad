# Audit Findings Triage — 2026-05-21

Source: AUDIT-A (events architecture) + AUDIT-B (polling regression), cycle 1538.

All 8 findings are severity:medium. Triage order below reflects relative urgency for the event-driven flip readiness goal.

---

## Tier 1 — Pre-event-flip blockers (4 issues)

These should land BEFORE flipping `event-driven: yes`. Each affects event-mode correctness or operability.

### 1. #9740 — Cursor re-anchor + per-event race loses event
**Severity tier**: 1 (data integrity)
**Why first**: silent data loss under disk-write failure. Hardest to detect post-hoc — event just gone. Most expensive failure mode in the audit. Small fix (reorder operations in `event_poll.py`); should be quick.
**Effort**: Small.

### 2. #9741 — /events/for/{role} dispatch with no ack
**Severity tier**: 1 (operational, polluting state)
**Why second**: every event delivered times out → log spam + `.event-state.json` accumulates in-flight entries that never clean up. Won't break the system but degrades observability and makes the diagnostics log noisy enough to mask real issues. Strip `dispatch()` call (Option 3 from #9741 body) is small.
**Effort**: Small.

### 3. #9744 — DM PR-merge-wait label-blind
**Severity tier**: 1 (operator UX during event mode)
**Why third**: in event mode, DM uses the PR-merge-wait pattern actively. An operator wanting to redirect via label would be ignored. Predictable problem if DM activity ramps up after the flip. Doc + small code change.
**Effort**: Small-medium.

### 4. #9742 — Boot TOCTOU Monitor hang
**Severity tier**: 1 (recovery semantics)
**Why fourth**: not strictly a blocker — the agent hangs but operator can restart. Still: an agent hung "in event mode" while harness is bouncing is exactly the failure mode that drove this whole session's debugging effort. Worth ironing out before the flip.
**Effort**: Doc-only in `l1-base.md`.

---

## Tier 2 — Quality/maintenance hardening (2 issues)

These don't block the flip but ship soon for codebase health.

### 5. #9745 — Wake-mode resolution duplicated across 4 files
**Severity tier**: 2 (latent drift risk)
**Why fifth**: pure refactor. No active bug. But this duplication has already produced subtle behavior differences across files (stderr suppression varies). A shared helper prevents future drift.
**Effort**: Small. Pure refactor + tests.

### 6. #9746 — Stale `references/agent-instructions.md`
**Severity tier**: 2 (deployment hygiene)
**Why sixth**: actively misleading if anyone reads the canonical template. Active agents are unaffected. Fix is a single `compose.py all` command + commit. CI check to prevent future drift is the load-bearing part.
**Effort**: Trivial action + small CI addition.

---

## Tier 3 — Documentation + accepted debt (2 issues)

These can ship anytime. No urgency.

### 7. #9743 — idle-cooldown-loop Monitor buffering docs
**Severity tier**: 3 (pure documentation)
**Why seventh**: no code change. Just clarify the semantics that `Monitor` output during a scan is buffered. Could be folded into any other docs PR.
**Effort**: Trivial.

### 8. #9747 — [ROLE] placeholder LLM-dependent
**Severity tier**: 3 (accepted debt)
**Why last**: regression test catches the immediate breakage path. The long-term hardening (per-role copies or script-level substitution) is worth doing but not urgent. Could bundle into a future templating refactor.
**Effort**: Medium (if shipped). Acceptable to defer.

---

## Recommended ordering for skill's queue

**Phase 1 (before event-mode flip)**: #9740 → #9741 → #9744 → #9742
**Phase 2 (concurrent with or after flip)**: #9745 → #9746
**Phase 3 (anytime, low priority)**: #9743 → #9747

Skill may parallelize Tier-1 issues if cycle bandwidth allows. The order within Tier 1 is by severity-of-failure-mode, not strict dependency.

## Note for skill

Pickup these per `feedback_auto_approve_bugs` (bug class, role:skill, status:open). PM has not produced individual RESEARCH/CONTEXT artifacts for each — the issue bodies + the source audits (`AUDIT-A-events-architecture.md`, `AUDIT-B-polling-mode-regression.md`) contain enough scope. If implementation surfaces ambiguity, comment on the issue and PM will write a CONTEXT artifact for that specific one.
