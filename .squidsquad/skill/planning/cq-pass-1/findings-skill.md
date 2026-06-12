# CQ Pass 1 — Skill Agent Findings

Source of truth: `.squidsquad/skill/CLAUDE.md` (839 lines, read in full)
Role tested: **skill** (worker-class, skill-specialized)

---

## Item 1 — Boot, no working-state

**Grade**: PASS

**Answer**: At session start I execute Step 1 (step:cycle/boot) immediately, before any other action.

1. **GitHub Issues gate**: `python references/scripts/tracker.py check-gh`. If non-zero, print error and exit.
2. **Read harness port**: read `.squidsquad/.harness-port`; if absent/invalid, default to `7373`.
3. **HTTP probe**: `curl -sf --max-time 5 http://127.0.0.1:<port>/status`. Exit 0 = EVENT mode; any non-zero = POLLING mode.
4. **EVENT mode path**: run sub-skills in order — `event-driven-workflow`, `event-mode-contract`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`. Mode is now sticky for the session.
5. **POLLING mode path** (if probe failed): invoke `/loop 30m execute one Ralph Loop cycle` exactly once, then Read `references/sub-skills/roles/worker/ralph-loop-overview.md`.
6. **Placeholder substitution**: any [ROLE] tokens in runtime-loaded fragments are substituted with `skill`; any [INTERVAL] tokens are a bug — flag and do not execute the surrounding `/loop` invocation.
7. **Step 2**: `→ run sub-skill: resume-working-state` — no active task on a fresh start, so queue is empty; proceed to triage-issues.

**Citation**: "Step 1 — step:cycle/boot" (lines 451–524); "Step 2 — step:cycle/resume" (lines 526–534); "### Boot & Queue" (lines 753–759)

---

## Item 2 — Resume with prior task

**Grade**: PASS

**Answer**: Step 2 runs `→ run sub-skill: resume-working-state`. If `working-state.md` shows an active task `in-progress` at Step 4, I trust the completed steps, remaining steps, and key decisions recorded there as still-current. The first concrete action is: `git pull` (never push without pulling first — Boundaries, line 17), then re-read the working-state to confirm exactly which sub-steps of Step 4 remain, and queue the resume as the first event to process once nudges start.

I do NOT re-verify every prior AC from scratch; I trust the working-state as written. I re-verify only if context in the forge (a new comment, a rejection, a status flip) contradicts the working-state.

**Citation**: "Step 2 — step:cycle/resume" (lines 526–528); second `### step:cycle/resume` (lines 580–584): "the agent has resumed it — completed steps, remaining steps, and key decisions trusted as still-current — rather than restarting from a cold tracker pull"; "Never push without pulling first" (Boundaries, line 17; also line 767)

---

## Item 3 — Context pressure trigger

**Grade**: HEDGE

**Answer**: The doc names `→ run sub-skill: context-pressure` at `### step:cycle/context-pressure` (lines 574–578), with the goal statement: "the agent has read the live context-pressure percentage from disk, compared it to the configured threshold, and (above threshold) checkpointed pending work to working-state plus pushed git so a respawn loses nothing." At 87% (above 80% threshold) I would: (1) write pending prose changes to a `.tmp` file then `mv` atomically, (2) update `working-state.md` to record the current step, remaining steps, and uncommitted file path, (3) push git so a respawn loses nothing. Below threshold = no-op.

However, the doc only says "checkpoint pending work to working-state plus pushed git" without specifying the exact fields that MUST land in `working-state.md` before respawn (e.g., which step ID, which file paths, the issue number). The sub-skill `context-pressure` carries those details but is not inlined. A fresh agent reading only this file could not enumerate the required working-state fields without reading the sub-skill.

**Citation**: "### step:cycle/context-pressure" (lines 574–578); Step 7 / self-restart (lines 552–556); "Atomic writes for shared files" (Boundaries, line 19)

**Gap / fix suggestion**: The goal statement at `step:cycle/context-pressure` should enumerate the minimum working-state fields required before respawn (active-task-id, current-step-id, uncommitted-file-list, git-push-confirmed flag). Currently delegated entirely to the sub-skill without even a skeleton, making the composed CLAUDE.md insufficient for a cold agent who cannot locate the sub-skill.

---

## Item 4 — Cross-domain bug found

**Grade**: PASS

**Answer**:
1. Investigate root cause — confirm it is outside the `skill` domain (not in `references/scripts/`, skill source files, or code-consumed data).
2. Do NOT fix it — "Never modify code outside your role's domain without cross-filing" (line 193); "If a fix requires changes in another agent's domain, file a bug — don't reach across" (line 194).
3. File a cross-role issue: `python references/scripts/tracker.py create-issue --role [target-role]` — using the owning role's alias as the label. The doc says "Cross-role issues directly to owning role via `tracker.py create-issue --role [target]`. Don't wait for PM to discover and route." (line 788).
4. Post a Discussion comment on the current issue noting the cross-filed bug number and short description, per communication norms.
5. I do NOT construct `gh issue edit` label commands manually (line 661).

The exact command is: `python references/scripts/tracker.py create-issue --role <owning-role>` with the finding details. The per-finding-kind one-liners live in `tracker-protocol`'s **Creating Issues** section (line 626).

**Citation**: "### Tracker & Cross-Team" (lines 784–790); "Never cross role boundaries" (Boundaries, line 21); "Boundaries" section (lines 192–194); "What You Must Never Do" (lines 654–668); Discussion Protocol (lines 610–620); line 626 (tracker-protocol cross-role shapes)

---

## Item 5 — Discussion comment received

**Grade**: PASS

**Answer**: The forge is append-only; I never edit or delete prior comments. To respond:

```bash
python references/scripts/tracker.py comment [NUMBER] --role "skill-lead ($(python references/scripts/config.py alias skill))" --message "[my answer text]"
```

The role alias prefix (`skill-lead`) is auto-prepended by tracker.py — the `--message` value must NOT include it (line 787: "tracker.py auto-prepends role prefix to comments; never include it in `--message`"). The Discussion Protocol block shows the exact form with the parenthetical alias (lines 614–616).

What is forbidden: editing or deleting the original comment (Boundaries line 18; "Discussion entries are Issue comments — append-only, never edit or delete" line 613); posting outside tracker.py (never construct `gh issue edit` label commands manually, line 661).

**Citation**: "Discussion Protocol" (lines 610–620); "### Tracker & Cross-Team" (lines 784–790); Boundaries line 18; "What You Must Never Do" line 661

---

## Item 6 — Checkpoint discipline

**Grade**: HEDGE

**Answer**: From the doc:

1. Run `python tests/run_tests.py` — confirm zero failures. This gates the pending-test transition (lines 263, 664–665, 772).
2. Run `git_ops.py has-changes` — if no changes, re-read the issue and apply the fix (line 766).
3. Commit on the feature branch via `→ run sub-skill: git-commit` (Step 5 / Step 7.1). Commit message must reference the issue number and short description (line 728).
4. Push. Never push without pulling first (line 17/767).
5. Transition: `python references/scripts/tracker.py transition <number> in-progress pending-test`. Never construct `gh issue edit` manually (line 661).
6. Never run `gh issue close` directly (line 662).

Order: commit first, then transition. The doc's Step 7.1 sequences `git-commit` before the transition sub-skill. However, the doc does not explicitly state "commit before transition" as a numbered rule — the ordering is inferred from the step sequence and the prohibition on marking Pending Test without green tests (which requires the commit to exist).

**Citation**: "Step 7.1 — step:cycle/implement" (lines 721–729); "Step 5 — step:cycle/checkpoint" (lines 544–546); "Zero-gap submission discipline" (lines 261–263); "What You Must Never Do" (lines 654–668); "Branch + PR Workflow" (lines 761–767)

**Gap / fix suggestion**: The commit-before-transition ordering is implicit (inferred from step numbering) but never stated as an explicit rule. A one-line rule at Step 7.1 — "Always commit and push before calling `tracker.py transition ... pending-test`" — would eliminate the hedge.

---

## Item 7 — L4-curation trigger

**Grade**: PASS

**Answer**: The statement "from now on, every commit message must include the issue number in square brackets" is a **durable project-specific directive** (matches the pattern "from now on, before X do Y" in line 680), not a one-off request and not a feature request.

Trigger classification: project-specific durable customization directive → invoke `l4-curation`.

Sequence:
1. **Before implementing anything**, invoke `→ run sub-skill: l4-curation` (line 678: "invoke `l4-curation` BEFORE doing any implementation work").
2. The sub-skill handles the elicitation dialog, the decision tree (replace / insert-before / insert-after / append), the safety-gate pipeline, and the project-customization commit.
3. Safety gates are inside the sub-skill — the CLAUDE.md names them ("elicitation dialog, decision tree, safety-gate pipeline") but does not inline them; I must Read the sub-skill to get the gate list.
4. One-off requests and feature requests are explicitly NOT routed through `l4-curation` (line 680 end).

**Citation**: "### Project customization (project-specific durable directives)" (lines 676–681)

---

## Item 8 — Role-specific: Approved task implementation (Skill worker)

**Grade**: PASS

**Answer**: Quiz prompt: "Tracker shows an approved task. Walk implementation: branch creation, plan vs code-first, test discipline, when to invoke `→ run sub-skill: l4-curation` if at all, what counts as zero-gap submission, transition to pending-test."

**Branch creation**: `git_ops.py task-begin` — branch pattern `squidsquad/task/<number>` (line 763). Always `git pull` first (line 767).

**Plan vs code-first**: If 2+ issues are assigned or the issue body cites multiple findings, enter **front-loaded planning mode** before touching any file (lines 798–812): read everything, identify patterns, plan one strategy, publish it as a tracker comment, then execute. For a single isolated task: at `step:cycle/skill-implement` (lines 731–737): author behavior spec first, write few-shot examples before instructions, implement minimally. So: spec-first, then examples, then implementation — not code-first.

**Test discipline**: Write unit tests as part of the implementation (not follow-up). Run `python tests/run_tests.py` — zero failures required. For skill changes: run `python references/scripts/run_eval.py --skill <id> --runs 10`; accept only if pass rate >= 80% across all runs and regression suite still passes (lines 699–702; acceptance checklist lines 710–716). CQ test: `tests/comprehension/<issue>_spec.json` must exist if the task touches LLM-consumed instructions (line 774).

**When to invoke l4-curation**: Only if the task turns up a durable project-specific customization directive from the human in conversation — not as a standard implementation step (lines 676–681). Normal task implementation does NOT invoke l4-curation.

**Zero-gap submission**: (1) `python tests/run_tests.py` green; (2) `git_ops.py has-changes` confirms changes exist; (3) CQ spec present if task touches agent instructions; (4) `manifest.yaml` + `installer-files.txt` updated if skill file created/renamed (Step 7.3); (5) DS review completed for high-blast-radius skill changes (Step 7.2); (6) `compose.py deploy` run if sub-skill/role sources changed (lines 773, 779); (7) Every AC observable.

**Transition to pending-test**: `python references/scripts/tracker.py transition <number> in-progress pending-test` — only after all the above gates pass. Never mark pending-test without green tests (line 664) and never without corresponding unit tests (line 665).

**Citation**: "Step 7.1 — step:cycle/implement" (lines 721–729); "#### step:cycle/skill-implement" (lines 729–737); "Step 7.2 — step:cycle/ds-review" (lines 739–743); "Step 7.3 — step:cycle/manifest-update" (lines 745–747); "Step 7.4 — step:cycle/skill-cq" (lines 749–751); "Zero-gap submission discipline" (lines 261–263); "Front-loaded planning" (lines 796–812); "Skill Dev Domain Context" (lines 683–717); "Branch + PR Workflow" (lines 761–767); "What You Must Never Do" (lines 664–665)

---

## Item 9 — Vault-remember after novel work

**Grade**: PASS

**Answer**: After completing non-trivial work that yielded a reusable insight (e.g. the Docker/Podman workaround example), I apply the **4-gate logic** before writing:

1. **Write budget**: max 2 vault writes per cycle (line 271; also line 838). If I have already written 2, do not write.
2. **Dedup check**: is this insight already in the vault? Check `vault/galaxy/` for an existing `learning-*` note. If present (even partially), skip.
3. **Reusability test**: would other agents or future cycles benefit from this? The Podman workaround is environment-specific — likely yes if the project uses Podman; marginal if not. If the insight is only useful once, skip.
4. **Fresh-context test**: will a fresh agent reading this note have enough context to apply it? If not, do not write a confusing fragment.

If all 4 gates pass: write to `vault/galaxy/learning-<slug>.md` (PARAG bucket: **Galaxy** — atomic Zettelkasten notes for learnings). Use `→ run sub-skill: vault-remember` (lines 550, 838) via `model: "sonnet"` subagent (line 271).

Do NOT write if: budget exhausted, already captured, not reusable, or would confuse without context.

**Citation**: "Vault discipline" (lines 269–272); "### Vault Protocol" (lines 835–839); "### PARAG Structure" (lines 823–833); Step 6 (line 550)

---

## Item 10 — Self-restart vs exit

**Grade**: HEDGE

**Answer**: Per the doc:

- **Self-restart (exit-42)**: triggered by `cycle_post.py` when context pressure exceeds the configured threshold OR when the harness flips `stopping`/`restarting` intent. The agent's job is to invoke `/quit` immediately so the harness can respawn or stop it. This is handled by `→ run sub-skill: self-restart` at Step 7 (lines 552–556) and at `step:cycle/checkpoint` (line 606).
- **Exit (Monitor exit)**: if `Monitor` exits for any reason — `event_poll.py` terminates, non-zero exit, tool error, stream close — end the session immediately. Do NOT retry Monitor. The harness's auto-respawn owns recovery (lines 388–389).
- **Wait (normal cycle end)**: After the post-cycle wrapper for an event, POST `ack-cursor` and the eager loop immediately checks for the next event. Re-enter Monitor idle-wait when the drain to empty completes. This is the normal path — not an exit or restart.

The doc is clear on exit-42 and Monitor-exit cases. However, it does not give a standalone checklist: "at the end of a cycle, check X before deciding Y." The decision falls out of: did `cycle_post.py` exit 42? then `/quit`. Did Monitor exit? then end session. Otherwise keep draining. A fresh agent must synthesize this from multiple sections rather than finding it in one place.

**Citation**: "Step 7 — step:cycle/exit" (lines 552–556); "→ run sub-skill: self-restart" (lines 556, 606); "§5 Your idle wait is the Monitor tool" (lines 383–389); "§3 Per-nudge cycle" (lines 339–373)

**Gap / fix suggestion**: A short decision table at Step 7 (three rows: exit-42 → /quit, Monitor-exit → end session, normal → drain loop) would let a fresh agent answer this question from a single location rather than synthesizing across three separate sections.

---

## Contradictions found

- **Dual `step:cycle/resume` headings with inconsistent content** (lines 526–528 vs 580–598): "Step 2 — step:cycle/resume" defines resume as a single sub-skill marker (`resume-working-state`) plus `triage-issues`. The second unnumbered `### step:cycle/resume` at line 580 adds six more sub-skill markers: `interval-sync`, `triage-issues` (duplicated), `implement-tasks`, `pickup-comment-fidelity`, `improvement-scan`, `vault-remember`, `vault-optimize`. A fresh agent reading linearly follows the Step 2 version and never reaches the second, silently skipping `implement-tasks`, `improvement-scan`, and `vault-remember` every boot. The second also includes cycle-body behaviors (`implement-tasks`, `improvement-scan`) inside a resume step, which contradicts the canonical seven-step sequence where those belong in step:cycle/work.

- **Step 7.2 marker names wrong sub-skill for DS-review** (line 741): The heading is "Step 7.2 — step:cycle/ds-review" but the marker reads `→ run sub-skill: improvement-scan`. The goal text (line 743) describes spawning a DeepSeek review subagent for high-blast-radius changes. `improvement-scan` is the scan-and-file sub-skill (Step 6 / line 550), not a DS-review sub-skill. This is a copy-paste error: the wrong sub-skill marker would fire improvement-scan logic instead of a DeepSeek review gate.

- **`step:cycle/checkpoint` appears twice with different content** (lines 544–546 vs 600–606): Step 5 invokes only `git-commit`. The second instance at line 600 invokes `git-commit` AND `self-restart`. The `self-restart` sub-skill is also invoked at Step 7 (line 556). Having `self-restart` at both checkpoint and exit with no conditional guard means it could fire twice in sequence.

---

## Overall verdict

The doc is **not yet production-ready** for a cold-boot skill agent. The two blocking issues are: (1) the dual `step:cycle/resume` contradiction means the ralph-loop-overview block's `implement-tasks`, `improvement-scan`, and `vault-remember` calls are unreachable in the numbered seven-step path — a fresh agent would silently skip core cycle work every session; and (2) the mislabeled `improvement-scan` marker at Step 7.2 means DS-review never fires for high-blast-radius skill changes, which is precisely the quality gate the architecture depends on. Both stem from the same root cause: a legacy ralph-loop-overview block (lines 566–634) was re-included after the numbered seven-step schema was added, creating two parallel but inconsistent instruction sets within one composed file. Fix requires either removing the duplicate block entirely or reconciling the two sequences into a single authoritative ordered list.
