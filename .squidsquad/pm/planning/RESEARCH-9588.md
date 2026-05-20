# RESEARCH-9588 — Lazy-Load Mode-Specific Instructions at Boot

**Issue**: #9588
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-20 (cycle 1535)

---

## 1. Question

Replace `compose.py` deploy-time inlining of mode-specific (polling vs event-driven) instruction fragments with a **boot-time read** that lets the agent load the right instructions based on the live `config.md` flag. The same mechanism should provide the harness-down fallback for event-mode agents (per cycle-1535 human direction: "fallback to /loop polling, don't run a bespoke degraded mode").

---

## 2. Current Architecture (Grounded)

### 2.1 Compose-time mode detection

`references/scripts/compose.py:34-66` (`_get_wake_mode`) reads two fields from `config.md` with this precedence:

1. `event-driven-<role>` — per-role override (e.g. `event-driven-skill: yes`)
2. `event-driven` — global default
3. Implicit default: `polling`

Returns `"event-driven"` or `"polling"`. The function is mirrored in `cycle_post.py:86-112` (`_get_role_wake_mode`) — same precedence, kept local "to avoid pulling in compose.py just for one read at post-cycle time."

### 2.2 Manifest selection

`compose.py:189`:
```python
primary_name = "includes-events.yml" if wake_mode == "event-driven" else "includes.yml"
fallback_name = "includes.yml"  # used when event-driven manifest absent
```

Each role has TWO manifests under `references/roles/<role>/`:
- `includes.yml` — polling-mode fragment list
- `includes-events.yml` — event-mode fragment list

### 2.3 Mode-specific fragment surface

**Polling-mode entry fragment** (in each role's `includes.yml`):
- `roles/pm/ralph-loop-overview.md` — 53 lines
- `roles/skill/ralph-loop-overview.md` — 47 lines (via dev manifest)
- `roles/qa/ralph-loop-overview.md` — 50 lines
- `roles/dm/ralph-loop-overview.md` — 47 lines

**Event-mode entry + support fragments** (`common-events/*`, in each role's `includes-events.yml`):
- `event-driven-workflow.md` — 30 lines (orientation page, references the others via `[[wikilinks]]`)
- `l1-base.md` — 105 lines (boot sequence Case A–E, working-state ownership)
- `cursor-management.md` — 34 lines
- `forge-read-pattern.md` — 29 lines
- `idle-cooldown-loop.md` — 52 lines
- `comment-handling.md` — 29 lines

**Total: 279 lines** of common-events + **role-specific events extras** (e.g. `roles/dm/events/pr-merge-wait.md`).

### 2.4 Stated constraint (existing)

Per `includes-events.yml` comments: *"parallel manifests, no mode-conditional logic inside fragments."* The current design pushes mode-conditionals to the manifest layer (compose-time decision) rather than embedding them in fragment text. The lazy-load approach respects this — mode detection happens once at boot, the fragment loaded is unconditional.

### 2.5 Current composed CLAUDE.md sizes

Measured from clones at cycle 1535:
- pm: 1939 lines
- skill: 1441 lines
- qa: 1256 lines
- dm: 1101 lines

### 2.6 Mode-change today requires recompose

Today, flipping `config.md` `event-driven: yes` requires running `python references/scripts/compose.py deploy <role>` for each role and distributing the resulting CLAUDE.md to that role's clone. Until then, agents still operate with their compose-time-baked instructions.

### 2.7 Runtime fragment-read precedent

No current CLAUDE.md instructs an agent to `Read references/sub-skills/<fragment>` at runtime. Agents DO read files at runtime constantly: `tracker.py` source when debugging, planning artifacts during cycles, vault notes, etc. New pattern is consistent with existing behavior — not unprecedented.

### 2.8 Per-role events extras

`references/sub-skills/roles/dm/events/pr-merge-wait.md` exists — DM has a role-specific event fragment beyond the common ones. Any lazy-load scheme must handle the "load common-events + load role-specific events" case, not just the common set.

---

## 3. Size Impact (Order-of-Magnitude Estimate)

**Lazy-loading just the polling fragment** (current default):
- Per role: removes 47–53 lines (3% of pm, 5% of qa).
- Marginal benefit — these fragments are small.

**Lazy-loading just the event fragments** (when event-mode flips):
- Per role: removes ~279 lines (15% of pm, 22% of qa).
- Meaningful benefit — event-mode composed CLAUDE.md is meaningfully larger today.

**Lazy-loading BOTH** (universal mechanism):
- Per role: removes 326–332 lines (~17% of pm).
- The bootstrap snippet itself adds ~20 lines back.
- **Net savings: ~310 lines per role**, ~17% reduction.

This is real but not transformative. The bigger value is **architectural cleanliness**: one source of truth per mode, mode flips without recompose, degraded-mode fallback uses the same mechanism.

---

## 4. Options Surveyed

### Option A — Lazy-load both modes (the proposed approach)

`compose.py` emits a small bootstrap snippet that reads `config.md` and tells the agent to Read the appropriate fragment(s). Polling fragment stays under `roles/<role>/ralph-loop-overview.md`; event fragments stay under `common-events/`. compose.py no longer inlines either.

**Pros**:
- Mode flip = config change + agent restart. No recompose.
- Single source of truth per mode (the fragment file).
- Degraded-mode fallback in event mode is the same mechanism (just Read the polling fragment when harness is unreachable).
- Composed CLAUDE.md ~17% smaller across the board.

**Cons**:
- New runtime-Read pattern. Bootstrap directive must be unambiguous (same prompt-following risk as #9581).
- Adds one file read per fresh agent session.
- compose.py must change in both modes (existing tests assume mode-specific inline).
- Migration touches all four roles + their clones.

### Option B — Lazy-load event mode only (status quo for polling)

Keep `compose.py` inlining `ralph-loop-overview.md` for polling roles (default). Switch only event-mode to lazy-load. Bootstrap snippet appears only when role is event-mode.

**Pros**:
- Smaller blast radius. Polling agents (today's default) unchanged.
- Still gets the degraded-mode-via-Read benefit.
- Event-mode flip cleanup is the win, polling-mode is untouched.

**Cons**:
- Two mechanisms (compose-inline vs runtime-Read) coexist — harder to reason about.
- Doesn't satisfy the broader "uniform mode-loading" architectural intent.
- Phase 6 (#8698, planned) wants to remove polling entirely — so the inlining would just get deleted later anyway.

### Option C — Inline both modes always

Always include both polling AND event fragments in composed CLAUDE.md. Bootstrap snippet at runtime decides which to follow.

**Pros**:
- No new runtime-Read pattern.
- Mode flip is instant (already loaded both).

**Cons**:
- Composed CLAUDE.md ~17% LARGER, not smaller — opposite of intent.
- Two contradictory instruction sets in the same file invites LLM confusion.
- Conflicts with stated constraint "no mode-conditional logic inside fragments" since the bootstrap snippet IS that conditional.

### Option D — Status quo (recompose-on-flip)

Keep current `compose.py` deploy-time inlining. Flip = recompose + redistribute. No lazy-load.

**Pros**:
- Zero migration effort.
- Mode-specific text is in the CLAUDE.md the agent reads — minimal indirection.

**Cons**:
- Mode flip requires deploy step in 4 clones.
- Doesn't address the cycle-1535 human requirement: degraded-mode-as-/loop without inlining polling fragment in event-mode CLAUDE.md.
- The "supersede" of #9580 only makes sense with lazy-load — without it, #9580's inline-fallback was the answer.

### Recommendation

**Option A** with phased migration. The decisive factor is the cycle-1535 requirement: degraded-mode fallback should be /loop polling, and the simplest way to provide that without doubling CLAUDE.md size is to read the polling fragment on demand. Option B is acceptable as a stepping stone if Option A's blast radius is concerning, but the destination is Option A.

---

## 5. Open Questions for CONTEXT (Phase 2)

1. **Where does the bootstrap snippet live?**
   - Option: new `common/boot-bootstrap.md` fragment at the very top of every manifest.
   - Option: extend the L1 base prefix in `compose.py:_assemble_claude` to emit the bootstrap directly (no fragment file).
   - Recommendation: separate fragment for testability and version-control clarity.

2. **How does the agent detect mid-session config change?**
   - Option: re-check on every cycle boundary in `cycle_post.py` and emit a `reload_mode` signal that triggers agent restart.
   - Option: accept "config change takes effect next cycle" semantics; no detection mechanism.
   - Recommendation: accept the semantics. Mode flips are operator-driven and infrequent; restart is the natural reload mechanism.

3. **How does the agent fall back from event-mode to polling on harness-unreachable?**
   - Option: at boot, if `event-driven` is yes BUT harness is unreachable AND no cursor exists, Read polling fragment immediately. If cursor exists, use the current event-mode degraded path (degraded-mode in l1-base.md §3).
   - Recommendation: ALWAYS Read polling fragment when harness is unreachable — even with a cursor. Per cycle-1535 human direction: "until we're very confident the harness doesn't break it, fall back to polling."

4. **What about role-specific events fragments (e.g. DM's `pr-merge-wait.md`)?**
   - Option: bootstrap directive enumerates known role-specific events fragments per role.
   - Option: role-specific events stay compose-inlined since they're small; only common-events are lazy-loaded.
   - Recommendation: lazy-load both. The bootstrap snippet for DM would say "Read common-events fragments AND `roles/dm/events/*.md`."

5. **Backward-compat — do existing composed CLAUDE.md files break?**
   - Option: hard cutover. Recompose all 4 roles. Old CLAUDE.md in clones overwritten.
   - Option: emit a deprecation marker in compose.py output that warns operators they're on an old composition.
   - Recommendation: hard cutover. Migration is one PR + four `compose.py deploy` calls.

6. **What about Phase 6 (#8698) which removes polling entirely?**
   - Option: design the bootstrap so the polling branch can be deleted without restructuring.
   - Recommendation: yes — the bootstrap should treat polling as a clear separate branch, not interleaved with event-mode logic. Deletion = remove the polling branch + the polling fragment files.

7. **Does the bootstrap directive need a regression test?**
   - Option: regression test asserts compose.py output contains the bootstrap and NOT the inlined fragment text.
   - Recommendation: yes. Easy to add, catches accidental re-inlining.

---

## 6. Dependencies

- `references/scripts/compose.py` — `_get_wake_mode` already exists; `_assemble_claude` will need to skip mode-specific includes and emit the bootstrap snippet instead.
- `references/sub-skills/common-events/l1-base.md` §3 — the existing degraded-mode block needs to be rewritten to reference the polling fragment.
- `references/sub-skills/common/boot-bootstrap.md` (new) — the bootstrap snippet itself.
- `references/roles/<role>/includes.yml` and `includes-events.yml` — manifests may stay as-is (compose.py reads them to know which fragments to lazy-reference, but doesn't inline them).
- Tests under `tests/test_compose.py` — likely need updates to assert the new compose output shape.
- Tests under `tests/test_compose_events.py` (if exists) — same.

## 7. Non-Goals

- Reorganizing the L1–L4 fragment hierarchy further. The bootstrap is additive; fragments stay where they are.
- Renaming `ralph-loop-overview.md` or any common-events fragment.
- Changing the polling-mode `/loop` interval or cadence semantics.
- Changing event-mode listening loop or `event_poll.py` behavior.
- Removing per-role events extras (e.g. DM's pr-merge-wait) — they stay role-scoped.

## 8. Risks

1. **Bootstrap directive is mis-followed by the agent** — same risk class as #9574 (CQ runner Write skipped) and #9581 (Monitor wording). Mitigation: imperative wording + regression test in #9398's subprocess fixture.
2. **Fragment file moves or renames break runtime Read** — mitigation: regression test that asserts the referenced paths exist after compose.
3. **First fresh session is slow** (one extra file read) — negligible cost, not worth mitigating.
4. **Mode-flip race**: operator flips config mid-cycle; agent finishes the cycle on old mode then restarts. Acceptable — flips are infrequent and cycle boundary is the natural restart point.
5. **Migration regression**: existing event-mode tests (#9398 in-flight work) may assume compose-inlined event fragments. Mitigation: update those tests as part of the #9588 PR, before #9398 lands its subprocess tests.

## 9. Next Step

Write **CONTEXT-9588.md** locking the decisions from §5 above, then transition #9588 to status:planned and present plan to human for approval. **No code changes until human gates approved.**
