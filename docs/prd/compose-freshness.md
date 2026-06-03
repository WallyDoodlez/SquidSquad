# PRD E — Compose Freshness (Harness-Owned) + v2 Cutover

> **Status**: shipped, 2026-06-02 (E6 V2 CUTOVER, #10685). Derived from TRD [[COMPOSE-ARCHITECTURE]] §8 (source-output sync — harness-owned freshness). Part of the COMPOSE-ARCH PRD slice family: A (link) / B (assemble) / C (L4 customization) / D (catalog + wake-mode) / E (this — freshness + final v2 cutover).
>
> **Scope:** the three-layer freshness model that keeps composed `CLAUDE.md` outputs in sync with their L1–L4 sources, PLUS the family-wide **v2 switch PR** that makes v2 the default and retires v1. Excludes link-stage mechanics (PRD A), the LLM assemble pass (PRD B), runtime L4 writes (PRD C), and catalog/wake-mode handling (PRD D).
>
> **Owner**: harness — no CI infrastructure in target repos (per [[project_compose_freshness_harness_owned]]).

---

## 1. Goal

Two coupled goals:

**Goal 1 — Freshness.** Composed `CLAUDE.md` outputs MUST be in sync with their L1–L4 sources whenever agents boot or pick up cycles. Today there is no enforcement — if an operator changes a sub-skill source and forgets to recompose, agents boot stale instructions until somebody notices. PRD-E delivers three reinforcing mechanisms (boot-time check, L4-write trigger, operator-driven check) all owned by the harness or operator, with **no CI infrastructure required in the target repo**.

**Goal 2 — v2 cutover.** After PRD-A through PRD-D story-PRs all land, a single "switch PR" makes v2 the default: renames v2 output paths to v1's canonical paths, deletes v1 compose code, removes the `--v2` opt-in flag. This is the moment the install actually transitions; everything before it is additive. The switch PR ships as the final story in PRD-E because PRD-E's boot-time checksum (E1) is the mechanism that makes the switch safe — the harness sees mismatched checksums (v1 outputs vs v2 sources), runs `compose.py deploy-all`, and agents boot with the fresh v2 output without operator ceremony.

## 2. User-facing outcomes

| Persona | Outcome |
|---|---|
| **Operator starting the harness** | Harness checksums the source tree against `last_compose_checksum` in `.squidsquad/.harness-state.json`. If drift, runs `compose.py deploy-all` BEFORE spawning agents. Agents always boot with up-to-date `CLAUDE.md`; no "stale CLAUDE.md" failure mode mid-session. |
| **Operator running `git pull`** then `start.sh` | Boot-time check detects the new source tree, recomposes, then spawns agents. Single command from operator's perspective. |
| **Operator's running install** while an agent invokes `l4-curation` to write L4 | Harness file-watches `.squidsquad/project/`, detects the L4 commit, runs `compose.py deploy` for the affected role-class's aliases, emits `restart-required` to those agents. Agents pick up the regenerated `CLAUDE.md` on next cycle. |
| **Operator running `squidsquad_cli.py check`** | Diagnostic command runs the same checksum + dry-run path the harness uses internally. Useful for pre-flight: "is this install consistent?" without spawning agents. |
| **Reviewer of a sub-skill source change** | Confidence that the next harness boot will pick up the change, regenerate composed outputs, and not silently ship stale instructions. |
| **Operator on a target repo** | Zero CI infrastructure required for SquidSquad. No GitHub Actions, no pre-commit hooks. The harness owns freshness; the target repo stays clean. |
| **All operators after the v2 switch PR lands** | Composed `CLAUDE.md` outputs follow the v2 model (slot grammar, sub-skill references, single-file L4, assemble-rewritten coherent prose). Boot-time checksum runs the v2 compose; agents flap to loop mode briefly during the switch via the existing boot-probe fallback, then return to event mode on the next session restart. |

## 3. Success criteria

PRD-E is "done" when ALL of the following hold:

### Freshness — three layers

1. **Layer 1 (boot-time, primary)** — on every harness start, before spawning any agent, the harness:
   - Checksums the source tree (`.squidsquad/config.md` + `.squidsquad/project/*.md` + `references/sub-skills/` + `references/roles/` + `references/sub-skills/manifest.md`).
   - Compares against `last_compose_checksum` in `.squidsquad/.harness-state.json`.
   - If drift (or first boot, or checksum missing): runs `compose.py deploy-all` AND updates the stored checksum.
   - Only then spawns agents.
2. **Layer 2 (L4-write trigger)** — harness file-watches `.squidsquad/project/` (or honors a post-write hook from `l4-curation`). On any write:
   - Runs `compose.py deploy` for every alias whose role-class L4 changed.
   - Emits `assigned-to(target_alias=<that-alias>, event_context="restart-required", payload={reason:"l4-recompose"})` to the affected agents (per [[AGENT-RUNTIME]] §8.5 disambiguation: `restart-required` for agents, distinct from `compose-needed` for PM).
   - Affected agents pick up the regenerated `CLAUDE.md` on next cycle.
3. **Layer 3 (operator-driven check)** — `squidsquad_cli.py check` is a new CLI command:
   - Runs the same checksum + dry-run path the harness uses at boot.
   - Exit 0 if clean; exit 1 if drift; exit 2 if error (couldn't read sources, malformed config).
   - Stderr emits a structured drift report.
   - Does NOT spawn agents and does NOT mutate state — pure diagnostic.

### State + plumbing

4. **`last_compose_checksum` field** at top level of `.squidsquad/.harness-state.json` (already added to HARNESS-ARCH §7.5 schema as part of an earlier round). Persisted across harness restarts.
5. **HARNESS-ARCH §10 step 1b integration** — the restart-safety sequence runs the freshness check between state-file read and PID verification (already documented in HARNESS-ARCH §10 as part of an earlier round; PRD-E implements it).
6. **Layer 1 is the primary gate.** Layers 2 and 3 are defence in depth. If Layer 1 alone is correct, the install is correct.
7. **No CI infrastructure** added to the target repo per [[project_compose_freshness_harness_owned]]. No GitHub Actions, no pre-commit hooks, no Makefile target the operator must run manually.

### v2 cutover (the switch PR)

8. **v2 switch PR** ships after A/B/C/D story-PRs all land:
   - Renames v2 output paths to v1 canonical paths (`CLAUDE.v2.md` → `CLAUDE.md`, `CLAUDE.linked.v2.md` → `CLAUDE.linked.md`, `CLAUDE.conflicts.v2.md` → `CLAUDE.conflicts.md`).
   - Renames `includes-v2.yml` → `includes.yml`; deletes `includes-events.yml` (per PRD-D's two-step approach).
   - Removes v1 compose code paths (`_assemble_claude`, the old `_resolve_includes`, multi-file L4 routing, manifest split).
   - Removes the `--v2` opt-in flag from CLI.
   - Removes `event-driven:` from `config.md` schema (per PRD-D D6).
   - Updates PRDs A/B/C/D/E "Status" headers to `shipped`.
9. **Post-switch, the boot-probe fallback (per [[AGENT-RUNTIME]] §8.3)** absorbs any transient event-mode breakage. Sessions that flap during the switch land in loop mode automatically; the next session restart probes again and either stays in loop (if harness still unreachable) or returns to event mode.
10. **Post-switch state**: an operator running `squidsquad_cli.py check` against a clean v2 install exits 0. Boot-time freshness check finds no drift. No legacy v1 paths or v1 manifests linger.

## 4. Non-goals

- Link-stage mechanics — [[compose-link-stage]] (PRD A).
- Assemble pass — [[compose-assemble-stage]] (PRD B).
- `l4-curation` sub-skill and runtime L4 write flow — [[compose-l4-customization]] (PRD C). PRD-E provides the harness file-watch trigger that PRD-C's commits flow into; PRD-C provides the gate-protected commit that the trigger reacts to.
- Sub-skill catalog gate and wake-mode unification — [[compose-catalog-and-wake-mode]] (PRD D).
- Any CI infrastructure (GitHub Actions, pre-commit hooks) in the target repo — explicitly out per [[project_compose_freshness_harness_owned]].
- Mid-session re-checksum (no continuous source-watching except for the narrow `.squidsquad/project/` L4 file-watch). Source-tree changes elsewhere (e.g., `references/sub-skills/` edits during a running session) are NOT detected mid-session by design — they take effect at the next harness restart.

## 5. Architectural anchors

- **TRD §8.1** — Boot-time check + auto-compose (Layer 1).
- **TRD §8.2** — L4-write trigger (Layer 2), `restart-required` event.
- **TRD §8.3** — Operator check (Layer 3).
- **TRD §8 closing paragraph** — "No target-repo CI dependency."
- **[[HARNESS-ARCH]] §7.5** — `.harness-state.json` schema (already updated with `last_compose_checksum`).
- **[[HARNESS-ARCH]] §10 step 1b** — Restart-safety integration point (already documented).
- **[[AGENT-RUNTIME]] §8.5** — `restart-required` vs `compose-needed` event-context disambiguation.
- **[[INSTALLER-ARCH]] §10.3** — Post-installer harness restart path (the consumer of "harness starts → freshness check → spawn agents").

## 6. Dependencies

| Dependency | From | Why |
|---|---|---|
| Harness already owns lifecycle (start/stop/restart of agents, state-file persistence) | Existing | Layers 1 + 2 extend existing harness responsibilities |
| File-watch capability in Python (`watchdog` or platform-native) | Existing — `pip install` if needed | Layer 2 watches `.squidsquad/project/` |
| `compose.py deploy-all` works (any v1 or v2 version) | Existing v1 / PRD-A (v2) | Layer 1 invokes it |
| PRD-A `--check` mode (story A4) | [[compose-link-stage]] | Layer 3 (`squidsquad_cli.py check`) reuses A4's in-memory composition path |
| PRD-C `l4-curation` commits land at `.squidsquad/project/<role-class>.md` | [[compose-l4-customization]] | Layer 2's file-watch reacts to these commits; PRD-C-PRD-E contract is the file commit |
| PRDs A, B, C, D story-PRs all merged | All PRDs in the family | The v2 switch PR (E story E6) is the LAST PR in the family — depends on every preceding story landing first |

## 7. Story breakdown (proposed)

| # | Story | TRD anchor | Effort | Notes |
|---|---|---|---|---|
| **E1** | Harness boot-time freshness check — checksum source tree, compare to `last_compose_checksum`, run `compose.py deploy-all` if drift, update checksum, then spawn agents | §8.1 | M | The core mechanism; gates everything else in §8 |
| **E2** | `last_compose_checksum` field plumbing — read on harness start, write on successful compose, atomic-write contract (`.tmp` + `mv`) consistent with rest of state file | §8.1 + HARNESS-ARCH §7.5 | S | Pure state-file work; couples with E1 |
| **E3** | L4-write file-watch — harness watches `.squidsquad/project/`, on write runs `compose.py deploy` for the affected role-class's aliases, emits `restart-required` event | §8.2 | M | Cross-platform file-watch (Windows + macOS + Linux); falls back to post-commit hook if file-watch unreliable on a platform |
| **E4** | `squidsquad_cli.py check` command — operator-driven equivalent of E1's check; exit 0/1/2 semantics + structured stderr diff | §8.3 | S | Wrapper around E1's check function |
| **E5** | HARNESS-ARCH §10 step 1b implementation — wire the freshness check into the harness restart-safety sequence between state-file read and PID verification | HARNESS-ARCH §10 | S | Pure plumbing on top of E1 |
| **E6** | **v2 switch PR** — rename v2 paths to v1 canonical, delete v1 compose code, remove `--v2` flag, drop `event-driven:` from `config.md` schema, update PRD status headers | §8 (consumer of all family work) | M | Final PR in the family; only proceeds after A/B/C/D story-PRs all merge AND E1-E5 are green |
| **E7** | Migration smoke — run the v2 switch PR locally against a fresh checkout of this repo, confirm boot succeeds, all agents pick up v2 outputs, no `CLAUDE.md` regression | E6 | M | Pre-merge sanity check — execute manually with operator (human) participation |

Effort scale: S = 1–2 days, M = 3–5 days, L = 1+ week.

**Recommended pickup order**:

1. **E2** (state-file field — pure I/O, no harness-loop changes)
2. **E1** (boot-time check — couples with E2)
3. **E5** (HARNESS-ARCH §10 step 1b — minor plumbing after E1 lands)
4. **E4** (operator `check` command — wraps E1's check function)
5. **E3** (file-watch — biggest in-harness change, independent of E1/E2)
6. **E6** (the switch PR — LAST; gated on A/B/C/D family-wide completion + E1–E5 green)
7. **E7** (migration smoke — gated on E6)

## 8. Open questions for this PRD

| # | Question | Resolution path |
|---|---|---|
| Q-E1 | Layer 2 file-watch library — `watchdog` (cross-platform Python) vs platform-native (`pyinotify` Linux, `fsevents` macOS, `ReadDirectoryChangesW` Windows)? | Decide in E3 — recommend `watchdog` for portability; fall back to platform-native if performance / reliability becomes an issue |
| Q-E2 | E3 file-watch vs `git post-commit` hook — which is the canonical trigger? | Decide in E3 — recommend file-watch as primary (handles non-git L4 writes too); post-commit hook can be a secondary trigger for human-driven L4 edits outside the agent dialog |
| Q-E3 | When E1's checksum mismatch fires `compose.py deploy-all` and that compose itself fails (e.g., a malformed sub-skill source), does the harness refuse to spawn agents, fall back to last known good `CLAUDE.md`, or attempt a degraded boot? | Decide in E1 — recommend refuse to spawn + emit a clear operator error. The TRD's "shipping inconsistent prose to the agent is worse than failing the deploy" rule applies |
| Q-E4 | The switch PR (E6) is large. Should it be split into sub-commits (e.g., rename paths in one commit, delete v1 code in another, drop flag in a third)? | Decide in E6 — recommend single squash-merge PR with the changes grouped logically. The switch is one logical change; splitting only complicates rollback |
| Q-E5 | Post-switch, should the v1 compose source files (`_assemble_claude` etc.) live in git history only, or be quarantined to an archive directory for a release cycle? | Decide in E6 — recommend straight delete (git history is the archive); no graveyard directories |

## 9. Out of scope — explicit list

- All non-§8 TRD work (link, assemble, L4 write, catalog, wake-mode) — covered by PRDs A/B/C/D.
- CI infrastructure of any kind in the target repo.
- Mid-session re-checksumming for source trees outside `.squidsquad/project/`.
- A "soft" freshness mode where stale CLAUDE.md is permitted with a warning — explicitly NO; freshness is either gate-passing or boot-blocking.
- Cross-platform file-watch optimization — defer to per-platform tuning if a real bottleneck surfaces.

## 9a. Coexistence with v1 — no broken installs during the transition

PRD-E is unique in the family because **it owns the cutover**. Its coexistence story is therefore the bridge.

**Pre-cutover (during E1–E5 development)**:
- E1–E5 operate against the v1 outputs that are still the default. The boot-time check reads `last_compose_checksum`, runs `compose.py deploy-all` against the v1 code path, writes v1 outputs to v1 paths. v2 paths are NOT yet involved.
- E3 file-watch watches `.squidsquad/project/` but the recompose it triggers is v1 (multi-file routing). v2's `l4-curation` writes don't take effect on the runtime until v2 is the default.
- E4 `squidsquad_cli.py check` reports drift against v1 outputs.

**During the cutover (E6 — the switch PR itself)**:
- E6 is the one PR where v1 → v2 transition happens.
- Pre-merge state: v1 is default; v2 outputs sit at `CLAUDE.v2.md` paths from A/B/C/D's prior work; everything coexists.
- Merge state: E6's atomic change renames paths, deletes v1 code, flips `--v2` from opt-in to default. Boot-time checksum sees the changed source tree (new code, removed paths) and runs the now-v2 `compose.py deploy-all` against v2 sources. v2 outputs land at the (now canonical) `CLAUDE.md` paths.
- Operator experience: pull, `start.sh`. Harness checksums, sees mismatch, runs v2 compose, spawns agents with v2 outputs. **No operator-side migration command.**
- Agents may flap to loop mode during the boot window if event-mode integration is briefly unstable per the switch — that's the [[AGENT-RUNTIME]] §8.3 boot probe absorbing it automatically. The next session restart re-probes and either stays in loop (if harness still unreachable) or returns to event mode.

**Post-cutover (E7 + ongoing)**:
- E7 smoke test confirms the migration on this repo's own install.
- v1 paths and v1 code do not exist. There is only v2. Future agents boot v2 outputs natively.

**Roll-back plan if E6 surfaces a critical issue**:
- `git revert` the E6 PR. v1 paths and code return; v2 outputs at v2 paths remain (harmless, ignored by v1 compose).
- Harness reboots, checksum re-runs against v1 sources, v1 outputs at v1 paths, agents pick up the rollback on next cycle.
- The boot probe again absorbs any wake-mode instability during the rollback window.

This roll-back path is the single biggest reason to keep v1 code intact through A–D and delete it only in E6 — easy rollback before deletion, harder after. The deletion in E6 is the irrevocable step; if any concern remains at that point, hold E6 and ship E1–E5 alone (the freshness mechanism works for v1 too).

## 10. Acceptance

This PRD is "done" when:

- All 7 stories (E1–E7) have shipped or been explicitly deferred (with rationale + target).
- The 10 success criteria above are demonstrably met.
- A live smoke: change a sub-skill source file in this repo, restart the harness, confirm the boot-time check detects drift, runs `compose.py deploy-all`, and spawns agents with the updated `CLAUDE.md`.
- A live smoke: invoke `l4-curation` to write to `.squidsquad/project/pm.md`, confirm the harness file-watch detects the write, recomposes the affected aliases, and emits `restart-required` to those agents (verified via event-bus inspection).
- A live smoke: run `squidsquad_cli.py check` on a clean install (exit 0) and on a manually-drifted install (exit 1, stderr report).
- After E6 ships: this repo's `.squidsquad/` is fully v2. No v1 paths or v1 manifests remain. PRDs A/B/C/D/E "Status" headers all read `shipped`.

## 11. References

- TRD: [[COMPOSE-ARCHITECTURE]] (canonical spec — §8)
- Sibling architecture: [[HARNESS-ARCH]] (§7.5 state schema, §10 step 1b), [[AGENT-RUNTIME]] (§8.3 boot probe, §8.5 `restart-required`), [[INSTALLER-ARCH]] (§10.3 post-installer restart)
- Companion PRDs: [[compose-link-stage]] (A), [[compose-assemble-stage]] (B), [[compose-l4-customization]] (C), [[compose-catalog-and-wake-mode]] (D)
- Memory rules: [[project_compose_freshness_harness_owned]], [[project_event_mode_default]], [[project_assemble_unconditional]], [[project_l4_long_living]], [[project_trd_prd_delivery_model]]
- Related closed work: PR #10383 (TRD §8 rewrite to harness-owned), PR #10382 (event-driven flag dropped)
