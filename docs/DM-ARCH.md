# Delivery Manager Architecture

The Delivery Manager (DM) is a **layered role**: a generic delivery essence at **L2**, domain-specific mechanics at **L3**, and project-specific policy at **L4**. Delivery is highly project-subjective — what "delivery" means, when a release is cut, and whether there is even a *version* at all vary by domain and project — so the universal layer must not bake in any one project's policy. (Concretely: SquidSquad's "every 10 shipped features → cut a semver bump" is **L4 project policy**, not part of the universal DM; the generic DM never knows about it.)

## 1. The layering principle

The override mechanism is the **existing L1–L4 compose machinery** — no DM-specific mechanism is introduced. Per [COMPOSE-ARCHITECTURE.md §3.2–§3.3](COMPOSE-ARCHITECTURE.md): each source fragment declares a `slot` + `ordinal`; `compose.py` gathers all L1–L4 fragments for a role, groups by slot, sorts by ordinal, and applies the layer op grammar (`replace` / `insert-before` / `insert-after` / `append`) — L2–L3 inline ops first, then L4 file ops — higher layers winning on conflict.

**L2 is mostly *slots*.** L2 authors the **spine** (§2) as addressable step-units — each step a stably-named anchor an L3 or L4 op can target. L2 supplies the universal *what* of each step plus a sane *default how*; **L3 and L4 override the *how* of specific steps** via the standard op grammar.

| Layer | Source location | What it contributes to the DM | SquidSquad instance |
|---|---|---|---|
| **L1** universal agent | `references/sub-skills/common/` + L1 portions of `references/roles/` | base agent behavior (all roles) | — |
| **L2** DM role | `references/roles/dm/` | the **spine as addressable step-units** + a default *how*; default delivery = *ship each verified item as it's ready* | — |
| **L3** domain variant | `references/roles/dm/<domain>/` | overrides the *how* of domain-variable steps (package / publish mechanics) | `roles/dm/skill/`: package+publish = merge-to-main + `compose` |
| **L4** this install | `.squidsquad/project/dm.md` | overrides the *how* of project-variable steps (cadence, version scheme, targets, record format) | batch-10 → semver bump + tag, `CHANGELOG.md`, the counter |

**L3 vs L4:** L3 = the *mechanism class* ("deploy to a host"); L4 = the *concrete target* ("**this** Vercel project, **this** branch"). Keep them separate or the L3 variants won't be reusable across installs.

The L3 DM variant infrastructure already exists in the tree — `dm/skill/`, `dm/web/`, `dm/android/`, `dm/ios/`, `dm/fullstack/` — so domain specialization is a content concern within an existing variant, not new machinery.

## 2. The DM lifecycle (L2 spine)

Steps 3–4 produce and confirm the deliverable; 5–6 are its *meaning* (record + knowledge); 7 announces it. **Publish is the last step** — you advertise only once it is deployed, confirmed, recorded, and its learnings captured.

1. **Detect ready work** — something is verified and cleared for delivery.
2. **Pre-flight** — the deliverable is coherent and complete (nothing half-merged, deps satisfied).
3. **Package** — produce a **complete, well-rounded product** at its destination, *not just the raw technical artifact*. The technical workers produce the technical work; the DM **completes the product** by adding what they don't: **product documentation** (user guide / README / API reference / manuals for software or hardware), polish, and completeness, so a *consumer* receives a finished product. *(mechanic + what-completes-it = L3.)* The **product docs** here are *part of the deliverable*; distinct from the **delivery report** (step 5), which is a record *about* the delivery.
4. **Confirm landing** — the deliverable reached its destination intact / is available. *(probe = L2, may be L3-specific.)*
5. **Generate the delivery report** — synthesize the **facts in the system of record** (for code: forge issue discussion, PR, commits, verification) **and traverse the vault knowledge graph** for provenance (*what knowledge informed the delivery*). The L2 act is "generate a report from the recorded facts + the knowledge graph"; **what** the report contains, its format, audience, and destination are L3/L4 (internal audit trail, external release notes, or both). Versioning, changelog format, and release tags are **L4 facets**; a version-less project still produces a report.
6. **Contribute institutional knowledge** — the DM contributes knowledge gained to the **vault** (§ The vault model). It contributes at **two granularities**: like every role it records the **part-level detail** of its own slice (delivery-process learnings, so it improves over time); and — *its signature contribution* — the **broad, task/job-level** knowledge (the whole wrapped-up job as a unit, tied to its issue, including cross-connections to other jobs) that only its end-to-end **vantage** can see. The DM owns both writes. Capture fires at **task completion** (end-of-task = end-of-cycle).
7. **Publish — the last step** — **make the delivery *known*** to its audience: announce/advertise that it is available. (Package made it *exist*; Publish makes it *known*.) *(mechanic + audience = L3/L4.)*
8. **Handle failure** *(cross-cutting)* — on a failed delivery at any step, roll back and/or route the work back to its owner.

**Default (no L4 policy):** ship each verified item as it's ready — no batching, no version concept.

Two architectural boundaries this establishes:
- **"Version" is not a spine step.** Many projects have no version; versioning is an optional **L4 facet of step 5**, not a universal step.
- **Release state belongs to the DM, not the verifier.** The verifier verifies and knows nothing about release policy; the DM owns all release state and reads its cadence from L4.

### Package & Publish across professions (L3 mechanics)

The L2 essence is **Package = make it *exist/available*; Publish = make it *known*.** The mechanics are the L3 binding:

| Profession | **Package** = make available (complete product) | **Publish** = make known |
|---|---|---|
| **Software** | build + deploy to prod (+ user docs / README) | release announcement / version tag / notify users |
| **Frontend/web** | build bundle + deploy to host/CDN (+ docs) | announce release, share prod URL, marketing |
| **Library (npm/pypi)** | build the distributable (+ API docs) | `npm publish` to registry + release notes |
| **Mobile** | build + sign the binary (+ store assets) | submit to store + store listing |
| **Law firm** | assemble + file the document/filing (+ exhibits, cover) | notify the client/court it's filed & ready |
| **Accounting** | finalize the return/report (+ summary memo) | submit to the authority + notify client |
| **Content/marketing** | finalize the asset | post it live + promote/advertise |
| **Design** | export final assets (+ usage guide) | deliver to client + portfolio/announce |

For **library** and **content**, "package"/"publish" are literally the domain verbs. SquidSquad's DM (L3 `dm/skill/`): Package = merge-to-main + `compose`; Publish = ship-comment + CHANGELOG. The "(+ docs)" in each Package cell is the DM completing the product — what the technical workers don't finish.

### Two stores (steps 5 & 6 substrates)

The DM's two "meaning" steps read/write two distinct stores with different universality:

| Store | Universality | Holds | DM step |
|---|---|---|---|
| **System of record** | **domain-specific** (forge/GitHub for code; an email+spreadsheet store, CRM, etc. for a non-code team) | raw work artifacts + the code/work audit trail | step 5 **reads** it → generates the report |
| **Vault** | **universal (L1)**, domain-agnostic | distilled institutional knowledge that **references** the external artifacts (rather than storing them) | step 6 **writes** it (all roles do; step 5 also reads it for provenance) |

So step 5's fact-source is **L3-bound** ("the forge" is the code binding of "the system of record"); step 6's store is **L1-universal** (the vault is the same for every team and domain).

### The vault model

The vault is the team's **universal, L1-exclusive** institutional memory — a **knowledge graph** (PARAG + Galaxy Zettelkasten; `[[wikilinks]]` are the edges; `resources/` summarize-and-reference external artifacts), domain-agnostic and contributed to by every role at every stage. The graph model itself is owned by [VAULT-ARCH](VAULT-ARCH.md); this doc describes only the DM's *participation* (step 5 traverses it; step 6 adds nodes and edges).

What is fixed vs. what composes:

- **Machine-fixed (the only truly fixed part):** the machine-readable **skeleton** — `[[wikilink]]` edge syntax (parsed by `vault_check.py` to build edges + maintain `links:`), the frontmatter schema, and PARAG placement. Fixed *because the tooling parses it to build the graph*, not because grammar is sacred.
- **Layered & composed — all content policy:** both **content governance** (*what may/may-not enter the vault*) and **content form** (*the kind/specificity a role produces*) are authored across L1–L4 and merged by `compose` into a per-agent verdict, exactly like every other slot. L1 sets the **default capture disposition** — *anything newly learned that was previously unknown (about people, systems, external references, processes, or domain facts) is input* — and L2/L3/L4 add exclusions/inclusions and role-shaped form (e.g. an L4 law-firm install: "exclude privileged/PII"; a worker's technical-note form). The note **body/prose** is free and role-shaped.

The **one default exclusion is *operator preferences*** — the operator's own behavioral preferences/directives, which have their own homes (**soul-shepherd** for observed signals, **L4** for explicit directives) — **not** people. Knowledge *about people* (clients, contacts, entities) is captured.

> The existing VAULT-ARCH guardrail ("the vault slot + contract spec are L1-exclusive") is sound for the slot/spec, but only the machine skeleton is genuinely format-load-bearing; content policy lives in other slots and composes normally. The precise scope-clarification is owned by **VAULT-ARCH (#10838)**.

## 3. What the DM fundamentally is

Not a "shipper." The DM is the **deliverer + the historian + an end-to-end knowledge vantage**:
- **Deliverer** (steps 3–4, 7) — gets verified work to its destination and makes it known.
- **Historian** (step 5) — generates the delivery report from the system-of-record facts + the knowledge graph.
- **End-to-end vantage** (step 6) — not the only knowledge contributor (every role feeds the universal vault), but the one role that sees completed deliverables *whole*, so it catches cross-connections single-stage roles miss.

## 4. Per-step layer classification

| # | Spine step | Layer of the *how* | Notes |
|---|---|---|---|
| 1 | Detect ready work | **L2-complete** | universal — react to the verified/cleared signal |
| 2 | Pre-flight | **L2-complete** (+ L3 checks) | coherence/completeness is universal; a domain may add checks |
| 3 | Package | **L3-overridable** | complete product = technical artifact + product docs + polish; mechanic + what-completes-it = L3 |
| 4 | Confirm landing | **L2-complete** (+ L3 probe) | "did it arrive / is it available" is universal; the probe may be domain-specific |
| 5 | Generate the delivery report | **L2 act + L3 fact-source + L3/L4 output** | L2 = "generate a report from the system-of-record facts"; the source is L3-bound (forge = code); content/format/audience/destination (version, changelog, release notes) = L3/L4 |
| 6 | Contribute institutional knowledge | **machine-fixed skeleton + composed content policy** | only the machine skeleton is L1-fixed; all content policy (governance + form) composes L1→L4 into a per-agent verdict |
| 7 | Publish *(last)* | **L3-overridable** (+ L4 audience) | make-known — announce/advertise availability; mechanism + audience = L3/L4 |
| 8 | Handle failure | **L2-complete** (+ L3 rollback) | route-back is universal; rollback mechanics may be domain |

**Authoring convention:** the spine lives in the `instructions` slot, one **H3 `### step:cycle/<id>` anchor per step** (e.g. `### step:cycle/package`), so L3/L4 ops can target a step by anchor; the `responsibility` slot carries the higher-level role summary. (This requires promoting the steps from the existing H4 to H3 — see COMPOSE-ARCHITECTURE §3.3 and #11227.)

## 5. Implementation

The L1–L4 refactor that realizes this architecture (strip the project policy from L2, move package/publish mechanics into the existing `dm/skill/` L3 variant, place the SquidSquad release policy in the `dm.md` L4 file, remove the status-bar counter, move the release-counter increment off the verifier onto the DM, and the descriptive-doc syncs) is tracked as a single coordinated delivery in **#12749** — doc and code land together in one PR.
