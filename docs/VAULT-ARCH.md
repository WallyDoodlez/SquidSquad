# Vault Architecture (v2 — target design)

> **Status**: v2 TRD draft, in progress 2026-07-18 (tracked on #10003, draft PR pending). This is a **prescriptive target design**, not a snapshot of current code — v1's descriptive-snapshot content is being replaced section by section as this draft lands. Where a section is not yet rewritten, it still reflects v1 (current/live) behavior; such sections are marked `[v1 — not yet migrated]` until superseded.
>
> **Why v2**: research comparing SquidSquad's vault against dmp-web's (a mature, actively-used agent-memory system) found SquidSquad's vault functions as a static decision log, not living institutional memory — full analysis in `.squidsquad/pm/planning/VAULT-COMPARISON-DMPWEB.md`. The root cause: consumption (search, ranking, verified usage) was never instrumented, so the write side curates blind and nothing measures whether captured knowledge is ever used. v2 ports dmp-web's consumption-pipeline pattern and telemetry-driven ranking as **domain-agnostic infrastructure** — not its SWE-specific taxonomy, which would be wrong for SquidSquad's general-purpose (non-technical-team) audience. See `VAULT-COMPARISON-DMPWEB.md` §9 (design) and §10 (scope correction + resolved decisions) for the full reasoning this doc formalizes.
>
> **Companion docs**: [`ARCHITECTURE.md`](ARCHITECTURE.md) (overall system; vault appears as "L6 Memory"), [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (cycle integration), [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) (vault slot in composed CLAUDE.md), [`sub-skill-catalog.md`](sub-skill-catalog.md) (vault sub-skill entries).
>
> **No implementation tasks get filed against this redesign until this TRD is human-reviewed and merged** (doc-first process).

---

## 1. Goal & scope

This doc describes the **v2 target design**:

- What the vault *is* — its purpose, the storage model, the entity types it holds
- The config-driven type registry that replaces v1's hardcoded PARAG taxonomy
- The consumption engine (search + telemetry-driven ranking) and how it's invoked
- The consumption-pipeline pattern — mandatory touchpoints producing committed receipts
- The sub-skills and scripts that operate on it
- How it integrates into the cycle (boot, task-creation, creative phase, capture-at-ship, quiet ticks)
- The migration path from v1's live content
- Known open decisions still needing resolution before/during implementation

It does NOT describe per-role-class access (read/write); that lives in [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) and [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) where the per-role-class `includes.yml` mapping is composed.

**Vault slot authorship is L1-exclusive** (guardrail dated 2026-05-29, carried forward into v2). The composed `## Vault` section in every agent's CLAUDE.md is authored entirely by L1 fragments shipped from this repo — L2 / L3 / L4 cannot contribute `slot: vault` content. **What changes in v2**: the type-registry (`vault-schema.json`, §3) IS the sanctioned per-install customization point — a project can define its own note types without touching the L1-exclusive slot content, resolving the old "projects that need bespoke vault behaviour file a framework feature request" limitation for the taxonomy specifically. The read/write *protocol* (search contract, telemetry, receipts) remains framework-owned.

It does NOT describe:

- The actual implementation (vault_search.py, migration script, etc.) — those are implementation tasks this TRD unblocks, filed separately once this lands
- How vault slot content gets into composed CLAUDE.md (see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) §5.5)
- The L4 project-local layer in `.squidsquad/project/` (different system; see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) §3)

---

## 2. What the vault is

> **Vault terminology** — this doc and COMPOSE-ARCHITECTURE use three distinct terms; conflating them is the source of long-running audit confusion:
>
> | Term | What it is | Authored by | Read by |
> |---|---|---|---|
> | **vault slot** | The `## Vault` H2 section in composed CLAUDE.md — short framework-shipped prose describing the vault contract | L1 only (this slot is L1-exclusive per COMPOSE-ARCHITECTURE §3.3) | Runtime agents at boot |
> | **vault store** | The on-disk knowledge store at `.squidsquad/vault/` (markdown notes organized via PARAG) | All agents at runtime via vault sub-skills (vault-remember, etc.) | All agents at runtime |
> | **vault contract** | The framework-owned design spec — type registry, entity model, wikilink grammar, search + telemetry contracts | SquidSquad framework (`references/sub-skills/common/vault-protocol.md` + this doc) | Vault sub-skills + agents that read the slot |
>
> When this doc says "vault" without a qualifier, assume the most specific applicable term from context. When the meaning is structurally significant (e.g., "L1-exclusive"), the qualifier is mandatory.

The vault store is a **shared, git-tracked, per-install knowledge store** at `.squidsquad/vault/`. It holds institutional knowledge that outlives any single cycle, task, or session — decisions, learnings, patterns, project context, ongoing concerns, and human preferences as the agents have observed them.

Four properties define it (the fourth is new in v2):

1. **Shared across roles** — all agents in the install read the vault, and so does the human. Write access is restricted; specifics on which agents write live in [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (cycle integration) and [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) (sub-skill composition).
2. **Git-tracked** — every note has a commit; every change has authorship and timestamp. There is no separate database, indexer, or memory service. (Telemetry, §6, is git-tracked too — but as append-only per-writer event shards under `vault/.telemetry/`, never as note content; see §6.3.)
3. **Per-install** — `.squidsquad/vault/` lives inside the project repo's `.squidsquad/` tree. A separate SquidSquad install has its own vault; there is no cross-install vault today.
4. **Consumption-instrumented (v2)** — every search and every cited use is an event (`impression`/`walked`/`used`, §6.1). This is the property v1 lacked entirely: nothing measured whether a written note was ever read, so the write side curated blind and dead notes accumulated indefinitely. v2 makes consumption a first-class, measurable signal that ranking and maintenance both consume.

The vault is **distinct from**:

- **L4 project-local content** (`.squidsquad/project/`): instruction overlays composed into CLAUDE.md. L4 is *what the agent does*; vault is *what the squad knows*.
- **Working state** (`.squidsquad/<role>/working-state.md`): per-cycle crash-recovery checkpoint, single-agent-owned. Working state is *what this agent is doing right now*; vault is *what the squad has learned over time*.
- **Iteration logs** (`.squidsquad/<role>/iterations/iter-N.md`): per-cycle activity log. Iteration logs are *what happened this cycle*; vault is the *durable filtered residue*.

---

## 3. On-disk layout — PARAG

### 3.0 What actually changes here, and why

**PARAG itself is not the diagnosis.** Nothing in the dmp-web comparison shows PARAG's actionability-based sorting caused SquidSquad's vault to underperform — SquidSquad simply never ran long enough, at scale, with real consumption pressure, to find out whether the folder axis mattered. What the comparison *does* show is that dmp-web's two structural additions — **a connected graph via dedicated hub/entity notes with budgeted traversal**, and **telemetry-driven ranking** (§6) — are directly responsible for its vault staying useful under real load. SquidSquad had neither. §3 replaces the *hardcoded* part of v1's layout (a single taxonomy baked into scripts and sub-skill prose, with no reachable hub layer) and adds the *missing* part (graph connectivity); it does not throw away PARAG on the strength of an unproven complaint.

Two changes, independent of each other:

1. **The taxonomy becomes configurable** (`vault-schema.json`, §3.1) — required regardless of what SquidSquad's own install picks, because SquidSquad is general-purpose (marketing/ops/content teams, not just SWE) and a hardcoded taxonomy is wrong for installs that aren't SquidSquad-on-SquidSquad.
2. **SquidSquad's own default profile keeps PARAG** (§3.2) — the folders don't change — but gains a genuine **hub/connective layer** (dmp-web's missing-in-v1 piece, gap G6 in the comparison doc) and a **traversal-budget** classification per type, so search can walk the graph instead of grepping a flat pile.

### 3.1 The type registry — `vault-schema.json`

Each install's vault ships a `vault-schema.json` at the vault root defining its own note types. Nothing in the engine, the validator, or the templates hardcodes folder names — everything reads this registry.

```json
{
  "traversalBudget": 2,
  "searchTopK": 12,
  "tieBreakWeights": { "used": 2.0, "impression": 0.25, "walked": 0.5, "recency": 0.25 },
  "types": {
    "<type-name>": {
      "folder": "<folder>",
      "traversal": "free | budgeted",
      "weight": 0.0-1.0,
      "hub": true | false
    }
  }
}
```

- **`traversal: free`** — connective/hub types. Free to traverse — following a wikilink through one of these doesn't cost budget. Dense knowledge notes can cluster around them without the traversal budget running out before reaching related content.
- **`traversal: budgeted`** — dense knowledge types (SquidSquad's galaxy leaves). Each hop through one of these costs 1 unit of `traversalBudget` (default 2, per dmp-web's tuned value) — keeps search on-topic instead of wandering the whole graph.
- **`hub: true`** — marks a type as the connective layer specifically (a stronger signal than `traversal: free` alone — used by §3.3's hub-linking convention and by the search engine's ranking to slightly favor hub notes as entry points).
- **`weight`** — per-type multiplier in the ranking tiebreak (§6.2), separate from the traversal classification.

An install customizes its taxonomy by editing this file — no code or sub-skill change required. `vault-init`, `vault-create`, `vault_check.py`, and the search engine all read it.

### 3.2 SquidSquad's own default profile — PARAG kept, hub layer added

```json
{
  "traversalBudget": 2,
  "searchTopK": 12,
  "tieBreakWeights": { "used": 2.0, "impression": 0.25, "walked": 0.5, "recency": 0.25 },
  "types": {
    "project":  { "folder": "projects",  "traversal": "free",     "weight": 0.8, "hub": true },
    "area":     { "folder": "areas",     "traversal": "free",     "weight": 0.8, "hub": true },
    "resource": { "folder": "resources", "traversal": "free",     "weight": 0.6, "hub": false },
    "decision": { "folder": "galaxy",    "traversal": "budgeted", "weight": 1.0, "hub": false },
    "pattern":  { "folder": "galaxy",    "traversal": "budgeted", "weight": 1.0, "hub": false },
    "learning": { "folder": "galaxy",    "traversal": "budgeted", "weight": 1.0, "hub": false },
    "system":   { "folder": "systems",   "traversal": "free",     "weight": 0.8, "hub": true }
  }
}
```

The folder layout stays PARAG, unchanged:

```
.squidsquad/vault/
├── BRIEFING.md         # active-context summary, ~50 lines target
├── vault-schema.json   # the type registry above
├── projects/           # active project context, goals, constraints
├── areas/              # ongoing concerns: human prefs, code conventions
├── resources/          # reference material, external docs, research
├── systems/            # NEW — hub notes for subsystems the squad keeps learning
│                        #   about (harness, event bus, compose pipeline, tracker,
│                        #   pr_merge, vault itself, ...): connective tissue with
│                        #   no actionability semantics, just a place galaxy
│                        #   leaves link INTO
├── archives/            # shipped features, closed decisions (now: status:archived
│                        #   on any type, no forced folder move — see §3.4)
├── galaxy/              # atomic knowledge notes (Zettelkasten):
│                        # decision-*, pattern-*, learning-*
└── .obsidian/           # optional Obsidian app config (gitignored)
```

**What's new**: `systems/` — the one gap PARAG genuinely had no answer for. §11.4 of v1 (gap G6, "no connective entity layer") observed that galaxy notes are 95% flat leaves with almost no hubs, so even a working search engine would have little graph to traverse. `systems/` notes are entity references for subsystems the squad repeatedly learns about — one note per subsystem (harness, event bus, compose pipeline, tracker, pr_merge, launcher, vault itself), each accumulating inbound wikilinks from the galaxy leaves that touch it. This is the direct fix for G6, and it's additive — nothing existing moves.

**What's dropped**: `style-*` galaxy notes (zero ever written in ~3 months of operation, per v1 §10.2 — folded into `pattern-*`, no evidence a fourth prefix was ever needed) and the `pattern-posture-*` subtype tag (superseded by `system` hub notes for cross-cutting principles — a posture is really "a decision that spans multiple systems," which the graph now expresses via wikilinks rather than a special tag).

**Migration cost**: near-zero for existing content — every current galaxy/areas/projects/resources note keeps its folder and (mostly) its type. The only *new* content required is authoring the initial `systems/` hub set (~7-10 notes) and retroactively linking existing galaxy leaves to the hub they're about — this is the M2 distillation pass from `VAULT-COMPARISON-DMPWEB.md` §9.5.

### 3.3 Hub-linking convention

A galaxy note SHOULD wikilink to at least one `systems/` hub if its subject matter clearly belongs to one (e.g., a `learning-*` about a harness restart bug links `[[harness]]`). This isn't enforced at write time (a false requirement would just get rubber-stamped), but `vault_check.py`'s Level 2 sweep flags galaxy notes with zero hub links as a maintenance signal — "orphaned from the graph" is a distinct, cheaper-to-fix defect from "orphaned from any other note" (v1's existing orphan check).

### 3.4 How notes move — archived by status, not by folder

v1 moved notes physically from an active folder to `archives/` on archival. v2 drops the forced move: any note's `status:` flips to `archived` in place. Two reasons this is better, both learned from dmp-web:

1. **Simpler engine.** The search engine and the file-path-based dedup logic don't need a "did this note's path change" special case — a note's identity (its path) never changes on status transitions, only on explicit rename (§4.5-equivalent, still a distinct operation).
2. **Ranking, not relocation, does the work.** §6.2's ranking formula scores `superseded`/`archived` notes near zero (still discoverable via direct search, just never surfaces as a default top-K result) — the same effect v1's folder-move achieved, without a file-move needing to happen at all.

`archives/` survives as a *type* (`status: archived` on any note, any folder) rather than a folder notes get physically relocated into. Existing physically-archived v1 notes migrate in place (folder stays, `status:` already says `archived`) — no data movement needed at migration time.

### 3.5 Templates

Vault templates live at `references/vault-templates/` and are the seed content for new notes — framework-shipped, only consulted by vault sub-skill operations, never read at agent runtime. What changes in v2: **the template set is derived from the type registry, not a hardcoded list.** Every type registered in `vault-schema.json` (§3.1) has a corresponding template (`<type>.md`), resolved by folder+type at note-creation time; an install that registers a custom type supplies a template for it (falling back to a generic skeleton if absent). Plus one special template outside the registry: `briefing.md` (the `BRIEFING.md` skeleton + section order, §5 — BRIEFING is not a typed note).

For SquidSquad's own profile (§3.2) that means: `project.md`, `area.md`, `resource.md`, `system.md` (new — hub-note skeleton), `decision.md`, `pattern.md`, `learning.md`. The v1 `style.md` template is deleted with its type (§4.2). Templates are not subject to the §4 frontmatter spec themselves; their job is to produce notes that conform.

---

## 4. Entity model

### 4.1 By folder

Derived entirely from the install's `vault-schema.json` (§3.1) — the table below is SquidSquad's own default profile (§3.2), not a framework-hardcoded mapping.

| Folder | Entity types | Traversal | Lifespan | Growth model |
|---|---|---|---|---|
| `projects/` | `project` | free (hub) | While project active | One note per project; updated as scope evolves |
| `areas/` | `area` | free (hub) | Ongoing | Few notes (typical: human-profile, code-conventions); grow freely |
| `resources/` | `resource` | free | While referenced | One note per reference; prefer linking to externals |
| `systems/` | `system` | free (hub) | Forever (connective) | ~7-10 initial notes (harness, event bus, compose pipeline, ...); grows slowly, one per subsystem the squad repeatedly learns about |
| `galaxy/` | `decision`, `pattern`, `learning` | **budgeted** | Forever (Zettelkasten) | Atomic; max ~500 lines each; split if larger |

`archives/` is **retired as a folder** (§3.4) — archival is a `status:` value on any note, any type, in its existing folder.

### 4.2 By note name prefix (galaxy only)

| Prefix | Type | Purpose |
|---|---|---|
| `decision-` | `decision` | Architectural choice, trade-off, or commitment |
| `pattern-` | `pattern` | Reusable pattern discovered or confirmed |
| `learning-` | `learning` | Something that failed or succeeded unexpectedly |

**Dropped from v1**: `style-` (zero notes ever written; folds into `pattern-` — a style preference is just a pattern about how, not what) and the `pattern + posture` tag subtype (superseded by `systems/` hub notes, §3.2 — a posture is a decision that spans multiple systems, now expressed via wikilinks to the relevant `systems/` hubs rather than a special tag).

### 4.2a Consistency rules (folder + prefix + type)

Same two-field agreement as v1, now checked against the schema registry instead of a hardcoded table:

1. **Folder ↔ type**: a note's folder must match its `type:`'s registered `folder` in `vault-schema.json` (§3.1).
2. **Galaxy prefix ↔ type**: `decision-X.md` → `type: decision`; `pattern-X.md` → `type: pattern`; `learning-X.md` → `type: learning`.
3. **Validation**: `vault_check.py check-structure` reads `vault-schema.json` at runtime — an install that adds a custom type gets consistency checking for free, no code change needed. (v1's hardcoded version of this check is tracked at #10098, closed as superseded — the schema-driven version replaces it, not extends it.)

### 4.3 Required frontmatter (all notes)

```yaml
---
type: <per vault-schema.json registry>
tags: [list]                          # see Tag convention below
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active | superseded | archived
owner: pm | worker | verifier | dm | shared   # primary author role-class
community: <string>                   # optional — cluster label, set by vault-optimize (§7.3-equivalent)
subcommunity: <string>                # optional — sub-cluster within community
last_optimized: YYYY-MM-DD            # optional — last time an optimize pass touched this note
---
```

**Dropped from v1**: `confidence` (was write-only — nothing ever consumed it for ranking or filtering; operator decision 2026-07-18, reintroduce only if a real ranking need surfaces with an actual consumer) and `source` (conversation/review/observation/research — provenance-of-claim metadata that, like `confidence`, had no downstream consumer). `links` is also dropped — v1 auto-maintained a `links:` field from body wikilinks via `vault_optimize.py reindex`; v2's search engine computes the link graph live from body content instead, so a stored, driftable copy is unnecessary.

**Not in frontmatter, ever**: `impression` / `used` / `walked` / `last_impression` — these look like note-level counters but are **telemetry**, not content. They live in the git-tracked per-writer telemetry shards (§6.3) and are joined against note content at query/read time — never written to the `.md` file. This is a deliberate divergence from dmp-web (which bumps these as frontmatter counters, livable for one dev on one checkout but a merge-conflict generator for N agents in N clones — `VAULT-COMPARISON-DMPWEB.md` §9.4 P1). The shard design (§6.3) makes the conflict class structurally impossible instead of auto-resolving it — "notes stay pure content" was always the load-bearing half of the §9.4 rule, and it survives unchanged.

**Ownership note** (`owner:` field): unchanged from v1 — authored role-class of the note's content, `owner: shared` for content that benefits multiple roles. The pre-#6274 naming drift (`qa`/`skill` vs `verifier`/`worker`) and the `<role>` vs `<role>-lead` convention drift (v1 §10.3) both get swept during migration (§9.5 M1) rather than patched in place.

**Tag convention** (for searchability) — unchanged from v1:

- **Required**: at least one **domain tag** identifying the subsystem, feature, or area the note is about. Domain tags are **project-specific** — they reflect the vocabulary of the codebase the vault serves. Use whatever a teammate searching for related notes would naturally type.
- **Recommended**: one **category tag** identifying the kind of insight. Categories are **universal** across projects: `architecture`, `process`, `testing`, `convention`, `migration`, `incident`, `lifecycle`.
- **Optional, role-relevance**: `role:<name>` prefix when the note is most useful to one role.
- **Free-form**: any additional keywords for searchability.

**Empty values**: `tags: []` is not allowed (the required domain tag rule means at least one tag is always present).

### 4.4 Staleness — usage-based, not time-based confidence decay

v1 had a `confidence` field that decayed `high → medium → low` purely on time since `updated:` (§4.4 in the v1 snapshot). **This entire mechanism is dropped**, not adapted — it's the exact thing the dmp-web comparison identifies as inferior (`VAULT-COMPARISON-DMPWEB.md` §3.2/§9.2.6): a note that's old but heavily used decayed anyway (unless manually tagged `evergreen` at creation, which requires foresight); a note that's young but never consulted didn't decay at all despite being dead weight from day one.

**Replacement**: staleness is now a **usage** signal, computed from the telemetry ledger (§6), not stored on the note. The impressions report (§6.4, port of dmp-web's `vault-impressions-report`) classifies every note as:

- **Cold** — never surfaced by a search.
- **Surfaced-but-never-used** — shown in results repeatedly, never cited (`used`) by any consumer.
- **Stale** — was `used` at least once, but not in the last N days (config, default 90 — dmp-web's tuned value).

These three buckets feed `vault_optimize.py`'s pruning decisions (§7.3-equivalent) — the same *function* v1's time-decay served (deciding what to archive), computed from a signal that actually correlates with whether the note is helping anyone.

No `evergreen` opt-out tag exists in v2 — it's unnecessary once staleness is usage-based: a genuinely evergreen note gets `used` regularly by definition and never enters the Stale bucket.

### 4.5 Wikilinks

Bare wikilink syntax in the body: `[[note-name]]`. No aliases. Cross-note references resolve via filename match anywhere under `.squidsquad/vault/` — unchanged from v1.

**What changes**: the link graph is no longer a stored, auto-maintained `links:` frontmatter field (dropped, §4.3) — the search engine (§6.1) computes it live by parsing body wikilinks at query/index time. This removes an entire class of v1 drift risk (a `links:` field that's out of sync with the body because `reindex` didn't run) at the cost of the engine needing to parse bodies rather than trust cached frontmatter — an acceptable tradeoff at vault scale (hundreds, not millions, of notes).

**Broken-link validation**: `vault_check.py check-wikilinks` — same contract as v1 (walks all notes, flags any `[[name]]` whose target doesn't exist, exit 1 if any found).

**Note renames**: v1's proposed fix was a CI/CD enforcement layer (#10100, closed as superseded by this redesign). v2's answer is different and more durable: the migration script (`VAULT-COMPARISON-DMPWEB.md` §9.5 M1) already builds an old→new redirect map and rewrites every wikilink vault-wide as part of the one-time v1→v2 migration. Post-migration, the same redirect-map mechanism is the generalizable answer to *any* future rename — a rename becomes "run the redirect tool," not "hope nobody renamed a file by hand." Whether to formalize this as an enforced CI gate (v1's prohibit-vs-reconcile question) is deferred — not needed for the TRD to be complete, since the redirect-map tool makes renames cheap to fix after the fact even without a gate.

---

## 5. BRIEFING.md — the hot layer

`.squidsquad/vault/BRIEFING.md` is the **active-context summary** every agent reads at session start and re-reads when more than one cycle has passed. It is the one vault file injected *wholesale* into agent context rather than reached through search — the hot layer over the searchable store.

**Outside the engine, by design.** BRIEFING.md is excluded from the search index, the ranking, and telemetry (`VAULT-COMPARISON-DMPWEB.md` §9.2.3): it is a *digest* of the vault and the tracker, not a knowledge note — indexing it would double-count every note it summarizes, and impression-counting a file every agent reads unconditionally would only add noise to the usage signal. It carries no §4 frontmatter and no `type:` — it is not a registry entity.

Spec (all carried from v1, now stated prescriptively):

- **Target length ~50 lines.** The hot layer's value is inverse to its size — it is read every session by every agent, so every line is a standing per-session token cost multiplied by the roster.
- **Trim-or-graduate, never delete.** Content that outgrows the budget graduates to a galaxy note or a dated archive note (e.g. `archives/briefing-active-priorities-<range>.md`) with a pointer if still relevant. BRIEFING is a cache; the vault proper is the store.
- **Update trigger: staleness check every cycle, including quiet cycles.** Fixing stale fields (version mismatch, agent-list mismatch, priority list diverging from tracker) does **not** consume the vault-remember write budget — staleness repair is hygiene, not knowledge capture.
- **New-content token budget** per `.squidsquad/config.md` (`BRIEFING Token Budget`).
- **Sections**: Active Priorities, Recently Shipped, Core Architecture, Recent Decisions, Human Preferences (a pointer to `[[human-profile]]`, never a copy), Constraints & Blockers, Team State.

**New in v2 — the auto-digest section** (target state; depends on §6 telemetry being live): a small auto-generated **Vault Pulse** section built from telemetry aggregates — hottest notes this period, newly added binding rules, missed-consultation count (§9's outcome-linking). This is the `VAULT-COMPARISON-DMPWEB.md` §7 4.4 leapfrog item: it keeps the hot layer honest (the digest reflects measured usage, not what an agent remembered to write) and gives the operator a vault health pulse for free. The rest of BRIEFING stays hand-maintained by the write path exactly as in v1.

---

## 6. Consumption engine — search, ranking, telemetry

This section is the heart of v2: the consumption side v1 never had. It specifies three contracts — the **event model** (§6.1), the **search + ranking contract** (§6.2), and the **telemetry storage** (§6.3) — plus the two consumers built on them (§6.4 impressions report, §6.5 compaction).

**Contracts, not implementation.** Per `VAULT-COMPARISON-DMPWEB.md` §10.2/§10.3, the engine is planned to be consumed as the portable dmp-web extraction invoked via the Skill tool (two feasibility checks still pending — see §7/§8). The contracts below hold regardless of how the engine is packaged: they are what any implementation must satisfy, and what the sub-skills and verifier check against.

### 6.1 Event model

Three counters, written by different parties, disjoint per run:

| Counter | Meaning | Written by |
|---|---|---|
| `impression` | The note surfaced in a search's top-K results | The engine, automatically, per search |
| `walked` | The engine traversed *through* this note's wikilinks to reach a result (connective credit) | The engine, automatically, per search |
| `used` | A consumer actually cited the note in a committed artifact (receipt section, research doc, PR body) | **Consumers only** — never the engine |

The engine/consumer split is load-bearing: `impression` measures what search *offers*, `used` measures what work *actually consumed*. Conflating them (letting the engine write `used`, or counting reads as usage) would collapse the signal that makes §4.4's staleness buckets and §6.2's ranking meaningful.

Every event is one JSONL record: `{id: <uuid>, ts, agent, task, slug, counter}`. `task` (the tracker issue number) is deliberately carried on every event — per-task attribution is richer than dmp-web's flat per-note integers and is what enables outcome-linked telemetry (§9: joining events against tracker outcomes to detect missed consultations). `id` is the dedup key (§6.3).

A `--no-write` dry-run flag suppresses event emission for diagnostic searches — telemetry should measure real consumption, not debugging.

### 6.2 Search contract & ranking

- **Tiered matching**: filename match > inbound-wikilink match > tag match > content match. Tier is the primary sort key — a filename hit always outranks a content hit.
- **Budgeted graph traversal**: from each matched note, the engine follows body wikilinks outward. Hops through `traversal: budgeted` types (galaxy leaves) cost 1 unit of `traversalBudget` (§3.1, default 2); hops through `traversal: free` types (hubs) are free. This keeps traversal on-topic while letting dense knowledge cluster around hubs without exhausting the budget (§3.2's `systems/` layer is what makes this productive).
- **Two-stage ranking**: Stage 1 orders by match tier. Stage 2 tiebreaks within a tier by the telemetry-weighted score — `used×2.0 + impression×0.25 + walked×0.5 + recency×0.25` (weights from `vault-schema.json` `tieBreakWeights`, tunable per install) — multiplied by the type's `weight` (§3.1) and by a status multiplier: `status: superseded|archived` rank near zero (still discoverable by direct query, never a default top-K result — this is what lets §3.4 retire the physical `archives/` move).
- **Top-K output** (`searchTopK`, default 12): metadata-only JSON — paths, tiers, scores, link map. The consuming agent Reads the note bodies it chooses; the engine never inlines content. Each note in the returned top-K gets an `impression` event; traversed connectors get `walked`.
- **Graceful degradation**: when telemetry is unavailable (fresh install, cold start, shard read failure), Stage 2 falls back to tier + recency + type weight. Search never blocks on telemetry.
- **Raw-grep ban**: sub-skills must reach the vault through the engine, never `grep -r`. The rationale is telemetry blindness, not style: a grep that finds the right note leaves no `impression`/`used` trail, so the note reads as dead to §6.4 and gets pruned — silent consumption actively corrupts the maintenance signal. (v1's sub-skill grep snippets are replaced wholesale at migration.)
- **BRIEFING.md is excluded** from index, ranking, and telemetry (§5).

### 6.3 Telemetry storage — git-tracked per-writer shards

> **Design status**: PM-recommended working design (2026-07-18), operator lock-in pending. Supersedes `VAULT-COMPARISON-DMPWEB.md` §9.4 point 1 (2026-07-12: harness-owned gitignored store) — see §10.5 for the full supersession rationale.

**Why §9.4's harness-local store had to change**: a SquidSquad install can run **multiple independent harness instances** — e.g. each teammate runs their own harness against their own clone, with no shared always-on server. A harness-local store fragments telemetry into N per-teammate partial pictures, defeating team-wide ranking. This is the same many-independent-checkouts topology dmp-web has — which is why dmp-web routes telemetry through git. dmp-web's *mechanism* (frontmatter counters + a custom `vault-note` merge driver) is still not the model: custom merge drivers require per-clone opt-in registration, and counters-in-notes is the conflict *source*, not a solution.

The design — telemetry is a grow-only counter, a solved distributed-systems shape (CRDT G-counter): **per-writer shards, sum at read**:

1. **Per-harness-instance, append-only JSONL shards, git-tracked**: `.squidsquad/vault/.telemetry/<harness-instance-id>.jsonl`. Each harness instance appends only to its own shard — cross-teammate merge conflicts are *structurally impossible*, not auto-resolved.
2. **`merge=union` in `.gitattributes`** on `.telemetry/*.jsonl` — git's built-in union strategy, no per-clone registration, works for every clone on day one. It covers the one residual divergence case (the same shard diverging across machines — restored backup, cloned VM); union-merge on append-only lines is safe because readers dedupe by event `id`, so a double-merged line is harmless.
3. **Sync layer = the git remote already serving as the bus.** `git pull` = telemetry sync; no new infrastructure — consistent with the house philosophy that git is the audit trail and GitHub the coordination bus.
4. **Read path**: any consumer (ranking Stage 2, impressions report, viewer) reads all shards + aggregates, dedupes by `id`, sums per note.
5. **PR-noise control**: shard commits ride routine `main` commits only, **never task branches** — telemetry stays out of review diffs. This preserves the intent behind §9.4's original "never in a PR" directive under the new storage model.
6. **Durability** (§9.6 open decision #5) largely **dissolves**: telemetry lives in repo history; a lost machine costs only its unpushed events (bounded by push cadence). No snapshot mechanism needed.

**What survives from §9.4 unchanged**: notes stay pure content, forever — no counter fields in frontmatter (§4.3). That rule was always the load-bearing half.

**Cloud agents considered and rejected** as the sync/storage layer (operator floated, 2026-07-18): ephemeral compute is not a datastore — the data still needs a durable home, which is either a hosted DB (new auth/availability/cost/privacy surface; note slugs leak repo content to a third party) or the git repo, i.e. where this design already is. Legitimate future niche: running scheduled compaction/report passes for installs with no always-on machine — optional convenience, not architecture.

### 6.4 Impressions report

The port of dmp-web's `vault-impressions-report`: reads the shards (§6.3), joins against the note inventory, and buckets every note (per §4.4):

- **Cold** — never surfaced by any search.
- **Surfaced-but-never-used** — repeatedly offered in top-K, never once cited by a consumer.
- **Stale** — `used` at least once, but not within the last N days (config, default 90).

The report is the **purge signal**: it feeds `vault_optimize.py`'s pruning/archival proposals (§7-equivalent) and PM's improvement scan. It replaces v1's time-based confidence decay entirely — the same maintenance function, computed from a signal that correlates with whether the note is helping anyone.

### 6.5 Compaction

A quiet-cycle maintenance pass rolls events older than N days into a **per-writer aggregate file** (still per-writer, so still conflict-free by construction), truncating the raw shard. Aggregates preserve per-note, per-counter totals plus last-event timestamps — sufficient for §6.2 ranking and §6.4 bucketing; per-task attribution older than the compaction horizon is dropped (outcome-linking consumes recent events, not deep history). Readers treat `aggregate + live shard` as one logical stream.

---

## 7. The sub-skills `[v1 — not yet migrated]`

All vault behavior is encoded as markdown fragments under `references/sub-skills/`. Each fragment is inlined into the consuming agent's composed `CLAUDE.md` by `compose.py`. Four distinct sub-skills are described below. The vault is **shared institutional knowledge** — every role (PM, verifier, worker, DM) has full R/W access via `vault-protocol`; the historical `vault-protocol-slim` read-only variant was retired in #11331 (Iter 56) when verifier/DM were granted write access for their lane-specific patterns (verifier: testing-and-verification learnings; DM: delivery patterns).

**Execution model**: vault sub-skills split into two execution lanes by weight. The principle: keep the consuming agent's context lean — anything that requires meaningful reasoning over vault content runs out of process.

- **Inline (runs in the consuming agent's context)**: `vault-protocol` (continuous read/write rules; the agent is doing real work the vault must record) and `vault-optimize` (thin wrapper around `vault_optimize.py run` — almost entirely mechanical, no reasoning to offload).
- **Background subagent (Agent tool, fresh context, `sonnet`)**: `vault-remember` (end-of-cycle reflection: 4-category candidate evaluation, dedup near-match decision, write/skip/update judgment per candidate) and `vault-synthesis` (cross-agent theme detection, convergence detection, posture drafting). Only the structured write decisions (and any new note paths) return to the main agent — never the reflection transcript.

Model choice rationale: vault reflection is pattern-matching + dedup judgment + small write decisions, not multi-step planning. Sonnet is the same tier already used for skill and DM subagent spawns (see `feedback_skill_sonnet_subagents`, `feedback_dm_sonnet_subagents`); Opus is overkill, Haiku underpowered for the dedup near-match call. The pin is by tier (`sonnet`), not a specific version — version selection follows the Agent-tool model alias, which tracks the latest in the tier.

Each sub-skill's **Cycle integration** line below names its lane.

### 7.1 `vault-protocol`

**Path**: `references/sub-skills/common/vault-protocol.md`

**Behavior**: Provides the full read/write protocol for vault interaction. Defines five operations the consuming agent performs as part of normal work:

- `vault-init` — if `.squidsquad/vault/` does not exist, create the PARAG structure (`projects/`, `areas/`, `resources/`, `archives/`, `galaxy/`), bootstrap `BRIEFING.md`, `areas/human-profile.md`, and `projects/<project-name>.md` from `references/vault-templates/`, plus `.obsidian/` for the Obsidian app. Idempotent.
- `vault-create` — pick the correct folder by entity type (per §4.1), name with kebab-case (galaxy notes use the `decision-`/`pattern-`/`learning-`/`style-` prefix per §4.2), copy the folder's template, fill frontmatter per §4.3 and body per template, use bare `[[wikilinks]]` per §4.5. Creation threshold: only create if the content is reusable beyond this cycle — transient observations belong in the iteration log.
- `vault-update` — read the full note first, surgical edits only, never delete existing content (mark superseded via `status` frontmatter instead), update the `updated:` date, append a Changelog body entry, then run `vault-check` Level 1.
- `vault-search` — four modes: by tag, by type, by keyword, by wikilink traversal (1-hop outbound + inbound, max 2-hop). Max 10 results sorted by recency; cache within a cycle.
- `vault-check` Level 1 — runs automatically after every `vault-create` or `vault-update`; validates the written note plus all notes within 2 wikilink hops against the §4 spec.

**Cycle integration**: Composed into the consuming agent's CLAUDE.md at session start; rules apply continuously during agent work, not at a single step. **Lane**: inline (the agent itself is doing the read/write the protocol governs).

**Scripts used** (from §8): `vault_check.py dedup-check` (before any create), `vault_check.py` Level 1 (after every write), `vault_entity.py` (template-backed note creation/update).

**Outputs**: New or updated `.squidsquad/vault/**/*.md` notes; never deletes.

**Source-vs-spec drift**: source file still references the dropped `links` frontmatter field, the dropped `source: code` value, the unimplemented "auto-maintain `links` frontmatter" behavior, and the pre-#6274 `owner:` enum values (`qa`, `skill` instead of `verifier`, `worker`). Sync tracked in #10098.

**Per-role write lanes**: every role uses the full `vault-protocol`. What differs is what each role writes about — patterns from its own lane (PM: coordination/decision; worker: implementation; verifier: testing-and-verification; DM: delivery). The verifier specifically does NOT use vault writes to revisit or rebut decisions made by PM/worker — the verifier's vault contribution is testing craft, not design call. Project-adaptation prose (under `.squidsquad/project/<role>.md`) names the per-role discipline; the universal write budget + 4-gate logic still applies (max 2 writes/cycle).

### 7.2 `vault-remember`

**Path**: `references/sub-skills/common/vault-remember.md`

**Behavior**: End-of-cycle reflection. Runs two responsibilities in order:

1. **BRIEFING.md staleness check** — runs every cycle, including quiet cycles. Compares `BRIEFING.md` key fields (version, active agents, current priorities) against `.squidsquad/config.md` and the tracker; updates any stale field. Staleness fixes do NOT consume the write budget.
2. **Reflection** — gated by a quiet-cycle check (skipped if the cycle did no real work). Evaluates this cycle's iteration log for vault-worthy candidates in five galaxy categories: DECISIONS, PATTERNS, LEARNINGS, STYLES, plus PROJECT CONTEXT (which targets `projects/` updates, not a galaxy prefix). Each candidate runs through four deterministic gates IN ORDER: (1) write budget remaining (default 2 per cycle, per `.squidsquad/config.md` `Vault Remember > Writes Per Cycle`), (2) dedup-check against existing notes by title + tags, (3) reusability beyond this cycle, (4) would a fresh agent benefit? Only candidates passing all four are written. When more than 2 pass, priority is decisions > learnings > patterns; surplus is deferred to iteration-log notes as `Vault-worthy but deferred (budget): <description>`. Behavioral or personality directives are explicitly out of scope — those go to soul-shepherd (observed signals) or L4 (explicit directives), not the vault.

**Cycle integration**: Post-cycle Step 4b. Gated by the per-cycle quiet check only — always-on, no feature toggle (the 4-gate filter already provides sufficient noise control; a blunt on/off flag on top earns no use case). **Lane**: background subagent (`sonnet`). The consuming agent hands the iteration log + write-budget + dedup-tool access to the subagent; the subagent runs the 4-gate evaluation and returns a structured list of `{action: write|update|skip, path, type, body, reason}` decisions plus the resulting note paths. The reflection transcript stays out of the consuming agent's context.

**Scripts used** (from §8): `vault_remember.py is-quiet`/`reset-writes`/`write-budget`/`inc-writes`/`briefing-budget` (gating and accounting), `vault_check.py dedup-check` (gate 2). (The legacy `config.py get vault-remember` enabled-flag read has been retired — the sub-skill is always-on and self-gates per its own per-cycle conditions.)

**Outputs**: Up to 2 new `.squidsquad/vault/galaxy/*.md` notes per cycle (`decision-*` / `pattern-*` / `learning-*` / `style-*`), optional `projects/*.md` updates from the PROJECT CONTEXT category, optional `BRIEFING.md` staleness updates, iteration-log notes for deferred candidates.

### 7.3 `vault-optimize`

**Path**: `references/sub-skills/common/vault-optimize.md`

**Behavior**: Quiet-cycle housekeeping. Runs after the improvement-scan check (if the scan ran this cycle, optimize skips). Activates only when the vault has 20+ notes. Invokes `vault_optimize.py run`, which performs four bundled operations:

1. **Prune** — auto-archive galaxy notes that are both stale (60+ days since `updated:`) and orphaned (no inbound wikilinks). Notes created today are never pruned.
2. **Confidence decay** — apply the §4.4 decay rules (high → medium at 60 days, medium → low at 120 days, terminal at `low`). Notes tagged `evergreen` are exempt.
3. **Reindex** — walk all notes and rebuild each note's `links:` frontmatter to match its body `[[wikilinks]]`; this link data is what prune-orphan-detection and relevance scoring read.
4. **Relevance scoring** — compute link-count + recency + confidence scores, write to `.squidsquad/vault/.relevance-index.json` (gitignored).

The sub-skill also exposes a pending-questions queue: optimization-surfaced questions that need human input (e.g., "should these similar notes be merged?") are added via `vault_optimize.py add-question`, surfaced in the status bar, and mentioned in the next agent check-in.

**Cycle integration**: Quiet cycle only, after the improvement-scan check. Gated by the 20+ note count — always-on, no feature toggle (the quiet-cycle + note-count gates already provide sufficient activation control). **Lane**: inline (thin wrapper around `vault_optimize.py run` — no reasoning happens in the agent's context).

**Scripts used** (from §8): `vault_optimize.py run` (the all-in-one orchestrator), `vault_optimize.py add-question` (pending-question queue).

**Outputs**: Archived notes (moved from `galaxy/` to `archives/`); in-place confidence-decay frontmatter edits plus body changelog entries; `.relevance-index.json`; pending-question queue entries.

### 7.4 `vault-synthesis`

**Path**: `references/sub-skills/roles/pm/vault-synthesis.md`

**Behavior**: Cross-agent pattern detection. Maintains a synthesis cycle counter (separate from the improvement-scan counter); fires after 5 consecutive quiet cycles. Counter resets on real work or on a completed synthesis. Activation also requires the vault to have 10+ galaxy notes.

When triggered, the synthesis runs in five steps:

1. Gather galaxy notes modified since the last synthesis or in the last 7 days (whichever is shorter).
2. Detect recurring themes — same tags across notes from different agents, similar topics across owners, wikilink clusters that span agent boundaries.
3. Detect convergent decisions — separate decisions that imply a shared principle (e.g., "Hard error over silent fallback" + "never ship with gaps" → "explicit failure over silent degradation"). Convergences must be supported by 2+ distinct notes from different agents or contexts.
4. For each detected posture (max 1 per synthesis cycle), create a `pattern-posture-<name>.md` galaxy note with `type: pattern`, `posture` tag, `confidence: medium`, and body citing the source notes via wikilinks. Then file a pending agent task requesting human review.
5. Touch the `.last-synthesis` sentinel file and log to iteration summary.

Postures need explicit human approval before becoming active scan criteria for other agents — they are never auto-approved. Single-agent patterns are not postures; convergence across agents is the defining property.

**Cycle integration**: Quiet cycle, sub-skill composed only for PM (the designated synthesizer role; pluggability across role-classes is not implemented today). Gated by the 5-consecutive-quiet-cycle counter and the 10+ galaxy-note threshold. **Lane**: background subagent (`sonnet`). The synthesizer agent hands the recent-notes set to the subagent; the subagent runs theme/convergence detection and returns at most one posture descriptor `{name, principle, source-notes, body}` for the consuming agent to write via `vault-create` (plus the pending-review task body). Cross-note reasoning transcript stays out of the consuming agent's context.

**Scripts used** (from §8): `vault_check.py` Level 1 (after creating the posture note), `tracker.py create-task` (file the pending-review task).

**Outputs**: At most 1 new `pattern-posture-*.md` note per cycle; one pending agent task per posture; `.last-synthesis` sentinel file.

---

## 8. The four scripts `[v1 — not yet migrated]`

All mechanical vault operations are encapsulated in scripts under `references/scripts/`. Agents shell out to these from inside the sub-skills.

### 8.1 `vault_check.py`

Validates vault integrity. Subcommands:

| Subcommand | Purpose |
|---|---|
| `validate` | Full vault validation (all checks) |
| `check-frontmatter` | Validate frontmatter fields in galaxy notes |
| `check-wikilinks` | Find broken `[[name]]` references |
| `dedup-check --title <t> --tags <t>` | Used by `vault-remember` Gate 2 |
| `check-structure` | Validate the folder ↔ prefix ↔ type consistency rules (§4.2a) |
| `list-orphans` | List galaxy notes with no inbound wikilinks |
| `suggest-connections` | Suggest candidate wikilinks between topically-related notes |
| `check-size` | Warn on galaxy notes exceeding the ~500-line advisory ceiling (§4.1); advisory, not a hard-fail |

Runs **automatically after every vault-create or vault-update** (Level 1 — single note + 2-hop neighborhood). Level 2 (full-vault sweep with orphan + staleness detection) is on-demand only.

### 8.2 `vault_entity.py`

Entity extraction. Given a block of text (e.g., a tracker comment, iteration log entry), detects entity candidates (decision, pattern, learning, style) for vault-remember to consider. Subcommands:

| Subcommand | Purpose |
|---|---|
| `extract "<text>"` | Extract entities from inline text |
| `extract --file <path>` | Extract entities from a file |

### 8.3 `vault_optimize.py`

On-demand maintenance. Subcommands:

| Subcommand | Purpose |
|---|---|
| `full-sweep [--dry-run]` | Full pass (prune + decay + reindex + relevance) |
| `prune-scan [--dry-run]` | Archive stale (60+ days, unupdated) + orphan (no inbound wikilinks) galaxy notes |
| `consolidate-scan [--dry-run]` | Detect merge candidates (similar topics) |
| `decay-apply [--dry-run]` | Confidence decay (high→medium after 60d, medium→low after 120d) |
| `add-question --agent <r> --note <p> --question "<q>"` | Queue pending question for human |
| `reindex` | Rebuild `links:` frontmatter across all notes from their body wikilinks |
| `relevance-report` | Print the relevance-score ranking (from `.relevance-index.json`) |
| `pending-count` | Count queued pending-questions |
| `run` | Convenience alias for the full pipeline (see `vault-optimize.md`) |

Notes never created today are protected — prune never targets them.

### 8.4 `vault_remember.py`

Deterministic gates for vault-remember reflection. Subcommands:

| Subcommand | Purpose |
|---|---|
| `is-quiet <role>` | Was this cycle quiet? (exit 0 = quiet, skip reflection) |
| `write-budget <role>` | Remaining write budget this cycle |
| `inc-writes <role>` | Increment write counter after a successful write |
| `reset-writes <role>` | Reset counter at start of reflection |
| `briefing-budget` | Remaining token budget for BRIEFING.md additions |
| `effective-confidence <note>` | A note's current confidence after time-decay is applied |
| `note-count` | Total vault note count (backs the 20+/10+ activation gates) |
| `decay-scan` | List galaxy notes currently due for confidence decay |

---

## 9. Cycle integration

v1 touched the vault at three points (boot read, an advisory "consult before work," post-cycle write sweep) — all of them **optional in practice**: nothing verified the consult happened, so it usually didn't (the root finding of the dmp-web comparison). v2's cycle integration is the **consumption pipeline**: vault touchpoints become mandatory, verifiable steps that produce **committed receipts**, with telemetry (§6) flowing from every touch. Nothing about the pipeline blocks at *runtime* — the enforcement is process-level (verifier gates), preserving the non-blocking philosophy (§9.6).

### 9.1 Boot — BRIEFING read

Unchanged from v1: every agent reads `BRIEFING.md` (§5) at session start and re-reads when stale. No write, no telemetry (§5 exclusion).

### 9.2 Task filing — context injection (PM intake)

When PM files a task, the intake flow runs an engine search (§6.2) on the task's keywords and appends a **`## Vault context`** section to the issue body — top-K note names + one-line relevance each. Dev agents read the issue body first (house rule), so relevant vault context arrives *with the task*, deterministically, before any agent has to remember to search. The search's `impression` events attribute to the task number. This is the leapfrog item dmp-web structurally can't do (single-agent, no intake step) — `VAULT-COMPARISON-DMPWEB.md` §7 4.1.

### 9.3 Task pickup — mandatory consultation + receipts

Before implementing, the working agent's task flow runs two engine-backed steps whose *output is committed*, not just performed:

1. **Context consultation**: an engine search on the task's subject; the result lands in the task artifact (CONTEXT.md / research doc / PR body) as a **`## Vault context consumed`** section — wikilink + one-line relevance per cited note, or an explicit "none relevant." Cited notes get `used` events with the task number.
2. **Rules matching**: a two-stage tag-catalog match against the binding-rules lane; the result lands as **`## Applicable rules`** (explicit "none matched" required). Matched rules get `used` events. *(The rules lane's placement in the type registry — a dedicated `rule` type vs. binding-flagged notes in an existing type — is an open decision, §11; the receipt contract here is independent of where the rules live.)*

The step *cannot be skipped silently*: an artifact without the receipt sections is an incomplete artifact (§9.4). "None relevant" is always available, so the cost floor is one honest line — the receipt is evidence the search ran, not busywork.

### 9.4 Verification — receipt enforcement

The verifier adds two cheap checks to every verification pass:

1. The receipt sections (`## Vault context consumed`, `## Applicable rules`) exist in the task artifacts.
2. The implementation does not violate any rule listed in `## Applicable rules`.

Missing receipt = back to dev, same as any other gap (zero-gap gate). This is the step that turns dmp-web's single-agent self-discipline into **team-enforced process** — the multi-agent structure is what makes the pipeline verifiable rather than aspirational.

### 9.5 Ship — capture-at-ship + end-of-cycle sweep

Two complementary write paths (dmp-web has only the first):

1. **Capture-at-ship** (worker, pre-PR): decide whether the task produced durable knowledge (decision / root cause / pattern — with a skip-list for chores); if yes, write the note **on the feature branch so it ships in the same PR** as the change that produced it, issue number in the note's references. Counts against the write budget; dedup gate applies.
2. **End-of-cycle `vault-remember`** (every role, post-cycle): the sweep for what per-task capture missed. Carried from v1 with one structural change: **dedup reroutes through the engine** — the gate calls the engine's search instead of v1's title/tag `dedup-check`, and adopts **prefer-update-over-create**: the top-ranked hit above a similarity threshold becomes the merge target; a new note is created only when nothing ranks. Most cycle output becomes *appends to existing notes* — the correct pressure for a vault that should consolidate, not sprawl. Write throttles survive v1 unchanged (budget, quiet-gate, role lanes — autonomy needs them).

### 9.6 Quiet cycles — maintenance

- **vault-optimize**: the analyze phase is **harness-scheduled** (not "hope a quiet cycle notices" — the v1 bug where `vault_optimize.py run` never fired). Queue ordered by `last_optimized` (14-day cutoff); community detection + subsplit; analyze-then-apply with **contradiction findings human-gated** as HITL tracker tasks, never auto-applied. Pruning/archival proposals consume the impressions report (§6.4) — usage-based, replacing v1's time decay.
- **Telemetry compaction** (§6.5) rides the same maintenance window.
- **vault-synthesis** (PM, cross-agent pattern detection): carried from v1, still human-gated. Its output target changes with §3.2: cross-cutting posture notes become `systems/` hub content or `pattern-*` notes (the `pattern-posture-*` subtype is retired).

### 9.7 Outcome-linked telemetry (target state)

Joining the event stream (§6.1, per-task attribution) with tracker outcomes — the second leapfrog dmp-web can't reach (it has no tracker):

- A task that fails verification, where the failure matches an existing note that was **never consulted** during §9.3 → a **missed-consultation** finding: direct evidence the read side failed. PM's improvement scan reviews these.
- A note repeatedly `used` by tasks that pass verification first-try → ranking boost signal.

dmp-web measures *usage*; this measures *effectiveness*. Depends on §6 telemetry + §9.3 receipts being live first — sequenced last.

### 9.8 Git integration

- Vault notes stay under `.squidsquad/vault/` on **main**, committed as part of normal cycle commits — unchanged from v1.
- **New**: telemetry shards (§6.3) also live under the vault tree and ride **routine main commits only, never task branches** — review diffs stay telemetry-free.
- The one PR that legitimately carries a vault note is capture-at-ship (§9.5.1) — a content note, deliberately atomic with its change.

### 9.9 Failure modes and recovery paths

The vault remains **non-blocking and degradation-tolerant** — no vault failure ever blocks a cycle from committing. v1's file-level failure rows (malformed note mid-write, missing counter state files, BRIEFING budget exhaustion, idempotent re-init, crash-before-commit) carry forward unchanged and are not repeated here. What changes or is new in v2:

| Failure | v2 behavior |
|---|---|
| **Engine unavailable** (Skill invocation fails, package missing) | Consultation steps (§9.2/§9.3) degrade to an honest receipt line stating the engine was unavailable — never a fabricated "none relevant." The verifier treats an engine-unavailable receipt as pass-with-note; PM sees recurrences via improvement scan. Search never blocks a cycle. |
| **Telemetry write fails** (shard I/O error) | Event dropped with a log line. Telemetry is operational signal, not content — losing an event is fine, blocking work on it is not. |
| **Telemetry unavailable at read** (cold start, shard read failure) | Ranking degrades to tier + recency + type weight (§6.2). Impressions report skips the run. |
| **Same-shard divergence across machines** (restored backup, cloned VM) | `merge=union` auto-resolves (§6.3); duplicate lines are read-time-deduped by event `id`. |
| **Cross-writer shard conflict** | Structurally impossible — each writer appends only to its own shard (§6.3). |
| **Merge conflict on a vault *note*** | Unchanged from v1: keep both versions, never discard vault content; human or PM reconciles. Rarer in v2 — prefer-update-over-create (§9.5) plus receipts reduce blind concurrent creation of near-duplicate notes. |
| **Contradiction found by optimize analyze** | Never auto-applied — filed as a HITL tracker task (§9.6). |
| **Receipt section missing from an artifact** | Not a runtime failure — a verification gap (§9.4): back to dev. |

### 9.10 What the vault does NOT do (v2)

- **No automatic propagation across SquidSquad installs.** Per-install vaults; no federated layer. (The cross-install memory-layer vision remains aspirational and out of scope here.)
- **No embeddings, no RAG.** The engine is tiered lexical matching + graph traversal + telemetry ranking (§6.2) — a CLI with a JSON contract, pinned by tests. The second-brain RAG vision stays a separate, later track.
- **No write-ahead log or transactional guarantees.** Writes are file writes + git commits.
- **No per-note access control.** Access is role-class-level; every role has R/W via the vault protocol.
- **No runtime blocking on any vault subsystem.** Enforcement is process-level (§9.4), never a cycle-blocking runtime gate.

---

## 10. Current state inventory (snapshot 2026-05-24) `[v1 — not yet migrated]`

> **Freshness note (2026-06-20):** the counts in this section are the 2026-05-24 snapshot and are now materially stale — the live `galaxy/` holds **~93 notes** (decision 19 / learning 56 / pattern 18; still 0 `style-*`, 0 `pattern-posture-*`) vs the 28 below, `archives/` has **1** note (not 0), and `BRIEFING.md` is **~102 lines**. The section *structure* (what is counted, the buckets, the distributions tracked) still holds; only the numbers are dated. Re-snapshot on the next VAULT-ARCH revision.

What is actually in `.squidsquad/vault/` right now in this repo:

### 10.1 Note counts

| Location | Count | Notes |
|---|---|---|
| `BRIEFING.md` | 1 (88 lines) | Active context, last updated cycle ~1499 per content; carries `status: active` in its header so it is counted in the §10.5 status distribution |
| `projects/` | 2 | `agent-communication-layer.md`, `squidsquad.md` |
| `areas/` | 2 | `human-profile.md`, `code-conventions.md` |
| `resources/` | 1 | `cli-anything-research.md` |
| `archives/` | 0 | Empty |
| `galaxy/` | 28 | Breakdown below |

### 10.2 Galaxy note breakdown by prefix

| Prefix | Count |
|---|---|
| `decision-*` | 16 |
| `learning-*` | 9 |
| `pattern-*` | 3 |
| `style-*` | 0 |
| `pattern-posture-*` | 0 |

### 10.3 Ownership distribution (across whole vault, 33 notes total)

| `owner:` value | Whole-vault count | Galaxy-only count (of 28) |
|---|---|---|
| `pm` | 13 | 9 |
| `skill` | 12 | 11 |
| `skill-lead` | 6 | 6 |
| `pm-lead` | 2 | 2 |

The galaxy-only column is what §11.1 row 1 references; whole-vault includes the `projects/`, `areas/`, `resources/` notes that also carry `owner:`.

**Two owner-label conventions are in use** (`skill` vs `skill-lead`; `pm` vs `pm-lead`). The spec in `vault-protocol.md` says `owner: pm | skill | qa | dm | shared`, so the `-lead` suffix variant is non-spec and looks like organic drift — agents have been writing `<role>-lead` (their tracker-comment role tag) instead of the spec'd bare role-class name. Not flagged in any open issue today; recorded here for traceability.

### 10.4 Confidence distribution (galaxy notes, 28 total)

| `confidence:` value | Count |
|---|---|
| `high` | 24 |
| `medium` | 4 |
| `low` | 0 |

### 10.5 Status distribution (whole vault, 33 notes)

| `status:` value | Count |
|---|---|
| `active` | 33 |

No notes are `archived` or `superseded` — consistent with the empty `archives/` folder.

### 10.6 Update recency (galaxy, top of mtime list)

| Note | mtime |
|---|---|
| `learning-migration-6274-cutover.md` | 2026-05-23 |
| `decision-event-bus-architecture-redesign.md` | 2026-05-21 |
| `learning-strip-vs-wire-audit-findings.md` | 2026-05-21 |
| `decision-phase-4-event-ack-lifecycle-deferred.md` | 2026-05-21 |
| `learning-broadcast-deque-cannot-have-in-stream-gaps.md` | 2026-05-19 |

Oldest galaxy notes are dated 2026-04-25 (vault store initialization), e.g. `decision-deterministic-testing.md`, `decision-comprehension-test-pipeline.md`, `decision-branch-per-feature-workflow.md`.

### 10.7 Vault templates

Under `references/vault-templates/`:

- `BRIEFING.md`, `archives-template.md`, `areas-template.md`, `galaxy-template.md`, `human-profile-seed.md`, `projects-template.md`, `resources-template.md`

These are seeds used by `vault-init` (per `vault-protocol.md` §Vault Initialization).

---

## 11. Known gaps `[v1 — not yet migrated]`

### 11.1 #5855 — Vault is static decision log

[Issue #5855 — Vault is static decision log, not living institutional memory](https://github.com/WallyDoodlez/SquidSquad/issues/5855) (status:pending, priority:high, role:skill).

Each claim from the issue body re-verified against the snapshot in §10:

| #5855 claim | Verdict | Verified state (2026-05-24) |
|---|---|---|
| "Only skill + PM contribute (skill 64%, PM 36%)" | **CONFIRMED** | Galaxy (28 notes): skill+skill-lead = 17 (61%); pm+pm-lead = 11 (39%); qa = 0; dm = 0 (§10.3). Whole-vault distribution same shape. |
| "20/22 galaxy notes are `confidence:high`" | **CONFIRMED, numbers shifted** | Today: 24/28 high (86%), 4/28 medium, 0 low (§10.4). The skew is still extreme but the vault has grown since the issue was filed. |
| "No notes updated in last 7+ days" | **NOT TRUE today** | Most-recent galaxy update is `learning-migration-6274-cutover.md` (2026-05-23, 1 day ago); 3 more notes updated 2026-05-21 (3 days ago) (§10.6). The claim was true when filed; the recent #6274 + event-bus work has driven fresh writes. |
| "No style notes (0)" | **CONFIRMED** | 0 `style-*` notes (§10.2). |
| "No posture notes from vault synthesis" | **CONFIRMED** | 0 `pattern-posture-*` notes (§10.2). Either `vault-synthesis` has never fired, or every firing skipped at one of its gates. |
| "No learnings captured from recent shipping" | **PARTIALLY TRUE** | 9 `learning-*` notes exist (§10.2), some recent. However, distribution suggests learnings cluster around large architecture work (6274, event-bus) and not around routine ships — most recently shipped items in BRIEFING.md have no corresponding learning note. |
| "Archives folder empty" | **CONFIRMED** | 0 notes in `archives/` (§10.1). All 33 notes have `status: active` (§10.5). |

#5855 also enumerates suspected causes (verbatim from the issue):

- vault-remember's 4-gate filter may be too aggressive (filters out everything)
- "Quiet cycle only" reflection trigger may be the wrong model
- QA and DM missing instructions / template gap / wrong incentives
- No automated capture of failure-mode learnings

Additional drift surfaced by this audit (not yet in #5855):

- **Owner label drift** (§10.3): two conventions in use, `<role>` vs `<role>-lead`. Spec says `pm | skill | qa | dm | shared` (no `-lead` suffix). Agents have been writing the role tag they use in tracker comments.
- **No `superseded` notes** (§10.5): every note is `active`. Either decisions are never superseded (unlikely over 1+ months of work) or the supersession mechanism isn't being used.

This doc does not propose fixes — those belong to whoever picks up #5855.

### 11.2 Future gap — vault knowledge-tree integrity enforcement (#10100)

The §4.5 operating assumption (SquidSquad-only writes; sub-skills mediate all modifications) is a convention, not a hard guarantee. A future CI/CD workflow should formally enforce knowledge-tree integrity on note renames:

- **Detect**: git diff between PR head and base reveals any vault note that was renamed (filesystem path change) or moved
- **Enforce**: one of two policies
  - **Reconcile**: auto-rewrite all incoming `[[wikilinks]]` to point at the new name; fail the CI check if the rewrite is ambiguous (e.g., name collision)
  - **Prohibit**: fail the CI check outright on any direct rename; force the rename to go through a vault sub-skill (e.g., `vault_optimize rename-note`) that triggers the existing rewrite logic
- **Policy choice**: prohibit-outright is simpler and matches the SquidSquad-only-write assumption (humans never rename vault notes directly); reconcile-automatically is more permissive but adds CI complexity. The recommendation in #10100 is to start with prohibit.

Tracked in #10100.

### 11.3 Future gap — usage-aware decay (impression-based / hybrid)

The current decay model (§4.4) is purely time-based: every note decays by `updated:` age regardless of how much it is actually being used. This is blunt — evergreen content that is heavily read still decays unless manually tagged `evergreen` at creation time, which requires foresight and is brittle to miscategorization.

A more accurate model would treat **usage as the primary signal**:

- **Impression-based**: decay based on impressions-since-last-event (read, search hit, wikilink traversal, BRIEFING reference). Heavily used notes never decay.
- **Hybrid (recommended direction)**: time decays as today, BUT every impression resets the timer. Captures both failure modes — old + unused → decays; old + used → stays.

Open design questions for whoever picks this up:

- What counts as an impression? Just file reads? Search hits? Wikilink traversal? BRIEFING-loads? All four with weights?
- Where do impression counters live? `.relevance-index.json` (already gitignored, already updated by `vault_optimize`) is the natural home. Frontmatter would be too noisy — counter increments every cycle.
- Cold-start: how do new notes accumulate enough impressions to defend themselves before the timer fires?
- Backfill for existing notes: assume average impression count, or start cold?

Falls under the broader vault-living-memory umbrella (#5855).

### 11.4 Future gap — event bus integration (vault emits/consumes zero events today)

[`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) §5 documents the event bus and §5.2 the signal catalog. The vault is presently **not on the bus**: vault operations (`vault-create`, `vault-update`, `decay-apply`, `prune-scan`, `vault-synthesis` posture writes) execute as in-process script calls plus git commits, with no event emission. Agents discover vault changes via git pull on the next cycle, not in real time.

Consequences for current behavior:

- No way for one agent to react to another agent's vault write before the next cycle boundary
- The §11.3 impression-tracking model has no natural event source today (every vault read would have to be observed in-process by the reader's own sub-skill rather than via a bus subscription)
- `vault-synthesis` cross-agent broadcast (notifying other agents when a posture lands) has to be done manually via `tracker.py create-task` instead of as an event subscription
- Sub-skills like `vault-remember` and `vault-optimize` cannot be triggered by external signals — they only fire on cycle steps

A future integration would add vault-related signal types to the catalog, e.g.:

- `vault.note-written` (payload: `path`, `type`, `owner`, `tags`) — emitted by `vault-create`
- `vault.note-updated` (payload: `path`, `fields-changed`) — emitted by `vault-update`
- `vault.note-archived` (payload: `from-path`, `to-path`, `reason`) — emitted by `vault_optimize.py prune-scan`
- `vault.posture-detected` (payload: `posture-name`, `source-notes`) — emitted by `vault-synthesis`
- `vault.note-read` (payload: `path`, `reader-role`) — would source the §11.3 impression model

Falls under the broader vault-living-memory umbrella (#5855) and overlaps with the event-driven mode work in [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) §8.

### 11.5 Implementation gap — heavy sub-skills currently run inline (target: background subagent)

§7's Execution model paragraph specifies that `vault-remember` and `vault-synthesis` must run as background subagents (`sonnet`) so the reflection / cross-note reasoning transcript stays out of the consuming agent's context. The current implementation runs both inline:

- `references/sub-skills/common/vault-remember.md` is composed directly into the consuming agent's `CLAUDE.md` and the agent itself performs the 4-gate evaluation, dedup decisions, and write reasoning every cycle.
- `references/sub-skills/roles/pm/vault-synthesis.md` is composed into PM's `CLAUDE.md` and PM itself performs theme/convergence detection across recent notes.

Consequences today:

- Every quiet cycle that triggers vault-remember consumes main-context tokens for candidate enumeration + per-candidate dedup-check output + write/skip reasoning. Each reflection is a meaningful slice of the cycle context, on top of whatever creative work happened.
- Every 5th quiet cycle vault-synthesis adds another bulk read of recent galaxy notes + cross-agent comparison reasoning into PM's context.
- Context-pressure thresholds get reached faster than they would with the offload — meaning more restarts at the agent layer, more cache invalidation, more wall-clock latency.

Closing this gap requires:

1. **Sub-skill source split** — the `references/sub-skills/common/vault-remember.md` body becomes two parts: a short stub composed into the consuming agent (defines the "spawn subagent at Step 4b with these inputs and apply the returned write list" contract) and a longer subagent prompt template stored separately (the actual 4-gate reflection instructions, loaded only by the subagent). Same split for `vault-synthesis.md`.
2. **Compose-time awareness** — `compose.py` must know to compose the stub into the role-class's CLAUDE.md but leave the subagent prompt at its source path for the spawned subagent to read.
3. **Subagent contract** — defined by the structured return shape on each sub-skill's §7 entry (vault-remember returns `{action, path, type, body, reason}` per candidate; vault-synthesis returns at most one posture descriptor).
4. **Model pin** — `sonnet` per §7's rationale; honor `feedback_skill_sonnet_subagents` / `feedback_dm_sonnet_subagents` consistency.

Filed as #10180. Until that lands, the §7 description is the architectural target and the current code is the documented departure from it.

---

## 12. Cross-references to other docs `[v1 — not yet migrated]`

### 12.1 Where vault appears in other docs today (verified)

| Doc | What it says about vault | Lines / sections | Depth |
|---|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | "L6 Memory" appears in the 7-layer stack (L17) and gets a **full section** at §L6 Memory Layer (L150-167) — file list, "what changes here," cycle interplay, PARAG explanation. Also referenced in the "Where to make changes" table (L264). | L17, L150-167, L264 | Substantial — second only to this doc |
| [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) | Vault is one of the 6 composed-output slots (`identity / responsibility / soul / instructions / project-context / vault`). §5.6 ("Vault") is intentionally short and points to `vault-protocol.md` for the per-cycle usage contract and to this doc for the architecture. §3.3 + §5.6 + §11.2 G4 lock the slot to **L1-exclusive** authoring (no L2/L3/L4 fragments) — see §1 of this doc for the policy summary. | §3.3, §5.6, §11.2 G4 | Slot-machinery + L1-exclusive policy |
| [AGENT-RUNTIME.md](AGENT-RUNTIME.md) | State-persistence table row (L507) — "Decisions / institutional memory" lives in `.squidsquad/vault/`. References an in-vault decision note for the event-bus architecture (L195, L1044). | L195, L507, L1044 | One row + two citations |
| [INSTALLER-ARCH.md](INSTALLER-ARCH.md) | Vault skeleton is part of the install scaffold (L100 §3.2 outputs row, L228 Phase 5 scaffold step, L292-293 file layout tree). Vault is explicitly preserved across clean-rebuild and upgrade (L436, L464, L472). | L100, L228, L292-293, L436, L464, L472 | Install-time scaffolding + preservation rules |
| [sub-skill-catalog.md](sub-skill-catalog.md) | Lists the 4 vault sub-skills (`vault-protocol`, `vault-remember`, `vault-optimize`, `vault-synthesis`) with one-line descriptions under the "Vault (institutional memory)" subheading. The `vault-protocol-slim` read-only variant was retired in #11331 (Iter 56). | "common/" → "Vault (institutional memory)" subsection | Catalog entries only |

This doc (`VAULT-ARCH.md`) is the first **dedicated** architecture treatment of the vault. ARCHITECTURE.md §L6 has the most content elsewhere, but it's overview-level — not an architecture spec.

### 12.2 Reconciliation needs surfaced by §12.1

The cross-references above are **accurate but not yet two-way**. Reconciliation work that should happen alongside this doc landing:

- **ARCHITECTURE.md §L6 Memory Layer**: Should add a single line pointing to `VAULT-ARCH.md` as the canonical deep-dive. Today's L150-167 content is overview-correct but doesn't reference this doc (it can't — this doc didn't exist before).
- **COMPOSE-ARCHITECTURE.md §5.6 and §11.2 G4**: §5.6 now references `VAULT-ARCH.md` for the architecture (vs `vault-protocol.md` for the per-cycle usage contract) and declares the slot **L1-exclusive** (no L2/L3/L4 authoring). §11.2 G4 is **CLOSED** as of 2026-05-29 — the "slot contract" gap is settled by the L1-exclusive guardrail (the slot contract is the L1 short-descriptor pattern; nothing else is authorable). Revisit when a concrete customization pattern surfaces.
- **AGENT-RUNTIME.md §6 state-persistence row**: Should link to `VAULT-ARCH.md` for the "what" (vs the row's "where" + "owner" + "why" data).
- **INSTALLER-ARCH.md §3.2 + §5 + §11**: All vault mentions are factual scaffolding/preservation notes. Should cross-reference `VAULT-ARCH.md` once in the file-layout section so a reader knows where to learn what they just installed.
- **sub-skill-catalog.md "Vault (institutional memory)" subsection**: Should add a header line linking to `VAULT-ARCH.md` for architecture context.

These are noted here; the actual edits land in a separate commit or as part of this PR depending on review preference.

### 12.3 Vault sub-skill source files (canonical specs)

- [`references/sub-skills/common/vault-protocol.md`](../references/sub-skills/common/vault-protocol.md) — full R/W contract (used by all 4 roles; the historical `vault-protocol-slim.md` read-only variant was retired in #11331 Iter 56)
- [`references/sub-skills/common/vault-remember.md`](../references/sub-skills/common/vault-remember.md) — reflection
- [`references/sub-skills/common/vault-optimize.md`](../references/sub-skills/common/vault-optimize.md) — quiet-cycle maintenance
- [`references/sub-skills/roles/pm/vault-synthesis.md`](../references/sub-skills/roles/pm/vault-synthesis.md) — PM cross-agent synthesis

### 12.4 Vault scripts (canonical implementations)

- [`references/scripts/vault_check.py`](../references/scripts/vault_check.py)
- [`references/scripts/vault_entity.py`](../references/scripts/vault_entity.py)
- [`references/scripts/vault_optimize.py`](../references/scripts/vault_optimize.py)
- [`references/scripts/vault_remember.py`](../references/scripts/vault_remember.py)

### 12.5 Related vault decisions in the vault itself

- [`galaxy/decision-vault-remember-source-agnostic.md`](../.squidsquad/vault/galaxy/decision-vault-remember-source-agnostic.md) — vault-remember treats QA-rejection learnings as equal in value to human-directive learnings (source-agnostic reflection)
- [`galaxy/decision-vault-subagent-model-sonnet.md`](../.squidsquad/vault/galaxy/decision-vault-subagent-model-sonnet.md) — heavy vault sub-skills (`vault-remember`, `vault-synthesis`) execute as background subagents on the `sonnet` tier; light ones stay inline (see §7 Execution model + §11.5)

---

## 13. Revision log

- **2026-05-24 (v1 draft, descriptive snapshot)** — initial draft. Consolidates the vault's specification (from 5 sub-skills + 4 scripts) and current state (from on-disk inventory) into one architecture doc. No design changes proposed. References open issue #5855 for the known living-memory gap; resolution out of scope.
- **2026-05-24 (v1 draft, expanded)** — added §9.6 failure modes + recovery paths, §9.7 explicit non-functionality, §10.3-§10.6 ownership/confidence/status/recency distributions, §11 re-verified #5855 claims (each verdict CONFIRMED / PARTIALLY TRUE / NOT TRUE TODAY) + new drift findings (owner label `<role>` vs `<role>-lead`; zero `superseded` notes), §12.1 verified cross-refs with line numbers, §12.2 reconciliation needs for ARCHITECTURE / COMPOSE-ARCHITECTURE / AGENT-RUNTIME / INSTALLER-ARCH / sub-skill-catalog.
- **2026-07-18 (v2 rewrite in progress, #10003)** — §1–§6 rewritten as prescriptive target design per `VAULT-COMPARISON-DMPWEB.md` §9+§10: consumption-instrumented as a defining property; `vault-schema.json` type registry replacing hardcoded PARAG (folders kept, `systems/` hub layer added); entity model drops `confidence`/`source`/`links`, staleness becomes usage-based; templates registry-derived (§3.5); §5 BRIEFING restated prescriptively + Vault Pulse auto-digest (target state); §6 replaced (was Templates) by the consumption engine — event model, search/ranking contract, **git-tracked per-writer telemetry shards** (supersedes §9.4's harness-owned store; operator lock-in pending), impressions report, compaction. Same day: §9 rewritten as the consumption pipeline — context injection at intake, mandatory consultation + committed receipts at pickup, verifier receipt enforcement, capture-at-ship + engine-rerouted prefer-update-over-create sweep, harness-scheduled maintenance, outcome-linked telemetry (target state), v2 failure-mode table. §7/§8 (blocked on §10.3 packaging verifications), §10–§12 still v1 pending rewrite.
