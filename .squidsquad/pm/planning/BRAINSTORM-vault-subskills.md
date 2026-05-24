# Brainstorm — Vault sub-skill redesign

**Status**: draft, exploratory
**Author**: pm-lead (interactive session with human)
**Date**: 2026-05-24
**Context**: surfaced during #10003 (massage docs/VAULT-ARCH.md). Goal: produce an absolutely-better-than-current plan for how SquidSquad uses its vault. Backward compatibility is **not** a constraint — tear down anything that doesn't earn its keep.

Relates to: #5855 (vault is static decision log), #10003 (this PR's doc work), and the (currently closed) #10008 vault-redesign task.

---

## Framing

Three layers, established in conversation:

| Layer | "When/where/how" | Implementation |
|---|---|---|
| **Triggers** | When does a vault write fire? | Events, hooks |
| **Integration** | How does the agent behave around vault? | Sub-skills (this doc's focus) |
| **Utilization** | How do humans + agents query the vault? | Slash commands, search UI |

Triggers already brainstormed and accepted (see "Proposed triggers" below).

---

## Proposed triggers (recap)

| # | Trigger | Fires on | Owning role |
|---|---|---|---|
| T1 | PR-bound capture | `gh pr create` (any role) | All roles |
| T2 | Improvement-scan finding | scan completes with systemic pattern | Skill (or any role running scans) |
| T3 | Decision-commit | tracker `planned → approved` transition | PM |
| T4 | Bug-ship learning | tracker `pending-ship → shipped` on a bug | DM |

Plus content-threshold and event-bus-driven secondary triggers (see below).

---

## Existing sub-skills — tear-down audit

`references/sub-skills/common/` and `roles/pm/`:

| Existing sub-skill | Verdict | Reason |
|---|---|---|
| `vault-protocol.md` | **Tear down** | Monolithic "do everything around vault" routine; failed in practice because it has no firing condition. |
| `vault-protocol-slim.md` | **Tear down** | Lighter copy of the same failure pattern. |
| `vault-remember.md` | **Tear down** | Currently "every cycle, check staleness". 147 cycles since BRIEFING last refreshed. |
| `vault-optimize.md` | **Tear down as cycle routine, keep script** | The "every quiet cycle" framing failed. The underlying decay/archive logic is sound — move it under a content-or-time trigger. |
| `roles/pm/vault-synthesis.md` | **Fold into briefing-regen** | Synthesis is BRIEFING regeneration with more aggressive galaxy promotion. Doesn't earn a separate sub-skill. |

**Keep without redesign:**
- PARAG storage schema (with the simplifications already agreed — drop `areas/`, drop `resources/`, drop `projects/`).
- Confidence levels (`high` / `medium` / `low`) and decay defaults.
- Frontmatter spec, wikilink syntax, `vault_check.py`'s link-rewrite-on-archive logic.

---

## Proposed sub-skill set (replacement)

Two classes:

- **Class A — composed-into-CLAUDE.md** (read-side, hook-into-agent-workflow)
- **Class B — event-bus-subscriber** (write-side, fire-on-event, lives in the harness layer not the agent layer) — this is a **new pattern** for SquidSquad; ties into `project_harness_vision`.

### Class A — composed sub-skills

#### A1. `vault-boot-context`
- **Composed into**: every role, at boot only
- **Replaces**: the "every cycle, check BRIEFING staleness" loop
- **Behavior**: read `BRIEFING.md` + `areas/<role>-context.md` (if any) at session start. Treat as fresh — the briefing-regen sub-skill (B1) keeps it that way. No staleness check inline.
- **Why this works**: removes the polling-loop dependency; trust is moved to the regen mechanism.

#### A2. `vault-precheck-task`
- **Composed into**: every role's task-pickup path
- **Replaces**: nothing (new behavior)
- **Behavior**: before transitioning `approved → in-progress`, dispatch `vault-search <task title + role + key terms>` (background subagent) and surface top-3 hits. Agent must read findings before continuing. If nothing relevant exists, proceed.
- **Why this matters**: the "we already decided this 50 cycles ago" failure is real; cheap to fix; high leverage on cross-cycle learning.

#### A3. `vault-capture-on-pr` (T1 trigger handler)
- **Composed into**: every role that opens PRs
- **Replaces**: nothing (new behavior)
- **Behavior**: mirrors dmp-web2 `/pr` Step 7.5 + 9.5. Before `gh pr create`, run signal-gate ("is there durable knowledge here?"), dispatch `vault-remember` background subagent if yes, await its report, stage `.squidsquad/vault/**` changes onto the feature branch, then create the PR. After PR creation, dispatch `vault-update` to backfill the PR URL.
- **Open question**: ASK-USER ambiguity protocol — when running autonomously in a cycle, "ASK-USER" becomes "ASK-HUMAN-NEXT-CYCLE" or "skip + log". Needs spec.

#### A4. `vault-capture-on-decision` (T3 trigger handler)
- **Composed into**: PM only
- **Replaces**: the implicit "decisions live in tracker Discussion comments forever"
- **Behavior**: on `planned → approved` transition, scan the task's Discussion comments for the agreed approach (most recent `**pm**:` block before approval). Auto-promote to a galaxy `decision-<task-slug>.md` note with the approved approach as body, links back to the tracker number.
- **Why this is high leverage**: every PM-mediated approval today silently buries its decision rationale. This makes them queryable.

#### A5. `vault-capture-on-ship-learning` (T4 trigger handler)
- **Composed into**: DM only
- **Replaces**: nothing (new behavior)
- **Behavior**: on `pending-ship → shipped` for items labeled `type:issue`, prompt the agent (via in-flow instruction, not user-facing): "did this bug's root cause produce a durable learning?" If yes, dispatch `vault-create` with `learning-<bug-slug>.md`. Includes the bug's root-cause analysis from the dev's PR description.

#### A6. `vault-capture-on-scan-finding` (T2 trigger handler)
- **Composed into**: skill (and any other role running improvement scans)
- **Replaces**: today's "filing as a bug" pipeline for systemic findings — augments, doesn't replace
- **Behavior**: when a scan finding has scope `systemic` (matches multiple files / files-of-a-pattern, like #10007's audit), dispatch `vault-create` with `pattern-<scan-slug>.md` recording the pattern, even when also filing a bug. Bug fixes; pattern note is the durable insight.

### Class B — event-bus-subscriber sub-skills

These are **new architecture** — sub-skills that the harness loads and which subscribe to event-bus events. They don't compose into any agent's CLAUDE.md.

#### B1. `vault-briefing-regen`
- **Subscribes to**: `vault-write-galaxy` events (any galaxy note created/updated)
- **Behavior**: rebuilds BRIEFING.md from the N most recent high-confidence galaxy notes plus standing `areas/` content. Atomic write (tmp + rename). Pushes when done.
- **Why this is the keystone**: removes the dependency on "every cycle, refresh BRIEFING". BRIEFING is now an artifact of vault content, not a hand-maintained file.
- **Open question**: does it run on every galaxy write (noisy but simple) or debounce/batch (cleaner but adds complexity)?

#### B2. `vault-decay-keeper`
- **Subscribes to**: real cron (`0 4 * * *` daily) AND content threshold (50+ new galaxy notes since last run)
- **Replaces**: `vault-optimize.md` "every quiet cycle"
- **Behavior**: walks `galaxy/`, applies confidence decay (high→medium at 60d, medium→low at 120d), archives orphans, archives `status: superseded`. Reports archived-count summary.
- **Why time + content trigger**: decay is genuinely time-based; orphan-detection benefits from running after enough new content has piled up. Cycle counter is the wrong proxy for both.

#### B3. `vault-l4-injector` (meta — wires into compose.py)
- **Not a sub-skill — a compose-time mechanism**
- **Behavior**: galaxy notes tagged `posture: agent-behavior` and `target: <role>` get composed into that role's CLAUDE.md as L4-style constraints when `compose.py deploy <role>` runs.
- **Why this closes the loop**: today, learned-behavior memory lives in user-personal memory (`feedback_*.md`) and never propagates to teammates. This makes cross-agent learning structural — once the vault knows it, every agent re-deploy picks it up.
- **Risk**: composed CLAUDE.md becomes a moving target; needs versioning + diff visibility. Slot only.

#### B4. `vault-cross-role-broadcast`
- **Subscribes to**: `vault-write-galaxy` events
- **Behavior**: inspect tags + body wikilinks. If the note references another role's domain (tag like `role:dm`, wikilink to a DM-owned area note), publish a `vault-note-relevant` event targeting that role. Receiving role surfaces it next cycle's check-in.
- **Why**: today writes are silent; teammates only see them by accident on `git pull`.

---

## Utilization — secondary, briefer

| # | Idea | Status |
|---|---|---|
| U1 | `/squidsquad-recall <topic>` slash command (human-facing) | New |
| U2 | Knowledge-budget search (max 2 knowledge nodes per path) | Lift from dmp-web2 |
| U3 | "Vault as compass, code as truth" rule | Lift from dmp-web2 |
| U4 | `/vault-write` for manual capture (agent or human) | New, low priority |

---

## What this gives us that we don't have now

1. **A working briefing**. BRIEFING.md becomes an artifact of vault writes, not a polling-loop chore.
2. **Cross-cycle learning visible at pickup**. Agents see "we already thought about this" before re-deriving.
3. **Per-PR durable knowledge capture**, atomically with code. No more "we shipped this and never wrote it down".
4. **Decisions extracted from tracker Discussion comments**. Today they're append-only mud; tomorrow they're queryable galaxy notes.
5. **Improvement-scan insights survive past the bug fix**. Pattern-* notes outlive the issue tracker.
6. **Bug learnings captured at ship time** (when context is freshest), by the role with full context (DM).
7. **Cross-role broadcast** via event bus — vault becomes part of squad coordination, not a side-system.
8. **L4 composition from vault** — learned behavior propagates structurally across redeploys.
9. **Decay actually runs**, time-triggered, not cycle-conditional.
10. **Two new architectural patterns**: event-bus-subscriber sub-skills (B class) and compose-time vault injection (B3). Both reusable beyond vault.

---

## Open questions for human

1. **B-class sub-skills introduce a new lifecycle for the harness to manage.** Acceptable, or does it need to wait for the harness vision to land further?
2. **ASK-USER protocol in autonomous cycles** — what's the right fallback? (Skip + log? Defer to next human-interaction cycle? Force user prompt?)
3. **B3 (L4 injector) is the most architecturally novel.** Worth pursuing in v1, or carve out as v2?
4. **Drop the `projects/` vault folder entirely?** Working-state + tracker arguably cover the same ground. Or keep as durable goals/constraints layer?
5. **Cron for `vault-decay-keeper`** — runs on what host? Inside the same harness process, or external? Affects how we ship this.

---

## What this brainstorm is not yet

- Not a phased rollout plan — that's the next step, not this one.
- Not a list of file edits — sub-skill specs are still high-level.
- Not approved scope — implementation is gated on a fresh task (re-file when ready; not the closed #10008).

---

## Next steps (if/when human approves)

1. Pick a wedge (e.g. A4 `vault-capture-on-decision` alone — single trigger, single role, isolated value).
2. File a new task with that wedge scoped concretely.
3. Phase 1 research on that task: sub-skill manifest changes, event-bus event names, vault-create subagent spec.
4. Iterate; expand to other A-class sub-skills once the wedge is proven.
5. B-class sub-skills come later — they depend on harness lifecycle for event subscribers, which deserves its own planning pass.
