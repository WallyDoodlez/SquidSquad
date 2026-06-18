# TEST-PLAN-12585

**Task**: #12585 — L1 Soul: "Health & Diagnostics — Facts Over Context" (priority:high, role:skill)
**PR**: #12782 (`squidsquad/task/12585` → `main`, MERGEABLE)
**Derived by**: qa (verifier), independently from the AC list in the issue body — NOT from the worker's diff.
**Created**: 2026-06-18 01:47 (cy320, EVENT mode)

## Nature of change
L1 base instruction (`references/roles/SOUL.md`) → universal (all roles). LLM-consumed instruction change ⇒ **comprehension test is a HARD GATE** (AC5).

## Test cases (one per AC)

- **TC1 (AC1) — subsection + five ideas present.** Grep `references/roles/SOUL.md` on the PR branch for the new `### Health & Diagnostics — Facts Over Context` subsection. Confirm all five ideas: (a) cares about own + team health; (b) facts-not-context, esp. for humans; (c) cross-check ≥1 independent source on surprising/alarming readings; (d) doctor-style RCA (proven vs inferred); (e) fix-as-filed-issue (observed + root cause + remediation). PASS = all five textually present.

- **TC2 (AC2) — no jargon / no contradiction / conceptual cross-ref.** Read surrounding Soul sections (Shared Discipline, Universal Quality Gate, User-Facing Communication). Confirm: (a) none of the User-Facing prohibited-jargon terms (ack/cursor/event id/GET/POST/no-op/care filter/nudge/drain) introduced; (b) no contradiction with Shared Discipline (timestamps/atomic-writes/append-only/pull-before-push) or Universal Quality Gate; (c) conceptually cross-references the trust-script-output discipline. PASS = no jargon, no contradiction, cross-ref present.

- **TC3 (AC3) — composed-output propagation (verify in composed output, not source).** Run `python references/scripts/compose.py deploy-all`; grep every composed `.squidsquad/<role>/CLAUDE.md` (dm/pm/qa/skill) for the subsection heading + key bullets. PASS = present exactly once in ALL roles (L1 ⇒ all).

- **TC4 (AC4) — installer-files.txt unchanged.** Diff `origin/main...squidsquad/task/12585`. PASS = no change to `installer-files.txt`; in-place edit only; no new file.

- **TC5 (AC5, HARD GATE) — comprehension.** Spawn a fresh agent (model sonnet) given ONLY the modified subsection text, no prior context. Ask: "A human asks whether the team is healthy — how do you answer?" PASS = reply reflects verify-ground-truth / cross-check / investigate-root-cause / fix-as-issue AND does NOT answer "from what I recall / from context". Record spec at `tests/comprehension/12585_spec.json`.

## Live instance
Verified on the PR feature branch (`squidsquad/task/12585`); composed-output check run via real `compose.py deploy-all` (EXIT=0). Comprehension test run via real fresh sonnet subagent.
