# Vault Systems Compared: SquidSquad vs dmp-web — and a Plan to Leapfrog

- **Date:** 2026-07-11
- **Author:** interactive Claude session (operator-requested research)
- **Sources:** direct reads of dmp-web's `ui-implementation-planner`, `jira-implementer`, `pr`, `vault-search`, `vault-development-rules` skills; full sweeps of `D:\Dev\LF\devedge\dmp-web\.obsidian-memory` + `.claude/` vault machinery, and `D:\dev\dev\SquidSquad\.squidsquad\vault` + `references/` vault machinery.
- **Status:** research report + proposal. Per doc-first process, the accepted parts of §7 should land as a human-reviewed update to `docs/VAULT-ARCH.md` before any implementation tasks are filed.

---

## 1. TL;DR

> **Revised 2026-07-12 after operator review.** The first draft framed the two vaults as mirror images ("SquidSquad strong writes / weak reads"). That was too generous: much of SquidSquad's write-side machinery is throttling required by autonomy (budgets, lanes, quiet gates — dmp-web doesn't have these because a human-in-the-loop system doesn't need them), part of it is dead in practice (decay/optimize/relevance never run), and the rest is blind (no usage feedback, so write quality is unmeasured and the corpus suggests it is low). The honest verdict: **SquidSquad's vault is generally weak; dmp-web's is strong precisely where it matters — consumption.**

| | Write side | Read side |
|---|---|---|
| **SquidSquad** | **Elaborate but unproven.** Deterministic throttles (2-writes/cycle budget, per-role lanes, quiet-cycle gate) exist because unsupervised agents need rate limits — necessity, not advantage. Dedup is title/tag matching only. Confidence decay is time-based *and* dead (`vault_optimize.py` never fires). No feedback on whether anything written is ever read. | **Weak.** Prose-mandated raw `grep`, no search engine, no ranking, no telemetry, no receipts (one exception: PM intake `--context`), an orphaned relevance index no code reads. |
| **dmp-web** | **Solid.** Search-based create-vs-update preference (dedup as a *search* problem, using the real engine), `DUPLICATE-BLOCKED`/orphan guards, periodic optimize merge sweeps with human-gated contradictions, usage-based staleness (impressions report). Conventions live in agent prose (drift risk) — the one respect SquidSquad's script-pinned approach is sounder. | **Strong.** Deterministic query engine, used-weighted ranking, consumption telemetry (`impression`/`walked`/`used`), binding dev-rules, provenance sections committed into plans, knowledge capture inside the PR itself. |

dmp-web's vault is "successful for injecting context into the development workflow" because of one design idea executed thoroughly: **consumption is a first-class, instrumented, receipted part of the task pipeline** — not an instruction to remember. Every task-lifecycle stage has a mandatory vault touchpoint, every touchpoint leaves an auditable artifact, and telemetry closes the loop so search gets better with use and dead notes become visible.

SquidSquad already has stronger raw materials than dmp-web had when it started (compose-time instruction injection, deterministic Python gate scripts, a multi-agent team, git-as-bus). The plan in §7 ports dmp-web's consumption loop **adapted for multi-agent operation**, then goes past it with four things dmp-web structurally cannot do: deterministic task-time context injection, verifier-enforced consumption receipts, outcome-linked telemetry ("this note prevented/failed to prevent rework"), and harness-owned freshness.

---

## 2. How dmp-web's vault actually gets consumed

### 2.1 The vault itself

`.obsidian-memory/` — 146 notes in five folders: `people/` (13), `systems/` (12), `projects/` (1), `knowledge/` (113, with `category: decision|learning|implementation|pattern|reference`), `development-rules/` (7, binding). Notes are kebab-case markdown with wikilinks, append-only `## Changelog`, and a "no implementation details" rule (no file paths/snippets — Jira/PRs are referenced, not restated). Deliberately no `tickets/` folder — Jira stays the source of truth.

Every note carries **consumption telemetry** in frontmatter:

- `impression` (int) — surfaced as a direct search result ("shown").
- `walked` (map source-slug → count) — reached by following a wikilink during traversal; records *which edge* was walked.
- `used` (int) — **genuinely informed a deliverable** ("clicked"): cited in a plan, matched as a binding rule, or relied on during implementation. Written only by consumers, never by the search engine.
- `last_impression` (date).

### 2.2 The search engine (`/vault-search`)

Not prose — a deterministic node script (`vault-query.mjs`, behavior pinned by a spec test) that does, in one invocation:

1. **Tiered matching:** filename > wikilink reverse-ref > frontmatter tag > full-text content.
2. **Knowledge-budgeted graph traversal:** follows wikilinks outward, but any single path may pass through at most 2 `knowledge/` notes; people/systems/projects/dev-rules are "free" connective nodes. This keeps traversal on-topic while letting entity notes bridge related knowledge.
3. **Two-stage ranking:** match tier first, then a consumption-weighted tiebreak — `used×2.0 + impression×0.25 + walked×0.5 + recency×0.25`, scaled by per-folder weights, all tunable via `vault-consumption.json`. A note that keeps getting shown but never used cannot climb.
4. **Telemetry write-back:** top-K (12) surfaced notes get `impression` or `walked` bumped (disjoint — direct match wins). `--no-write` for dry runs.

Raw-grepping the vault is **explicitly banned** in the consuming skills: "a raw grep reads the same notes but leaves the telemetry blind, which starves the impression-weighted ranking."

### 2.3 The consumption pipeline (the actual answer to "how do the skills use it")

**`ui-implementation-planner`** (plan a Jira ticket before any code):

- **A2.5 — mandatory `/vault-search` on every run**, before critical review: "never start planning cold." Queries built from the ticket's feature area, components, people, prior tickets. Results feed the conflict/gap review, component mapping, and CMS planning.
- **A5.6 — binding rules matched via `/vault-development-rules`:** a two-stage tag-catalog skill (stage 1 enumerates what rule-topics exist; stage 2 matches the ticket context against that real catalog — so a rule is never missed because nobody grepped the right word). Results go into the plan's `## Applicable Development Rules` section — or an explicit "None matched" so the reader knows the check ran.
- **A6 — provenance section:** the committed plan gets `## Vault context consumed` — one wikilink + one-line relevance note per vault note that *actually shaped the plan* (not everything skimmed). Then `record-consumption.mjs --counter used` is run on exactly those slugs. Because plans are committed to git, the vault viewer's plan-scanner auto-links plan⇄note graph edges from these mentions.

**`jira-implementer`** (implement the ticket):

- **Step 1.5** — reads the plan; the plan's `## Vault context consumed` is its **starting context set** ("open the listed notes before coding; they explain *why* the plan chose its approach"), and `## Applicable Development Rules` is **binding** while writing code (violation = stop and flag, not plan around).
- **Step 2** — mandatory `/vault-search` with ticket entities before exploring code, complementing the plan's set.
- **Step 4** — "search the vault on the fly": on an unfamiliar subsystem, surprising failure, or design fork mid-implementation, `/vault-search` *before grinding through code*. Notes that genuinely shaped what was written get `used` bumped.

**`/pr`** (ship):

- **Step 7.5 — capture BEFORE the PR opens:** durable knowledge (decisions, root causes, new patterns, integrations) is extracted via `/vault-remember` and **committed on the feature branch so the vault update ships inside the same PR** as the code. Explicit skip-list for chores/lint/dep bumps ("the vault should be signal, not a PR archive").
- **Step 9.5** — the PR URL is backfilled into the note's `## References` once it exists.

**Repo `CLAUDE.md`** adds ambient enforcement: a first-turn entity-probe (if the first user message names a code symbol/ticket/vault entity, do one cheap grep pass and read ≤5 notes), a "MUST run `/vault-search` before deep planning" rule, and the compass rule: *vault tells you where to look; code tells you what's true; never return vault content as the answer to a code question.*

### 2.4 Maintenance and observability

- **`/vault-optimize`** (on-demand, never scheduled): queue by `last_optimized` staleness (14-day cutoff), link-density community detection + sub-splitting, parallel analyze-only workers with an append-only discovery ledger, **human gate on contradictions**, then an apply phase. Communities/subcommunities get stamped on knowledge notes for grouping.
- **`vault-impressions-report.mjs`**: read-only report ranking notes hot→cold and emitting purge candidates — **Cold** (never surfaced), **Surfaced-but-never-used**, **Stale** (once-used, idle >90d). Data-driven pruning instead of guesswork.
- **vault-viewer**: zero-dep local graph UI; edges carry walked-traffic, plans appear as nodes linked to the notes they consumed.
- Write-side skills (`vault-create/update/remember/check`) are thin dispatchers to **background subagents**, keeping the main thread unblocked; validation runs inline in the writer.

---

## 3. How SquidSquad's vault is consumed today

### 3.1 The vault itself

`.squidsquad/vault/` — 140 notes, PARAG layout: `galaxy/` (133 atomic notes: 91 `learning-*`, 21 `pattern-*`, 20 `decision-*`, 1 `style-*`), `areas/` (2: `human-profile`, `code-conventions`), `projects/` (2), `resources/` (2), `archives/` (2), plus `BRIEFING.md` (hot active-context layer, PM-maintained, read by all roles at boot) and `.relevance-index.json`.

Frontmatter (per `references/vault-templates/galaxy-template.md`): `type, tags, created, updated, owner, status (active|superseded|archived), confidence (high|medium|low), source, links`. Notable: **no consumption fields of any kind.** Schema is drifting — newer notes (e.g. `learning-doc-first-for-architecture-changes.md`) carry skill-style `name:`/`description:`/nested-`metadata:` frontmatter alongside the canonical fields.

### 3.2 Write side (elaborate machinery, unmeasured quality)

`vault-remember` runs end-of-cycle per role, guarded by deterministic scripts: quiet-cycle gate, **2-writes/cycle budget**, `vault_check.py dedup-check`, reusability + fresh-context judgment gates, per-role write lanes (verifier may not relitigate PM/worker decisions), priority ordering when over budget. `vault_check.py` validates every write (required fields, type↔folder, wikilink resolution, auto-maintained `links`). `vault_optimize.py` prunes stale orphans, decays confidence (high→medium@60d, medium→low@120d), reindexes links, and writes the relevance index. PM's `vault-synthesis` writes cross-agent posture notes, human-gated.

Critical caveats (added on operator review):

- **The throttles are necessity, not advantage.** Budget/lanes/quiet-gates exist because autonomous agents writing every cycle would otherwise flood the vault. dmp-web needs none of this — a human decides when capture is worth it, and `/pr` carries an explicit skip-list. Comparing these as "SquidSquad strengths" was a category error.
- **Dedup is weaker than dmp-web's, not stronger.** `dedup-check` matches title + tags; a differently-phrased duplicate passes. dmp-web treats "find the note this should merge into" as a search problem: `vault-remember` routes through the ranked engine and *prefers update over create*. Without a search engine, SquidSquad structurally cannot do this.
- **Decay is both inferior and dead.** Time-based decay is a worse staleness signal than dmp-web's usage-based one (cold / surfaced-never-used / stale-once-used), and it doesn't run anyway (§3.3).
- **The pipeline is blind.** With zero read telemetry, nothing measures whether written notes are ever consulted. Gate 3 ("reusable beyond this cycle?") is self-judged by the writing agent, and the corpus suggests it passes too easily: 91 of 133 galaxy notes are learnings, mostly single-incident gotchas, sparsely linked, no hubs. Throughput is disciplined; yield is unknown and plausibly low.

### 3.3 Read side (the weak half)

- **Search is prose-wrapped raw grep.** `vault-search` in `vault-protocol.md` describes four grep modes and "max 10 results, sorted by most recently updated." No script, no ranking beyond mtime, no traversal engine (a "max 2-hop wikilink" rule exists only as prose).
- **Consumption mandates exist but leave no trace.** Worker `implement-tasks.md` step 2c, verifier `verification.md` step 1b, PM `task-intake.md` ("MANDATORY") and `improvement-scan.md` all say *consult the vault first* — but except for PM's requirement to paste vault context into the research spawn's `--context` (or write "Vault consulted — no relevant prior context found"), **nothing verifies consultation happened, and nothing records what was consulted.**
- **`.relevance-index.json` is write-only rot.** Generated by `vault_optimize.py` (`score = links×0.4 + recency×0.3 + confidence×0.3`), consumed by **no code path at all**, last regenerated **2026-05-16**, covering 28 of today's 140 notes. Its existence also implies `vault_optimize.py run` effectively never fires.
- **No binding-rules lane.** `areas/code-conventions.md` and `decision-*` notes are advisory context; nothing marks a note as *binding on implementation*, and no step matches rules against a task's surface.
- **Capture is decoupled from shipping.** Learnings are written at cycle end, disconnected from the PR that produced them — no "vault note ships inside the PR" atomicity, no PR↔note back-references as a rule.
- **Content shape limits traversal.** The galaxy is a flat sea of leaf learnings about the harness itself; there are almost no entity/hub notes (systems, subsystems, people) to serve as connective tissue, so graph traversal — even if built — would have few edges to walk.

### 3.4 What genuinely survives scrutiny (assets, mostly potential rather than realized)

Revised on operator review — the first draft's "already does better" list conflated machinery with outcomes. The honest residue:

1. **Scripts-pinned-by-tests as an approach.** SquidSquad's gates are deterministic CLIs with test coverage; dmp-web's write conventions live in agent prose and can drift. The *approach* is sounder even though what it currently gates is throttle-plumbing. Carry this approach into the read side (Phase 1).
2. **Supersession semantics.** `status: superseded` + append-only changelogs are used in practice and keep the corpus honest about reversals. Modest but real.
3. **BRIEFING.md as a concept.** An always-read hot layer is a good idea dmp-web lacks — but the current file is a ~40 KB PM session-log, far past its ~50-line design, so today it's as much token tax as asset. Needs a diet (see 4.4).
4. **The compose pipeline + multi-agent team as delivery mechanisms.** These make the *plan* possible (deterministic injection, verifier-enforced receipts) — they are why SquidSquad can leapfrog, not evidence that it currently leads. Metadata like `owner`/`confidence`/`source` belongs here too: potentially valuable ranking signals, currently consumed by nothing.

---

## 4. Side-by-side matrix

| Dimension | dmp-web `.obsidian-memory/` | SquidSquad `.squidsquad/vault/` |
|---|---|---|
| Layout | people / systems / projects / knowledge / development-rules | PARAG: galaxy / areas / projects / resources / archives + BRIEFING |
| Note count / shape | 146; entity notes + knowledge, heavily cross-linked | 140; 95% flat galaxy leaves, sparse links, few hubs |
| Search | Deterministic engine: tiered match + budgeted graph traversal + used-weighted ranking; spec-tested | Prose grep protocol; mtime ordering; no script |
| Consumption telemetry | `impression`/`walked`/`used`/`last_impression` per note; tunable weights; raw grep banned | None |
| Binding rules | `development-rules/` + two-stage tag-catalog matcher; binding on implementer; explicit "none matched" receipts | None (code-conventions is advisory) |
| Consumption receipts | `## Vault context consumed` + `## Applicable Development Rules` committed in plans; `used` recorded on cited slugs | PM intake `--context` paste only |
| Capture loop | `/pr` captures to vault **before** PR opens; note ships in the same PR; URL backfilled | End-of-cycle reflection, decoupled from PRs |
| Write gates | Prose conventions in background subagents (no-orphan, dedup-search, changelog) | Deterministic scripts: budget, dedup, validation, decay, write lanes |
| Maintenance | On-demand optimize (communities, human-gated contradictions) + impressions report (cold/never-used/stale purge lists) | `vault_optimize.py` prune/decay/reindex — **rarely or never runs** |
| Relevance ranking | Live, consumed on every search, improves with use | Orphaned JSON index; stale since 2026-05-16; zero consumers |
| Observability | Graph viewer w/ plan nodes + walked-traffic edges | None |
| Enforcement | CLAUDE.md policy + skill triggers + first-turn probe (single-session discipline) | Compose-slot instructions (structural) but zero verification |
| Consumers | Human-driven skills (planner, implementer, /pr) | Autonomous roles (PM, worker, verifier, DM), every cycle |

---

## 5. Gap analysis — what dmp-web has that SquidSquad lacks

Ranked by impact on "tasks actually taking advantage of the vault":

1. **G1 — No search engine.** Grep with mtime ordering finds recent notes, not relevant ones; 133 galaxy notes is already past the point where grep-and-skim works. This is the root gap: everything else (telemetry, ranking, receipts) hangs off a deterministic query path.
2. **G2 — No consumption telemetry.** Nobody can answer "which notes get used? which are dead? did the vault help this task?" The write side curates blind: decay is time-based, not usage-based.
3. **G3 — No binding-rules lane.** Human-preference and convention notes (`human-profile`, `code-conventions`, many `decision-*`) have the *content* of binding rules but not the *mechanism* — nothing forces a worker to match them against a task's surface, and nothing tells the verifier which rules applied.
4. **G4 — No receipts.** "Consult the vault" is unverifiable. dmp-web's key trick is that consumption produces a *committed artifact* (the plan sections), which downstream consumers then build on and which can be audited later.
5. **G5 — Capture decoupled from shipping.** A learning discovered while fixing #13454 lands (maybe) at cycle end via reflection, not in #13454's PR. The knowledge and the change it came from are not atomic and not cross-referenced.
6. **G6 — No connective entity layer.** No `systems`-style hub notes for harness / compose pipeline / tracker / pr_merge / event bus etc., so related learnings don't cluster and traversal has nothing to walk.
7. **G7 — Dead maintenance loop.** The relevance index proves `vault_optimize.py` doesn't run; confidence decay and pruning likely aren't happening either.
8. **G8 — Write side has no quality feedback and weak dedup.** Nothing measures whether written notes are ever read (yield is unknowable); dedup is title/tag matching rather than search-based update-preference, so the corpus accretes near-duplicate single-incident learnings instead of consolidating into fewer, denser notes.

---

## 6. Design principles for the port — adapt, don't copy

Three SquidSquad realities mean dmp-web's mechanics must be adapted, and each adaptation is also an opportunity to do better:

- **P1 — Git-as-bus forbids frontmatter counters.** dmp-web bumps `impression:` inside note files — fine for one dev on one checkout. SquidSquad has N agents in N clones committing through PRs; frontmatter counter bumps would generate constant merge conflicts and telemetry commits polluting the audit trail. → Telemetry must be an **append-only event ledger** (per-agent JSONL, e.g. `.squidsquad/vault/.telemetry/<role>.jsonl` or harness-collected events), aggregated into rankings at read time or by a maintenance pass. Strictly better: it preserves *who/when/which-task* per event, which dmp-web's flat ints throw away.
- **P2 — Multi-agent means receipts can be *enforced*, not just requested.** dmp-web relies on one agent's discipline. SquidSquad has a verifier and a DM in the loop: consumption receipts can become **checkable gates** (QA test plans verify the receipt section exists and cited rules were obeyed; DM citation gates already exist as a pattern — see `pattern-dm-citation-soft-gate-satisfied-for-qa-bugs`).
- **P3 — The compose pipeline enables deterministic injection.** dmp-web can only *instruct* the model to search. SquidSquad can *put relevant vault context in front of the agent without asking*: at task-creation time (tracker attaches a vault-context section to the issue body) and at compose/boot time (BRIEFING digest). Instructions-to-remember lose to context-already-present.

---

## 7. Improvement plan

> **Superseded in part (operator decision 2026-07-12):** rather than retrofitting dmp-web's consumption loop onto the current system, we adopt dmp-web's vault system wholesale as the base — see **§9**. §7's Phase 0.5 (distillation) folds into the migration, Phase 1's engine is adopted rather than designed, Phase 1.2's in-repo ledger is replaced by §9.4's harness-owned store (operator: telemetry must never appear in installed-project PRs), and **Phases 2–4 carry over unchanged** as the multi-agent adaptation/leapfrog layer on top.

Phased so each phase is independently shippable and valuable. Per house process: **Phase 0 can go straight to tasks (bug-class hygiene); Phases 1–4 need a `docs/VAULT-ARCH.md` TRD update reviewed by the human first**, and every task that changes agent instructions carries comprehension-test (CQ) specs.

### Phase 0 — Stop the rot (hygiene, small)

- **0.1** Decide the relevance index's fate: it gets a consumer in Phase 1, so keep it — but regenerate it now and wire freshness (below). If Phase 1 is rejected, delete it instead of shipping a lie.
- **0.2** Audit why `vault_optimize.py run` never fires (quiet-cycle trigger conditions); wire it into the harness's scheduled maintenance (harness-owned freshness, same three-layer model as compose freshness).
- **0.3** Fix schema drift: extend `vault_check.py` Level-1 to reject skill-style frontmatter in galaxy notes; sweep the existing offenders.
- **0.4** Close the `decision-vault-subagent-model-sonnet` gap (#10180): heavy vault sub-skills actually run as sonnet subagents, not inline.
- **0.5** One-time distillation sweep of the galaxy (G8): human-gated pass over the 91 learnings — merge near-duplicates, prune single-incident notes with no reuse value, consolidate clusters into pattern notes. This is the SquidSquad analogue of dmp-web's optimize merge sweep, run once as a cleanup before the read-side engine indexes the pile. (The hub-note work in 4.2 attaches what survives.)

### Phase 1 — Read-side engine + telemetry (the foundation; port of dmp-web G1/G2 under P1)

- **1.1 `vault_search.py`** — deterministic query CLI mirroring `vault_check.py`'s style (tested, Windows-safe):
  - Tiered matching: filename > inbound-wikilink > tag > content.
  - Budgeted traversal: follow `links`/wikilinks outward; galaxy notes cost budget (max 2 per path), area/project/hub notes free — dmp-web's knowledge-budget idea mapped onto PARAG.
  - Ranking: match tier first; tiebreak = `used×2.0 + impression×0.25 + walked×0.5 + recency×0.25`, **multiplied by SquidSquad-only signals dmp-web doesn't have: `confidence` weight and `status` (superseded notes rank near zero, still discoverable)**. Weights in a tunable `vault-consumption.json` equivalent.
  - Output: JSON metadata (paths, tiers, scores, link map) — agent Reads the bodies it wants. Replace every `grep -rl` snippet in role sub-skills with `python references/scripts/vault_search.py ...`; ban raw grep for vault search in `vault-protocol.md` with dmp-web's rationale (telemetry blindness).
  - **Reroute dedup through the engine (G8):** `vault-remember`'s dedup gate calls `vault_search.py` instead of title/tag `dedup-check`, and adopts dmp-web's *prefer-update-over-create* rule — the top-ranked hit above a similarity threshold becomes the merge target, and a new note is only created when nothing ranks.
- **1.2 Telemetry ledger** — search writes `impression`/`walked` events, consumers write `used` events (`vault_search.py record --counter used --slugs a,b --task #NNN`) to **append-only per-role JSONL**, each event carrying `{ts, role, task, slug, counter, source}`. No note-file writes → no merge conflicts (P1). A small aggregator produces per-note totals for ranking; `vault_optimize.py relevance` consumes aggregated `used` so the index finally reflects reality.
- **1.3 Impressions report** — port `vault-impressions-report`: cold / surfaced-never-used / stale-once-used lists feeding `vault_optimize.py` pruning and PM's improvement scan. Decay becomes usage-aware, not just time-based.

### Phase 2 — Consumption receipts + binding rules (port of G3/G4 under P2)

- **2.1 Rules lane.** New vault category `galaxy/rule-*` (or `areas/rules/`) with `binding: true` frontmatter; migrate the binding-shaped content out of `code-conventions.md`, `human-profile.md`, and applicable `decision-*` notes. Authoring stays inside the existing write gates.
- **2.2 Rule matching step.** A `vault-rules` sub-skill (two-stage tag catalog, straight port of `/vault-development-rules`): worker runs it before implementing; result lands in the task artifact as `## Applicable rules` (explicit "none matched" required). Matched rules get `used` events.
- **2.3 Receipts everywhere.** Standardize a `## Vault context consumed` section (wikilink + one-line relevance, or explicit "none relevant") in: research docs (PM intake already half-does this via `--context`), CONTEXT.md / plan artifacts, and **PR bodies**. Cited slugs get `used` events with the task number.
- **2.4 Verifier enforcement.** QA verification adds two cheap checks: the receipt section exists, and the implementation doesn't violate any rule listed in `## Applicable rules`. Missing receipt = back to dev, same as any other gap. This is the step dmp-web cannot do — single-agent discipline becomes team-enforced process.

### Phase 3 — Capture-at-ship (port of G5)

- **3.1** Add a capture step to the skill role's ship flow (pre-PR, mirroring `/pr` Step 7.5): decide if the task produced durable knowledge (decision / root cause / pattern — with dmp-web's skip-list for chores); if yes, write the note **on the feature branch so it ships in the same PR**, with the issue number in `## Related`. Counts against the existing write budget; dedup gate unchanged.
- **3.2** Keep end-of-cycle `vault-remember` as the *sweep* for what per-task capture missed — the two are complementary (dmp-web only has per-PR capture; we get both).
- **3.3** Backfill: PR URL / issue ref appended to the note's changelog on merge (DM or pr_merge hook).

### Phase 4 — Leapfrog (things dmp-web structurally can't do)

- **4.1 Task-time context injection (P3).** When PM files a task, `tracker.py` (or the intake sub-skill) runs `vault_search.py` on the task's keywords and appends a `## Vault context` section — top-K note names + one-liners — **into the issue body**. Dev agents read the body first (house rule), so relevant vault context arrives with the task deterministically, before any agent has to remember to search. Impression events attribute to the task.
- **4.2 Hub/entity layer (G6).** Create ~10–15 hub notes for the systems agents keep learning about (harness, event bus, compose pipeline, tracker, pr_merge, launcher, QA gates, vault itself); a one-time linking pass attaches existing galaxy leaves to their hubs. Hubs are traversal-free connective nodes (P1.1) — this is what makes graph search *better than grep* in practice.
- **4.3 Outcome-linked telemetry.** Join the ledger with tracker outcomes: a QA-failed task whose failure matches an existing un-consulted note = **missed-consultation event** (PM improvement-scan reviews these — direct evidence the read side failed); a note repeatedly `used` by tasks that pass QA first try gets a ranking boost. dmp-web measures *usage*; this measures *effectiveness*.
- **4.4 BRIEFING vault digest.** A small auto-generated BRIEFING section (from ledger aggregates): hottest notes this week, newly added rules, missed-consultation count. Keeps the hot layer honest and gives the operator a vault health pulse for free.
- **4.5 (Optional) viewer.** Port the zero-dep graph viewer onto the harness web server (`/vault` route): graph + walked-traffic edges + task nodes (issues in place of dmp-web's plan files). Cosmetic but cheap once the harness serves HTTP anyway.

### Sequencing and effort (rough)

| Phase | Depends on | Size | Value |
|---|---|---|---|
| 0 Hygiene | — | S | Stops active rot; restores trust in optimize loop |
| 1 Engine + ledger | 0.2 | M | Foundation; makes search relevant and measurable |
| 2 Receipts + rules | 1 | M | The dmp-web magic: consumption becomes verifiable |
| 3 Capture-at-ship | — (parallel w/ 2) | S | Knowledge atomic with the change that produced it |
| 4 Leapfrog | 1 (4.1, 4.3, 4.4); none (4.2) | M–L | Beyond parity: injection, enforcement, effectiveness |

Quick wins if only two things get approved: **1.1 + 2.3** (a real search engine, and receipts in PR bodies) capture most of dmp-web's value at a fraction of the surface area. **4.2** (hub notes) is a PM-writable, zero-code improvement that can start immediately.

---

## 8. Risks / open questions for the human

1. **Telemetry ledger location** — **resolved 2026-07-12 (operator):** harness-owned, gitignored, never visible in installed-project PRs — see §9.4. Remaining sub-decision: periodic aggregate snapshot for durability (§9.6 #5).
2. **Receipt overhead** — every artifact gains a section; mostly one line ("none relevant"). Verifier check keeps it honest; write-budget analogue (cap cited slugs, like dmp-web's top-K restraint) prevents receipt spam.
3. **Rules-lane migration** — deciding which decision-*/convention content is *binding* vs advisory needs human judgment; propose PM drafts the initial rule set for operator review.
4. **Search-engine scope creep** — 1.1 is deliberately a CLI + JSON contract (like dmp-web's, pinned by tests), not an embedding/RAG system. The second-brain RAG vision stays a separate, later track.

---

## 9. Revision 2 (2026-07-12): wholesale adoption strategy

Operator decision: **adopt dmp-web's vault system as the base, overwriting the current one**, keeping only what is demonstrably superior, and improving the parts that don't transfer (folder taxonomy → dynamic). This supersedes §7 Phases 0–1; §7 Phases 2–4 (receipts + rules enforcement, capture-at-ship, leapfrog) remain the layer built on top.

### 9.1 What we adopt as-is (dmp-web contracts, unchanged semantics)

- **Note schema:** `type / created / updated / last_optimized / community / subcommunity / impression / used / walked / last_impression / tags` (+ per-type fields), kebab-case filenames, wikilinks, append-only `## Changelog`, "no implementation details" rule, no tickets-folder rule (GitHub issues are the source of truth, referenced in `## References`).
- **Search contract:** tiered matching (filename > inbound-link > tag > content), budgeted graph traversal (dense types cost budget, connective types free), two-stage used-weighted ranking, top-K telemetry write-back, `--no-write` dry-run, metadata-only JSON output. Raw-grep ban with the telemetry-blindness rationale.
- **Consumption model:** `impression`/`walked` written by the engine, `used` written only by consumers, disjoint per run, tunable weights file.
- **Write-side semantics:** search-based prefer-update-over-create, `DUPLICATE-BLOCKED` / `ORPHAN-BLOCKED` guards, background-subagent execution for heavy writes (aligns with the existing sonnet-subagent decision, #10180).
- **Maintenance:** optimize queue by `last_optimized` (14-day cutoff), community detection + subsplit, analyze-then-apply with **human-gated contradictions**, impressions report (cold / surfaced-never-used / stale) as the purge signal.
- **Viewer data contracts:** `/api/vault`, `/api/note`, per-edge walked traffic, plan/task nodes with `ticket`/`mention` edges.

### 9.2 What survives from the current system (the superior shortlist)

1. **`status: active | superseded | archived`** added to the adopted schema. dmp-web has no supersession concept; a status field beats both dmp-web (nothing) and old-SquidSquad's `archives/` folder (statuses don't require moving files). Engine rule: superseded/archived rank near zero but stay discoverable. This also **retires the `archives/` folder**.
2. **Deterministic, test-pinned tooling as the approach.** Whatever we adopt gets the `vault_check.py` treatment: scripts with tests, not subagent prose. dmp-web's own spec tests get translated with the port (§9.4).
3. **BRIEFING.md hot layer** — kept at vault root, excluded from ranking, **dieted back to its ~50-line design** with the §7 4.4 auto-digest replacing hand-maintained sprawl.
4. **Write throttles (budget, quiet-gate, role lanes)** — kept because autonomy needs them (necessity, not advantage), but re-based on the new dedup: with prefer-update-over-create, most cycle output becomes *appends to existing notes*, which is the correct pressure.
5. **Human-gated `vault-synthesis`** and the compose-pipeline delivery mechanism (vault protocol as a compose slot).
6. **Dropped entirely:** confidence decay (replaced by usage-based staleness), `.relevance-index.json` (replaced by engine ranking + impressions report), the grep-protocol prose, and the `confidence` field itself **unless** the engine consumes it as a ranking multiplier — no more write-only metadata. `owner` is kept (cheap, useful for lane accountability in a multi-role vault).

### 9.3 Folder taxonomy: adopt the shape, make it dynamic

dmp-web's five folders mostly *do* apply — `systems/` is exactly the missing hub layer (G6), `development-rules/` is the missing binding lane (G3), `knowledge/` + `category` maps 1:1 onto galaxy prefixes. What doesn't transfer is the *hardcoding*: dmp-web bakes the taxonomy into skill prose and script constants. We make it config-driven:

**`vault-schema.json` (type registry, at vault root):**

```json
{
  "traversalBudget": 2,
  "searchTopK": 12,
  "tieBreakWeights": { "used": 2.0, "impression": 0.25, "walked": 0.5, "recency": 0.25 },
  "types": {
    "person":    { "folder": "people",    "traversal": "free",     "weight": 0.6 },
    "system":    { "folder": "systems",   "traversal": "free",     "weight": 0.8 },
    "project":   { "folder": "projects",  "traversal": "free",     "weight": 0.8 },
    "knowledge": { "folder": "knowledge", "traversal": "budgeted", "weight": 1.0,
                   "categories": ["decision", "learning", "pattern", "implementation", "reference"] },
    "rule":      { "folder": "rules",     "traversal": "free",     "weight": 1.0, "binding": true }
  }
}
```

- Engine, validator, templates, and `vault-init` all read the registry; nothing hardcodes folder names. dmp-web's knowledge-budget rule generalizes to `traversal: budgeted|free`; its `folderWeights` and binding-rules concept become per-type attributes.
- **Per-install extensibility is the point:** SquidSquad installs into arbitrary repos — an infra org can add `runbook`, a data org `dataset`, each with its own template, weight, and traversal class, without touching engine code. dmp-web cannot do this.
- Default registry ships the five dmp-web-equivalent types. Old-SquidSquad mapping: galaxy → `knowledge/` (prefix → `category`), `code-conventions` + binding human preferences → `rules/`, `human-profile` → `people/` (operator note; agent-role actor notes optional), `resources/` → `knowledge` `category: reference`, `archives/` → `status: archived`.

### 9.4 The two adaptations that are non-negotiable

> **Point 1 REVISED 2026-07-18 (operator) — see §10.5.** This subsection's "telemetry never enters git, harness-owned" design assumed exactly one harness process per install. Operator confirmed that's false in general: a SquidSquad install can have **multiple independent harness instances** (e.g. each teammate running their own local harness against their own clone, no shared always-on server) — the same "many independent local checkouts" topology dmp-web actually has, which is *why* dmp-web needs git as its sync layer. A purely harness-local store would fragment per teammate instead of sharing usage across the team. §10.5 replaces the design below with git-tracked, append-only, per-harness-instance shards — kept for the historical record of the reasoning that got superseded, not as the current design.

1. ~~**Telemetry never enters git — harness-owned, invisible to the installed project's PRs**~~ (operator directive 2026-07-12, superseding the earlier in-repo ledger idea — **now itself superseded, §10.5**). dmp-web's frontmatter counters are only livable with a local husky hook auto-resolving conflicts; SquidSquad, as an installed product, must not surface telemetry noise in the host repo's PRs *at all*. The harness — an always-on daemon dmp-web doesn't have — makes the clean design possible:
   - **Emit:** the engine and consumers POST events (`{ts, agent, task, slug, counter, source}`) to a harness endpoint (the harness is already the event bus). Best-effort: if the harness is unreachable (rare — it supervises the agents), the event is dropped with a log line. Telemetry is operational signal, not content; losing an event is fine, blocking a search on it is not.
   - **Store:** harness-owned, **gitignored** store in the install (e.g. `.squidsquad/telemetry/vault-events.jsonl` + compacted aggregates). Never committed, never in a PR, never in the host repo's history.
   - **Consume:** the engine fetches per-note aggregates from the harness (`GET /vault/stats`) for Stage-2 ranking, degrading gracefully to tier + recency when unavailable. The viewer and the impressions report compose note content (git working tree) with live telemetry (store) **at request time** — no materialization step.
   - **Notes stay pure content, forever.** No counter fields in frontmatter at all — which also erases dmp-web's lazy-seeding schema variance (47/146 notes with counters, inconsistent field order) and retires the husky-class conflict patching as a concept. Events keep per-task attribution (richer than dmp-web's flat ints), powering §7 4.3 outcome-linking centrally in the harness where tracker outcomes already flow.
   - **Durability trade-off:** telemetry resets on fresh install / lost machine (it rebuilds within weeks of normal use). Optional mitigation — harness periodically exports a compact aggregate snapshot for backup — operator call (§9.6). A slug-redirect map from migrations (§9.5) lets aggregation reconcile events emitted by behind-main clones against renamed notes.
2. **Tooling language.** Recommendation: **port the engine/consumption/check/optimize scripts to Python** (`vault_query.py` etc.), preserving dmp-web's JSON contracts and translating its spec tests — the installer's runtime stays Python-only. The **viewer frontend (zero-dep prebuilt `index.html`) gets vendored as-is**, with the harness serving compatible `/api/vault` / `/api/note` endpoints on a `/vault` route (fits the harness web-server vision). Plan-scanner adaptation: scan tracker issues / planning artifacts instead of `.planning/*.md`, so task nodes replace plan nodes in the graph.
   - Alternative (vendor the .mjs scripts, require node) is faster to land but adds a runtime dependency to every target install — flagged for operator call in §9.6.

Smaller adaptations: Jira → GitHub issue references; dmp-web's first-turn probe → boot-BRIEFING + task-time injection (§7 4.1); dmp-web's "never schedule optimize" → harness *schedules the analyze phase*, and its human-gated items are filed as HITL tracker tasks (fits existing HITL patterns) rather than blocking a terminal.

### 9.5 Migration design (per house process)

Framing: this is not a one-off cleanup of our repo. **Every installed project has its own vault content**, so the migration ships as a product feature — a deterministic transform script + an optional distillation pass + a `references/migrations/` entry per the upgrade-is-fresh-install model. Our own repo is simply the first (and hardest, 140 notes) install to run it.

**Sequencing wrapper:** TRD first (`docs/VAULT-ARCH.md` v2, human-reviewed — this §9 is the seed); v2 tooling/templates land side-by-side behind an opt-in compose flag (v1-coexistence pattern); migration runs M0→M4 below; atomic cutover PR flips the default and deletes v1 machinery; then the leapfrog layer (§7 Phases 2–4).

**M0 — Snapshot & freeze.**
- Freeze vault writes by setting the existing write-budget gate to 0 via config (deterministic, reuses `vault_remember.py write-budget`). Vault writes are low-volume; a 1–2 day freeze is harmless and beats delta-replay complexity.
- Snapshot v1 (`git tag` or branch) as the rollback point and the migration input.

**M1 — Mechanical transform (deterministic script, tested, no judgment).**

Mapping table:

| v1 | v2 | Notes |
|---|---|---|
| `galaxy/decision-*.md` | `knowledge/`, `category: decision` | type prefix dropped from slug |
| `galaxy/learning-*.md` | `knowledge/`, `category: learning` | prime M2 distillation candidates |
| `galaxy/pattern-*.md` | `knowledge/`, `category: pattern` | |
| `galaxy/style-*.md` | `rules/` | style conventions are binding |
| `areas/code-conventions.md` | `rules/*` (split) | one atomic rule per note, topic-tagged — M2 proposes the split |
| `areas/human-profile.md` | `people/wallace-chan.md` + `rules/*` | profile stays a person note; binding preferences extracted to rules (M2) |
| `projects/*.md` | `projects/` | as-is |
| `resources/*.md` | `knowledge/`, `category: reference` | |
| `archives/*.md` | `knowledge/`, `status: archived` | or pruned in M2 |
| `BRIEFING.md` | vault root, unchanged path | dieted separately (§7 4.4) |
| `.relevance-index.json` | **deleted** | replaced by engine + telemetry store |

- **Frontmatter transform:** keep `created`/`updated`/`tags`/`owner`/`status`; map `type` per table (+ set `category`); add empty `community`/`subcommunity`/`last_optimized`; drop `confidence` and `source` (pending §9.6 #2 — if kept, they migrate to tags); drop `links` (the engine computes the link graph from body wikilinks; no more manually-maintained duplication).
- **Slug policy:** drop `decision-`/`learning-`/`pattern-`/`style-` prefixes — folder + `category` now carry the type, matching dmp-web's convention. The script maintains an **old→new redirect map**, rewrites every wikilink vault-wide in the same pass, and greps the whole repo (`docs/`, `references/`, `.squidsquad/`) for out-of-vault references to old slugs, fixing or flagging each. The redirect map ships as a migration artifact (also used by telemetry aggregation, §9.4).
- **Changelog:** preserved verbatim; every migrated note gets one appended entry (`- **<date>** — migrated to vault v2 (from <old-path>).`).
- Script is idempotent and dry-runnable; pinned by tests like the rest of the tooling.

**M2 — Distillation (agent judgment, analyze-only, absorbs §7 0.5).**

Modeled on dmp-web's optimize Phase A: sonnet subagents per topical cluster, **proposing** rather than applying:
- Per note or note-cluster, a verdict: `keep` / `merge-into <target>` (with the merged draft) / `prune` (with one-line justification). The 91 single-incident learnings are the main target.
- Extract the initial `systems/` hub set (~10–15: harness, event bus, compose pipeline, tracker, pr_merge, launcher, QA gates, vault) and propose which surviving knowledge notes link to which hub — this is what makes traversal work on day one.
- Propose the `rules/` split of `code-conventions` + `human-profile`'s binding preferences (atomic, topic-tagged, `binding: true`).
- Output: a single reviewable **migration manifest** (every v1 note → disposition).

**M3 — Human gate, then apply.**
- Operator reviews the manifest — merges and prunes are the judgment calls that must not be autonomous (same philosophy as dmp-web's contradiction gate). Filed as a HITL item, not a blocking terminal prompt.
- Apply phase executes the approved manifest on top of M1's output.
- **Verification gates (all must pass):** full `vault_check` sweep with zero errors; zero broken wikilinks; reconciliation — 140 notes in = Σ(migrated + merged-into + pruned) with per-note disposition, committed as a migration artifact; dry-run of the whole M1→M3 pipeline on a test clone first (house rule: create test environments, never rehearse on live state).

**M4 — Cutover + unfreeze.**
- Atomic PR: new vault replaces old in place, compose default flips to v2 sub-skills (rewritten around the engine + receipts, with CQ specs per house rule), v1 machinery deleted (grep-protocol prose, relevance index, decay paths, old templates).
- `references/migrations/v<N>-to-v<N+1>.md` documents the same M0→M4 walk for installed projects: mechanical script always runs; the M2 distillation pass is offered but skippable (config), since a small young vault may not need it; M3's human gate scales down to reviewing whatever M2 proposed.
- Unfreeze writes (budget restored). Telemetry starts cold — by design (§9.4).

### 9.6 Open decisions for the operator

1. **Engine language:** Python port with translated spec tests (recommended — keeps installs node-free) vs vendoring dmp-web's .mjs scripts (fastest, adds node to target-repo runtime requirements). **Superseded — see §10.2.**
2. **`confidence` field:** keep as an engine ranking multiplier, or drop (no write-only metadata). Recommendation: drop at migration, reintroduce only with a consumer.
3. **Distillation aggressiveness:** how hard to prune the 91 learnings during migration (recommendation: aggressive — usage telemetry will vindicate or refute survivors within weeks).
4. **Viewer priority:** vendored-frontend + harness endpoints is cheap but still optional polish; confirm it belongs in the cutover scope vs the leapfrog layer.
5. **Telemetry durability:** accept reset-on-reinstall (recommended — signal rebuilds within weeks of use), or have the harness export a periodic compact aggregate snapshot as backup.

---

## 10. Revision 3 (2026-07-18): scope correction — mechanics over shape, and a packaging option §9 didn't anticipate

Operator decision, superseding §9's "adopt wholesale" framing. Two new facts changed the plan:

### 10.1 SquidSquad is general-purpose; dmp-web's vault is SWE-only — that's a real conflict, not a footnote

§9.2's "make the folder taxonomy dynamic" (a config-driven `vault-schema.json`) still shipped dmp-web's five SWE-shaped types (`people/systems/projects/knowledge/development-rules`) as the *default*, and §9.1's "adopt as-is" list includes dmp-web's Jira/PR-shaped receipt conventions and its "no implementation details, Jira/PRs are the source of truth" rule. SquidSquad's own product vision (`areas/human-profile.md` Product Vision section) explicitly targets non-technical teams (marketing, ops, content) with no GitHub/git knowledge. Shipping a SWE-coupled default is wrong on day one for that audience, even though it's *fine for SquidSquad's own self-hosted install today* (self-hosting is inherently dev-work).

**Corrected framing — port the mechanics, not the shape:**
- **Adopt (domain-agnostic, ports directly):**
  - The **consumption pipeline pattern**: mandatory vault touchpoints baked into a skill's own steps (not "remember to check the vault" — the step *cannot proceed* without running the search), producing a committed receipt (`## Vault context consumed` / `## Applicable rules`) that downstream steps and the verifier can check. This is §7 Phase 2's G3/G4 port — nothing about it assumes software.
  - The **telemetry-driven ranking**: `impression`/`walked`/`used` events replacing time-based confidence decay. Nothing about counting "was this note used" assumes software either.
- **Do NOT adopt as the hardcoded default:** dmp-web's specific five-folder taxonomy, its Jira/PR-only receipt shape, its "no implementation details" rule. These become *one configurable type-registry profile* (the one SquidSquad's own self-hosted install uses, since it IS software work) — never the engine's baked-in assumption. §9.3's `vault-schema.json` config-driven design already pointed this direction; this revision makes it the *load-bearing* requirement, not an extensibility nice-to-have.

### 10.2 Packaging: the portable extraction may resolve §9.6 open decision #1 differently

dmp-web's vault system is being separated out of dmp-web's own codebase into a standalone, multi-project-capable tool — **packaged as Node + Claude Skills**, scoped to software-development use for now (consistent with §10.1 — SquidSquad still needs to generalize the taxonomy regardless of how the engine is packaged).

This opens a third option §9.4.2 didn't consider: **invoke the portable package's Claude Skills directly from within a SquidSquad agent session**, rather than either (a) porting the engine to Python or (b) vendoring the `.mjs` scripts as a subprocess dependency SquidSquad's Python installer has to manage. SquidSquad agents already run as Claude Code sessions with Skill-tool access (demonstrated live this session — Skill invocations to `deep-research` etc. work identically to how a `/vault-search` skill would). If viable, this sidesteps §9.4.2's Python-runtime-purity constraint entirely: the Node dependency would sit on whatever machine already runs Claude Code, not on SquidSquad's own install-time Python runtime.

**Two things must be verified before this becomes the plan, not assumed:**
- Whether invoking another project's Claude Skill reliably works from inside an *autonomous, non-interactive* agent session the way it does in this interactive one.
- Whether Node is guaranteed present on a target machine just because Claude Code is (not yet confirmed).

**This does not change §10.1** — even if the engine is consumed via Skill invocation rather than ported/vendored, the taxonomy/schema genericization is still required; packaging and domain-scope are orthogonal decisions.

### 10.3 §9.6 decisions #1–#2 resolved (2026-07-18, operator)

- **§9.6 #1 (engine language) superseded by §10.2's packaging question — resolved: invoke via Skill tool.** SquidSquad agents call the portable package's Claude Skills directly (as this session's PM does with `deep-research` etc.), rather than porting to Python or vendoring the `.mjs` scripts. Rationale: zero maintenance drift (upstream improvements arrive free), no new install-time runtime dependency for SquidSquad's Python-only installer. **Still pending, not yet verified** (do NOT treat as fully locked until confirmed): (a) Skill invocation reliability from an autonomous, non-interactive agent session; (b) Node-alongside-Claude-Code guarantee on arbitrary target machines. §10.1's taxonomy/schema genericization requirement is unaffected either way — packaging and domain-scope are orthogonal.
- **§9.6 #2 (`confidence` field) — resolved: drop.** No write-only metadata in the v2 schema. Reintroduce only if a real ranking need for "how sure are we" surfaces later, with an actual consumer at adoption time — not speculatively.

Remaining open: §9.6 #3 (distillation aggressiveness), #4 (viewer priority), #5 (telemetry durability) — not yet needed to start drafting the TRD's core sections; resolve when the migration/viewer/durability sections are reached.

### 10.4 Next steps

1. Verify the two pending §10.3 items (Skill-invocation-from-autonomous-session viability; Node-alongside-Claude-Code guarantee) — before finalizing the TRD's §7/§8-equivalent sections (sub-skills/scripts), since their concrete shape depends on the answer.
2. Write `docs/VAULT-ARCH.md` v2 as a human-reviewed TRD update per doc-first process — this document (§9 as corrected by §10) is the seed; no implementation tasks get filed before the TRD lands and is reviewed. **In progress as of 2026-07-18 on `#10003`** (branch `squidsquad/task/10003`, draft PR #13708; §1–§4 drafted).
3. **Cleanup done 2026-07-18**: closed 10 vault tickets superseded by this direction (#10098, #10099, #10100, #10179, #10182, #5855, #207, #20, #1290, #9875). Kept open as independent of this redesign: #10180 (subagent offload, explicitly still-aligned), #19 (hybrid RAG, explicitly a separate future track), #7464 (QA vault write access), #3497 (CLAUDE.md/SOUL.md cross-linking investigation), #3419 (human expertise mapping), #5613 (mostly an event-bus ticket), #555 (DM doc-site page, needs a rewrite later but isn't superseded).

### 10.5 Telemetry storage redesigned: git-tracked per-writer shards (2026-07-18, supersedes §9.4 point 1)

**Triggering fact (operator)**: a SquidSquad install can run **multiple independent harness instances** — e.g. each teammate runs their own harness against their own clone, with no shared always-on server. §9.4's harness-local gitignored store assumed exactly one harness per install; under multi-harness it fragments telemetry into N per-teammate partial pictures, defeating the whole point (team-wide usage informing one shared ranking). This is the same "many independent local checkouts" topology dmp-web has — which is *why* dmp-web routes telemetry through git.

**Why dmp-web's answer is still not the model**: their latest code (DMP-14418) adds a custom `vault-note` merge driver via `.gitattributes` to auto-resolve counter conflicts — but custom merge drivers require **per-clone local registration** (`register-merge-driver.mjs`, opt-in; verified live in their `.gitattributes` 2026-07-18: "The driver only takes effect once registered locally"). Any teammate who hasn't run the registration script gets raw conflicts. It also treats the symptom: conflicts exist because N writers mutate the same lines of the same note files.

**The design (operator reviewing — recommended by PM, treat as the working design pending explicit lock-in)**: telemetry is a grow-only counter — a solved distributed-systems shape (CRDT G-counter). Per-writer shards, sum at read:

1. **Per-harness-instance, append-only JSONL shards, git-tracked**: `.squidsquad/vault/.telemetry/<harness-instance-id>.jsonl`. Each harness appends only to its own file — cross-teammate conflicts are structurally impossible, not auto-resolved. Every event: `{id: <uuid>, ts, agent, task, slug, counter}`.
2. **`merge=union` in `.gitattributes`** on `.telemetry/*.jsonl` — git's *built-in* union strategy (no local registration, works for every clone on day one, unlike dmp-web's custom driver). Covers the one residual case: the same shard diverging across machines (restored backup, cloned VM). Union-merge on append-only lines is safe; readers dedupe by event `id`, so a double-merged line is harmless.
3. **Sync layer = the git remote already serving as the bus.** `git pull` = telemetry sync. No new infrastructure, honors [[project_github_philosophy]].
4. **Compaction**: a quiet-cycle maintenance pass rolls events older than N days into a per-writer aggregate file (still per-writer, still conflict-free). PR-noise control: telemetry commits ride routine `main` commits only, never task branches.
5. **Durability (§9.6 #5) largely dissolves**: telemetry now lives in repo history; machine loss costs only unpushed events (bounded by push cadence). No snapshot mechanism needed.

**Cloud Claude agents — considered and rejected as the sync/storage layer** (operator floated, PM advised against, 2026-07-18): cloud agents are ephemeral compute, not a datastore — the data still needs a durable home, which becomes either a hosted DB (new auth/availability/cost/privacy surface; note slugs leak repo content to a third party) or the git repo, i.e. where this design already is. Legitimate future niche only: running the compaction/impressions-report pass on a schedule for installs with no always-on machine — optional convenience, not architecture.

**Consequence for the TRD**: §6 (telemetry architecture) of `docs/VAULT-ARCH.md` v2 should specify the shard design above, NOT §9.4's harness-endpoint/gitignored-store design. The "notes stay pure content, no counters in frontmatter" rule from §9.4 **survives unchanged** — it was always the load-bearing half.

### 10.6 §10.5 LOCKED + granularity refined (2026-07-18, operator inline review)

Operator explicitly confirmed the §10.5 shard design after stress-testing it live (per-note-vs-per-writer sharding; append-only-still-conflicts-in-git; multi-squad-per-developer topology). Two refinements came out of that review, now canonical in `docs/VAULT-ARCH.md` §6.3 (which supersedes §10.5's wording where they differ):

- **Granularity: per writing clone, not per harness instance** — under clone isolation one harness supervises N agents in N separate clones, each committing independently; a shared per-harness shard would recreate concurrent writers within one squad. Shard = `.telemetry/<harness-instance-id>-<role>.jsonl`.
- **Instance identity: UUID minted at provision time, persisted in gitignored local harness state** — never hostname/username-derived (a developer running X parallel squads would collide), never in a committed file (all clones would inherit it). Makes one-install/X-squads safe by construction.

Related but out of scope for vault-v2: the *rest* of the per-role state layer (`working-state.md`, scan-history, subloop-driver at fixed per-role paths) is NOT multi-instance-safe; parallel squads per developer needs its own design task if the operator wants it as a supported workflow (raised inline 2026-07-18, not yet confirmed as a requirement).

### 10.7 §10.3's two pending verifications — RESOLVED (2026-07-18, PM live probes)

- **(a) Skill invocation from an autonomous agent session: CONFIRMED (mechanism).** PM's own harness-spawned EVENT-mode session invoked a Claude Skill live (2026-07-18 ~23:08) — no permission prompt, no interactivity required, instructions loaded synchronously. Caveats: the invoked skill must be installed/listed on the target machine (user-level or project-level) — *availability*, not invocation, is the real dependency; an additional fully-headless confirmation from a never-inline session would make it airtight but the mechanism risk is retired.
- **(b) Node-alongside-Claude-Code: NOT a guarantee.** This machine happens to be an npm-mode install (`claude` under AppData\Roaming\npm, Node v24 present) — npm-mode implies Node, but Claude Code also ships as a native binary (installer script/brew) with no Node dependency. **Design consequence**: Node is a *checkable soft prerequisite* of the engine feature — the wizard/installer preflights `node --version` when enabling vault-v2's engine; absent Node → feature degrades per TRD §6.2's no-telemetry fallback semantics (or the Python-port fallback path per §9.4.2 stays open). Robust under either distribution reality.
- **Residual unknown (new, replaces the two above)**: the portable dmp-web package's concrete Skill surface (names/contracts of the skills it exposes) is unpublished — TRD §7/§8 therefore spec SquidSquad's own sub-skill layer against an abstract engine interface (search / record / report per TRD §6) and bind concrete skill names at implementation time.
