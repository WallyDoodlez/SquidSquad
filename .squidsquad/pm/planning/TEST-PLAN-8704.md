# TEST-PLAN-8704 — Harness TUI Surfaces Human-Assigned Work

## Overview

Phase 5 task that adds a new harness HTTP endpoint plus a TUI panel surfacing any issue in a `pending-human-*` status, so humans can see and act on assigned work without polling the forge. HITL is treated as ordinary role assignment — any agent may transition an item to `pending-human-*`, and the queue shows everything regardless of which role transitioned it (CONTEXT.md §3.8, §5.6, §11 "HITL transition").

The endpoint and panel are co-resident with #8700's status-line panel in the same harness-served TUI process, sharing the harness HTTP base URL and a single delayed refresh cadence (CONTEXT.md §5.7).

**Zero-gap gate**: any TC failure routes the task back to dev. No "noted for follow-up" exceptions.

**Co-ship**: ships together with #8700 (shared TUI architecture). Hard prereq: #8692 singleton enforcement (CONTEXT.md §6.1).

---

## 1. Acceptance Criteria

Verbatim from CONTEXT.md §5.6 plus measurable refinements:

- **AC1** — `GET /human/queue` returns all open issues with any `status:pending-human-*` label, regardless of role (CONTEXT.md §5.6 Acceptance).
- **AC2** — Results are ordered by priority (`priority:high` → `priority:medium` → `priority:low`), then by age oldest-first within each priority bucket (Issue #8704 body, "ordered by priority and age").
- **AC3** — Each returned item exposes at minimum: issue number, title, role that transitioned to human, status label, priority label, and the timestamp of transition into `pending-human-*` (CONTEXT.md §5.6 Deliverables, panel renders).
- **AC4** — Endpoint result is cached briefly (5–10s) inside the harness to avoid hammering the forge (CONTEXT.md §5.6 Deliverables).
- **AC5** — TUI human-queue panel reads `GET /human/queue` on the shared delayed refresh loop and renders a non-zero badge whenever ≥1 item is pending-human; renders `0` (or equivalent empty affordance) when none are pending (CONTEXT.md §5.6 Acceptance, §5.7).
- **AC6** — TUI panel lists items with number, title, role-that-transitioned, transition timestamp (CONTEXT.md §5.6 Deliverables).
- **AC7** — HITL is role-agnostic. Any role (`skill`, `qa`, `dm`, `designer`, future roles) emitting a `pending-human-*` transition surfaces in the queue with no role-specific code paths (CONTEXT.md §3.8, §5.6 Deliverables).
- **AC8** — Future `pending-human-*` variants (e.g., a new `pending-human-decision` label introduced later) are picked up automatically without code changes — implementation filters by label prefix, not a hardcoded list (CONTEXT.md §5.6 Acceptance "regardless of role" generalised across `pending-human-*`).
- **AC9** — Any designer-loop special-casing currently in the codebase is removed (CONTEXT.md §5.6 Acceptance bullet 3).
- **AC10** — Status-line panel (#8700) and human-queue panel coexist in a single TUI process, sharing harness base URL (resolved from `.squidsquad/.harness-port`) and refresh cadence (2–5s) (CONTEXT.md §5.7).
- **AC11** — When a human acts on an item via the forge (status transitions out of `pending-human-*`), the item disappears from `GET /human/queue` and from the TUI panel within one refresh interval (Issue #8704 body, "resulting status transition flows back through the normal event stream").
- **AC12** — Backward compatibility: existing per-issue notification surfaces (Discussion comments, email-on-mention) continue to function alongside the new queue (Issue #8704 body, "Backward compatibility").

---

## 2. Test Categories Map

| Section | Category                       | Count |
|---------|--------------------------------|-------|
| §3      | Unit — endpoint + panel format | 6     |
| §4      | Integration — end-to-end       | 5     |
| §5      | Negative                       | 4     |
| §6      | TUI cross-task (#8700)         | 3     |
| §7      | Manual smoke                   | 3     |

---

## 3. Unit Tests

### TC-U1: GET /human/queue returns items with any pending-human-* status label

- **Precondition**: Harness running; tracker contains seeded open issues — one `status:pending-human-review`, one `status:pending-human-setup`, and one not in pending-human-* (control).
- **Steps**: `curl -s http://localhost:<PORT>/human/queue` and parse JSON.
- **Expected**: Response contains exactly the two `pending-human-*` items; the control item is absent.
- **Verification**: `python -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://localhost:<PORT>/human/queue')); nums=sorted(i['number'] for i in d); assert nums==[<rev>,<setup>], nums; print('PASS')"`

### TC-U2: Items ordered by priority then age

- **Precondition**: Seed five `pending-human-*` issues with mixed priority and `updatedAt` / transition timestamps: A=high/oldest, B=high/newest, C=medium/old, D=medium/newer, E=low/any.
- **Steps**: Query the endpoint, capture order.
- **Expected**: Order is `[A, B, C, D, E]` — high → medium → low; within each bucket, oldest first.
- **Verification**: Assert returned list matches the expected sequence; fail if any pair is mis-ordered.

### TC-U3: Empty queue returns empty list

- **Precondition**: No open issue carries any `status:pending-human-*` label.
- **Steps**: Query the endpoint.
- **Expected**: HTTP 200 with body `[]` (or `{"items": []}` — match implementation). No `null`, no 404.
- **Verification**: `curl -s -o body -w '%{http_code}' http://localhost:<PORT>/human/queue` returns `200` and body parses to an empty list.

### TC-U4: Future pending-human-* variants are included automatically

- **Precondition**: Create a fresh, never-before-seen label `status:pending-human-decision` on an open issue. No code change to the harness between server start and this step.
- **Steps**: Query the endpoint.
- **Expected**: The issue appears in the result. No hardcoded enumeration of `pending-human-review` / `pending-human-setup` is required — filter is prefix-based (AC8).
- **Verification**: Returned items include the issue number. Inspect `harness.py` source to confirm the filter is `status:pending-human-*` (prefix / glob), not a hardcoded list — fail if a literal list is found.

### TC-U5: Cached briefly to avoid hammering the forge

- **Precondition**: Harness instrumented (or use a tracker mock) to count outbound `gh issue list` calls.
- **Steps**: Issue 10 consecutive `GET /human/queue` calls within 5 seconds.
- **Expected**: At most 1 underlying tracker query is fired (cache window 5–10s per AC4).
- **Verification**: Counter reads ≤1 outbound call across the 10 requests.

### TC-U6: TUI panel badge count formatting

- **Precondition**: Mock endpoint returns 0, 1, and 7 items in three separate panel renders.
- **Steps**: Render the panel with each mock payload.
- **Expected**: Badge displays `0` (or empty affordance) when zero; integer count otherwise — `1`, `7` — no thousands separators on small numbers; no `null`/`undefined`/`NaN` ever surfaces.
- **Verification**: String comparison against rendered output for each of the three cases.

---

## 4. Integration Tests

### TC-I1: End-to-end agent transition → endpoint → TUI panel

- **Precondition**: Harness + tracker live. A test issue exists at `status:in-progress` assigned to one role (e.g., `skill`).
- **Steps**:
  1. Have the role transition the issue to `pending-human-review` via `tracker.py transition`.
  2. Wait one refresh interval (≤5s per CONTEXT.md §5.7 cadence).
  3. Query `GET /human/queue`.
  4. Inspect TUI human-queue panel content.
- **Expected**: Item appears in both the endpoint response and the TUI panel within the refresh interval. Role-that-transitioned is shown as `skill`.
- **Verification**: Issue number present in JSON response; panel screenshot (or text capture) lists the issue with role `skill` and a transition timestamp.

### TC-I2: Human resolves via forge → next refresh removes from queue

- **Precondition**: TC-I1 item is visible in the queue.
- **Steps**:
  1. Human acts via forge: transition the item from `pending-human-review` → `in-progress` (or `pending-ship`).
  2. Wait one refresh interval + cache window (max ~15s).
  3. Re-query endpoint; re-inspect TUI panel.
- **Expected**: Item is gone from both surfaces. No stale entry.
- **Verification**: Item number absent in JSON; panel no longer renders it.

### TC-I3: Multiple agents transitioning multiple items all appear

- **Precondition**: Three issues, each assigned to a different role (`skill`, `qa`, `dm`), all at `in-progress`.
- **Steps**: Each role transitions its issue to `pending-human-review` (or `pending-human-setup`) in rapid succession (within one refresh interval).
- **Expected**: All three items appear in a single queue response; correct role attribution per item; ordering by priority/age (AC2).
- **Verification**: JSON contains all three issue numbers; per-item `role` field matches the transitioning role.

### TC-I4: Items from different roles all surface — no role filtering

- **Precondition**: Active dev agents in `config.md` include at minimum `skill`, `qa`. Seed one `pending-human-*` issue per active role.
- **Steps**: Query endpoint.
- **Expected**: Every seeded item is present. No role is silently filtered out. Designer role items appear if a `designer` agent transitioned one (CONTEXT.md §3.8 — designer is just another worker).
- **Verification**: For each active role with a seeded item, the item appears in the response.

### TC-I5: Both pending-human-review AND pending-human-setup appear

- **Precondition**: One issue at `status:pending-human-review`, one at `status:pending-human-setup`, both open.
- **Steps**: Query endpoint.
- **Expected**: Both items are present. Each item's `status` field reflects its actual label.
- **Verification**: Result length ≥ 2; both labels represented in the result set.

---

## 5. Negative Tests

### TC-N1: Items NOT in pending-human-* status are excluded

- **Precondition**: Seed issues at every other status (`approved`, `in-progress`, `pending-test`, `pending-ship`, `planning`, `planned`, `pending`, `open`).
- **Steps**: Query endpoint.
- **Expected**: None of the seeded non-`pending-human-*` items are in the response.
- **Verification**: Assert response is empty (assuming no other pending-human issues exist in fixture).

### TC-N2: `design:needed` label without pending-human status is NOT surfaced

- **Precondition**: One issue with `design:needed` + `status:in-progress`. Per CONTEXT.md §3.8, design labels are metadata only (Phase 6 retirement candidate).
- **Steps**: Query endpoint.
- **Expected**: Item is NOT in the queue. Design labels do not gain special routing.
- **Verification**: Issue number absent from response.

### TC-N3: Closed items are excluded

- **Precondition**: One issue at `status:pending-human-review` but state `closed` (e.g., closed manually after a misfile).
- **Steps**: Query endpoint.
- **Expected**: Closed item is not returned. Query is scoped to `--state open` only.
- **Verification**: Issue number absent; inspect `harness.py` / `tracker.py` invocation to confirm `--state open` filter.

### TC-N4: Already-resolved items do not reappear on next refresh

- **Precondition**: Item was in the queue; human transitioned it out; cache has not yet expired.
- **Steps**: Wait for cache window to elapse (≥10s per AC4), then query again.
- **Expected**: Item stays absent. No flap, no resurrection from stale cache.
- **Verification**: Two consecutive queries spaced beyond the cache window both omit the item.

---

## 6. TUI Integration (cross-task with #8700)

### TC-T1: Status-line panel + human-queue panel coexist in same TUI process

- **Precondition**: TUI launched; both #8700 status line and #8704 human-queue panels enabled.
- **Steps**: Start the TUI; observe both panels render.
- **Expected**: A single process hosts both panels. No second TUI / no second display surface (CONTEXT.md §5.7 "one TUI process").
- **Verification**: Process listing shows one TUI binary; both panels visible in the same terminal.

### TC-T2: Shared refresh loop drives both panels at the same cadence

- **Precondition**: Instrument the TUI's refresh tick (log timestamps).
- **Steps**: Capture 10 refresh ticks; observe both panel data fetches.
- **Expected**: Each tick triggers a fetch for both panels at the same cadence (2–5s, CONTEXT.md §5.7). No independent timers per panel.
- **Verification**: Tick log shows paired fetches with the same tick id / timestamp.

### TC-T3: TUI handles harness unreachable gracefully for both panels

- **Precondition**: TUI running with both panels. Harness reachable.
- **Steps**: Stop the harness mid-session (`start_team.py --stop` for harness, or kill the harness process). Observe both panels for ≥2 refresh intervals. Restart harness; observe recovery.
- **Expected**: Neither panel crashes the TUI. Both display an "unreachable" / stale-data affordance during the outage. Both recover on the next successful fetch after harness restart.
- **Verification**: TUI process stays alive; both panels render a degraded state during outage and refreshed data after recovery.

---

## 7. Manual Smoke Tests

- **SM-1**: File a fresh issue, transition it to `pending-human-review`. Observe it appears in the TUI human-queue panel within one refresh interval. Confirm the badge count increments.
- **SM-2**: Resolve the SM-1 item from the forge (transition out of `pending-human-*`). Observe it disappears from the TUI panel within one refresh interval. Badge count decrements.
- **SM-3**: File three items with mixed priorities (`high`, `medium`, `low`) and stagger their transition timestamps. Observe TUI panel orders them by priority then age (oldest first within each bucket).

---

## 8. Gating Conditions

- **Co-ships with #8700** — shared TUI architecture (CONTEXT.md §5.7). Neither lands without the other.
- **Hard prereq**: #8692 singleton enforcement is shipped (CONTEXT.md §6.1). Without it, multiple harness or agent instances race on event handling and can produce duplicate / inconsistent queue state.
- **Standard plan-checker gate**: planning artifacts (RESEARCH.md if applicable, CONTEXT.md ref §5.6, this TEST-PLAN) reviewed via draft PR.
- **Human approval gate**: explicit human "go" required before status moves from `planned` → `approved` (PM CLAUDE.md Task Approval Gate).

---

## 9. Post-Ship Validation

- **PSV-1** — After ship: agents handing off to humans via any `pending-human-*` transition are visible to operators without polling the forge. Confirmed by SM-1 / SM-2 reproduction on the shipped build.
- **PSV-2** — Designer workflow (if/when designer role is active per `config.md`): designer transitions work to `pending-human-review` (or a future `pending-design` variant). Human sees the item in the queue with role `designer` attribution. Confirms AC7 (role-agnostic) holds in production.
- **PSV-3** — Soak: across N (≥10) real human handoffs over a week, the queue accurately tracks all transitions — no stale entries, no missed transitions. Confirms AC11 (timely removal) and AC4 (cache correctness) under real usage.

---

## 10. Open Questions / Gaps

These are not blockers for filing the test plan, but the dev pickup should resolve them or surface them on the issue before implementation lands.

- **Q1 — Refresh cadence exact value**: CONTEXT.md §5.7 says 2–5s; this plan assumes ≤5s for "within one refresh interval" checks. Dev should lock the exact value (probably matching #8700's choice) and document it on the issue.
- **Q2 — Transition timestamp source**: AC3 / AC6 require a "timestamp of transition into `pending-human-*`". Source options: (a) issue `updatedAt`, (b) the label's `created_at` from `gh issue view --json labels` (not always available), (c) parse from Discussion comment audit trail. Dev to pick and document.
- **Q3 — Response shape**: list (`[...]`) vs object wrapper (`{"items": [...]}`). Tests are written to tolerate either; dev should pick a shape and align with #8700's endpoint convention for consistency.
- **Q4 — Designer-loop special-case removal scope**: AC9 says any existing designer-loop special-case code is removed. Dev to grep the codebase for `design:needed` / `designer-loop` branching and confirm what (if anything) needs deletion in this task vs Phase 6 (#8698 cleanup).
- **Q5 — Pagination**: not in scope per Issue #8704 non-goals, but if pending-human count ever exceeds (say) 50, does the panel truncate, scroll, or page? Capture as a follow-up if it surfaces during soak (PSV-3).
- **Q6 — Cache invalidation on event**: AC4 specifies a 5–10s cache. If a `status_transition` event fires for a `pending-human-*` label, should the cache be invalidated immediately to keep the panel snappy? Not required by the AC, but worth a dev discretion note.

---

## 11. Citations

- CONTEXT.md §3.8 — HITL is ordinary role assignment, `design:*` labels are metadata only.
- CONTEXT.md §5.6 — #8704 scope, deliverables, files touched, acceptance criteria.
- CONTEXT.md §5.7 — TUI / status surface architecture (shared process, base URL, cadence).
- CONTEXT.md §6.1 — #8692 singleton enforcement (hard prereq).
- CONTEXT.md §11 glossary — "TUI", "HITL transition".
- Issue #8704 body — endpoint shape, ordering, refresh interval (default 5s), backward-compat with Discussion/email-on-mention.
