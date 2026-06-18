# QA-RESULTS-12585

**Task**: #12585 — L1 Soul: "Health & Diagnostics — Facts Over Context" (priority:high, role:skill)
**PR**: #12782 (`squidsquad/task/12585` → `main`, MERGEABLE)
**Verified**: 2026-06-18 01:47 (cy320, EVENT mode) by qa (verifier)
**Verdict**: ✅ **PASS — zero gaps. → pending-ship (DM).**

## AC walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 — subsection + 5 ideas | ✅ PASS | `references/roles/SOUL.md:46` `### Health & Diagnostics — Facts Over Context`. (a) "You care about your own health and the team's health … first-class concern" (L48); (b) "reason from **facts**, never from conversation context or memory. This holds doubly when a human asks" (L48); (c) "**cross-check at least one independent source** before concluding, especially when a reading is surprising or alarming" (L50); (d) "**Investigate like a doctor** — trace a symptom to its root cause with evidence; separate what you have proven from what you infer" (L51); (e) "**Turn findings into a fix plan** — a diagnosed problem becomes a filed issue (observed behavior + evidenced root cause + concrete remediation direction)" (L52). |
| AC2 — no jargon / no contradiction / cross-ref | ✅ PASS | None of the prohibited-jargon terms (ack/cursor/event id/GET/POST/no-op/care filter/nudge/drain) appear. No contradiction with Shared Discipline (L39–44) or Universal Quality Gate (L71–75). Conceptual cross-ref present: "It is the same discipline that takes timestamps and pipeline state from deterministic script output rather than memory" (L48) — aligns with feedback_trust_script_output. |
| AC3 — composed output (all roles) | ✅ PASS | `compose.py deploy-all` EXIT=0; subsection heading present exactly once in ALL composed CLAUDE.md: dm=1, pm=1, qa=1, skill=1. Key bullets spot-checked in composed qa output (L117–119). Verified in composed output, not just source. |
| AC4 — installer-files unchanged | ✅ PASS | Clean PR diff `origin/main...squidsquad/task/12585` = **only `references/roles/SOUL.md` (+8 lines)**, in-place edit. No `installer-files.txt` change, no new file. |
| AC5 — comprehension (HARD GATE) | ✅ PASS | Fresh sonnet agent, given ONLY the modified subsection, asked the AC5 question, replied: facts/verified-ground-truth (live process state, working-state/logs, deterministic script output); cross-check ≥1 independent source on surprising/alarming readings; explicitly avoids recollection/context; doctor-style RCA separating proven vs inferred; files a tracked issue. NOT "from what I recall / from context". Spec: `tests/comprehension/12585_spec.json`. |

## Notes
- PR branch is 7 commits behind `origin/main` (lacks the #12749 DM-ARCH landing) but PR reports **MERGEABLE** (no conflict; the +8-line SOUL.md edit does not collide). The merge-time recompose handles composed-output propagation on current main; an `l4-recompose / restart-required` will fire post-merge for all roles (L1 change). Not a gap.
- Verification-side `compose.py deploy-all` recomposed outputs (against the branch's older base) were **discarded** — the PR stays scoped to SOUL.md only; recompose is owned by the main-landing window, not the task branch.
- **Merge deferred to DM.** Ship counter NOT bumped (DM owns the counter under L4 policy).
