# CQ Pass 1 — Verifier (QA) Findings

Role: Verifier (QA)
Source: `.squidsquad/qa/CLAUDE.md`
Date: 2026-06-11

---

## Item 1 — Boot, no working-state

**Grade**: PASS

**Answer**: At session start I execute Step 1 (step:cycle/boot) immediately before any other action. First, run `python references/scripts/tracker.py check-gh`; if it fails print the error message and exit. Next check harness reachability: read `.squidsquad/.harness-port`, default to 7373 if absent/invalid, then run `curl -sf --max-time 5 http://127.0.0.1:<port>/status`. Exit code 0 means EVENT mode: load sub-skills in order (`event-driven-workflow`, `event-mode-contract`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`). Any non-zero exit means POLLING mode: invoke `/loop 30m execute one Ralph Loop cycle` exactly once, then Read `references/sub-skills/roles/verifier/ralph-loop-overview.md`.

**Citation**: "### Step 1 — step:cycle/boot" (lines 384-456); "#### Verify GitHub Issues access" (lines 389-395); "#### Check harness reachability" (lines 397-410); "#### EVENT mode — load the event-mode contract" (lines 412-428); "#### POLLING mode — schedule /loop, then Read the polling fragment" (lines 430-440).

---

## Item 2 — Resume with prior task

**Grade**: HEDGE

**Answer**: At Step 2 I execute `-> run sub-skill: resume-working-state`. The inline text says: "Read `working-state.md`. If an active task is `in-progress`, queue it as the first thing to handle once nudges start arriving." I would trust the working-state snapshot for which task is active and queue it immediately. However, the doc does not inline what to re-verify versus trust, nor specify the pull-or-skip decision (whether to run `git pull` before resuming or whether the harness pre-cycle already handled it). The pull behavior is implied by the universal prohibition "Never push without pulling first" and the pre-cycle wrapper description, but no explicit "re-verify these fields" checklist appears in inlined text — fully deferred to the sub-skill.

**Citation**: "### Step 2 — step:cycle/resume" (lines 459-461); "### Boundaries — Never push without pulling first" (line 17); "The harness wraps every cared event with a mechanical pre-cycle (git pull...)" (lines 257-258).

**Gap / fix suggestion**: The inline text at Step 2 should state at minimum: (a) "git pull is handled by the harness pre-cycle wrapper; do not re-pull manually" and (b) which fields in working-state.md are authoritative vs. which to re-verify from the forge (e.g., re-read the issue body but trust the step pointer). Without this, an agent spawning mid-task has no way to know whether to trust the working-state task pointer or re-read the full forge state.

---

## Item 3 — Context pressure trigger

**Grade**: HEDGE

**Answer**: The doc names `-> run sub-skill: context-pressure` at `step:cycle/context-pressure` (line 509) and `-> run sub-skill: self-restart` at Step 7 (line 489). The inline description of exit-42 at Step 7 says: "when the post-cycle wrapper (cycle_post.py) detects your own context pressure exceeded the configured threshold OR observes a stopping/restarting intent flip on the harness, it commits/pushes and exits with code 42. Your job is to immediately invoke /quit." The working-state.md requirements before respawn and the specific sequence for uncommitted prose changes mid-cycle are fully deferred to the `context-pressure` sub-skill — not inlined. I cannot answer "what MUST land in working-state.md" or the exact mid-cycle sequence from the composed doc alone.

**Citation**: "### step:cycle/context-pressure" (lines 508-525); "-> run sub-skill: self-restart with exit-42 explanation" (lines 489-490).

**Gap / fix suggestion**: Step 5 (checkpoint) or the step:cycle/context-pressure block should inline the minimum working-state fields required before a context-pressure respawn: at minimum, the active task number, last completed sub-step, and any uncommitted file paths. Add a 3-bullet "what must be in working-state before respawn" block to that section.

---

## Item 4 — Cross-domain bug found

**Grade**: HEDGE

**Answer**: The universal prohibition says "Never cross role boundaries. If work belongs to another role, file it there." (line 21). The verifier-specific boundary says "Never implement fixes — file bugs to the worker agent who owns the code" (line 176). I would: (1) investigate the bug, (2) classify the owning role from the domain description (PM = docs, Worker = code/code-consumed data, etc.), (3) file a GitHub Issue using tracker.py. However, the exact `tracker.py` command for cross-filing (the --role flag, label format, Issue type flag) is fully deferred to `-> run sub-skill: roles/verifier/issue-filing` (line 529) and `-> run sub-skill: tracker-protocol` (lines 494-495). Neither command is inlined in the composed doc.

**Citation**: "### Boundaries — Never cross role boundaries" (line 21); "### Boundaries — Never implement fixes" (line 176); "-> run sub-skill: roles/verifier/issue-filing" (line 529); "-> run sub-skill: tracker-protocol" (lines 494-495).

**Gap / fix suggestion**: Inline at minimum a one-line example of the `tracker.py create-issue` invocation with --role targeting, as the skill CLAUDE.md does ("Cross-role issues directly to owning role via tracker.py create-issue --role [target]"). The verifier doc omits this concrete command entirely, leaving an agent unable to cross-file without reading a sub-skill.

---

## Item 5 — Discussion comment received

**Grade**: HEDGE

**Answer**: I know from Communication Style (lines 159-172) that Discussion entries lead with finding -> evidence -> impact -> recommendation and the example entries show the `**verifier**` alias prefix. I know from Boot & Scope (line 589): "No direct human interaction. Route all human communication through PM via Discussion comments." The doc references `-> run sub-skill: roles/verifier/discussion-protocol` (line 533) for the actual command. The inline text provides format guidance and illustrative example entries but does not provide the `tracker.py comment` command or specify whether the alias prefix is auto-prepended vs manually written. I cannot confirm the exact invocation without reading the sub-skill.

**Citation**: "### Communication Style" (lines 159-172); "### Boot & Scope — No direct human interaction" (line 589); "-> run sub-skill: roles/verifier/discussion-protocol" (line 533); "-> run sub-skill: tracker-protocol" (lines 494-495).

**Gap / fix suggestion**: Inline a single concrete `tracker.py comment` invocation example. Without it, an agent must load a sub-skill just to post a comment. A one-liner like `python references/scripts/tracker.py comment [NUMBER] --role "verifier-lead" --message "[message]"` would close this gap. The skill CLAUDE.md includes this; the verifier CLAUDE.md should too.

---

## Item 6 — Checkpoint discipline

**Grade**: HEDGE

**Answer**: Step 5 (step:cycle/checkpoint) says `-> run sub-skill: git-commit` and notes "use this step to mark logical checkpoints so the post-cycle commit captures a coherent diff." Step 7.1 (step:cycle/verify) states: "If all ACs pass and tests are green -> transition to pending-ship." The Merge & Ship section (lines 612-616) states: "Any TC failure = back to the worker." What constitutes a gate (all TCs PASS, tests green, no deferred findings) is clearly stated. What an agent must NEVER do at checkpoint is covered in prohibitions. But the specific commit-first vs transition-first order is not stated inline — deferred to `-> run sub-skill: git-commit`. The zero-gap gate requirement is strong.

**Citation**: "### Step 5 — step:cycle/checkpoint" (lines 479-480); "### Merge & Ship" (lines 612-616); "## What You Must Never Do" (lines 550-563); "#### Step 7.1 — step:cycle/verify" (lines 577-583).

**Gap / fix suggestion**: Add an explicit ordering rule to Step 5 or Step 7.1: "Commit and push BEFORE transitioning status — a tracker transition with no committed evidence is a gap." The git-commit sub-skill presumably carries this, but commit order is a basic runtime decision that should not require sub-skill loading to resolve.

---

## Item 7 — L4-curation trigger

**Grade**: PASS

**Answer**: The trigger phrase "from now on, in this project, every commit message must include..." matches a project-specific durable customization directive. The Reactive sub-skills section (lines 567-575) defines the trigger: "When the human gives a project-specific durable customization directive (e.g. 'from now on, before X do Y'; 'in this project, never Z')". Classification: durable directive (not a one-off request, not a feature request — both explicitly excluded). Before invoking: nothing else — the doc says "invoke l4-curation BEFORE doing any implementation work." Sub-skill: `l4-curation`. Safety gates named inline: (1) elicitation dialog, (2) decision tree (replace / insert-before / insert-after / append), (3) safety-gate pipeline, (4) project-customization commit. The exact gate ordering is inside the sub-skill, but the doc names all four stages.

**Citation**: "## Reactive sub-skills — Project customization" (lines 567-575).

---

## Item 8 — Role-specific: pending-test verification walk

**Grade**: PASS

**Answer**:
1. **Derive TEST-PLAN independently**: Upon seeing a `pending-test` item, produce `TEST-PLAN-<NUMBER>.md` under `.squidsquad/qa/planning/`. Derive from the AC list in the issue body/CONTEXT.md — independent of the worker's code and PR diff. Cite ACs explicitly.
2. **CQ spec**: If the task touches LLM-consumed instructions (CLAUDE.md, sub-skills, SOUL.md), produce `tests/comprehension/<NUMBER>_spec.json`. Owned by verifier, not PM.
3. **Execute**: Run `-> run sub-skill: verification`. Spawn a fresh agent for comprehension testing (give only modified files, no existing context). Every TC must produce PASS, FAIL, or HUMAN-REQUIRED — no "deferred" or "skipped". Execute against a real live test instance.
4. **QA-RESULTS**: Produce `QA-RESULTS-<NUMBER>.md` summarizing AC walk, test runs, and verdict. Append-only; never edited after publication.
5. **Pass outcome**: All ACs PASS, tests green -> `gh pr review --approve` + `python references/scripts/git_ops.py pr-merge` -> transition to `pending-ship`.
6. **Fail outcome**: Any TC failure -> route back to `in-progress`. File rejection as Discussion comment with full evidence (specific TC, file path, output). Zero-gap gate is absolute.
7. **Role boundary**: Verifier does NOT implement fixes, does NOT alter ACs, does NOT approve tasks.

**Citation**: "#### Step 7.1 — step:cycle/verify" (lines 577-583); "### Test Plan Creation (#9184)" (lines 597-602); "### Test Execution" (lines 604-610); "### Merge & Ship" (lines 612-616); "### Responsibility — What this role does" (lines 33-41); "### Zero-gap gate is absolute" (lines 188-191); "### What this role does NOT do" (lines 44-48).

**Gap / fix suggestion**: The path for `QA-RESULTS-<NUMBER>.md` is never explicitly stated. Line 37 names the file but not the directory. Line 599 gives the path for TEST-PLAN (`.squidsquad/qa/planning/`). An agent can reasonably infer the same directory, but it should be stated explicitly. Add "`QA-RESULTS-<NUMBER>.md` under `.squidsquad/qa/planning/`" to the Test Plan Creation section or File Conventions.

---

## Item 9 — Vault-remember after novel work

**Grade**: FAIL

**Answer from doc**: The Scanning & Vault section (line 621) states: **"Vault is read-only for the verifier. The verifier reads vault context but does not write vault notes."** The correct answer is: I do NOT write to the vault. I read the vault before starting work but never write vault-remember.

**Why FAIL**: The Vault Protocol section (lines 653-657) says: "After completing real work, **use vault-remember to capture durable learnings** (max 2 writes per cycle; apply 4-gate logic: write budget -> dedup -> reusability -> fresh-context test)." This directly contradicts the read-only rule. An agent reading both sections faces a conflict with no tiebreaker. The Scanning & Vault rule is more specific (names the role explicitly); the Vault Protocol rule is later in the doc and uses imperative voice. This is simultaneously a FAIL and the most severe contradiction in the document.

**Citation**: "### Scanning & Vault" (lines 618-622); "### Vault Protocol" (lines 653-657); "### Vault-First Institutional Knowledge" (lines 89-98).

**Gap / fix suggestion**: Remove the vault-remember instruction from the generic "### Vault Protocol" section for this role and replace it with: "Exception: the verifier is vault read-only. Do not call vault-remember. Read vault notes before starting work; do not write." Alternatively, if vault writes are intended for verifier, remove "Vault is read-only for the verifier" from Scanning & Vault. One rule must be canonical; the doc currently holds both.

---

## Item 10 — Self-restart vs exit

**Grade**: PASS

**Answer**: Step 7 with `-> run sub-skill: self-restart` covers this with inline detail. Three distinct outcomes:
1. **Self-restart**: triggered when `cycle_post.py` detects context pressure exceeded threshold OR observes `stopping`/`restarting` intent flip -> commits/pushes -> exits with code 42 -> immediately invoke `/quit` so harness can respawn or mark stopped.
2. **Wait / idle**: normal post-cycle outcome: POST `ack-cursor`, re-enter Monitor idle-wait until next nudge.
3. **Session exit**: triggered if Monitor exits for any reason (termination, non-zero exit, tool error, stream close) -> end session immediately. Do NOT retry Monitor, do NOT pivot to polling. Harness auto-respawn path owns recovery.

**Citation**: "### Step 7 — step:cycle/exit" (lines 485-490); "-> run sub-skill: self-restart" (line 489); "#### 5. Your idle wait is the Monitor tool" (lines 323-329).

---

## Contradictions found

- **Vault write permission**: Line 621 ("Vault is read-only for the verifier. The verifier reads vault context but does not write vault notes.") directly contradicts lines 655-657 ("After completing real work, use vault-remember to capture durable learnings (max 2 writes per cycle; apply 4-gate logic...)"). The verifier-specific rule in "Scanning & Vault" names the role explicitly and should dominate, but the generic Vault Protocol section gives the opposite instruction in imperative voice with no exception note. An agent reading both will face a conflict with no tiebreaker.

- **TEST-PLAN ownership latent confusion**: Line 561 (prohibitions) warns: "If PM's comments reference planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) you cannot find, stop and push back." This phrasing implies TEST-PLAN.md might be produced by PM or the worker, which contradicts lines 35 and 601 establishing that verifier owns TEST-PLAN derivation independently (#9184 workflow). Not a hard logical contradiction, but an agent could read the prohibitions section and conclude TEST-PLAN is an input the verifier waits for rather than produces itself.

---

## Overall verdict

The qa/CLAUDE.md is close to production-ready but has one blocking contradiction and four HEDGE items that would cause an autonomous agent to guess under adversarial conditions. The vault read/write contradiction (Item 9) is the highest-severity defect: two sections give directly opposite instructions with no tiebreaker, and sequential reading can produce either behavior depending on which section dominates. The four HEDGE items (resume working-state trust rules, context-pressure sequence, cross-filing command, Discussion command) share the same root cause: concrete commands and ordering rules are deferred entirely to sub-skills with no inlined minimum, meaning the composed CLAUDE.md alone is insufficient for those operational decisions. Fix priority: (1) resolve the vault contradiction with a clear exception note in the Vault Protocol section, (2) inline the `tracker.py create-issue --role [target]` cross-filing command, (3) inline the `tracker.py comment` invocation example, (4) add explicit commit-before-transition ordering to Step 5 or Step 7.1.
