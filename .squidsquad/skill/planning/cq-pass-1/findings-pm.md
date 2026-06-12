# CQ Pass 1 — PM Findings

Evaluated against: `.squidsquad/pm/CLAUDE.md`

---

## Item 1 — Boot, no working-state

**Grade**: PASS

**Answer**: At session start I execute Step 1 (step:cycle/boot) before any other action. First, verify GitHub Issues access:
```bash
python references/scripts/tracker.py check-gh
```
If that fails, print the error message and exit. Next, resolve the harness port: read `.squidsquad/.harness-port`; if absent/unreadable/empty/non-integer, default to `7373`. Then probe:
```bash
curl -sf --max-time 5 http://127.0.0.1:<port>/status
```
If exit code is 0 -> EVENT mode: load sub-skills in order -- `event-driven-workflow`, `event-mode-contract`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`. If non-zero exit -> POLLING mode: invoke `/loop 30m execute one Ralph Loop cycle` exactly once, then Read `references/sub-skills/roles/pm/ralph-loop-overview.md`. After mode is set, it is sticky for the session.

**Citation**: "Step 1 -- step:cycle/boot" (L423-496): "Verify GitHub Issues access" (L427-435), "Check harness reachability" (L437-449), "EVENT mode -- load the event-mode contract" (L451-467), "POLLING mode -- schedule /loop" (L469-479).

**Gap / fix suggestion**: N/A

---

## Item 2 — Resume with prior task

**Grade**: PASS

**Answer**: Step 2 says `-> run sub-skill: resume-working-state`. That sub-skill instructs me to Read `working-state.md`. If it shows an active task `in-progress`, I queue it as the first thing to handle once nudges start arriving. I do NOT re-verify the full tracker from scratch -- the forge is the source of truth, but the working-state primes the queue. My first concrete action is to Read `.squidsquad/pm/working-state.md` (File Conventions, L601) and follow the `resume-working-state` sub-skill. Because Step 1 pre-cycle mechanics include a `git pull` via the harness wrapper, no separate pull decision is needed at resume -- the wrapper owns it.

**Citation**: "Step 2 -- step:cycle/resume" (L498-500), File Conventions (L601).

**Gap / fix suggestion**: The doc does not explicitly state whether the agent should re-read the forge issue to verify the task is still `in-progress` vs. already transitioned between sessions. The universal prohibition "Never trust conversation memory for pipeline state" (L20) plus "forge is the source of truth" implies a forge re-check is required, so this is inferable -- but a clarifying sentence in Step 2 would make it explicit.

---

## Item 3 — Context pressure trigger

**Grade**: GAP

**Answer**: The PM CLAUDE.md does not contain a dedicated `step:cycle/context-pressure` step. The only reference to context pressure is in Step 7 (step:cycle/exit, L584-588), which defers entirely to `-> run sub-skill: self-restart`. The inline text explains: "when the post-cycle wrapper (cycle_post.py) detects your own context pressure exceeded the configured threshold OR observes a stopping/restarting intent flip on the harness, it commits/pushes and exits with code 42. Your job is to immediately invoke /quit." But the question asks what I do MID-CYCLE with uncommitted prose changes. The doc is silent on: (a) who monitors intra-cycle pressure (agent or wrapper?), (b) what the configured threshold value is or where to read it, (c) whether a mid-cycle checkpoint is required from the agent side before the wrapper fires, and (d) what MUST land in working-state.md before respawn. Step 5 (step:cycle/checkpoint) mentions `-> run sub-skill: git-commit` for logical checkpoints but does not mention context-pressure as a trigger. The SKILL CLAUDE.md has a dedicated `step:cycle/context-pressure` step; PM CLAUDE.md lacks it entirely.

**Citation**: "Step 7 -- step:cycle/exit" (L584-588), "Step 5 -- step:cycle/checkpoint" (L540-542). Missing: no `step:cycle/context-pressure` in the hydrated cycle diagram (L367-408).

**Gap / fix suggestion**: Add `step:cycle/context-pressure` to the PM hydrated cycle diagram and document it: (1) read context-pressure percentage from disk, (2) compare to threshold in config.md, (3) if above threshold, call `git-commit` sub-skill immediately, write active task + completed steps to working-state.md, push, invoke /quit. Without this, a PM agent at 87% with uncommitted work has no documented intra-cycle path.

---

## Item 4 — Cross-domain bug found

**Grade**: HEDGE

**Answer**: The boundary rules (Responsibility L44-46; Project Adaptation Boundaries L195-199) establish that PM does NOT write code or touch skill files. The universal prohibition (L21) says "If work belongs to another role, file it there." The issue-filing reactive sub-skill (L645-649) says to invoke `-> run sub-skill: roles/pm/issue-filing` when a bug surfaces, using `tracker.py create-issue` / `create-task` with the right role, severity/priority, and labels. However, the doc contains a direct contradiction: L44 says "Does NOT do root-cause analysis when filing bugs. PM describes observed behavior + impact + reproduction; the assigned agent does the RCA," while L195 says "Never file a bug without investigating root cause first (Bug Discussion Flow)." Under L195 I must investigate before filing; under L44 I must NOT do RCA. The exact tracker command is cited as `tracker.py create-issue` / `create-task` but the flag/argument syntax is deferred to `tracker-protocol` (L592-594), which is not inlined.

**Citation**: "What this role does NOT do" (L44-46), "Boundaries" Project Adaptation (L195-199), "Reactive sub-skills > Issue filing" (L645-649), "Tracker Protocol" (L592-594).

**Gap / fix suggestion**: Resolve the L44 vs L195 contradiction (see Contradictions section). Inline the minimal `tracker.py create-issue` command with required flags. The "Bug Discussion Flow" referenced at L195 is never defined in the doc -- it must be named explicitly or its sub-skill must be cited.

---

## Item 5 — Discussion comment received

**Grade**: HEDGE

**Answer**: The doc directs me to invoke `-> run sub-skill: roles/pm/discussion-protocol` (L653-655) when responding to or relaying an agent's Discussion comment. The protocol governs: alias prefix, append-only, route by `role:*` label, no editing prior comments. The alias prefix in comments would be `**pm**` (per Identity L5: "Discussion comments are prefixed with the bare alias"). What is forbidden: editing or deleting prior comments (L105, L617). The concrete `tracker.py comment` command syntax is not inlined in PM CLAUDE.md -- it defers to the `tracker-protocol` and `discussion-protocol` sub-skills. A real agent must Read those sub-skills to get the literal command, so the doc alone is insufficient for the specific "which command" question.

**Citation**: "Reactive sub-skills > Discussion comment routing" (L653-655), "Tracker Protocol" (L592-594), Soul > Shared Discipline L105, "What You Must Never Do" L617, Identity L5.

**Gap / fix suggestion**: Inline at least one concrete example of the `tracker.py comment` command for PM (as SKILL CLAUDE.md does in its "Discussion Protocol" section). The alias prefix is stated but the tool invocation pattern is not, leaving the agent needing to Read a sub-skill to answer a basic operational question.

---

## Item 6 — Checkpoint discipline

**Grade**: HEDGE

**Answer**: Step 5 (step:cycle/checkpoint, L540-542) says `-> run sub-skill: git-commit`. The mechanical commit and push are part of the post-cycle wrapper (cycle_post.py). Status transitions always use `python references/scripts/tracker.py transition` per L621 -- never `gh issue edit` label commands directly. What PM must NEVER do at this step: construct `gh issue edit` label commands manually (L621); merge or close PRs directly (L200-201). The explicit ordering question ("commit first or transition first?") is not stated in PM CLAUDE.md -- it defers to the `git-commit` and `tracker-protocol` sub-skills. Note: PM does not mark items `pending-test` -- that is the worker's transition. PM's checkpoint is committing planning artifacts (prose changes).

**Citation**: "Step 5 -- step:cycle/checkpoint" (L540-542), "What You Must Never Do" (L621), "Process Governance" (L204-222).

**Gap / fix suggestion**: The explicit ordering ("commit first or transition first?") is absent and deferred to sub-skills. The doc should specify this order inline for PM's prose-change scenario.

---

## Item 7 — L4-curation trigger

**Grade**: PASS

**Answer**: The human's statement "in this project, from now on, every commit message must include the issue number in square brackets" matches the trigger pattern in the l4-curation reactive sub-skill section (L639-643): "from now on, before X do Y" / "in this project, never Z" = project-specific durable customization directive. Classification: durable directive (not a one-off request, not a feature request). I invoke `-> run sub-skill: l4-curation` BEFORE doing any implementation work. The doc says this sub-skill "handles the elicitation dialog, the decision tree (replace / insert-before / insert-after / append), the safety-gate pipeline, and the project-customization commit." Safety gates are named inside the sub-skill body (not inlined), which I Read at runtime. The doc explicitly states one-off requests and feature requests are NOT routed through l4-curation.

**Citation**: "Reactive sub-skills > Project customization" (L639-643).

**Gap / fix suggestion**: N/A -- trigger classification, pre-condition, and sub-skill invocation are unambiguous. Safety gates deferred to sub-skill body is acceptable by design.

---

## Item 8 — Worker blocked on scope question (PM-specific)

**Grade**: HEDGE

**Answer**: The worker comment is a mid-task scope question on an in-progress issue. This does NOT go through 5-phase task intake (task-intake is for NEW pending items, L519-522). PM's path: (1) pipeline-sentinel (Step 4.1, L535-537) detects the blocking comment; (2) PM consults vault for recorded decisions on storage technology (`galaxy/decision-*`, L88); (3) PM applies Decision-Making Style (L158-167): present 2-3 options with clear trade-offs and recommendation -- surfaces question to human via check-in (Step 2.1); (4) once human answers, PM documents decision via vault-remember (L700-705) and comments on the issue with the locked ruling; (5) locked decision captured in CONTEXT.md at `.squidsquad/pm/planning/` (File Conventions, L601-606). For approval: scope clarification on already-approved task -- no fresh approval gate needed.

The doc does NOT explicitly describe the workflow for mid-task blocking scope questions from workers. Task-intake covers new items; pipeline-sentinel covers stalls; but there is no named flow for "worker asks a design Q in Discussion on an in-progress issue." The planning-artifact update path (CONTEXT.md update for locked mid-task decisions) is implied by File Conventions but not prescribed for this scenario.

**Citation**: "Step 3.1 -- task-intake" (L519-522), "Step 4.1 -- pipeline-sentinel" (L535-537), "Decision-Making Style" (L158-167), "Communication Style" (L169-183), "Reactive sub-skills > Discussion comment routing" (L653-655), "File Conventions" (L601-606), "Vault Protocol" (L700-705).

**Gap / fix suggestion**: Add a sub-section (or extend the discussion-protocol reactive sub-skill trigger description) covering "mid-task scope Q&A from a worker." The flow should specify: detect in pipeline-sentinel -> vault-check -> surface to human -> lock decision -> update CONTEXT.md -> comment on issue with ruling. Currently the agent must stitch this from 5+ separate sections.

---

## Item 9 — Vault-remember after novel work

**Grade**: PASS

**Answer**: After completing non-trivial work yielding a reusable insight, I follow vault-remember protocol (L700-705). Write-budget rule: max 2 vault writes per cycle. Apply 4-gate logic in order: (1) write budget -- has this cycle consumed 2 writes? If yes, skip. (2) dedup -- is insight already in `vault/galaxy/`? If yes, skip. (3) reusability -- would another agent benefit? If too task-specific, skip. (4) fresh-context test -- is this derivable from existing vault notes? If not fresh, skip. For the docker/Podman example: PARAG bucket = `vault/galaxy/` as a `learning-*` note (L89: "past mistakes and surprises to avoid repeating"). All four gates pass. I invoke `-> run sub-skill: vault-remember` (Step 6, L544-545).

**Citation**: "Vault Protocol" (L700-705), PARAG Structure (L690-699), Soul > Vault-First (L84-93).

**Gap / fix suggestion**: N/A

---

## Item 10 — Self-restart vs exit

**Grade**: HEDGE

**Answer**: Step 7 (step:cycle/exit, L584-588) defers to `-> run sub-skill: agent-lifecycle` and `-> run sub-skill: self-restart`. The inline text explains three outcomes: (1) normal cycle end -> POST ack-cursor, eager loop checks for next event, re-enter Monitor idle-wait when drain is empty -- this is "wait" (not exit or restart); (2) context-pressure exceeds configured threshold OR intent-flip detected by wrapper -> post-cycle wrapper exits with code 42 -> PM invokes /quit immediately -- this is self-restart; (3) Monitor exits for any reason (L344-349) -> end session immediately -- this is exit. The trigger check for (2) is performed by cycle_post.py, not by the agent; the agent only invokes /quit when it observes exit-42. The specific threshold value and how to read it are not stated inline. The concrete decision tree for "which outcome applies now?" is inside the sub-skills, not inlined.

**Citation**: "Step 7 -- step:cycle/exit" (L584-588), "Section 5 -- Your idle wait is the Monitor tool" (L344-349).

**Gap / fix suggestion**: Inline a minimal decision table for the three exit outcomes. A 3-row table (trigger -> agent action) at the end of Step 7 would make this PASS without requiring sub-skill reads for a basic lifecycle question.

---

## Contradictions found

- **L44 vs L195 -- PM RCA on bugs**: "What this role does NOT do" (L44-45) states "Does NOT do root-cause analysis when filing bugs. PM describes observed behavior + impact + reproduction; the assigned agent does the RCA as part of fixing." But "Boundaries" under Project Adaptation (L195) states "Never file a bug without investigating root cause first (Bug Discussion Flow)." These are directly contradictory: L44 prohibits RCA before filing; L195 requires it before filing. The "Bug Discussion Flow" referenced at L195 is never defined anywhere in CLAUDE.md. Suggested resolution: clarify that PM investigates enough to determine ownership and describe observable behavior (not deep technical RCA), and name the "Bug Discussion Flow" sub-skill explicitly.

- **Hydrated cycle diagram vs Step 7 prose -- sub-step representation (minor)**: The hydrated diagram (L367-408) shows S7 (step:cycle/exit) with no sub-step boxes, yet Step 7 prose (L584-588) contains two `-> run sub-skill` entries. Cosmetically inconsistent but not behaviorally contradictory -- these are sub-skill markers, not numbered sub-steps. Minor; no behavioral impact.

---

## Overall verdict

The PM CLAUDE.md is substantially production-ready for its core workflows (boot, l4-curation, vault-remember, task-intake for new items, triage). Two blocking issues prevent a clean production rating: (1) context-pressure mid-cycle handling is entirely absent -- there is no `step:cycle/context-pressure` step, no threshold reference, and no prescribed intra-cycle checkpoint path for a PM agent that hits high pressure with uncommitted prose (GAP on Item 3); (2) the direct contradiction between L44 ("PM does NOT do RCA before filing bugs") and L195 ("Never file a bug without investigating root cause first") makes cross-domain bug handling unpredictable (HEDGE + contradiction on Item 4). A recurring structural weakness is that runtime-critical details (Discussion comment syntax, tracker.py flag shapes, checkpoint ordering) are deferred to sub-skills not inlined in the document -- acceptable by design but means the doc alone cannot fully answer Items 3, 5, and 6.
