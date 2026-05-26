**Reported By**: pm-lead
**Priority**: Low
**Status**: ON HOLD — do not pick up until explicitly approved

**Parent**: spawned from PR #10004 (docs/VAULT-ARCH.md + docs/AGENT-RUNTIME.md polish, currently in review).

### Why this is on hold

The architectural decisions captured in PR #10004 are the contract for this task. **Do not start implementation until PR #10004 has merged** and you have read both docs end-to-end. Picking this up earlier risks chasing a moving target.

### Scope (7 coordinated changes, bundled because they touch overlapping code)

This is one bundled task — split commits per concern internally, but ship as one PR. Bundling because several items touch `config.md`, `cycle_pre.py`, `cycle_post.py`, and the harness in overlapping ways; splitting into 7 PRs would create rebase pain.

**1. Retire 4 `Enabled` flags from `config.md`** (vault-remember, vault-optimize, improvement-scanning, cycle-runner)

- Drop the `- **Enabled**: yes` line under each of those 4 `##` sections in `config.md` and template defaults
- Drop the corresponding `config.py get <slug>` calls and any skip-if-no paths in sub-skill sources (`references/sub-skills/common/vault-remember.md`, `vault-optimize.md`, `improvement-scan.md`, the cycle-runner fragment)
- Drop the flag-read in `cycle_pre.py:539-540` (vault-remember + vault-optimize)
- Update wizard defaults to not write these fields
- Rationale: all 4 sub-skills already self-gate via deterministic per-cycle conditions; the on/off toggles add no use case. See VAULT-ARCH.md §7.2/§7.3 Cycle integration lines + §9.2.

**2. Mode-aware event-bus consumption in cycle scripts**

- `cycle_pre.py`: when running in loop mode (`config.md` `event-driven: no`), skip the `GET /events/for/<role>?since=cursor` call entirely. Derive mechanical reactions from tracker state changes since last cycle instead (see #3 below).
- `cycle_post.py`: when running in loop mode, skip the event-cursor advance.
- New tracker-state dedup mechanism: persist a `last-cycle-timestamp` field in `working-state.md`; loop-mode mechanical reactions compare `gh pr list` / `gh issue list` results against this timestamp.
- Loop mode must remain free to emit transient events (observability); only consumption + cursor are gated.
- Rationale: loop/event-bus mutual exclusivity per AGENT-RUNTIME.md §2 + §6 + §4.5/§4.6. Loop = emit-only; event = emit + consume.

**3. Rename `qa-rejected` → `verifier-rejected` across emitters**

- `references/scripts/triage.py`: rename `qa-rejected` subcommand to `verifier-rejected`. Update all internal references.
- `references/scripts/cycle_pre.py:614`: update the `_run_script("triage.py", "qa-rejected", ...)` call.
- Any other `qa-rejected` string emitters anywhere in the codebase (grep `qa-rejected` to confirm scope).
- Post-#6274 rename completion. Doc already describes target.

**4. Drop `responsibility.md` files and compose-pipeline reads**

- Delete `references/roles/*/responsibility.md` (and `references/sub-skills/.../responsibility.md` if any)
- Drop `compose.py` reads of `responsibility.md`
- Drop the harness boot read of composed `responsibility.md` files (see #5 below)
- Drop `responsibility.md` from `installer-files.txt`
- Rationale: prose was ~90% L2/L3-duplicated; `## Bus contract` section becomes irrelevant after #5. See decision-class-vs-alias-routing-model in vault galaxy.

**5. Drop harness permission-table; replace with alias-existence check**

- Harness: drop the `accepts assigned-to from: [list]` permission-table build at boot.
- Replace with: on `POST /work/assign`, validate `target_alias` exists in `config.md` `## Aliases` registry. Return `HTTP 404 Not Found` with body `{"error": "unknown alias", "target_alias": "<value>", "known_aliases": [...]}` if unknown.
- Preserve the self-assign invariant (`target_alias == emitter_alias` → 4xx). This is structural, not permission.
- Drop `HTTP 403 Forbidden` response shape entirely (no class-from-class denials anymore).
- Rationale: process discipline lives in L2/L3/L4; harness is a transport bus, not an orchestrator. Mis-route recovery happens at agent layer via re-`/work/assign`. See AGENT-RUNTIME.md §7.3 + decision-class-vs-alias-routing-model.

**6. Rename `target_role` field → `target_alias` in all wire-format emitters**

- Grep `target_role` across `references/scripts/` and the harness — every emitter of `assigned-to` events, every `/work/assign` POST body, every care-filter consumer.
- Field name change is the same byte-by-byte everywhere — automated find/replace works, but verify cascade (event payload schemas, tests, fixtures).
- Update `cycle_pre.py` care-filter code to compare `target_alias` against `my_alias` (agent's own alias from `config.md` or env).
- Update tests under `tests/` that reference `target_role`.

**7. Rename `tracker.py work-assign --target` CLI flag → `--target-alias`**

- `references/scripts/tracker.py`: rename the `--target` argument to `--target-alias` in the `work-assign` subcommand.
- Update any call sites (sub-skill sources, docs that show CLI examples).
- Keep `--target` as a deprecated alias for one release to avoid breaking in-flight scripts? Decide as you implement.

### Out of scope (filed separately)

- `vault_optimize.py` reindex code-path removal — already filed as #10179.
- `vault_optimize.py` STALE_DAYS config wiring — already filed as #10099.
- `vault_check.py` + 34-note migration for §4.3 frontmatter changes — already filed as #10098.
- Knowledge-tree integrity CI/CD for vault note renames — already filed as #10100.
- Sub-skill-catalog reconciliation — already filed as #10178 (deferred until arch implementation completes).

### Acceptance

- All 4 `Enabled` flags absent from `config.md` and wizard defaults; `config.py get vault-remember` and `config.py get vault-optimize` calls absent from any sub-skill source or script
- `cycle_pre.py` in loop mode: zero `GET /events/for/` calls (verify with strace or log inspection); reactions derived from tracker timestamp dedup
- `cycle_post.py` in loop mode: zero cursor-advance calls
- `cycle_pre.py` in event mode: behavior unchanged (still consumes events with cursor)
- `grep qa-rejected` repo-wide: zero hits in code (occurrences in archived docs / iteration logs are fine)
- `grep responsibility\.md` repo-wide: zero hits in code; files deleted from filesystem
- Harness `POST /work/assign` with unknown alias returns HTTP 404 with documented body shape
- Harness `POST /work/assign` with self-assigned alias returns 4xx (specific code: skill chooses)
- Harness no longer returns HTTP 403 for any `/work/assign` call
- `grep target_role` repo-wide: zero hits in code
- `tracker.py work-assign --target-alias <name>` works; `--target` either removed or marked deprecated with a warning
- Tests pass (existing test suite + any new tests covering the alias-existence check and mis-route recovery)
- Run `compose.py deploy-all` and verify all 4 agent CLAUDE.md files compose without referencing dropped flags or `responsibility.md`
- Live cycle test: PM cycles one full Ralph Loop in loop mode without event-bus calls; observe via harness logs

### References

- PR #10004 (docs/VAULT-ARCH.md + docs/AGENT-RUNTIME.md polish) — the contract
- `docs/VAULT-ARCH.md` §7.2/§7.3/§9.2 (flag retirement)
- `docs/AGENT-RUNTIME.md` §2 / §4.5 / §4.6 / §6.1 / §6.3 / §6.5 / §7.3 / §7.4 / §8.5 Group D / §9 Q2 + Q6 / §10.4 rev 9 + rev 10 (everything else)
- `.squidsquad/vault/galaxy/decision-class-vs-alias-routing-model.md`
- `.squidsquad/vault/galaxy/decision-vault-subagent-model-sonnet.md`
- Memory rule `feedback_model_tier_not_version`

### When to pick up

When all of the following are true:

1. PR #10004 has merged
2. Human has explicitly removed the "ON HOLD" framing from this task or commented "go ahead"
3. You have read both VAULT-ARCH.md and AGENT-RUNTIME.md end-to-end on the merged main branch
4. You have read `decision-class-vs-alias-routing-model.md` in vault

Until then, this task stays `status:pending` and is not in your pickup queue.
