# CONTEXT-9588 — Lazy-Load Mode-Specific Instructions at Boot

**Issue**: #9588
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1535)
**Status**: planning → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9588 is the authoritative scope for what ships. This CONTEXT-9588.md locks the design decisions surfaced by RESEARCH-9588.md and grounds them in file references. Do not redefine the ACs here; refer to the body.

---

## 1. Locked Decisions (human-approved, cycle 1535)

All 7 RESEARCH-9588.md §5 questions answered. Decisions:

### D1. Bootstrap snippet location

**Locked: new fragment** at `references/sub-skills/common/boot-bootstrap.md`. Added as the FIRST include in every role's `includes.yml` AND `includes-events.yml` manifest.

Reasoning: testability (a fragment file can be unit-tested), version-control clarity (changes show up in normal git diffs of the fragment), separation of concerns (boot-bootstrap is mechanically loaded same as any other sub-skill).

### D2. Mid-session config-change detection

**Locked: no detection mechanism.** Config flag changes take effect on next agent restart. Operator-driven, not automated.

Reasoning: flips are infrequent (event-mode flip is a deliberate operator action, possibly once per project lifetime), restart is the natural reload point, adding a `reload_mode` detection adds complexity and a new failure mode for negligible benefit.

### D3. Harness-unreachable fallback path

**Locked: ALWAYS Read polling fragment when harness is unreachable**, regardless of cursor state, regardless of whether the agent was previously in event-mode.

Reasoning: human cycle-1535 direction — "we don't trust the harness yet. Until we're very confident it doesn't break, fall back to polling." The bespoke "degraded mode" in current `l1-base.md` §3 (sleep 60s + retry `work_queue()`) is unproven and adds a third execution mode; consolidating to polling fallback simplifies the contract.

This means the `l1-base.md` §3 unreachable branch is rewritten to: "Read `references/sub-skills/roles/<role>/ralph-loop-overview.md` and follow its instructions" — exactly the same `/loop 30m execute one Ralph Loop cycle` mechanism polling agents already use.

### D4. Role-specific events fragments (e.g. DM's `pr-merge-wait.md`)

**Locked: lazy-load — uniform mechanism.** The bootstrap directive enumerates BOTH the common-events set AND the role-specific events extras.

Concretely for DM in event-mode: bootstrap tells DM to "Read common-events fragments AND Read `references/sub-skills/roles/dm/events/pr-merge-wait.md`". For roles without `events/` extras (currently pm, qa, skill), bootstrap reads only common-events.

Reasoning: uniform mechanism is easier to reason about than mixed compose-time + runtime loading. Cost of role-specific events extras is small (one extra Read per boot for DM), benefit is consistency.

### D5. Backward-compat for existing composed CLAUDE.md

**Locked: hard cutover.** One PR ships:
1. New `boot-bootstrap.md` fragment
2. `compose.py` change to stop inlining mode-specific fragments
3. Recompose all 4 roles (`pm`, `skill`, `qa`, `dm`)
4. Distribute new CLAUDE.md to each clone

No soft cutover, no deprecation warning. Live agents read the new CLAUDE.md on their next session start (cycle restart or context-pressure respawn).

Reasoning: small blast radius (4 roles, all in the same repo, agent restart is routine), no need for backward-compat machinery, simpler PR review.

### D6. Phase 6 (#8698) alignment — "remove polling entirely"

**Locked: design bootstrap with polling as a clearly separable branch.**

The bootstrap snippet uses explicit conditional structure (e.g., "If `event-driven: yes` AND harness reachable → Read event fragments. Else → Read polling fragment."). When Phase 6 deletes polling, the cleanup is: (a) remove the polling branch from `boot-bootstrap.md`, (b) delete the polling fragment files (`ralph-loop-overview.md` per role), (c) delete `includes.yml` manifests (event-mode `includes-events.yml` becomes the only manifest). Bootstrap stays.

Reasoning: small forward-compat win. The bootstrap's branching structure must be conditional today anyway (mode detection); just keep the branches lexically separable so future deletion is mechanical.

### D7. Regression test

**Locked: yes, regression test added.**

The test (under `tests/test_compose.py` or new `tests/test_boot_bootstrap.py`):
- Composes a role's CLAUDE.md.
- Asserts the composed output contains the bootstrap snippet (substring or marker check).
- Asserts the composed output does NOT contain the inlined mode-specific text — both `ralph-loop-overview.md` content and `l1-base.md` content should be referenced, not inlined.
- Verifies the referenced fragment paths exist in the repo (no broken Read targets).

Reasoning: cheap test, catches accidental re-inlining (e.g., someone re-adds the fragment to the manifest without realizing bootstrap is supposed to replace it), catches path moves.

---

## 2. Grounded File References

### 2.1 Mode detection (already exists)

- `references/scripts/compose.py:34-66` — `_get_wake_mode(role_name)`. Reads `event-driven-<role>` → `event-driven` → defaults to polling. Returns `"event-driven"` or `"polling"`. **This logic is unchanged by #9588.**
- `references/scripts/cycle_post.py:86-112` — `_get_role_wake_mode(role)`. Mirror of compose's function (kept local). Also unchanged.

### 2.2 Manifests (referenced, not modified beyond manifest list)

- `references/roles/pm/includes.yml`, `references/roles/skill/includes.yml`, `references/roles/qa/includes.yml`, `references/roles/dm/includes.yml` — polling-mode manifests. Add `common/boot-bootstrap` as the FIRST entry. Remove `roles/<role>/ralph-loop-overview` from the list (since it will be Read at runtime).
- `references/roles/pm/includes-events.yml`, etc. — event-mode manifests. Add `common/boot-bootstrap` as the FIRST entry. Remove `common-events/event-driven-workflow`, `common-events/l1-base`, `common-events/cursor-management`, `common-events/forge-read-pattern`, `common-events/idle-cooldown-loop`, `common-events/comment-handling` (all Read at runtime instead).
- For DM specifically: also remove `roles/dm/events/pr-merge-wait` from `includes-events.yml`.

### 2.3 Files referenced at runtime (NOT inlined into composed CLAUDE.md)

- `references/sub-skills/roles/<role>/ralph-loop-overview.md` — polling-mode entry, Read at runtime when in polling mode or when event-mode degraded fallback fires.
- `references/sub-skills/common-events/*.md` — event-mode fragments, Read at runtime when in event-mode + harness reachable.
- `references/sub-skills/roles/dm/events/pr-merge-wait.md` — role-specific events extra for DM, Read at runtime when in event-mode + harness reachable.

### 2.4 New file: `references/sub-skills/common/boot-bootstrap.md`

New sub-skill fragment. Compose-time inlined. Content (locked text):

```markdown
<!-- sub-skill: boot-bootstrap -->
## Boot Mode Detection (#9588)

On first invocation of this session, BEFORE any other action:

1. Read `.squidsquad/config.md` to determine wake mode.
2. Read `references/scripts/.harness-port` (relative to repo root) to check
   for a live harness port. Use `cat` or the Read tool — file present and
   non-empty = harness MAY be running; file absent = harness definitely
   not running.
3. Apply the decision tree below.

### Decision tree

- **If config has `event-driven: yes` (or per-role override) AND `.harness-port` exists AND a `curl http://localhost:<port>/status` returns 200 within 5s**:
  → You are in EVENT-DRIVEN mode. Read these files in order and follow them:
    - `references/sub-skills/common-events/event-driven-workflow.md`
    - `references/sub-skills/common-events/l1-base.md`
    - `references/sub-skills/common-events/cursor-management.md`
    - `references/sub-skills/common-events/forge-read-pattern.md`
    - `references/sub-skills/common-events/idle-cooldown-loop.md`
    - `references/sub-skills/common-events/comment-handling.md`
  - **For role `dm`** ADDITIONALLY: `references/sub-skills/roles/dm/events/pr-merge-wait.md`.

- **ELSE (event-driven is no, OR harness is unreachable, OR `.harness-port` missing)**:
  → You are in POLLING mode. Read this file and follow it:
    - `references/sub-skills/roles/<your-role>/ralph-loop-overview.md`
    (e.g. `references/sub-skills/roles/pm/ralph-loop-overview.md` for pm)

### Why the fallback to polling on harness-unreachable

Per #9580/#9588: until the harness is proven stable across all failure modes, agents fall back to polling (`/loop 30m execute one Ralph Loop cycle`) — a battle-tested mechanism that has served continuously through multiple harness outages. The bespoke event-mode "degraded mode" is removed in favor of this fallback.

The fallback applies at boot only. Once an agent has Read the polling fragment and entered `/loop`, it stays in polling until next session restart, even if the harness comes back online. Operator restarts the agent to re-enter event-mode after harness recovery.

### Loaded mode is sticky

Once you've Read the appropriate fragment(s), they ARE your instructions for this session. Do not re-check mode mid-session. Re-check happens at next agent boot.

<!-- /sub-skill: boot-bootstrap -->
```

Note: the bootstrap text must reference the role placeholder (`<your-role>`) — the composed CLAUDE.md should substitute the actual role name at compose time, OR the agent is expected to know its own role from the prior L1-L4 layers (which already identify the role in agent identity sections). Locking the latter: agent knows its role; bootstrap uses `<your-role>` literally and agent substitutes.

### 2.5 compose.py changes

- `_assemble_claude()` (line ~352 per RESEARCH-9588.md §2.1) currently resolves the manifest's include list and inlines each fragment. **Change**: when the include is `common/boot-bootstrap`, inline it normally (same as today). When the include is one of the mode-specific entries (`roles/<role>/ralph-loop-overview` OR any `common-events/*` OR `roles/<role>/events/*`), SKIP it — compose should not inline these.

This is the cleanest implementation: include lists still mention all fragments (for documentation and future restorability), but compose skips inlining the runtime-Read ones. Alternatively the manifests can be updated to remove these entries entirely; either works. Skill picks the lower-blast-radius option.

Locked: implementation strategy is at skill's discretion (manifest cleanup vs compose-level skip) as long as the compose output meets the regression test (§2.7 above and D7).

### 2.6 `l1-base.md` §3 — the unreachable branch

Today (`references/sub-skills/common-events/l1-base.md:24`): bespoke degraded-mode block describing sleep 60s + retry `work_queue()` + retry `bootup-complete` with backoff cap.

After #9588: the unreachable branch is **deleted** from l1-base.md entirely. The decision is made BEFORE l1-base is ever Read — by the bootstrap. If l1-base is being Read, the bootstrap already decided event-mode is appropriate. The unreachable branch becomes unreachable in the literal sense.

This implicitly closes #9580 — its scope is subsumed by #9588.

---

## 3. Sequencing

1. **#9574** ships first (already at pending-test) — unrelated but useful to clear from the deck.
2. **#9588 ships next** — this issue. Single PR with bootstrap fragment + compose.py change + l1-base.md trim + recompose all 4 roles + distribute composed CLAUDE.md to 4 clones.
3. **#9398 phase A subprocess fixture work** — currently in-progress on skill. May overlap with #9588; if so, skill coordinates the merges (one will need rebase).
4. **#9580** closes as superseded by #9588 (already commented).
5. **#9581** folds into #9588 — the Monitor-invocation-imperative wording lands as part of the bootstrap fragment design.
6. **Phase 6 (#8698)** is now mechanically deletable when the team is ready: remove polling branch from bootstrap, delete polling fragment files, delete polling manifests.

---

## 4. Out of Scope

- Reorganizing the L1-L4 fragment hierarchy further. Bootstrap is additive at the L1 layer.
- Renaming `ralph-loop-overview.md` or any common-events fragment. Path stays.
- Changing the polling-mode `/loop` interval or cadence semantics.
- Changing event-mode listening loop or `event_poll.py` behavior.
- Removing per-role events extras beyond DM's `pr-merge-wait.md`. None currently exist; if new ones are added by other roles, the bootstrap will need to be updated then.
- Mid-session reload mechanism — Q2 explicitly accepts restart-as-reload.

---

## 5. Acceptance (Restated from #9588 Body)

The body's ACs stand. Re-grounding here against the locked decisions:

- `compose.py` no longer inlines mode-specific fragments. Bootstrap is the only mode-relevant content in composed CLAUDE.md. ✓ per D1, D5, §2.5
- Polling-mode agents Read `ralph-loop-overview.md` on boot via the bootstrap. ✓ per D1, §2.4
- Event-mode agents: harness reachable → Read event fragments; unreachable → Read polling fragment. ✓ per D3, §2.4
- Mode flip (config.md change) takes effect on next agent cycle boundary without recompose. ✓ per D2 (restart = next boundary)
- Composed CLAUDE.md size measurably smaller — at least 30% reduction expected for event-mode roles, 5–10% for polling roles (per RESEARCH-9588.md §3 estimates).
- Regression test in `tests/test_compose.py` or `tests/test_boot_bootstrap.py` per D7.
- Existing polling agents continue cycling correctly. Existing event-mode tests in #9398 continue to pass once bootstrap lands.

---

## 6. Open Questions Resolved

All 7 from RESEARCH-9588.md §5 are now locked (D1–D7). No open questions remain for skill at pickup. If skill encounters implementation ambiguity, comment for PM clarification rather than deviate.

---

## 7. Risk Notes (for skill at pickup)

1. **Bootstrap directive must be unambiguous.** Same risk class as #9574/#9581. Use imperative wording; pin the Read targets by exact path; add the regression test (D7) to catch accidental drift.
2. **The harness reachability check via curl is a new bootstrap step.** If curl fails or takes longer than expected, the agent may incorrectly enter polling mode when event mode is actually available. Mitigation: 5-second timeout is tight enough that operator notices via tracker comments if mistakes happen, and restart resolves them.
3. **The bootstrap is loaded into agent's initial context.** Increases first-message context cost by ~25 lines. Acceptable.
4. **Migration affects 4 clones.** If anything goes wrong with compose.py changes, all four roles regress simultaneously. Mitigation: ship behind a feature flag (config field) OR do per-role rollout. Skill picks; locked: skill discretion.

---

## 8. Next Step

PM transitions #9588 status:planning → status:planned. Human reviews this CONTEXT-9588.md + the locked decisions. On explicit human approval, PM transitions planned → approved. Then skill picks up.
