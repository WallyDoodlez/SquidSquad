# Design: `human` as a role + async-no-pause (L1)

**Status**: LOCKED with operator (polish-mode session 2026-06-18). Doc-first per [[feedback_doc_first_for_arch]]. This is the buildable spec; AGENT-RUNTIME.md is the TRD of record (edited in the same change).

**Motivation (operator-observed):** skill agent keeps **pausing**, synchronously waiting for the human to interact promptly. Agents should never block on a human — all human interaction is asynchronous except inline mode. Separately, when the reboot decision came up there was **no `human` role** to assign it to, so it lived as an informal "deferred per operator" note instead of a tracked, assigned ticket.

---

## Locked decisions

### D1 — `human` is a role (like a worker role)
- `human` is a **first-class, routable role**. Agents can assign work to it via `/work/assign --target-alias <human-alias>`.
- **Aliases allowed; multiple humans supported** — exactly like multi-instance workers. Human aliases are registered in `.squidsquad/config.md` `## Aliases` (e.g. `human`, or `wallace`/`alice`).
- **No L1–L4, no SOUL, no compose.** Humans are not agents — "humans have their own L1–L4" (the person). Consequences:
  - `compose.py` / `compose.py deploy-all` MUST **skip human aliases** — they have no composed `CLAUDE.md` and no L4 file. The role-class resolver must not try to map a human alias to an agent role-class.
  - The harness does **not** spawn, supervise, health-check, or restart human aliases. No `event_poll`, no Monitor, no cursor, no `bootup-complete`, no `ack-cursor` for a human.
- **`human` is NOT on the event bus.** An `assigned-to <human>` event is appended to the deque like any other (so the forge label + audit trail are correct) but is **never consumed via the bus** — the human reads it on the forge (GitHub assignee/notification) or hears it inline. This is expected, not a bug.

### D2 — L1 async-no-pause (the expedited slice)
**L1, all roles.** Rule:

> **Never block on a human.** When you need a human's attention or decision, **assign a tracked ticket to a `human` alias** (`role:<human>` + the appropriate `pending-human-*` status) and **immediately continue** — pick up your next queue item, or go idle. The human responds **asynchronously** (on the forge, or inline later). **The only synchronous human interaction is inline mode** (the human initiated the direct message). Do not sit and wait for a human in any autonomous mode.

- A "need human" handoff MUST be a **transition/assignment**, not a bare comment (bare comments don't wake anyone, and we want the audit trail + ownership).
- After assigning to `human`, the agent releases to its normal flow (event mode: idle/next event; loop mode: next cycle). It does not hold the session.

### D3 — inline mode is an explicit status-bar state
- When an agent is in inline mode, the status bar's **current-event indicator reads `inline`**.
- This **replaces** the current §3 behavior (status-bar `current-state` left untouched/stale during inline) and **supersedes the #9358 workaround** (telling PM's sentinel to treat staleness as expected). The bar now carries an honest `inline` value.
- **Who writes it:** the agent self-writes the `inline` status-bar state when it detects a human (inline) turn, and clears it (back to normal idle/working state) when the inline session ends (human signals done, or the next autonomous wake fires). Cycle wrappers don't fire in inline mode, so this is agent-side.

### C1 — routing flip for human-*needed* work
- §8.3 routing table: `* → pending-human-review` and `* → pending-human-setup` now target a **`human` alias** (was `pm`).
- Human-*provided* events stay routed to an **agent**: `human-comment` (a human authored a forge comment) → `pm`. Distinction: "agent needs human" → assign `human`; "human gave input an agent must act on" → route to an agent.

### C3 — PM is no longer the mandatory human funnel
- Agents assign to `human` **directly**. PM still curates/surfaces human items in inline check-ins but is **not a required gate** for human-attention work. (Shift away from "PM is the sole human bridge.")

### C2 — return path is human-mediated (inline), not auto-routed
When the human answers:
- **Human → originating agent (inline):** the agent records the answer into the ticket and **re-assigns the ticket back to itself** to resume the work.
- **Human → PM (inline):** PM records the answer into the ticket and **assigns it back to the originating agent on its behalf.**
- **Human → wrong agent** (not originator, not PM): that agent replies **"not my territory — wrong agent"** and points the human at the right agent/PM. (Existing mis-route-recovery posture, applied to a human who mis-addressed.)
- No new metadata needed: the ticket's prior `role:*` label records the originator, so whoever helps the human re-assign knows where it came from.

---

## Where it lands
- **AGENT-RUNTIME.md (TRD, PM-owned, edited in this change):** Terminology § (human as non-agent role + aliases + multi-human + no-compose); §3 (async-no-pause L1 rule + inline status-bar = `inline` + human-mediated return path); §8.3 routing table (human-needed → `human`); revision log.
- **Implementation (role:skill, code-consumed source):**
  - **L1 source** — async-no-pause rule into L1 (`references/roles/SOUL.md` and/or L1 instructions) so every composed agent reads it. **EXPEDITED SLICE** (skill is pausing now).
  - **Inline status-bar** — agent self-writes `inline` current-event state on inline turn, clears on exit (statusline / `cycle.py status-bar` + the inline-detection path).
  - **`## Aliases`** — accept/register human aliases; `config.py` resolver returns them as a non-agent role.
  - **compose.py / deploy-all** — skip human aliases (no CLAUDE.md, no L4).
  - **tracker.py** — `role:<human>` is a valid label/target; `/work/assign` alias-existence check passes for human aliases.
  - **§8.3 routing** — human-needed transitions target the human alias.

## Acceptance criteria (testable)
- **AC1 (no-pause, L1 compose):** the async-no-pause rule is present in every composed event-mode + loop-mode agent `CLAUDE.md` after `compose.py deploy-all` (verify composed output, not just source).
- **AC2 (no-pause behavior / comprehension):** a fresh agent quizzed "you need a human decision mid-task and you're NOT in inline mode — what do you do?" answers "assign a ticket to a `human` alias and continue / release; I don't wait," NOT "I pause and wait for the human." (REQUIRED — instruction change.)
- **AC3 (human alias registers):** a `human` alias added to `## Aliases` is accepted by `config.py`; `tracker.py` accepts `role:<human>` and `/work/assign --target-alias <human>` (alias-existence passes).
- **AC4 (compose skips human):** `compose.py deploy-all` with a human alias present produces no `CLAUDE.md`/L4 for it and does not error; agent aliases still compose normally.
- **AC5 (routing flip):** `* → pending-human-review|setup` routes/assigns to the human alias (was pm); `human-comment` still routes to pm. Deterministic test on the routing table.
- **AC6 (inline status bar):** entering inline mode sets the status-bar current-event indicator to `inline`; it clears on inline-session end. Test the write + clear.
- **AC7 (return path):** a ticket assigned to `human`, once answered and re-assigned (by originator or PM), wakes the originating agent (assigned-to fires) and it resumes. Test the re-assign → wake.
- **AC8 (docs reconcile):** AGENT-RUNTIME §3 no longer says current-state is untouched in inline mode; #9358 workaround note updated; §8.3 table + Terminology consistent; no dangling refs.
- **AC9 (DS-audit):** high-blast-radius L1 + routing change → DS-review per [[feedback_ds_review_per_change]] + internal/cross-pair audit per prose-drift discipline before settled.
- **AC10 (installer-files.txt):** updated iff a new source file is added (likely none — in-place edits).

## Sequencing
1. **Expedite the L1 async-no-pause slice** (AC1/AC2) — skill is pausing right now; this is the urgent fix and can land using existing `pending-human-*` statuses even before full human-alias support.
2. Then the full human-as-role build (AC3–AC7) + doc reconcile (AC8) + DS-audit (AC9).
