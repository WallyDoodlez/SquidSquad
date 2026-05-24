# Vault Architecture (current state)

> **Status**: Descriptive snapshot, 2026-05-24. Documents the vault as it exists in code, sub-skills, and on-disk content today. **No proposals or recommendations.** Where a section says "specification" it reflects what the existing sub-skills and scripts implement; where it says "current state" it reflects what is actually present in this repo's `.squidsquad/vault/` right now.
>
> **Companion docs**: [`ARCHITECTURE.md`](ARCHITECTURE.md) (overall system; vault appears as "L6 Memory"), [`AGENT-RUNTIME.md`](AGENT-RUNTIME.md) (cycle integration), [`COMPOSE-ARCHITECTURE.md`](COMPOSE-ARCHITECTURE.md) (vault slot in composed CLAUDE.md), [`sub-skill-catalog.md`](sub-skill-catalog.md) (vault sub-skill entries).
>
> **Known live gap**: [#5855 — Vault is static decision log, not living institutional memory](https://github.com/WallyDoodlez/SquidSquad/issues/5855) (status:pending, high, role:skill). Documented in §11; not addressed by this doc.

---

## 1. Goal & scope

This doc describes:

- What the vault *is* — its purpose, the storage model, the entity types it holds
- Where it lives on disk
- Who reads and who writes (per agent role)
- The five sub-skills and four scripts that operate on it
- How it integrates into the cycle (boot, pre-cycle, creative phase, post-cycle, quiet ticks)
- What is actually present in this repo's vault as of the snapshot date
- Known gaps between the spec and the live behavior

It does NOT describe:

- Proposed fixes for the gaps in §11 (out of scope; planned for follow-up under #5855)
- How vault content gets into composed CLAUDE.md (see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) §5.5)
- The L4 project-local layer in `.squidsquad/project/` (different system; see [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) §3)

---

## 2. What the vault is

The vault is a **shared, git-tracked, per-install knowledge store** at `.squidsquad/vault/`. It holds institutional knowledge that outlives any single cycle, task, or session — decisions, learnings, patterns, project context, ongoing concerns, and human preferences as the agents have observed them.

Three properties define it:

1. **Shared across roles** — all four canonical agent roles (pm / qa / worker / dm) reach into the same vault. Read access is universal; write access is partial (see §6).
2. **Git-tracked** — every note has a commit; every change has authorship and timestamp. There is no separate database, indexer, or memory service.
3. **Per-install** — `.squidsquad/vault/` lives inside the project repo's `.squidsquad/` tree. A separate SquidSquad install has its own vault; there is no cross-install vault today.

The vault is **distinct from**:

- **L4 project-local content** (`.squidsquad/project/`): instruction overlays composed into CLAUDE.md. L4 is *what the agent does*; vault is *what the squad knows*.
- **Working state** (`.squidsquad/<role>/working-state.md`): per-cycle crash-recovery checkpoint, single-agent-owned. Working state is *what this agent is doing right now*; vault is *what the squad has learned over time*.
- **Iteration logs** (`.squidsquad/<role>/iterations/iter-N.md`): per-cycle activity log. Iteration logs are *what happened this cycle*; vault is the *durable filtered residue*.

---

## 3. On-disk layout — PARAG

The vault uses a **PARAG** taxonomy: **P**rojects, **A**reas, **R**esources, **A**rchives, **G**alaxy. The first four letters come from Tiago Forte's PARA system in *Building a Second Brain*; the fifth letter (G — Galaxy) is a SquidSquad addition for Zettelkasten-style atomic notes.

```
.squidsquad/vault/
├── BRIEFING.md         # active-context summary, ~50 lines target (today: 80+)
├── projects/           # active project context, goals, constraints
├── areas/              # ongoing concerns: human prefs, code conventions,
│                       # design system, company values, team culture
├── resources/          # reference material, external docs, research
├── archives/           # shipped features, closed decisions, historical context
├── galaxy/             # atomic knowledge notes (Zettelkasten):
│                       # decision-*, pattern-*, learning-*, style-*
├── .relevance-index.json   # written by vault_optimize.py (gitignored)
└── .obsidian/          # optional Obsidian app config (gitignored)
```

### 3.1 The PARA buckets — what goes where

PARA sorts notes by **actionability** rather than topic. The original framing (paraphrased): "How soon will I need to act on this?" Buckets are ordered by decreasing actionability.

| Bucket | What it holds | Test for placement |
|---|---|---|
| `projects/` | Bounded, scoped work with a definition-of-done | "Does this end?" If yes → project. One note per project. |
| `areas/` | Ongoing responsibilities and standing context with no end date | "Will I always care about this?" If yes → area. Stable, slow-changing, few notes. |
| `resources/` | Reference material — research, external docs, third-party patterns | "Would I look this up later?" Prefer linking to externals over copy-paste. |
| `archives/` | Anything from the three above that is no longer active | "Has this shipped / been superseded / become irrelevant?" |

The placement test is **"actionable now vs. someday vs. never"**, not topic similarity. The same subject can validly live in `projects/` (active work), `areas/` (the ongoing concern behind that work), and `archives/` (a closed past project on it) simultaneously — each captures a different lifecycle slice.

### 3.2 Galaxy — the Zettelkasten layer

PARA covers *contextual* knowledge (what's active, what's standing, what's reference). It does not cover **atomic, durable, cross-cutting knowledge**: a single architectural decision, a reusable pattern observed across many projects, a lesson from a single incident. Those are too small to be a project, too pointed to be an area, and too internal to be a resource — but too valuable to lose.

The `galaxy/` folder fills that gap with Zettelkasten-style notes:

- **Atomic** — one idea per note; if a note grows past ~500 lines or covers more than one idea, split it (per §4.1).
- **Typed by filename prefix** — `decision-*`, `pattern-*`, `learning-*`, `style-*` (full taxonomy in §4.2).
- **Heavily cross-linked** — body text uses bare `[[wikilinks]]` to connect related notes; the `links:` frontmatter field is auto-maintained from those wikilinks by `vault_check.py` (§4.5).
- **Append-only in practice** — galaxy notes are rarely deleted; superseded ones get `status: superseded` and are auto-archived by `vault_optimize.py prune-scan` (§3.3).

Galaxy is the **compounding** layer: every decision the squad makes and every learning it captures adds one more linkable node. PARA tells you *what's hot right now*; Galaxy tells you *what we have learned over time*.

### 3.3 How notes move between buckets

Note movement is rare and almost always one-directional:

- **`projects/` → `archives/`** — when a project completes or is abandoned, the note's `status:` flips to `archived` and either an agent or `vault_optimize.py prune-scan` moves the file. Project notes are not deleted; the historical context matters.
- **`galaxy/` → `archives/`** — `vault_optimize.py prune-scan` auto-archives galaxy notes that are (a) `status: superseded`, or (b) stale **and** orphaned (no inbound wikilinks for longer than the staleness threshold in `config.md`). Archived galaxy notes get a `<!-- archived: [[name]] moved to archives/ -->` breadcrumb appended to every note that linked to them, so the link graph degrades gracefully.
- **`areas/` and `resources/`** — generally stay put. Areas are stable by definition; resources stay as long as someone might look them up. Both can be manually archived if the squad decides they're dead weight, but `vault_optimize.py` does not touch them automatically.

There is no automatic *promotion* path (e.g., a `learning-*` note that turns out to be a fundamental pattern is rewritten or split manually; the script doesn't second-guess). The trim-or-graduate rule in §5 covers the **BRIEFING → galaxy** edge case, where lines trimmed from BRIEFING.md become new galaxy notes rather than being deleted.

### 3.4 Why this layout

The PARAG split serves three jobs that a single flat folder couldn't:

1. **Boot-time signal** — `BRIEFING.md` + `projects/` + `areas/` are the small, hot set agents read at every cycle start. Keeping them as separate top-level folders means an agent can read "current context" without scanning the (much larger) `galaxy/` or `archives/`.
2. **Long-tail without dilution** — `galaxy/` can grow to thousands of notes without dragging on every read, because nothing reads the whole folder during a cycle — only `vault_optimize.py reindex` and `vault-synthesis` traverse it, and both are quiet-cycle work.
3. **Lossless decay** — `archives/` is the dumping ground that keeps prune scans honest. Nothing is deleted; if a hot note turns cold, it moves to `archives/` and the link graph rewrites itself.

Concrete operational consequences appear in §6 (who reads/writes which bucket), §8 (which script touches which folder), and §10 (what the buckets actually contain in this repo today).

---

## 4. Entity model

### 4.1 By folder

| Folder | Entity types | Lifespan | Growth model |
|---|---|---|---|
| `projects/` | `project` | While project active | One note per project; updated as scope evolves |
| `areas/` | `area` | Ongoing | Few notes (typical: human-profile, code-conventions); grow freely |
| `resources/` | `resource` | While referenced | One note per reference; prefer linking to externals |
| `archives/` | any type, status `archived` | Forever (historical) | Auto-populated by `vault_optimize.py prune-scan` |
| `galaxy/` | `decision`, `pattern`, `learning`, `style` | Forever (Zettelkasten) | Atomic; max ~500 lines each; split if larger |

### 4.2 By note name prefix (galaxy only)

| Prefix | Type | Purpose |
|---|---|---|
| `decision-` | `decision` | Architectural choice, trade-off, or commitment |
| `pattern-` | `pattern` | Reusable pattern discovered or confirmed |
| `learning-` | `learning` | Something that failed or succeeded unexpectedly |
| `style-` | `style` | Preferred coding/structural/communication style |

Subtypes layered on top via tags:

- `pattern` + tag `posture` = synthesis-derived cross-agent principle (written only by `vault-synthesis`, see §6.3).

### 4.3 Required frontmatter (all notes)

```yaml
---
type: decision | pattern | learning | style | area | project | resource
tags: [list]
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: pm | skill | qa | dm | shared
status: active | archived | superseded
confidence: high | medium | low   # see §4.4
source: conversation | code | review | observation | research
links: [bare-note-names]          # auto-maintained from body wikilinks
---
```

The `links` field is **auto-maintained** by `vault_check.py` from `[[bare-wikilinks]]` in the body — agents do not curate it manually.

### 4.4 Confidence levels

| Level | Meaning |
|---|---|
| `high` | Human explicitly stated or confirmed this |
| `medium` | Agent observed this directly (e.g., from code review, conversation pattern) |
| `low` | Agent inferred this (e.g., from indirect signals, extrapolation) |

Confidence decays automatically via `vault_optimize.py decay-apply`: `high → medium` after 60 days, `medium → low` after 120 days (defaults; configurable as "Confidence Decay Days" in `config.md`).

### 4.5 Wikilinks

Bare wikilink syntax in the body: `[[note-name]]`. No aliases (e.g., `[[note-name|display]]` is not used). Cross-note references resolve via filename match anywhere under `.squidsquad/vault/`. Broken wikilinks are flagged by `vault_check.py check-wikilinks`.

---

## 5. BRIEFING.md

`.squidsquad/vault/BRIEFING.md` is the **active-context summary** every agent reads at session start and at every cycle.

| Property | Spec | Current state |
|---|---|---|
| Target length | ~50 lines | 80+ lines (today's snapshot) |
| Update trigger | Every cycle (staleness check, not gated by quiet) | Implemented by `vault-remember.md` Step 4b |
| Token budget for new content | 2000 (per `config.md` `BRIEFING Token Budget`) | Trim-or-graduate rule: trimmed content moves to a galaxy note, never deleted |
| Sections | Active Priorities, Recently Shipped, Core Architecture, Recent Decisions, Human Preferences (via `[[human-profile]]`), Blockers | Today's BRIEFING has Active Priorities, Recently Shipped, Core Architecture, Recent Decisions; no explicit Blockers section |

The staleness check is special — it runs every cycle including quiet cycles, and fixing stale fields (version mismatch, agent list mismatch, priority list mismatch with tracker) does **not** consume the vault-remember write budget.

---

## 6. Who reads, who writes

### 6.1 Read access — universal

All four roles (pm, qa, worker, dm) include either `common/vault-protocol` or `common/vault-protocol-slim` in their composed CLAUDE.md. Both grant read access.

### 6.2 Write access — pm and worker only

| Role | Write access | Composed sub-skill |
|---|---|---|
| `pm` | full R/W | `common/vault-protocol` |
| worker (`dev` variant in this install) | full R/W | `common/vault-protocol` |
| `qa` | read-only | `common/vault-protocol-slim` |
| `dm` | read-only | `common/vault-protocol-slim` |

Source: per-role `includes.yml` files at `references/roles/<role>/includes.yml`.

This split is by design: vault writes happen at end-of-cycle reflection (`vault-remember`) and on quiet cycles (`vault-optimize`, `vault-synthesis`); QA and DM consume vault knowledge but do not generate it. (See §11 for the known consequence — QA + DM write zero notes ever.)

### 6.3 Write protocols

Three write paths exist; each is gated, deterministic, and triggered from inside a cycle:

| Sub-skill | Trigger | Who | What it writes |
|---|---|---|---|
| `vault-remember` | End-of-cycle reflection (Step 4b), if not a quiet cycle | pm, worker | Up to 2 galaxy notes per cycle: `decision-*`, `pattern-*`, `learning-*` |
| `vault-optimize` | Quiet cycle, vault has 20+ notes | pm, worker | Archives stale+orphan notes; rebuilds `links`; computes relevance scores; logs pending human questions |
| `vault-synthesis` | Every 5th consecutive quiet cycle, vault has 10+ galaxy notes | pm only | Max 1 `pattern-posture-*` note per synthesis; files a pending PM task for human review |

`vault-remember` applies four deterministic gates IN ORDER for each write candidate:

1. **Write budget** — `vault_remember.py write-budget` must return >0 (default 2 per cycle, per `config.md` `Vault Remember > Writes Per Cycle`).
2. **Dedup check** — `vault_check.py dedup-check` against existing notes by title + tags.
3. **Reusability** — is this specific to only this cycle with no future value? Skip if yes.
4. **Fresh-context test** — would a fresh agent in a new context benefit? Write if yes.

The priority when more than 2 candidates pass: decisions > learnings > patterns. Surplus candidates are logged in the iteration log as `Vault-worthy but deferred (budget)` and dropped.

---

## 7. The five sub-skills

All vault behavior is encoded in five markdown fragments under `references/sub-skills/`:

| Sub-skill | Path | Used by |
|---|---|---|
| `vault-protocol` | `common/vault-protocol.md` | pm, worker |
| `vault-protocol-slim` | `common/vault-protocol-slim.md` | qa, dm |
| `vault-remember` | `common/vault-remember.md` | pm, worker |
| `vault-optimize` | `common/vault-optimize.md` | pm, worker |
| `vault-synthesis` | `roles/pm/vault-synthesis.md` | pm only |

Each is inlined into the consuming role's composed CLAUDE.md by `compose.py`. The split between `vault-protocol` and `vault-protocol-slim` is the standard "full vs read-only" pair used elsewhere in SquidSquad — `compose.py` knows to map base name → slim variant for read-only roles (per the comment at `references/scripts/compose.py:311`).

---

## 8. The four scripts

All mechanical vault operations are encapsulated in scripts under `references/scripts/`. Agents shell out to these from inside the sub-skills.

### 8.1 `vault_check.py`

Validates vault integrity. Subcommands:

| Subcommand | Purpose |
|---|---|
| `validate` | Full vault validation (all checks) |
| `check-frontmatter` | Validate frontmatter fields in galaxy notes |
| `check-wikilinks` | Find broken `[[name]]` references |
| `dedup-check --title <t> --tags <t>` | Used by `vault-remember` Gate 2 |

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
| `run` | Convenience: invokes the full pipeline (see `vault-optimize.md`) |

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

---

## 9. Cycle integration

The vault is touched at four points in a cycle:

### 9.1 Session start (boot)

- Boot reads `.squidsquad/vault/BRIEFING.md` for active context (priorities, recent decisions, human preferences). No write.

### 9.2 Pre-cycle (mechanical)

- `cycle_pre.py` reads the `vault-remember` and `vault-optimize` config flags (`cycle_pre.py:539-540`) and includes them in `cycle-input.json` so the creative phase knows which sub-skills are active.
- No vault read or write.

### 9.3 Creative phase (agent)

- Agent consults vault "before work" per `vault-protocol` — typically targeted searches by tag, type, keyword, or wikilink (max 10 results, cached within cycle).
- Source: per the locked principle, "all agents consult vault before work (PM in research, dev/QA before pickup)" (BRIEFING.md recent decisions, #5571, #5572).

### 9.4 Post-cycle (mechanical wrap)

In order:

1. **vault-remember Step 4b** (every cycle, gated):
   - Staleness check on BRIEFING.md (always runs, ignores quiet gate, doesn't consume budget).
   - Quiet-cycle gate via `vault_remember.py is-quiet`.
   - If active: reflection across 4 categories (DECISIONS / PATTERNS / LEARNINGS / PROJECT CONTEXT), four gates per candidate, up to 2 writes.

2. **vault-optimize** (quiet cycles, vault ≥20 notes, after improvement scan):
   - Prune + decay + reindex + relevance scoring via `vault_optimize.py run`.

3. **vault-synthesis** (PM only, every 5th quiet cycle, vault ≥10 galaxy notes):
   - Cross-agent pattern detection; writes at most 1 `pattern-posture-*` note; files pending human-review task.

The agent's working-state holds two relevant counters: the synthesis counter (per `vault-synthesis.md`) and the write counter (per `vault_remember.py`).

### 9.5 Git integration

- Vault files are under `.squidsquad/vault/` and committed by `cycle_post.py` as part of normal cycle commits.
- Per `git_ops.py:659` the vault path is registered in the standard commit set.
- Per `state_bus.py:194` comment: "Everything else stays on main (code, templates, config, vault, planning)" — vault stays on the `main` branch (not the `squid-squad` state branch).
- Per `migrate_state_branch.py:36` the vault dir is part of state-migration scope.

### 9.6 Failure modes and recovery paths

The vault is designed to be **non-blocking and degradation-tolerant** — no vault failure ever blocks a cycle from committing. Concrete failure paths today:

| Failure | Behavior today |
|---|---|
| **Harness unreachable during cycle** | Vault operations are local file I/O + git commits with no harness dependency. Cycle continues; vault writes succeed; commit and push happen at `cycle_post.py`. |
| **vault-create fails mid-write** | Not transactional. If the agent writes a `.md` file but crashes before frontmatter is complete, a malformed note can land on disk. `vault_check.py validate` flags missing fields on next run; agent (or human) must repair. |
| **vault-check Level 1 finds issues post-write** | Prints `[vault-check]` warnings; **does not block** the cycle. The flawed note remains on disk until manually fixed or next vault-optimize run. |
| **Merge conflict on a vault note** | Per `vault-protocol.md` rule: "keep both versions, never discard vault content." No automated conflict resolution — human (or PM at next cycle review) must reconcile. The git merge driver does not have special handling for vault notes today. |
| **Two roles write the "same" note concurrently** | Each writes to its own clone; on push the second to push hits a non-fast-forward, must pull-rebase, and may produce a merge conflict (see row above). The dedup gate (`vault_check.py dedup-check`) only checks the *local* vault at write time and does not coordinate across clones. |
| **`vault_remember.py` state files missing** | `.write-counter`, `.synthesis-counter` etc. — implementations default to zero/unset, equivalent to a fresh-cycle start. No hard failure. |
| **Stale `.relevance-index.json`** | The file is `.gitignored` per §9.5 / `.obsidian/` convention. Recomputed on next `vault_optimize.py run`. If missing entirely, relevance scoring just returns empty. |
| **BRIEFING.md token budget exhausted** | `vault_remember.py briefing-budget` returns 0. New content cannot be added without trimming; trimmed content moves to a galaxy note (per `vault-remember.md` "trim-or-graduate" rule). No hard failure. |
| **vault-init re-run on already-initialized vault** | Idempotent per `vault-protocol.md` §Vault Initialization. Creates only what's missing; never overwrites existing notes or `BRIEFING.md`. |
| **`cycle_post.py` crashes after vault write but before commit** | Uncommitted vault files remain in the working tree. Next `cycle_pre.py` `git pull` would surface them; if no conflict they get committed in the next successful cycle_post. |
| **vault-optimize prunes a note an agent still references** | Pruned notes move to `archives/`, not deleted. Wikilinks to archived notes resolve (still in vault tree) but `vault_check.py check-wikilinks` doesn't track folder moves — broken-link warnings may appear until the agent updates the link. |
| **`vault-synthesis` produces a posture an agent later disagrees with** | Posture notes are written with `confidence: medium` and require a pending PM task → human approval before becoming "active scan criteria." Until approved, they're informational notes only. |

### 9.7 What the vault does NOT do today

For completeness, behaviors that some readers might expect but that are not implemented:

- **No automatic propagation across SquidSquad installs.** Each install has its own vault; there is no shared/federated layer. (See `project_memory_layer_vision` in PM auto-memory for an aspirational note on cross-install sharing; not implemented.)
- **No queryable index or embedded search.** All search is `grep` over the markdown files (per the 4 search modes in `vault-protocol.md` §vault-search).
- **No machine-learning on vault content.** No embedding store, no semantic search, no RAG. Confidence levels and tags are agent-assigned, not computed.
- **No write-ahead log or transactional guarantees.** Writes are file overwrites + git commits.
- **No per-note access control.** Read/write is at the role level (full vs slim variant), not the note level.

---

## 10. Current state inventory (snapshot 2026-05-24)

What is actually in `.squidsquad/vault/` right now in this repo:

### 10.1 Note counts

| Location | Count | Notes |
|---|---|---|
| `BRIEFING.md` | 1 (88 lines) | Active context, last updated cycle ~1499 per content |
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

| `owner:` value | Count |
|---|---|
| `pm` | 13 |
| `skill` | 12 |
| `skill-lead` | 6 |
| `pm-lead` | 2 |

**Two owner-label conventions are in use** (`skill` vs `skill-lead`; `pm` vs `pm-lead`). The spec in `vault-protocol.md` says `owner: pm | skill | qa | dm | shared`, so the `-lead` suffix variant is non-spec and looks like organic drift — agents have been writing `<role>-lead` (their tracker-comment role tag) instead of the spec'd bare role name. Not flagged in any open issue today; recorded here for traceability.

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

Oldest galaxy notes are dated 2026-04-25 (vault initialization), e.g. `decision-deterministic-testing.md`, `decision-comprehension-test-pipeline.md`, `decision-branch-per-feature-workflow.md`.

### 10.7 Vault templates

Under `references/vault-templates/`:

- `BRIEFING.md`, `archives-template.md`, `areas-template.md`, `galaxy-template.md`, `human-profile-seed.md`, `projects-template.md`, `resources-template.md`

These are seeds used by `vault-init` (per `vault-protocol.md` §Vault Initialization).

---

## 11. Known gap — #5855

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

---

## 12. Cross-references to other docs

### 12.1 Where vault appears in other docs today (verified)

| Doc | What it says about vault | Lines / sections | Depth |
|---|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | "L6 Memory" appears in the 7-layer stack (L17) and gets a **full section** at §L6 Memory Layer (L150-167) — file list, "what changes here," cycle interplay, PARAG explanation. Also referenced in the "Where to make changes" table (L264). | L17, L150-167, L264 | Substantial — second only to this doc |
| [COMPOSE-ARCHITECTURE.md](COMPOSE-ARCHITECTURE.md) | Vault is one of the 5 composed-output slots (`identity / soul / instructions / project-context / vault`, see L119, L137, L199, L1002). §5.5 ("Vault") is intentionally short (L378-380) and points to `vault-protocol.md` for detail. §G4 (L956) explicitly flags "Vault slot is the most underspecified — a future revision should expand it." | L119, L137, L199, L230, L378-380, L417, L538, L956, L1002, L1009 | Slot-machinery + acknowledged gap |
| [AGENT-RUNTIME.md](AGENT-RUNTIME.md) | State-persistence table row (L507) — "Decisions / institutional memory" lives in `.squidsquad/vault/`. References an in-vault decision note for the event-bus architecture (L195, L1044). | L195, L507, L1044 | One row + two citations |
| [INSTALLER-ARCH.md](INSTALLER-ARCH.md) | Vault skeleton is part of the install scaffold (L100 §3.2 outputs row, L228 Phase 5 scaffold step, L292-293 file layout tree). Vault is explicitly preserved across clean-rebuild and upgrade (L436, L464, L472). | L100, L228, L292-293, L436, L464, L472 | Install-time scaffolding + preservation rules |
| [sub-skill-catalog.md](sub-skill-catalog.md) | Lists all 5 vault sub-skills (`vault-protocol`, `vault-protocol-slim`, `vault-remember`, `vault-optimize`, `vault-synthesis`) with one-line descriptions under the "Vault (institutional memory)" subheading. | "common/" → "Vault (institutional memory)" subsection | Catalog entries only |

This doc (`VAULT-ARCH.md`) is the first **dedicated** architecture treatment of the vault. ARCHITECTURE.md §L6 has the most content elsewhere, but it's overview-level — not an architecture spec.

### 12.2 Reconciliation needs surfaced by §12.1

The cross-references above are **accurate but not yet two-way**. Reconciliation work that should happen alongside this doc landing:

- **ARCHITECTURE.md §L6 Memory Layer**: Should add a single line pointing to `VAULT-ARCH.md` as the canonical deep-dive. Today's L150-167 content is overview-correct but doesn't reference this doc (it can't — this doc didn't exist before).
- **COMPOSE-ARCHITECTURE.md §5.5 and §G4**: §5.5 currently says "most vault detail belongs in `references/sub-skills/common/vault-protocol.md`." Should also reference `VAULT-ARCH.md` for the architecture (vs `vault-protocol.md` for the per-cycle usage contract). §G4 ("Vault slot is the most underspecified") can be partially closed by pointing to VAULT-ARCH §3 entity model + §5 BRIEFING + §4 frontmatter spec.
- **AGENT-RUNTIME.md §5 state-persistence row**: Should link to `VAULT-ARCH.md` for the "what" (vs the row's "where" + "owner" + "why" data).
- **INSTALLER-ARCH.md §3.2 + §5 + §11**: All vault mentions are factual scaffolding/preservation notes. Should cross-reference `VAULT-ARCH.md` once in the file-layout section so a reader knows where to learn what they just installed.
- **sub-skill-catalog.md "Vault (institutional memory)" subsection**: Should add a header line linking to `VAULT-ARCH.md` for architecture context.

These are noted here; the actual edits land in a separate commit or as part of this PR depending on review preference.

### 12.2 Vault sub-skill source files (canonical specs)

- [`references/sub-skills/common/vault-protocol.md`](../references/sub-skills/common/vault-protocol.md) — full R/W contract
- [`references/sub-skills/common/vault-protocol-slim.md`](../references/sub-skills/common/vault-protocol-slim.md) — read-only variant
- [`references/sub-skills/common/vault-remember.md`](../references/sub-skills/common/vault-remember.md) — reflection
- [`references/sub-skills/common/vault-optimize.md`](../references/sub-skills/common/vault-optimize.md) — quiet-cycle maintenance
- [`references/sub-skills/roles/pm/vault-synthesis.md`](../references/sub-skills/roles/pm/vault-synthesis.md) — PM cross-agent synthesis

### 12.3 Vault scripts (canonical implementations)

- [`references/scripts/vault_check.py`](../references/scripts/vault_check.py)
- [`references/scripts/vault_entity.py`](../references/scripts/vault_entity.py)
- [`references/scripts/vault_optimize.py`](../references/scripts/vault_optimize.py)
- [`references/scripts/vault_remember.py`](../references/scripts/vault_remember.py)

### 12.4 Related vault decisions in the vault itself

- [`galaxy/decision-vault-remember-source-agnostic.md`](../.squidsquad/vault/galaxy/decision-vault-remember-source-agnostic.md) — the only `decision-vault-*` note today

---

## 13. Revision log

- **2026-05-24 (v1 draft, descriptive snapshot)** — initial draft. Consolidates the vault's specification (from 5 sub-skills + 4 scripts) and current state (from on-disk inventory) into one architecture doc. No design changes proposed. References open issue #5855 for the known living-memory gap; resolution out of scope.
- **2026-05-24 (v1 draft, expanded)** — added §9.6 failure modes + recovery paths, §9.7 explicit non-functionality, §10.3-§10.6 ownership/confidence/status/recency distributions, §11 re-verified #5855 claims (each verdict CONFIRMED / PARTIALLY TRUE / NOT TRUE TODAY) + new drift findings (owner label `<role>` vs `<role>-lead`; zero `superseded` notes), §12.1 verified cross-refs with line numbers, §12.2 reconciliation needs for ARCHITECTURE / COMPOSE-ARCHITECTURE / AGENT-RUNTIME / INSTALLER-ARCH / sub-skill-catalog.
