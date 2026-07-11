# QA-RESULTS-13327 — surface the L4-customization affordance (discoverability)

**Issue**: #13327 (type:task, priority:medium, PM-specced UX)
**PR**: #13427 `squidsquad/task/13327`, head 85c3e275a (4 files: INSTALLER-RUNTIME.md +4, pm/instructions.md +2, worker/instructions.md +2, new 13327_spec.json +30)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13327.md`
**Verdict**: **PASS -> pending-ship.** Source-only, additive, entry-point + discoverability change.

## AC walk
- **AC1 PASS** — INSTALLER-RUNTIME.md §7 adds "Two moments make it discoverable — hit both": (a) any "can I change this later?" question → lead with the talk-to-PM affordance (NOT re-run setup/upgrade); (b) hand-off summary → state plainly, benefit language only, "L4"/"compose" explicitly banned from user-facing.
- **AC2 PASS** — pm/instructions.md + worker/instructions.md both add a "generic customization invitation also routes here" paragraph: recognize the open-ended ask, don't point at re-run setup, ask one short plain-language question, then invoke l4-curation. Worker prose text-equivalent to PM's.
- **AC3 PASS** — confirmed by diff scope: only entry-point prose in instructions.md + INSTALLER-RUNTIME.md; NO l4-curation sub-skill body or gate scripts touched. Prose states "l4-curation's elicitation dialog and safety gates are unchanged."
- **AC4 PASS (CQ)** — LLM-consumed pm/instructions.md "### Project customization". 13327_spec 4 Qs verifier-reviewed; fresh Sonnet agent on the named section only → **4/4 zero misreads**: specific directive → l4-curation; generic invitation → ask one question then l4-curation; no special command + pipeline unchanged; one-off ("skip the changelog this task") correctly EXCLUDED.
- **Static gate + landing** — branch 1 behind main + shares docs/INSTALLER-RUNTIME.md with #13339 (§7 vs §4/§9). Verified COMBINED state (local merge origin/main, no push): 3-way CLEAN; combined doc carries BOTH #13327 §7 AND #13339 §4/§9; combined static gate **5308/0/0**.

## Actions
- PR #13427 squash-merged to main. #13327 pending-test -> pending-ship (DM ships). Composed pm+worker/skill CLAUDE.md regenerate via deploy post-merge (source-only, not hand-edited).
