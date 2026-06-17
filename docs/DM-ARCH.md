# Delivery Manager Architecture (DRAFT — kickoff)

> **Status: DRAFT / kickoff (2026-06-17).** This document captures the initial operator+PM discussion that reframed the SquidSquad DM from a project-specific "bump version every 10 features" role into a **generic, layerable Delivery Manager**. It is intentionally incomplete — it records what we have agreed so far and frames the open questions. A subsequent **polish/brainstorm pass** will expand the L2 process, define the L3 variant model, and specify the L4 plug-in points before any refactor task is filed.

## 1. Why this doc exists

The DM role today bakes a **SquidSquad-specific policy** — "when `Shipped Since Last Bump` reaches 10, cut a semver bump" — into the **universal (L2) DM role**. That policy therefore wrongly applies to every project that installs SquidSquad. The role of a delivery manager is, in reality, **highly project-subjective**: what "delivery" means, when a release is cut, whether there is even a *version* at all — all vary by project and domain.

This doc defines the DM as a layered role so the generic essence lives at L2, domain mechanics at L3, and project policy at L4.

## 2. The layering principle (load-bearing)

**The override mechanism is not new — it is the existing L1–L4 compose machinery.** Per [COMPOSE-ARCHITECTURE.md §3.2–§3.3](COMPOSE-ARCHITECTURE.md): each source fragment declares a `slot` + `ordinal`; `compose.py` gathers all L1–L4 fragments for a role, groups by slot, sorts by ordinal, and applies the **layer op grammar** (`replace` / `insert-before` / `insert-after` / `append`) — L2–L3 inline ops first, then L4 file ops — with higher layers winning on conflict. This is the same machinery `l4-curation` already uses. **We do not design a DM-specific override system; we author the DM so the existing op grammar can target it.**

**Consequence for the DM: L2 is mostly *slots*.** L2 authors the **spine** (the 8 steps in §3) as **addressable step-units** — each step a stably-named unit an L3 or L4 op can target. L2 supplies the universal *what* of each step plus a sane *default how*; **L3 and L4 override the *how* of specific steps** via the standard op grammar. "How we achieve each spine step" is exactly what varies per domain (L3) and per project (L4).

| Layer | Source location | What it contributes to the DM | SquidSquad example |
|---|---|---|---|
| **L1** universal agent | `references/roles/` (base) | base agent behavior (all roles) | — |
| **L2** DM role | `references/roles/dm/` | the **spine as addressable step-units** + a default *how*; default delivery = *ship each verified item as it's ready* | — |
| **L3** domain variant | `references/roles/dm/<domain>/` | **overrides the *how*** of domain-variable steps (package / publish mechanics) | `roles/dm/skill-dev/`: package+publish = merge-to-main + `compose` |
| **L4** this install | `.squidsquad/project/dm.md` | **overrides the *how*** of project-variable steps (cadence, version scheme, targets, record format) | "batch 10 → semver bump + tag", `CHANGELOG.md`, the counter |

**L3-vs-L4 crux:** L3 = the *mechanism class* ("deploy to a host"); L4 = the *concrete target* ("**this** Vercel project, **this** branch"). Keep them separate or the L3 variants won't be reusable across installs.

**The real design work** is therefore NOT a mechanism — it is **(a)** author each spine step as a discrete, stably-addressable unit (so ops can target "step 6: Document" specifically), and **(b)** classify each step's *how* as **L2-complete** (universal), **L3-overridable** (domain mechanics), or **L4-overridable** (project policy). §6 tracks that classification.

## 3. The generic DM lifecycle (L2 spine)

Any delivery manager, any project, runs this lifecycle. Steps 3–4 are the *act* of delivery; steps 6–7 are its *meaning*.

1. **Detect ready work** — something is verified and cleared for delivery.
2. **Pre-flight** — the deliverable is coherent and complete (nothing half-merged, deps satisfied).
3. **Package** — assemble the actual deliverable (the thing that goes out). *(form = L3)*
4. **Publish** — execute the delivery. *(mechanics = L3)*
5. **Confirm landing** — it reached its destination intact.
6. **Generate the delivery report** — synthesize the **facts in the system of record** (for code: forge issue discussion, PR, commits, verification) **and traverse the vault knowledge graph** to attribute *what knowledge informed the delivery* (e.g. "this delivery drew on knowledge K, which summarizes external doc D"). Covers what was delivered, done, investigated, changed, why — plus provenance. **The L2 act is "generate a report from the recorded facts + the knowledge graph"; *what* the report contains, its format, audience, and destination are determined per L3/L4** (internal audit trail, external release notes, or both — a parameter, not a fixed L2 structure). Versioning, changelog format, and release tags are L4 facets; a version-less project still produces a report.
7. **Contribute institutional knowledge (vault graph)** — like **every role at every stage** (planning, task-creation, build, verification, delivery), the DM contributes knowledge gained to the **vault**. *This is not a DM invention:* the vault is the team's **universal, L1-exclusive** institutional memory — a **knowledge graph** (PARAG + Galaxy Zettelkasten; `[[wikilinks]]` are the edges; `resources/` **summarize-and-reference** external artifacts) — domain-agnostic and contributed to by all roles (see VAULT-ARCH / the L1 `vault-remember` discipline). The DM **adds nodes and `[[wikilink]]` edges**; its *distinctive* edges are the **cross-connections** its end-to-end **vantage** surfaces ("this client/job relates to that other one," recurring patterns) that no single-stage role sees.
8. **Handle failure** *(cross-cutting)* — on a failed delivery, roll back and/or route the work back to its owner.

**Default (no L4 policy):** ship each verified item as it's ready — no batching, no version concept.

### Two stores (steps 6 & 7 substrates)

The DM's two "meaning" steps read/write two **distinct stores with different universality**:

| Store | Universality | Holds | DM step |
|---|---|---|---|
| **System of record** | **domain-specific** (forge/GitHub for code; an email+spreadsheet store, CRM, etc. for a non-code team) | raw work artifacts + the code/work audit trail | step 6 **reads** it → generates the report |
| **Vault** | **universal (L1)**, domain-agnostic | distilled institutional knowledge that **references** the external artifacts (rather than storing them) | step 7 **writes** it (as do all roles) |

Consequence: **step 6's fact-source is L3-bound** ("the forge" is the *code* binding of "the system of record"); **step 7's store is L1-universal** (the vault is the same for every team and domain).

> **The vault is a knowledge graph, owned by VAULT-ARCH — not by this doc.** Nodes = distilled knowledge summaries; edges = `[[wikilinks]]` (internal↔internal) and `resources/` summarize-and-reference links (internal→external). Built incrementally across the lifecycle: a role (e.g. PM at intake) reads an external doc → summarizes it → references the source → the node persists and any agent can reuse it later. **DM-ARCH only describes the DM's *participation*** (step 6 traverses, step 7 adds nodes/edges); it does not define the graph. The **usage-provenance** edge ("what knowledge was used in doing what") and **forward-reuse / retrieval** ("a future task reuses this node") that the DM's report depends on are vault-graph capabilities tracked in **#10690 (wiki-link rework)** and **#10838 (VAULT-ARCH alignment)** — reconcile there, not here.

### Vault: fixed contract (L1) vs role-shaped contribution (role layers)

Two different things must not be conflated:

- **The vault's *usage* is universal and non-customizable (L1-exclusive).** Every agent uses the vault as its shared memory brain, and one **universal capture rule** governs all of them: *anything newly learned that was previously unknown to the team's agents — about people, systems, external references, processes, or domain facts — is knowledge to input.* The PARAG model, entity types, `[[wikilink]]` grammar, and confidence levels are framework-owned and identical for every role, domain, and install (VAULT-ARCH §2 guardrail, 2026-05-29).
- **The *kind/specificity* of knowledge a role contributes is role-shaped** — a worker contributes technical work-notes; the DM contributes deliverable summaries + its vantage cross-connections; a verifier contributes test/verification learnings. **This flavor lives in each role's own layers (its L2/L3/L4 `instructions`/`responsibility`), not by customizing the `vault` slot.** It is normal role layering, *not* a relaxation of the L1-exclusive vault contract — the vault still receives every role's knowledge through the same grammar.

So step 7's *how* = **L1 (the contract + the capture rule)** + **the role's own form** (for the DM: "deliverable summary + cross-connection edges").

> **Tension to confirm (not assumed):** if "customize how we write to the vault" is meant to include the *note format / grammar itself* (not just the content kind), that would **relax the L1-exclusive vault contract** — a deliberate VAULT-ARCH decision, out of scope for DM-ARCH. This doc assumes the contract stays L1-exclusive and only the *content a role produces* is role-shaped.

## 4. What the DM fundamentally is

Not a "shipper." The DM is the **deliverer + the historian + an end-to-end knowledge vantage**:
- **Deliverer** (steps 3–5) — gets verified work to its destination.
- **Historian** (step 6) — generates the report from the system-of-record facts.
- **End-to-end vantage** (step 7) — the DM is *not* the only knowledge contributor (every role feeds the universal L1 vault); it is distinguished only by **vantage** — it sees completed deliverables whole, so it catches cross-connections single-stage roles miss.

**The original problem dissolves:** "bump every 10 features" is simply an **L4 record-policy** layered onto step 6 — *accumulate deliveries; every 10th, the record stamps a semver bump + tag.* The generic DM never knows about it.

## 5. Design corrections already agreed

- **"Version" is not an L2 spine step.** Many projects have no version. Versioning is an optional L4 facet of step 6 (Document), not a universal step.
- **Release state belongs to the DM, not the verifier.** Today SquidSquad's *verifier* increments the bump counter — a release concern leaking into verification. In the clean model, the **verifier verifies and knows nothing about release policy**; the DM owns all release state and reads its cadence from L4.
- **Status-bar counter is removed.** The `Shipped Since Last Bump` display is an L4 policy artifact shown universally; it comes out of the generic status bar (operator-confirmed).

## 6. Per-step layer classification (the core polish work)

The override *mechanism* is settled (§2 — existing compose op grammar). The real design work is classifying each spine step's *how* as **L2-complete** (universal, no override expected), **L3-overridable** (domain mechanics), or **L4-overridable** (project policy). First-pass classification (to be confirmed/refined in polish):

| # | Spine step | Likely layer of the *how* | Notes |
|---|---|---|---|
| 1 | Detect ready work | **L2-complete** | universal — react to the verified/cleared signal |
| 2 | Pre-flight | **L2-complete** (+ L3 checks) | coherence/completeness is universal; domain may add checks |
| 3 | Package | **L3-overridable** | *what a deliverable is* = domain mechanics |
| 4 | Publish | **L3-overridable** (+ L4 target) | mechanism class = L3; concrete target = L4 |
| 5 | Confirm landing | **L2-complete** (+ L3 probe) | "did it arrive" is universal; the probe may be domain-specific |
| 6 | Generate the delivery report | **L2 act + L3 fact-source + L3/L4 output** | L2 = "generate a report from the facts in the system of record"; the **system of record is L3-bound** (forge=code); report *content/format/audience/destination* (version, changelog, release notes) = L3/L4. |
| 7 | Contribute institutional knowledge | **L1 contract+rule + role-shaped form** | vault *usage* + the **universal capture rule** ('anything newly learned = input') = L1-exclusive, non-customizable; the *kind/specificity* of what a role contributes (DM = deliverable summary + vantage cross-connections) lives in the **role's own layers**, not the vault slot. |
| 8 | Handle failure | **L2-complete** (+ L3 rollback) | route-back is universal; rollback mechanics may be domain |

### Open questions
1. **Default L2 behavior** — confirm: *ship each verified item on ready* (no batching) when L4 specifies nothing. *(PM rec: yes.)*
2. **Extract L3 now vs later** — define the generic `skill-dev DM` L3 variant now (SquidSquad's DM becomes an instance), or keep SquidSquad's DM as L2+L4 and extract L3 when the frontend DM actually appears? *(PM rec: extract now — forces an honest L2/L3 boundary; a second variant is already foreseen.)*
3. **Step 7 knowledge scope** — narrow (only delivery/release patterns) vs broad (any cross-connection in the *content* delivered — client/job/entity relationships). The operator's "client relates to another job" example points **broad**. *(PM rec: broad — the DM is the end-to-end catch-point; but it widens the DM's knowledge lane beyond process.)*
4. **Step addressability** — each spine step must be a stably-named unit (likely an H3 sub-section in the `responsibility`/`instructions` slot) so an L3/L4 op can target it by anchor. Confirm the authoring structure (one H3 per step) and which slot(s) the spine lives in.

## 7. Next steps

- **Polish/brainstorm pass** — confirm §6's per-step layer classification; nail step addressability (§6 Q4); define what an L3 DM-variant file concretely contains (which step-units it overrides + with what op); enumerate the L4 plug-in points (cadence, scheme, targets, record format); reconcile step 7 with the institutional-memory architecture (VAULT-ARCH).
- **Then** file the refactor tasks: strip policy from L2 DM, add the L3 skill-dev variant, move SquidSquad specifics + counter to L4, remove the status-bar counter, move the bump-counter increment off the verifier onto the DM.

## Revision log

- **2026-06-17 (DRAFT kickoff)** — Created from operator+PM discussion. Captured: the layering principle (L2 parameterizes, never hardcodes), the L2 lifecycle spine (with the operator's correction that *version* is not a spine step and *document the delivery / audit trail* is the universal step), the DM-as-deliverer+historian+knowledge-harvester conception, the verifier-counter-leak correction, and three open questions for the polish pass.
- **2026-06-17 (reframe — override = existing compose)** — Operator correction: the override mechanism is NOT new — it is the existing L1–L4 compose machinery (slot + ordinal + the `replace`/`insert`/`append` op grammar, COMPOSE-ARCHITECTURE §3.2–§3.3). Reframed §2: "L2 is mostly slots" = the spine authored as addressable step-units; L3/L4 override the *how* of specific steps via the standard op grammar. The real work is per-step **classification** (§6: L2-complete / L3-overridable / L4-overridable) + step **addressability**, not designing a mechanism. Added §6 classification table + Q4 (addressability).
- **2026-06-17 (step 6 deep-dive)** — Operator refinement: step 6 L2 act = **"generate a report from the facts in the forge"**; the report's content/format/audience/destination are L3/L4 (collapses the earlier 6a/6b split into a single L2 act with L3/L4-parameterized output). **Storage-by-type** distinction added: forge = code/work audit store (step 6 reads it); vault = new-knowledge store (step 7 writes it), because the forge isn't the right home for knowledge.
- **2026-06-17 (step 7 / vault elevation)** — Operator: institutional knowledge is **universal (L1)** — every role at every stage (plan / task / verify / build / deliver), in **any domain** (a code team or an accountant team on emails+spreadsheets), contributes knowledge to the **vault**, which holds distilled knowledge and **references** external artifacts. So step 7 is NOT a DM invention — it is the DM's instance of the L1 vault-contribution, distinguished only by the DM's **end-to-end vantage**. Added the **two-stores** model (system-of-record = domain-specific/L3-bound, read by step 6; vault = universal/L1, written by step 7), which also resolves the step-6 fact-source question (fact-source is L3-bound; 'the forge' is the code binding of 'the system of record').
- **2026-06-17 (vault as knowledge graph)** — Operator: the vault is a **linked knowledge graph** — internal↔internal AND internal→external links; external docs are **summarize-and-referenced**; built across the lifecycle by all roles (PM reads/summarizes an external doc at intake → persists a reusable node → DM/any agent grabs it → future tasks reuse it). Confirmed already-documented in VAULT-ARCH (PARAG + Galaxy Zettelkasten, `[[wikilinks]]`, `resources/` = link-to-externals; vault contract is **L1-EXCLUSIVE**). Enriched DM steps: step 6 also **traverses the graph** for provenance ('what knowledge informed this delivery'); step 7 **adds nodes + `[[wikilink]]` edges**. Added a note deferring the graph model itself to VAULT-ARCH; the usage-provenance + forward-reuse dimension connects to #10690 / #10838.
- **2026-06-17 (vault usage vs role-shaped contribution)** — Operator: vault *usage* is universal/non-customizable (memory brain for all; one **capture rule**: anything newly learned — people/systems/external-refs/anything-unknown — is knowledge to input). But the *kind* of knowledge a role contributes IS role-shaped (worker = technical docs; DM = deliverable summaries). Reconciled with the L1-exclusive vault guardrail: the role-flavor lives in the **role's own layers**, NOT by customizing the `vault` slot — so no relaxation of the contract. Flagged the tension (if 'customize the write' means the note format/grammar itself, that WOULD relax the L1-exclusive contract → a VAULT-ARCH decision, out of scope here).
