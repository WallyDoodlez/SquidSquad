# PRD: VAULT-ARCH v2 implementation

**Source TRD**: `docs/VAULT-ARCH.md` v2 (merged 2026-07-19, PR #13708 = `800bf4049`; DS audit r3/r4 CONVERGED).
**Status**: drafted 2026-07-19, phase structure operator-approved inline (same day); awaits formal approval of this PRD.
**Supersedes**: #10838 (v1-era alignment PRD — all findings dissolved by v2 or ported here; see §Ported below).
**Delivery model**: TRD → this PRD → Stories/Tasks (worker breaks phases into stories at pickup; every task's ACs must verify the consumption path, not file existence).

## Framework deliverable vs. this-install prepopulation

SquidSquad builds SquidSquad, so this PRD delivers at **two distinct layers** — do not conflate them (operator directive, 2026-07-19):

**Framework deliverable** — content-free mechanism, shipped to *every* install by the installer/wizard:
- `vault-schema.json` default profile (PARAG + `system` type registered) and the registry loader
- Registry-derived templates including the `system.md` hub skeleton; `briefing.md` skeleton
- Empty PARAG folder scaffold + `.telemetry/.gitattributes` (installer seeds)
- The engine (search/telemetry/report/compaction), consumption-pipeline steps, rewritten sub-skills, harness hooks
- A fresh deployment on **another project** starts with an *empty* vault: its team authors its own hubs for *its* subsystems and accumulates its own notes. Nothing SquidSquad-specific ships as content.

**This-install prepopulation** — content authored for the SquidSquad-project vault specifically (the dogfood install), carried by the stories marked ⌂ below:
- ⌂ The initial `systems/` hub set (~7–10 notes: harness, event bus, compose pipeline, tracker, pr_merge, launcher, vault itself) — S2.2's authoring half. These name *our* subsystems; they are vault **content**, not framework files, and are never shipped by the installer.
- ⌂ Retroactive hub-linking of our existing galaxy leaves (M2 distillation)
- ⌂ Migration of our existing note inventory through M0–M4 (transform, distillation, owner-label sweep)
- ⌂ Our BRIEFING.md and existing areas/projects/resources content, migrated in place

Story ACs must respect the split: a framework AC is verified on a scratch/greenfield install; a ⌂ prepopulation AC is verified against this repo's `.squidsquad/vault/`. A story that mixes both layers must state which AC belongs to which.

## Phase structure (operator-approved)

Ordering rationale: P1 first — everything downstream consumes the engine, and both feasibility probes (Skill invocation from harness-spawned session; Node-preflight model) already passed. P4 before P5 — receipts are the value proposition; maintenance polish trails. The M-track runs after P1–P4 land (M4 cutover needs the pipeline live) and carries the #13854 doc-reconciliation umbrella.

### P1 — Engine foundation (TRD §7.5, §8.5)

Package the portable engine, invoked via the Skill tool; establish the engine boundary.

- **S1.1 Engine packaging**: the portable reference-system extraction lands as an invocable Skill; wizard/installer preflights `node --version` when enabling (absent Node → feature degrades per §6.2/§9.9, install does not fail). AC: a harness-spawned non-interactive agent session invokes the engine Skill and receives top-K JSON; a Node-less environment degrades to tier+recency ranking with an engine-unavailable receipt — both demonstrated live by the verifier.
- **S1.2 Engine-boundary contract**: the §8.5 table (search / telemetry-write / impressions-report in engine; everything else SquidSquad-side) is enforced — no SquidSquad script reimplements engine operations. AC: grep-audit shows vault sub-skills/scripts reach search only through the engine call (raw-grep ban, §6.2); `--no-write` dry-run suppresses telemetry.

### P2 — Structure: registry + hubs + templates (TRD §3)

- **S2.1 `vault-schema.json`**: type registry shipped with the §3.2 default profile; loader validates; unknown types fall back to generic template. AC: registering a custom type in a scratch install produces a working folder/template/traversal config consumed by search — not just a parsed file.
- **S2.2 `systems/` hub layer** *(two-layer story — see §Framework vs. prepopulation)*: **framework half** — `system` type registered, hub template, `vault_check.py` Level-2 flags galaxy notes with zero hub links (§3.3); AC verified on a scratch install. **⌂ Prepopulation half** — initial hub set authored for *this* install (~7–10 notes: harness, event bus, compose, tracker, pr_merge, launcher, vault); AC: engine traversal demonstrably reaches one of our galaxy leaves through a hub at budget cost 0 for the hub hop, verified against this repo's vault.
- **S2.3 Registry-derived templates**: template set derived from registry (§3.5), `style.md` deleted with its type; `briefing.md` special-cased. AC: note creation for every registered type resolves its template; custom-type fallback works.

### P3 — Telemetry (TRD §6)

- **S3.1 Event model + shards**: JSONL events `{id, ts, agent, task, slug, counter}`; per-writing-clone shards `vault/.telemetry/<instance-uuid>-<role>.jsonl`; `.gitattributes` `merge=union`; instance-id minted/persisted by harness (P5 dependency for mint; a provisional local mint is acceptable in P3). AC: two clones writing concurrently produce zero merge conflicts (live demonstration); engine writes `impression`/`walked` only, consumers write `used` only.
- **S3.2 Ranking integration**: two-stage ranking with telemetry tiebreak + graceful degradation (§6.2). AC: cold-start search (no shards) returns tier+recency ordering without error.
- **S3.3 Impressions report**: shard-join report bucketing per §4.4 (healthy = no bucket). AC: report output consumed by a `vault_optimize.py` proposal run (consumption path, not file existence).
- **S3.4 Compaction**: per the §6.5 invariants — owner-only, aggregate-before-truncate in one commit, idempotent via last-absorbed id. AC: kill-mid-compaction test shows no double-count on re-run; horizon + naming fixed here (closes §11 #6's compaction slice).

### P4 — Consumption pipeline + sub-skills (TRD §9.2–9.5, §7)

- **S4.1 Intake injection**: PM task filing appends `## Vault context` (top-K + relevance) to issue bodies; impression events attribute to the task. AC: a filed test task's body carries the section; a dev agent session demonstrably reads it (comprehension check).
- **S4.2 Consultation + receipts**: pickup flow produces `## Vault context consumed` + `## Applicable rules` in the issue's **plan/lineage file** (TRD §9.3 as amended 2026-07-20: planned tasks append to CONTEXT.md; bug flow **creates a lean fix-plan at pickup** — root cause, intended direction, impact — the human review surface for non-auto-merged auto-fixes); the file ships in the PR diff (all work rides a PR, #9478). `used` events consumer-written. AC: lineage file present in the PR diff with receipt sections; bug-flow pickup demonstrably creates the fix-plan; "none relevant" path costs one line.
- **S4.3 Verifier receipt enforcement**: verification checks receipt presence + rule compliance; missing receipt routes back (zero-gap). AC: comprehension spec for the verifier instruction change (house rule for agent-instruction changes).
- **S4.4 Write paths**: capture-at-ship on the feature branch + end-of-cycle sweep with engine-rerouted dedup (prefer-update-over-create; threshold from `dedupThreshold` — set the shipped default here, closing §11 #6's dedup slice). AC: a duplicate-subject capture demonstrably lands as an append to the ranked hit, not a new note.
- **S4.5 Sub-skill rewrites**: `vault-protocol` / `vault-remember` / `vault-optimize` / `vault-synthesis` rewritten engine-backed; consultation/receipt steps added; catalog entries updated (rides M4 per #13854 if sequencing demands). AC: composed CLAUDE.md outputs reach agents (compose consumption path); comprehension specs per changed instruction.
- **Gate to resolve at P4 drafting**: §11 #3 rules-lane placement (dedicated `rule` type vs `binding: true` flag) — PM recommendation + operator call before S4.2 implementation.

### P5 — Maintenance + harness hooks (TRD §9.6; → HARNESS-ARCH)

- **S5.1 Harness-scheduled optimize**: analyze phase scheduled (queue by `last_optimized`, 14-day cutoff); contradiction findings HITL-gated; pruning proposals consume the impressions report. AC: scheduled run fires without "hope a quiet cycle notices"; a seeded contradiction produces a HITL tracker task, never an auto-apply.
- **S5.2 Instance-id mint/persist**: harness responsibility per §6.3 (provision-time UUID in gitignored local state); replaces any P3 provisional mint. AC: two harness instances on one machine mint distinct ids; ids survive restart.
- **S5.3 HARNESS-ARCH doc update**: rides #13854 (§12.2 reconciliation umbrella).

### M-track — Migration M0–M4 (TRD §10) ⌂ *(entirely this-install: migrates our existing vault; a fresh deployment has nothing to migrate)*

M0 snapshot & freeze → M1 mechanical transform (deterministic, tested; **ported from #10838**: owner-label normalization `<role>-lead` → class values; plus dropping retired fields `confidence`/`source`/`links` from existing notes) → M2 distillation (analyze-only; §11 #4 aggressiveness decided at M3) → M3 human gate (operator manifest review) → M4 cutover & unfreeze (+ #13854 doc reconciliation, S4.5 catalog rides here, §11 #5 viewer call any time before this).

## Ported from #10838 (v1 alignment PRD — closing as superseded)

| #10838 finding | v2 disposition |
|---|---|
| 1. `source: code` in code vs spec | Field dropped in v2 §4.3 — cleanup = M1 transform + S4.5 rewrites |
| 2. `links` auto-maintain unimplemented (#10098) | Field dropped in v2; #10098 already CLOSED |
| 3. Confidence-decay config unread (#10099) | Mechanism dropped in v2 §4.4; #10099 already CLOSED |
| 4. Owner-label `-lead` drift (8 notes) | **Ported → M1 transform** (explicit story item) |
| 5–10. STALE planned items | Superseded wholesale by the v2 rewrite |

## Open decisions surfaced to operator (from TRD §11)

- **#3 rules-lane placement** — decision point: P4 drafting (PM recommendation forthcoming with sub-skill design).
- **#4 distillation aggressiveness** — decision point: M3 manifest review (TRD recommendation: aggressive).
- **#5 viewer priority** — decision point: any time before M4 scoping.
- **#6 numeric defaults** — resolved inside P3 (compaction horizon) and P4 (dedupThreshold); config-overridable.

## Non-goals

Per TRD §9.10 and locked decisions: no runtime blocking on vault availability; no cloud/hosted storage; no `evergreen` tag; no per-note telemetry files; BRIEFING stays outside index/telemetry; multi-instance state layer is #13725, not this PRD.
