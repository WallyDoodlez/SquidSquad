# RESEARCH-6274 — Terminology generalization (`dev → worker`, `qa → verifier`)

**Issue**: #6274
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-23
**Status**: pending → planning (after this artifact lands)
**Dependency**: event-arch v2 doc (PR #9945) merged 2026-05-23 — this task spawns from there

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/RESEARCH-6274.md` + `CONTEXT-6274.md` (to be written in Phase 2) + the GitHub issue body for #6274. Read all three before pickup.

---

## 1. Goal recap

Two terminology generalizations in one task:
- `dev → worker` — base role for technical implementation; current variants `skill`, `ios`, `android`, `fullstack`, `web`
- `qa → verifier` — base role for verification; current single instance `qa` but variants conceivable (e.g., security-auditor, performance-tester)

`pm` and `dm` stay — already categorical. No semantic change to the agent state machine; this is naming + scaffolding rename.

Aligns with the event-arch v2 doc's terminology section (the doc uses `worker`/`verifier` already; codebase catches up here).

---

## 2. Blast radius — measured

Grep survey on the current main branch (2026-05-23):

- **`dev` occurrences in `references/`**: 188 across 30 files
- **`qa` occurrences in `references/`**: not yet measured; expected similar order
- Key surfaces (call-site count where known):

| Surface | Key call sites | Touchpoint type |
|---|---|---|
| `references/scripts/compose.py` | `_list_known_role_identities()` line 492; hardcoded "dev" at lines 41, 212, 459, 462, 464, 570 | Role-detection logic |
| `references/scripts/config.py` | "dev-agents" field parsing | Config field name |
| `references/scripts/boot_remote.py` | `_parse_dev_agents()` line 104; hardcoded `{pm, qa, dm}` mandatory set line 127 | Boot lifecycle + mandatory roles list |
| `references/scripts/add_role.py` | hardcoded `("pm", "qa", "dm")` line 63; `dev-agents` field line 60 | Add-role tooling |
| `references/scripts/wizard.py` | Install flow asks for "dev variants" | User-facing install language |
| `references/statusline.sh` | 39 occurrences | Status display |
| `references/agent-instructions.md` | 19 occurrences | Composed-output template prose |
| `references/wizard/WIZARD.md` | 19 occurrences | Operator-facing docs |
| `references/sub-skills/manifest.md` | 23 occurrences | Sub-skill manifest |
| `references/sub-skills/project/{dev,dev-soul-directives}-*.md` | 2+2 files | L4 seed templates |
| `references/sub-skills/roles/qa/verification.md` | 9 occurrences | L2 sub-skill |
| `references/roles/dev/{base,android,fullstack,ios,skill,web}/` | 5 variant dirs | L3 variant trees |
| `references/roles/qa/{android,fullstack,ios,skill,web}/` | base + 5 variant dirs | L2 + L3 (variant dirs exist on disk as scaffolding from the symmetric layout, but no `instructions.md` content authored yet — variants not in active use, only structure present). D5 in CONTEXT enumerates them explicitly so the rename doesn't miss the scaffolding tree. |
| `.squidsquad/.harness-state.json` | top-level `agents.<key>` dict | Keys are role identities (`pm`, `dm`, `qa`) or worker variants (`skill`). D4 wizard upgrade renames `agents.qa` → `agents.verifier` (and `agents.dev` → `agents.worker` if present, rare). Variant keys like `agents.skill` unchanged per D5. Schema: `{harness_pid, start_time, port, agents: {<role>: {intent, status, boot_time, clone_path, claude_pid, terminal_pid, bootup_complete}}}`. |

**Per-install touchpoints** (will need migration):

| File | What | Migration approach |
|---|---|---|
| `.squidsquad/config.md` | `Dev Agents: skill` field | Backward-compat shim in `config.py` reads both `Dev Agents` and `Workers`; wizard upgrade rewrites |
| `.squidsquad/{dev,qa}/` | Per-agent runtime dirs | Rename via wizard upgrade step (or symlink for transition) |
| `.squidsquad/{dev,qa}/*` files (composed CLAUDE.md, working-state.md, iterations/) | Per-agent state | Move with the dir rename |
| GitHub Issue labels `role:dev`, `role:qa` | Label taxonomy | Dual-label transition: keep both active for one release; deprecate old |

---

## 3. Migration patterns precedent

Two recent migrations to draw lessons from:

**#9925 (4-layer responsibility model)** shipped 50 files in one PR (post 4 PM CONTEXT drafts + 2 DS reviews + 1 QA reject loop). Lessons:
- Pickup-comment-fidelity bug (#9946) surfaced — claims didn't match diff. Now mitigated by the new sub-skill.
- L4 stubs deferred actual content per variant — same pattern works for `#6274`'s rename: rename now, content stays where it was.

**#9926 (orphan_cleanup D3 per-role skip)** went through normal PM intake → DS review → human approval → skill implementation → QA reject (AC6 missed) → fix → ship. Lessons:
- Tests can break in non-obvious ways when load-bearing assertions are flipped (D7 test rewrites). Plan test rewrites explicitly per AC.

**Phase-based migration (event-arch §15.5 E1/E2/E3)** is the pattern for `#6274`:
- **Phase 1**: introduce new names ALONGSIDE old (compose.py reads both; symlinks or duplicate files for transition).
- **Phase 2**: migrate config.md + L2/L3/L4 files (running installs upgrade via wizard).
- **Phase 3**: delete old names + backward-compat shims.

Each phase reversible at its boundary. Phase 1 is silent; Phase 2 is operator-observable; Phase 3 is irreversible.

---

## 4. compose.py impact (the critical path)

`compose.py` is the central dispatcher for role-related operations. Without it the rename is impossible. Key functions:

- `_list_known_role_identities()` — currently returns hardcoded set including `"dev"`, `"qa"`. Becomes `{"worker", "verifier", "pm", "dm"}` after rename.
- `_resolve_variant(role_name)` — maps `dev-skill` → `(dev, skill)`. Post-rename: maps `worker-skill` → `(worker, skill)`.
- `_get_entry_file_for_role()` — maps role aliases to entry files. Updates per the new identities.
- `_read_config_value("dev-agents")` line 570 — field name change.
- Hardcoded "dev" defaults at lines 41, 212, 459, 462, 464 — replace with "worker".

**During Phase 1**, compose.py needs dual-mode logic — accept both old and new identities. This is the largest single piece of work in `#6274`.

---

## 5. Backward-compatibility surface

Existing installs cannot break on upgrade. Concerns:

1. **`config.md` field**: agents read `Dev Agents: skill` today. After Phase 2 it becomes `Workers: skill` (or whatever name we lock). `config.py` shim: read both keys for one release; warn if old key is used; remove the shim in Phase 3.
2. **Tracker labels**: `role:qa` and `role:dev` exist on hundreds of forge issues today. Migration: GitHub Actions or one-off `gh api` script to dual-label every open issue (add `role:verifier` next to `role:qa`); after one release, remove old. Closed/historical issues stay as-is.
3. **Sub-skill names embedded in `includes.yml`** — `roles/dev/foo` references need to become `roles/worker/foo`. Compose.py during Phase 1 accepts both; templates progressively migrate.
4. **Wizard at install**: new installs go straight to worker/verifier; old installs need an upgrade path.

---

## 6. Test surface

New + updated tests required:

- **New**: `tests/test_terminology_migration_6274.py` — covers dual-mode compose.py, config.py field-shim, identity resolution
- **Updated**: tests touching role names (`test_compose*.py`, `test_config*.py`, `test_boot_remote*.py`, `test_add_role*.py`, `test_wizard*.py`)
- **Updated** (#9925-spawned): `tests/test_agent_boundaries.py` — references `dev`/`qa` in identity resolution; needs rename

Rough estimate: 50–100 test functions touched.

---

## 7. Open questions for Phase 2 CONTEXT

Phase 2 (`CONTEXT-6274.md`) needs decisions on these before implementation can be scoped:

1. **Final config.md field name**: `Workers: skill` or `Worker Agents: skill`? `Verifiers: qa` or `Verifier Agents: qa`? Or keep collapsed as `Agents: skill, qa` since they're all "agents"?
2. **Phase 1 mechanism**: symlinks (`references/roles/worker → dev`) OR file copies OR dual-aware compose.py? Each has different rollback profile.
3. **Tracker label migration**: dual-label transition window length? Recommended: one release (matches event-arch v2 plan).
4. **Per-install upgrade path**: automatic via wizard (riskier, "magic"), OR explicit operator opt-in (safer, more friction)?
5. **GitHub label rename**: keep both old + new active, OR mass-rename via API (loses history but cleaner)?
6. **L3 variant dir naming**: `references/roles/worker/skill/` (rename in place) OR `references/roles/worker/<variant>/` with `skill` as a special case?
7. **Should this absorb the `#9925` follow-up issue** about updating the L1 roster's manifest description if drift was introduced by the rename?
8. **Compose-completed trigger interaction**: event-arch v2 has `assigned-to(pm, event_context=compose-needed)` on `references/` changes. Will `#6274`'s reorg trigger a flood of these? Throttle or batch?
9. **PR sequencing**: one big PR (riskier), 3-phase (matches event-arch §15.5 pattern), or per-script PRs (slowest, safest)?
10. **Test rewrites within the same PRs that rename** OR separate test-update PR? Coupled is more atomic; decoupled is smaller diffs.

---

## 8. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Existing installs break on upgrade | High | Dual-mode shims in compose.py + config.py for one release |
| Composed CLAUDE.md regresses for in-flight tasks | Medium | Phase 2 lands during low-activity window; cycle_post triggers respawn on the new templates |
| GitHub label history confusion | Low-medium | Dual-label transition; document the cutover in a vault note |
| `#9925` follow-up wizard task (deferred from event-arch session) now blocked on this | Low | Wizard updates roll into this PR's Phase 1 |
| 188+ touchpoints means missed renames are likely | High | Comprehensive grep-driven test (`tests/test_terminology_migration_6274.py`) asserts no stale `\bdev\b` or `\bqa\b` role-string references in active code paths |
| Tracker.py label commands embedded in agent CLAUDE.md prose | Medium | Comprehension testing per `feedback_comprehension_testing` — spawn fresh agent and quiz |

---

## 9. Recommended approach summary

- Run as **3-sub-phase migration**, naming sub-phases `Sub-phase 6274.1 / 6274.2 / 6274.3` to mirror event-arch §15.5 E1/E2/E3 disambiguation.
- 6274.1: introduce dual-mode in compose.py + config.py; both old and new names resolve.
- 6274.2: rename directories + L2/L3/L4 files + composed templates; wizard upgrade step for existing installs.
- 6274.3: delete backward-compat shims; remove old labels from GitHub; lock the new names as canonical.

Each sub-phase is reversible at its boundary. Each is its own PR. Estimated 5–10 working days of skill time end-to-end (vs `#9925`'s ~6 hours — this is 10x the file surface).

---

## 10. Next step

Phase 2 — write `CONTEXT-6274.md` with locked decisions. Requires AskUserQuestion pass on the 10 open questions in §7. Then DS-review the locked CONTEXT before human approval gate.
