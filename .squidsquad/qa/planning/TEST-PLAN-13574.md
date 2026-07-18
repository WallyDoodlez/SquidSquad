# TEST-PLAN-13574 — Boot gate + health checks blind to forge WRITE-outage

**Source**: GitHub issue #13574 Acceptance Criteria (AC-F1, AC-CQ1-4, AC-D1).
**Derived without reading the diff** (diff read only afterward for AC-D1 file-location confirmation).

## Test Cases

### TC-1 (covers AC-F1): tracker.py check-gh probes write capability after read check
- **Precondition**: real repo, real gh identity (currently push:true)
- **Steps**: (a) live `python references/scripts/tracker.py check-gh`; (b) independent black-box repro (own script, not worker's fixtures) forcing `_run_list_timeout` to return `false`/timeout/error/garbage
- **Expected**: (a) OK, no #13574 warning (push is true); (b) false → prints ERROR with "WRITE"/"#13570"/"Remediation", returns False; inconclusive (timeout/error/garbage) → prints "inconclusive" warning, returns True (fail-open)
- **Verification command**: `python references/scripts/tracker.py check-gh`; own `python -c` repro script

### TC-2 (covers AC-CQ1): health-check comprehension — what the probe is and what false means
- **Precondition**: fresh sonnet agent, given ONLY `references/sub-skills/roles/pm/health-check.md`
- **Steps**: ask "How do you check team health each cycle?" (no leading mention of write/permissions/outage)
- **Expected**: agent states unprompted that it probes forge WRITE capability (`.permissions.push`) once per health check, and that `false` means an infrastructure outage escalated to the human — NOT per-agent stall findings
- **Verification command**: Agent tool comprehension spawn, transcript review

### TC-3 (covers AC-CQ2): pipeline-sentinel classification ordering
- **Precondition**: same fresh agent, given ONLY `references/sub-skills/roles/pm/pipeline-sentinel.md`
- **Steps**: present the #13570-signature scenario (pipeline frozen across multiple roles simultaneously, every agent's health green) and ask how to classify it and in what order to test
- **Expected**: classifies as halt class (e) forge write-outage; states it tests for (e) BEFORE attributing (b) dead-agent / (d) genuine-no-progress to any individual agent; names the confirming probe (`.permissions.push`)
- **Verification command**: same spawn, transcript review

### TC-4 (covers AC-CQ3): mid-outage conduct
- **Precondition**: same spawn/scenario as TC-3
- **Steps**: ask what must NOT be done during the outage, and how to reach the human
- **Expected**: states it must NOT boot agents or re-transition items (all writes fail, including its own escalation attempt); states the escalation transition itself is EXPECTED to fail with a permission error (further confirming (e)); names a non-forge fallback (inline session / operator channel)
- **Verification command**: same spawn, transcript review

### TC-5 (covers AC-CQ4): fail-open nuance
- **Precondition**: same spawn, either file
- **Steps**: ask what an inconclusive or erroring probe result means for the boot/health check
- **Expected**: "note it and move on" / "warn + pass" — explicitly NOT a hard fail
- **Verification command**: same spawn, transcript review

### TC-6 (covers AC-D1): consumption path — deployed content carries the fix
- **Precondition**: local qa clone (isolated — does not affect the live PM agent's clone)
- **Steps**: `python references/scripts/compose.py deploy pm`; grep composed `.squidsquad/pm/CLAUDE.md` for the probe/halt-class markers; if absent, confirm the composed file instead carries `→ run sub-skill: health-check` / `→ run sub-skill: pipeline-sentinel` runtime markers, then confirm the runtime-Read source files contain the #13574 text
- **Expected**: the content a PM session actually loads (composed file directly, or composed file's runtime-Read markers resolving to the modified fragments) carries the probe step and halt-class (e) text
- **Verification command**: `compose.py deploy pm`; `grep -n "13574\|permissions.push" .squidsquad/pm/CLAUDE.md references/sub-skills/roles/pm/health-check.md references/sub-skills/roles/pm/pipeline-sentinel.md`

## Coverage matrix
- AC-F1 → TC-1
- AC-CQ1 → TC-2
- AC-CQ2 → TC-3
- AC-CQ3 → TC-4
- AC-CQ4 → TC-5
- AC-D1 → TC-6

## Comprehension Questions

This task modifies LLM-consumed instructions (`references/sub-skills/roles/pm/health-check.md`, `references/sub-skills/roles/pm/pipeline-sentinel.md`).

### CQ-1: "How do you check team health each cycle?"
- **Files**: `references/sub-skills/roles/pm/health-check.md`
- **Expected answer**: probes forge WRITE capability (`.permissions.push`) once per health check; `false` → infrastructure outage, escalate to human, not per-agent stall findings.

### CQ-2: Given the #13570-signature scenario (fleet-wide halt, all-green health), how do you classify it and in what order do you test?
- **Files**: `references/sub-skills/roles/pm/pipeline-sentinel.md`
- **Expected answer**: halt class (e) forge write-outage; test for (e) BEFORE attributing (b)/(d) to any individual agent; confirm via `.permissions.push` probe.

### CQ-3: Same scenario — what must you NOT do, and how do you reach the human?
- **Files**: `references/sub-skills/roles/pm/pipeline-sentinel.md`
- **Expected answer**: do NOT boot agents or re-transition items (writes fail including the escalation itself, which is expected to fail with a permission error — that failure further confirms (e)); fall back to a non-forge human-reaching surface (inline session / operator channel).

### CQ-4: What does an inconclusive or erroring probe result mean?
- **Files**: `references/sub-skills/roles/pm/health-check.md` (or pipeline-sentinel.md)
- **Expected answer**: warn and proceed / note and move on — not a hard fail (fail-open on uncertainty).

Spec persisted at `tests/comprehension/13574_spec.json`.
