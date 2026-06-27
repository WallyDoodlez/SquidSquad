---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step 6f — Pipeline Sentinel (always runs)

This step runs **every cycle regardless of verifier presence**. It monitors the ticket pipeline for stalls, conflicts, and unmerged work.

Print: `[🦑 HH:MM:SS] Running pipeline sentinel...`

Write status bar: `python references/scripts/cycle.py status-bar [ROLE] "verifying" "pipeline-sentinel — Checking pipeline health..."`

**1. PR Conflict Detection**

List open SquidSquad PRs and check for conflicts (#9478: branch+PR is the only mode):
```bash
gh pr list --search "squidsquad/" --state open --json number,title,headRefName,mergeable --limit 20
```

For each PR with `mergeable` = `CONFLICTING`:
- Parse the issue number from the branch name (e.g., `squidsquad/skill/475` → `#475`)
- Comment on the issue: `python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR #[PR] has merge conflicts. Worker agent: merge main into your branch and re-push."`
- If the task is at `pending-ship` or `pending-test`, transition back to `in-progress`:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] [current-status] in-progress --role pm-lead
  ```

**2. Halt Detection → Investigate → Unblock-or-Escalate**

The sentinel monitors the *flow* of the pipeline: detect a halt, **investigate the cause, actively unblock if you have the authority, otherwise escalate for a decision** — never go silent and never rely on a bare comment to drive a handoff.

Query all open SquidSquad items:
```bash
gh issue list --label squidsquad --state open --json number,title,labels,updatedAt --limit 50
```

**2.1 Detect a halt — by lack of PROGRESS, not by absence of comments.** A **halt** is *no forward progress on a non-terminal item past **90 minutes*** (3 cycles). Forward progress means a **status/label change or a PR push** — **NOT** a new comment. Treat any non-terminal item past threshold with no status/label/PR movement as a halt candidate, **regardless of comment activity**.

> **Failed-handoff sub-rule (the case the old "no recent comments = stalled" test missed):** an item is halted **even when recent comments exist** if those comments carry an **unactioned ask/handoff while the owning agent is idle**. A recent comment is NOT progress.

**2.2 Investigate — classify the cause before any remedy.** Read the latest comments + check agent health (`health_check.py --json`), then assign exactly one class:

- **(a) failed-handoff** — an ask/handoff was posted *as a bare comment*, the status never changed, and the owner is idle. A bare comment wakes **no** agent in event mode ([[comment-handling]]), so the handoff silently never fired. *(The EAD auto-re-emits recognized handoff **statuses** ~600s — #12442 — so status-based handoffs self-heal; this class is the COMMENT-only ask the EAD has nothing to re-fire.)* **If the asked-for action is outside PM authority (e.g. "DM, merge this PR") or needs a process choice, classify (c) instead — not (a).**
- **(b) dead-agent** — the owning agent's health is `stalled`/`stopped`/`unknown` (see check 4f).
- **(c) blocked-on-decision** — the halt needs a **human/PM process choice**, or the only unblock is outside PM authority (e.g. #12460 needed the shadow-vs-split call). No purely mechanical, in-authority unblock exists.
- **(d) genuine-no-progress** — agent alive and event-mode-reachable but not advancing (workload saturation, an unrecognised block, or a task larger than one cycle).

**PM-authority boundary for "unblock" — check BEFORE acting in 2.3 (load-bearing, do NOT cross).** Allowed: an authorized `tracker.py transition`; convert draft PR → ready (metadata); boot a dead/stalled agent via `boot_remote.py`; escalate to the human. **Prohibited** as "unblock": transitioning **another role's** task outside PM authority, merging/closing PRs, or touching git branches. If the only fix crosses this boundary, it is an escalation (2.4), not a PM unblock — so it is class (c), not (a).

**2.3 Unblock — only via an EVENT-MODE-EFFECTIVE action you are authorized for.** A bare comment does **not** wake an event-mode agent, so a comment is never an unblock. Verify the action is within the authority boundary above, then use a **wake-causing** action ([[comment-handling]] — wakes ride a status/label change, not a comment):

- **(a) failed-handoff** → effect the handoff the bare-comment ask *should* have been: an **authorized `tracker.py transition`** that moves the item into the next owner's pickup state (the harness EAD turns the resulting `role:*`/status change into an `assigned-to` that wakes that owner). Do **not** re-post the ask as another comment. *(If you reach here and the action turns out to be outside PM authority, you mis-classified — it is (c); go to 2.4.)*
- **(b) dead-agent** → `boot_remote.py` stall-recovery (check 4f Tier 0), or return to `approved` for re-pickup (4f Tier 1).
- **(c) blocked-on-decision** → **escalate** (2.4) — there is no in-authority unblock.
- **(d) genuine-no-progress** → one authorized re-wake transition if applicable; if already reachable and simply mid-work, leave it (not every slow item is a halt); if saturated/over-scope, escalate with that finding.

**2.4 Escalate for a decision when you cannot unblock.** When no in-authority unblock exists, **surface to the human** — with (i) the investigation findings and (ii) **concrete options** — via a human-REACHING surface, **not** a bare comment and **not** a silent bug-file. Transition the item to `pending-human-review` (the harness emits this and it flags the item for the human) and put findings + options in the accompanying comment:
```bash
python references/scripts/tracker.py transition [NUMBER] [current-status] pending-human-review --role pm-lead
python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "HALT investigated — [class]. Findings: [...]. Decision needed: (A) [...] / (B) [...]."
```
*(If `current-status → pending-human-review` is not a legal transition for the item's state, escalate via the equivalent flagged surface — `pending-human-setup`, or `tracker.py transition … --force` which bypasses the legality matrix, only when the operator explicitly directs it (#12475) — never downgrade to a bare comment.)*

**Worked example — #12460 (the incident this step exists for).** skill finished the shadow increment and posted *"DM please merge PR #12472"* **as a bare comment**, then went idle; status stayed `in-progress`. **Detect:** `in-progress` >90 min, no status/label/PR movement — halt (despite the recent comment). **Investigate:** an unactioned handoff ask with the owner idle looks like *failed-handoff* — but the ask ("merge now vs split the cutover") needs a **process choice** PM can't make unilaterally, and DM-merge is outside PM authority, so it is **(c) blocked-on-decision**. **Act:** escalate — transition to `pending-human-review` with options *(A) ship the shadow now + split the cutover into a follow-up, (B) keep #12460 open, merge the shadow, observe, then add the cutover commits*. This is exactly how it resolved (operator chose the split, PATH B). The wrong move — which the old sentinel would have made — is a bare-comment "Task in-progress for N min" nudge, which wakes no one.

**Noise caps.** **Max 2 advisory comment nudges per cycle** (the check-4 advisory nudges only); skip items already nudged in the last 90 min (check Discussion). **Halt-driven actions are NEVER capped and never subject to the 90-min cooldown** — 2.3 authorized transitions and 2.4 escalations always run, so the noise budget can never suppress surfacing a real halt.

**3. PR Status Sync**

For each open PR (from the conflict check query above):
- **If merged**: find the tracker item and transition to `pending-ship` if not already (expected state: `pending-test`). Comment: `"PR merged. Status → Pending Ship."`
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR merged. Status → Pending Ship."
  ```
  If the task is not at `pending-test` (e.g., already at `pending-ship` or `shipped`), skip the transition silently.
- **If closed without merge**: transition back to `in-progress` (expected state: `pending-test`). Comment: `"PR closed without merge. Status → In Progress."`
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR closed without merge. Status → In Progress."
  ```

**4. Stuck-State Detection (comprehensive)**

After the halt and PR sync checks, run these additional stuck-state detections. Each has a **Tier 1** and **Tier 2** (root-cause bug filing) response. **Max 2 auto-filed bugs per cycle** to avoid noise — prioritize by severity.

> **Tier 1 here is ADVISORY only — not a handoff/unblock.** The Tier-1 comments below are visibility trails absorbed at the next pickup ([[comment-handling]]: PM advisory comments are fine as bare comments); they do **not** wake an event-mode agent and must never be relied on to *drive* a handoff. When a stuck item actually needs the owner to act (e.g. an approved item not picked up because its agent is down or saturated), that is a **halt** — route it through section 2 (classify → event-effective unblock or escalate), not a bare-comment nudge.

Before filing a Tier 2 bug, check if an open bug already exists for the same root cause:
```bash
python references/scripts/tracker.py list-issues [target-role] --status open
```
If a matching bug title exists, skip filing (already tracked).

**4a. Orphaned PR** — tracker item shipped/closed but PR still open and unmerged.

Query: cross-reference open PRs against closed/shipped tracker items.
```bash
gh pr list --search "squidsquad/" --state open --json number,title,headRefName --limit 20
```
For each open PR, parse the issue number from the branch name. Check if that issue is closed:
```bash
python references/scripts/tracker.py get-state [NUMBER]
```
If the issue is closed but the PR is open and unmerged:
- **Tier 1**: Comment on the tracker issue routing to owning agent — `python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "Orphaned PR #[PR] — item shipped but PR still open. [role]-lead or human: close or merge the PR."`
- **Tier 2**: File bug against DM — `"DM delivery did not enforce PR merge before marking shipped. Item #[NUMBER] shipped but PR #[PR] left open. Code on branch may never reach main."`

**4b. Shipped without merge** — item marked shipped but PR branch never merged (code lost).

For each recently closed item with `status:shipped` (last 20 closed items):
```bash
gh issue list --label squidsquad --label status:shipped --state closed --json number,title,labels --limit 20
```
Check if a corresponding branch exists and was never merged:
```bash
git branch -r --list "origin/squidsquad/*/[NUMBER]"
```
If the branch exists, check if it was merged to main:
```bash
git log main --oneline --grep="#[NUMBER]" -n 5
```
If no merge evidence and branch still exists:
- **Tier 1**: Comment on the issue — `"Warning: branch squidsquad/[role]/[NUMBER] exists but may not be merged to main. Code could be lost. Please verify."`
- **Tier 2**: File bug against the role that shipped it — `"Item #[NUMBER] shipped but feature branch may not be merged. Delivery process should verify PR merge before shipping."`

**4c. Approved but no pickup** — item at `status:approved` for more than 90 minutes with no agent pickup.

From the open items query, filter for `status:approved` items stalled >90 min. An approved item already received an `assigned-to` wake from the EAD at approval, so a no-pickup means the owner did not wake — treat it as a **halt** and run it through section 2:
- **Investigate**: check the owner's health. **dead-agent** → `boot_remote.py` (2.3b / 4f). **genuine-no-progress** (alive, saturated) → escalate per 2.4 with that finding. A bare-comment "please pick up" nudge does NOT wake the agent and is not a remedy.
- **Tier 1 (advisory only)**: optionally leave a visibility comment, but it does not substitute for the section-2 action above.
- **Tier 2**: Only file if stalled >4 hours — `"Task #[NUMBER] approved but no agent picked it up for [N] hours. Possible causes: agent down, workload saturation, or task not visible in agent's query."`

**4d. Planned but never approved** — `status:planned` for more than 4 hours.

From the open items query, filter for `status:planned` items stalled >4 hours:
- **Tier 1**: Comment — `"Task planned for [N] hours but not yet approved. Human: please review and approve or defer."`
- **Tier 2**: Not auto-filed (requires human decision — approval is a human gate).

**4e. Pending with no planning** — `status:pending` for more than 4 hours with no `status:planning` transition.

From the open items query, filter for `status:pending` items stalled >4 hours:
- **Tier 1**: Comment — `"Item pending for [N] hours with no planning started. PM: please triage and begin planning or defer."`
- **Tier 2**: Only if >8 hours — file against PM — `"Item #[NUMBER] pending for [N] hours with no planning activity. May need triage prioritization."`

**4f. In-progress on dead agent** — task `status:in-progress` but assigned agent's health is stalled/stopped.

For each `in-progress` item, extract the `role:*` label. Cross-reference with agent health:
```bash
python references/scripts/health_check.py --json
```
Parse the JSON output. If the assigned agent's health is `stalled`, `stopped`, or `unknown`:
- **Tier 0** (#9272 — try recovery first): if auto-boot in `cycle_pre.py` did not recover the agent, attempt manual stall recovery via `python references/scripts/boot_remote.py --role <name>` (see `boot-remote-agents` sub-skill). Only if the boot fails OR the agent remains unhealthy on the next health check, proceed to Tier 1. Skip this tier if the agent's intent is `stopping` or `stopped` (genuinely shut down on operator request, not a stall).
- **Tier 1**: Transition the task back to `approved` so another agent (or the same agent after restart) can pick it up:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] in-progress approved --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "Agent [role] is [health status]. Returning task to approved for re-pickup."
  ```
- **Tier 2**: File bug if agent has been unhealthy for >1 hour — `"Agent [role] health is [status] but task #[NUMBER] was in-progress. Harness may need investigation."`

<!-- #9478: branch+PR is the only mode; all checks above run unconditionally. -->

