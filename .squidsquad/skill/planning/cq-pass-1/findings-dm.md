# CQ Pass 1 — DM Findings

Role: DM
Source: `.squidsquad/dm/CLAUDE.md`
Date: 2026-06-11

---

## Item 1 — Boot, no working-state

**Grade**: PASS

**Answer**: On fresh spawn, execute Step 1 (step:cycle/boot) before any other action. First, run `python references/scripts/tracker.py check-gh` — if it fails, print the error message and exit. Second, read `.squidsquad/.harness-port` to resolve the port (default 7373 if absent/invalid), then probe: `curl -sf --max-time 5 http://127.0.0.1:<port>/status`. If exit code is 0 → EVENT mode: load sub-skills in order: `event-driven-workflow`, `event-mode-contract`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`, `roles/dm/events/pr-merge-wait`. If probe fails → POLLING mode: invoke `/loop 30m execute one Ralph Loop cycle` exactly once, then Read `references/sub-skills/roles/dm/ralph-loop-overview.md`. Mode selection is sticky for the session.

**Citation**: "Step 1 — step:cycle/boot", lines 374–448 (Verify GitHub Issues access, Check harness reachability, EVENT mode contract load, POLLING mode block)

---

## Item 2 — Resume with prior task

**Grade**: PASS

**Answer**: At Step 2 (step:cycle/resume), invoke `→ run sub-skill: resume-working-state`. Read `working-state.md`. If an active task is shown as `in-progress`, queue it as the first thing to handle once nudges start arriving — trust the working-state for completed steps and key decisions, do not restart cold. Then at Step 2.1 (step:cycle/issue-triage) invoke `→ run sub-skill: task-pickup` and scan for pending-ship items. Before touching any of them, check the `delivery:skip` label. As for pull-or-skip: the universal prohibition at line 17 is "Never push without pulling first" and the Delivery Flow section (line 611) says "Always `git pull` before starting work" — so pull unconditionally before starting any task continuation.

**Citation**: "Step 2 — step:cycle/resume" (lines 450–458); "Branch + PR Workflow" section (lines 609–613); universal Boundaries (lines 17–26)

---

## Item 3 — Context pressure trigger

**Grade**: HEDGE

**Answer**: Invoke `→ run sub-skill: context-pressure` (referenced at `step:cycle/context-pressure`, lines 503–508). Per the step goal: read the live context-pressure percentage from disk, compare to configured threshold. At 87% > 80%, checkpoint pending work to `working-state.md` and push git so a respawn loses nothing. The working-state.md must contain sufficient state for a respawn to resume without restarting cold. After checkpointing, the cycle exits via the exit-42 path — the post-cycle wrapper owns this, and DM invokes `/quit` so the harness can respawn (self-restart sub-skill, lines 478–480). Do NOT continue creative work above threshold.

**Citation**: "`step:cycle/context-pressure`" (lines 503–507); "Step 7 — step:cycle/exit" and self-restart sub-skill (lines 478–480)

**Gap / fix suggestion**: The configured threshold (80%) and the exact working-state fields required before respawn are not inlined — they are delegated entirely to `→ run sub-skill: context-pressure`. A fresh agent cannot determine the threshold number or the mandatory working-state schema from this CLAUDE.md alone. HEDGE rather than PASS because a real agent might not know which threshold applies or what working-state fields are mandatory at respawn. Suggest: inline the threshold value and a one-line schema summary at step:cycle/context-pressure.

---

## Item 4 — Cross-domain bug found

**Grade**: PASS

**Answer**: DM's role boundary is delivery artifacts only — "DM = delivery artifacts only. If work belongs to another role, file it there" (line 21). Do NOT fix the bug; do NOT implement anything. Investigate to confirm the bug is outside DM's domain, then file it via the issue-filing sub-skill: `→ run sub-skill: roles/dm/issue-filing` (line 534). The correct role label for the owning role must be included (e.g., `role:skill` for a worker-owned bug). Post a Discussion comment on the relevant issue to notify the owning agent. Never construct `gh issue edit` label commands manually (line 559).

**Citation**: "Boundaries" universal section (lines 13–26), line 21; "What this role does NOT do" (lines 40–45); `→ run sub-skill: roles/dm/issue-filing` (line 534); "What You Must Never Do" (line 559)

---

## Item 5 — Discussion comment received

**Grade**: PASS

**Answer**: Responding to a forge comment goes through `tracker.py`. Every comment is posted via: `python references/scripts/tracker.py comment <NUMBER> --role "dm" --message "[message]"`. The role alias prefix (`**dm**`) is auto-prepended by tracker.py — never include it in `--message`. All timestamps come from `python references/scripts/cycle.py timestamp-short` — never guess or fabricate (line 22, line 105). Forbidden: editing or deleting any prior comment (lines 19, 556); constructing raw `gh issue edit` commands (line 559); overriding durable state changes outside tracker.py.

**Citation**: "Tracker Protocol — GitHub Issues" (lines 484–486); "What You Must Never Do" (lines 550–564); "Shared Discipline" soul section (lines 103–108); Tracker section (lines 629–634)

---

## Item 6 — Checkpoint discipline

**Grade**: HEDGE

**Answer**: At step:cycle/checkpoint (Step 5), invoke `→ run sub-skill: git-commit` to mark a logical checkpoint — "The mechanical commit and push are part of the post-cycle wrapper (`cycle_post.py` — you don't execute it)" (line 470). For DM's delivery cycle: delivery work (merge, CHANGELOG, docs) occurs at step 7.1; the `shipped` transition is made via `python references/scripts/tracker.py transition <issue> pending-ship shipped` — auto-closes the issue. NEVER: construct `gh issue edit` label commands (line 559), skip the `delivery:skip` check (line 557), delete CHANGELOG entries (line 558), or push without pulling (line 555).

**Citation**: "Step 5 — step:cycle/checkpoint" (lines 468–471); "Step 7.1 — step:cycle/delivery-packaging" (lines 578–582); "What You Must Never Do" (lines 550–564)

**Gap / fix suggestion**: The doc does not explicitly state whether the tracker transition fires before or after the git commit/push in the delivery step — it defers entirely to `→ run sub-skill: delivery-packaging`. The inline summary at Step 7.1 (line 582) implies merge → CHANGELOG → transition order, but "commit first or transition first" is not made unambiguous from this CLAUDE.md alone. HEDGE because the ordering question requires reading the delivery-packaging sub-skill.

---

## Item 7 — L4-curation trigger

**Grade**: PASS

**Answer**: "From now on, every commit message must include the issue number in square brackets" is a project-specific durable customization directive (pattern: "from now on, every X"). Classification: durable directive. Action: invoke `→ run sub-skill: l4-curation` BEFORE doing any implementation work. Do nothing else first — the sub-skill handles: elicitation dialog, the decision tree (replace/insert-before/insert-after/append), the safety-gate pipeline, and the project-customization commit. One-off requests and feature requests are explicitly NOT routed through l4-curation (line 576). No pre-invoke steps are specified in the doc beyond recognizing the trigger pattern.

**Citation**: "Reactive sub-skills / Project customization" (lines 569–576)

---

## Item 8 (DM-specific) — delivery:skip vs full delivery walk

**Grade**: PASS

**Answer**:

**Case A — pending-ship with `delivery:skip` label**:
At Step 2.1, scan for pending-ship items and check `delivery:skip` before starting packaging. Per line 604: "If the task's Discussion contains `delivery: skip`, mark Shipped immediately — no packaging needed." Use `python references/scripts/tracker.py transition <issue> pending-ship shipped` — no CHANGELOG entry, no branch merge, no packaging. The shipped transition auto-closes the issue. Still increment `Shipped Since Last Bump` in config.md (line 605: "after every ship," no exception stated for skip items).

**Case B — pending-ship WITHOUT `delivery:skip`**: Full delivery walk:
1. **Branch handling**: `git pull` before starting; use `git_ops.py task-begin`/`task-end` for branch checkout (lines 609–613). Merge feature branch into main.
2. **CHANGELOG framing**: write a user-benefit-framed entry — "describe what users GET, not internal changes. Non-technical language" (line 617). Anti-patterns: commit-message-style entries (line 137); worker-perspective entries (line 145).
3. **Version-bump-counter logic**: after every ship, increment `Shipped Since Last Bump` in config.md (line 605). At Step 7.2, invoke `→ run sub-skill: version-bumps` and monitor the counter. When threshold is reached: increment minor version, update `config.md` + `SKILL.md` frontmatter + `CHANGELOG.md`, create git tag, push, reset ship counter to 0 (lines 63, 616). Write migration walk doc at `migrations/v<N-1>-to-v<N>.md` (line 618).
4. **Final transition**: `python references/scripts/tracker.py transition <issue> pending-ship shipped` — auto-closes the issue. Never raw `gh issue edit` (line 559).
5. **Post-ship**: if task changed templates/sub-skills, trigger `reboot_agent.py` for affected agents (lines 187–188). Enable any config feature flags via `python references/scripts/config.py set` (line 606). Update README/SKILL.md if affected.

**Citation**: Step 2.1 (lines 454–458); "Delivery Flow" (lines 602–606); "Version Bumps" (lines 614–618); Step 7.1 (lines 578–582); Step 7.2 (lines 584–588); "What You Must Never Do" (lines 550–564); "Complete ownership" (lines 182–184); "Template changes require reboots" (lines 186–188)

---

## Item 9 — Vault-remember after novel work

**Grade**: PASS

**Answer**: After completing non-trivial work yielding a reusable insight, invoke `→ run sub-skill: vault-remember` (line 474, line 664). Apply the 4-gate logic before writing: (1) write budget — max 2 vault writes per cycle; (2) dedup check — is this already in the vault?; (3) reusability — would another agent benefit in a future session?; (4) fresh-context test — is this genuinely new, not obvious from current context? If all 4 gates pass, write to the Galaxy bucket (`vault/galaxy/`) as a `learning-*` note (PARAG table, line 657). Do NOT write if budget is exhausted, insight already exists, it's too specific to reuse, or it's obvious from existing context.

**Citation**: "Vault Protocol" (lines 640–665); PARAG table (lines 650–658); "step:cycle/cleanup" (line 474)

---

## Item 10 — Self-restart vs exit

**Grade**: PASS

**Answer**: After a successful cycle, the agent does NOT exit. At Step 7 (step:cycle/exit), invoke `→ run sub-skill: agent-lifecycle` then `→ run sub-skill: self-restart`. Three possible outcomes: (1) **Continue cycling**: POST `ack-cursor` per-event, eager loop fetches next event — no waiting. (2) **Re-enter Monitor idle-wait**: when queue drains to empty, invoke Monitor tool streaming `event_poll.py` stdout; each `NUDGE\n` wakes the next cycle. (3) **Self-restart (exit-42)**: if `cycle_post.py` detects context pressure above threshold OR `stopping`/`restarting` intent flip, it commits/pushes and exits code 42 — DM must immediately invoke `/quit` so harness can respawn. (4) **Hard session end**: if Monitor exits for any reason — do NOT retry Monitor, do NOT pivot to polling, end the session immediately; harness auto-respawn owns recovery.

**Citation**: "Step 7 — step:cycle/exit" (lines 478–480); "Your idle wait is the `Monitor` tool" (lines 309–314); "Per-nudge cycle §3" (lines 265–297)

---

## Contradictions found

- **`delivery:skip` signal — label vs. Discussion comment**: Step 2.1 (line 458) says "Check `delivery:skip` **label** before starting packaging." The "Delivery Flow" section (line 604) says "If the task's **Discussion** contains `delivery: skip`…" The "Boundaries" section (line 167) says "Never skip `delivery:skip` check" without specifying which signal. GitHub labels and Discussion prose comments are entirely different signals — an item can have one but not the other. A fresh agent cannot determine which to trust. This is the highest-severity contradiction in the doc.

- **`step:cycle/run` orphan block vs. numbered-step structure**: Lines 496–528 define `step:cycle/run`, `step:cycle/context-pressure`, a second `→ run sub-skill: resume-working-state`, and a sequence of additional sub-skills (`interval-sync`, `issue-triage`, `delivery-packaging`, `version-bumps`, `doc-improvement-loop`, `vault-remember`, `vault-optimize`, `self-restart`). These appear after Step 7 in the document and are not mapped to any node in the hydrated cycle diagram (lines 330–359). They appear to be a legacy loop-mode polling fragment that was never reconciled with the numbered-step (Steps 1–7) structure introduced for event mode. A fresh agent reading linearly would execute both sequences or be confused about which is authoritative.

- **Version-bump threshold unstated**: Lines 584–588 and 616 describe the complete bump sequence but never specify the threshold count that triggers it. The doc says "when the threshold is reached" and defers to `→ run sub-skill: version-bumps`. Not a contradiction but a actionable gap — a fresh agent cannot execute the gate without the sub-skill.

---

## Overall verdict

The DM CLAUDE.md is largely production-ready: boot sequence, mode selection, delivery flow, version-bump sequencing, CHANGELOG framing, vault discipline, and verify-before-blocked posture are all documented with sufficient specificity for correct autonomous execution. The one blocking issue is the `delivery:skip` signal contradiction — the doc inconsistently points to a GitHub label in one place and a Discussion comment in another; these are different forge surfaces and a fresh agent could skip packaging when it should not, or do packaging when it should skip. The secondary structural issue — the orphan `step:cycle/run` block sitting after Step 7 with no diagram anchor — should be removed or explicitly marked as a loop-mode-only fragment to prevent a fresh agent from double-executing cycle steps. Both issues are fixable with a targeted two-line edit to the source sub-skills.
