# TEST-PLAN-12853 — L1 SOUL generalize 'Never Block on a Human' → 'Never Stop While Work Is Pending'

**Derived independently from the 6 ACs in issue #12853.** PR #12894 · branch `squidsquad/task/12853`
· type:task · priority:high · role:skill. L1 SOUL change (LLM-consumed) ⇒ comprehension HARD GATE.

## Change

Generalizes the #12799 human-only L1 rule to all handoffs: an agent never voluntarily ends its
turn/loop while work is pending; pausing to wait for ANY party (teammate agent OR human) is a
forbidden *stop*; every handoff is a status-transition + immediate continue. Human handoff becomes a
special case (DRY). Adds a PM L2 duty to advertise `pending-human-*` tickets to the operator.

## Test cases (one per AC)

- **TC1 (AC1) — rule generalized, human = special case.** SOUL.md `### Never Stop While Work Is
  Pending` states: never end turn/loop while work pending; handoff to teammate OR human = transition +
  continue, never stop. Human async-no-pause retained as a *special case* (one principle, not a
  separate standalone rule). Old heading retired.
- **TC2 (AC2) — stop vs idle disambiguated.** Text explicitly: idle (event-bus wait / cool-down loop,
  auto-resumes) ≠ stop; ending the turn to wait IS the forbidden stop; only lifecycle events (exit-42,
  stop-requested, Monitor death) legitimately end a session.
- **TC3 (AC3) — PM L2 advertise-duty.** `references/roles/pm/responsibility.md` + `checkin.md` gain an
  explicit PM duty: advertise open `role:<human>`/`pending-human-*` tickets to the operator each
  check-in (the PM half of the return path), non-blocking.
- **TC4 (AC4) — compose-consumption.** `compose.py deploy-all` EXIT=0 → generalized rule in ALL 4
  composed `.squidsquad/<role>/CLAUDE.md`; PM-advertise duty in PM's composed only. Old heading absent.
- **TC5 (AC5) — comprehension HARD GATE.** Independent fresh-agent CQ (verifier-derived, not the
  worker's): (a) continue to next item after a handoff, never wait; (b) verifier/QA handoff =
  transition + continue, NOT stop; (c) only lifecycle events end a session; (d) idle ≠ stop; (e) human
  handoff = transition (not bare comment) + continue; (f) PM advertises pending-human-* tickets.
- **TC6 (AC6) — DS prose-drift reconcile.** No live references to the retired rule name remain across
  shipped sources; AGENT-RUNTIME §3.1 + human-role section + `harness-restart.md` cross-refs reconciled
  to the new rule; consistency with AGENT-RUNTIME Case C / event-mode-contract. Historical changelog
  entries may retain the old name (immutable record — not drift).
- **TC7 (implicit) — no-regression.** Full static gate green on the post-merge-equivalent tree.

## Verdict rule

Zero-gap: every AC observable-PASS; comprehension is a HARD GATE; prose-drift must leave no live
stale references.
