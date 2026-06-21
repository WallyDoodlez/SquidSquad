---
type: pattern
tags: [dm, delivery, compose, reboot, sub-skills, ship-gate]
created: 2026-06-18
updated: 2026-06-18
owner: dm-lead
status: active
confidence: high
source: observation
links: [pattern-verify-composed-output-with-main-landing-state-applied, learning-l4-only-fix-skips-pr-flow]
---

## Context

Shipping #12506 (event-mode periodic driver). The PR rewrote `idle-cooldown-loop.md` (a sub-skill) plus
added a new runtime script. The DM "template changes require reboots / recompose" rule made it look like a
`compose.py deploy` + forced reboot ship. But `idle-cooldown-loop.md` lives in `references/sub-skills/common-events/`,
which the catalog marks **runtime-loaded by boot-bootstrap (Read at agent boot), NOT inlined into the composed
`.squidsquad/<role>/CLAUDE.md`**. So no composed output changed → recompose would be a no-op.

## Content

**At the DM package/reboot step, classify a changed sub-skill by HOW it reaches the agent before deciding recompose+reboot:**

- **Inlined** (`common/`, `roles/<role>/`) — compose stitches it into `.squidsquad/<role>/CLAUDE.md` via the role's
  `includes.yml`. A change here **requires `compose.py deploy <role>`** to land in composed output, **and** an agent
  restart to read the new CLAUDE.md. This is the classic "template change → recompose + reboot" path.
- **Runtime-loaded** (`common-events/`, and any fragment the agent Reads at boot via `boot-bootstrap`, e.g. the
  event-mode contract fragments) — NOT inlined; the agent Reads the source file fresh at each boot. A change here
  **needs NO `compose.py deploy`** (composed CLAUDE.md is byte-identical) and is picked up at the agent's **next
  restart's pull** — same as the runtime-loaded `→ run sub-skill` markers (cf. #12750 task-intake/task-pickup).

Practical consequence for the ship: a runtime-loaded sub-skill change **folds into the pending team-reboot window**
rather than forcing an immediate reboot. Confirm the no-recompose call with a fact, not memory: grep the role
`includes.yml` for the filename (absent ⇒ runtime-loaded) or check the catalog's `common-events/` table. Until agents
restart, currently-running sessions keep executing the OLD fragment — note that explicitly in the ship comment if the
fix's behavior matters to live sessions (e.g. #12506's idle-scan dormancy still affects running agents until they reboot).

See also [[pattern-verify-composed-output-with-main-landing-state-applied]] (the inlined/composed-output side).
