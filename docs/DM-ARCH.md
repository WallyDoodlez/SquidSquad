# Delivery Manager Architecture (DRAFT — kickoff)

> **Status: DRAFT / kickoff (2026-06-17).** This document captures the initial operator+PM discussion that reframed the SquidSquad DM from a project-specific "bump version every 10 features" role into a **generic, layerable Delivery Manager**. It is intentionally incomplete — it records what we have agreed so far and frames the open questions. A subsequent **polish/brainstorm pass** will expand the L2 process, define the L3 variant model, and specify the L4 plug-in points before any refactor task is filed.

## 1. Why this doc exists

The DM role today bakes a **SquidSquad-specific policy** — "when `Shipped Since Last Bump` reaches 10, cut a semver bump" — into the **universal (L2) DM role**. That policy therefore wrongly applies to every project that installs SquidSquad. The role of a delivery manager is, in reality, **highly project-subjective**: what "delivery" means, when a release is cut, whether there is even a *version* at all — all vary by project and domain.

This doc defines the DM as a layered role so the generic essence lives at L2, domain mechanics at L3, and project policy at L4.

## 2. The layering principle (load-bearing)

**L2 defines delivery as a lifecycle with policy *hooks*; it never *hardcodes* a policy.** The things that vary by project (release cadence, version scheme, what "publish" physically means, changelog format) are **extension points** that L3 and L4 fill. L2 ships a sane **default** so a generic DM is useful out of the box.

| Layer | The DM owns | SquidSquad example |
|---|---|---|
| **L1** universal agent | base agent behavior (all roles) | — |
| **L2** DM role (any project) | the delivery **lifecycle** + the policy hooks; default = *ship each verified item as it's ready* | — |
| **L3** domain variant | what *package* & *publish* physically **mean** for a product type | **skill-dev DM**: deliver by merge-to-main + `compose` |
| **L4** this install | the *cadence*, *version scheme*, concrete *targets*, record format | "batch 10 → semver bump + tag", `CHANGELOG.md`, the counter |

**L3-vs-L4 crux:** L3 = the *mechanism class* ("deploy to a host"); L4 = the *concrete target* ("**this** Vercel project, **this** branch"). Keep them separate or the L3 variants won't be reusable across installs.

## 3. The generic DM lifecycle (L2 spine)

Any delivery manager, any project, runs this lifecycle. Steps 3–4 are the *act* of delivery; steps 6–7 are its *meaning*.

1. **Detect ready work** — something is verified and cleared for delivery.
2. **Pre-flight** — the deliverable is coherent and complete (nothing half-merged, deps satisfied).
3. **Package** — assemble the actual deliverable (the thing that goes out). *(form = L3)*
4. **Publish** — execute the delivery. *(mechanics = L3)*
5. **Confirm landing** — it reached its destination intact.
6. **Document the delivery** — the **operator-facing audit trail**: what was delivered, what was done, what was investigated, what changed, and why. **This — not versioning — is the universal record step.** Versioning, changelog format, and release tags are *optional facets* applied here per L4 policy; a version-less project (a one-off deliverable, a doc, a client job) still produces this record.
7. **Contribute institutional knowledge** — having seen the finished deliverable end-to-end, the DM harvests durable learnings and **cross-connections** (e.g. "this client/job relates to that other one," recurring patterns) into the institutional memory (vault).
8. **Handle failure** *(cross-cutting)* — on a failed delivery, roll back and/or route the work back to its owner.

**Default (no L4 policy):** ship each verified item as it's ready — no batching, no version concept.

## 4. What the DM fundamentally is

Not a "shipper." The DM is the **deliverer + the historian + the knowledge-harvester**:
- **Deliverer** (steps 3–5) — gets verified work to its destination.
- **Historian** (step 6) — produces the definitive operator-facing record / audit trail of what happened.
- **Knowledge-harvester** (step 7) — the natural catch-point for content-level cross-connections, because it sees completed deliverables whole.

**The original problem dissolves:** "bump every 10 features" is simply an **L4 record-policy** layered onto step 6 — *accumulate deliveries; every 10th, the record stamps a semver bump + tag.* The generic DM never knows about it.

## 5. Design corrections already agreed

- **"Version" is not an L2 spine step.** Many projects have no version. Versioning is an optional L4 facet of step 6 (Document), not a universal step.
- **Release state belongs to the DM, not the verifier.** Today SquidSquad's *verifier* increments the bump counter — a release concern leaking into verification. In the clean model, the **verifier verifies and knows nothing about release policy**; the DM owns all release state and reads its cadence from L4.
- **Status-bar counter is removed.** The `Shipped Since Last Bump` display is an L4 policy artifact shown universally; it comes out of the generic status bar (operator-confirmed).

## 6. Open questions (for the polish pass)

1. **Default L2 behavior** — confirm: *ship each verified item on ready* (no batching) when L4 specifies nothing. *(PM rec: yes.)*
2. **Extract L3 now vs later** — define the generic `skill-dev DM` L3 variant now (SquidSquad's DM becomes an instance), or keep SquidSquad's DM as L2+L4 and extract L3 when the frontend DM actually appears? *(PM rec: extract now — forces an honest L2/L3 boundary; a second variant is already foreseen.)*
3. **Step 7 knowledge scope** — narrow (only delivery/release patterns) vs broad (any cross-connection in the *content* delivered — client/job/entity relationships). The operator's "client relates to another job" example points **broad**. *(PM rec: broad — the DM is the end-to-end catch-point; but it widens the DM's knowledge lane beyond process.)*

## 7. Next steps

- **Polish/brainstorm pass** — expand §3 into a precise per-step contract; define the L3 variant model (what an L3 DM variant file specifies); enumerate the L4 plug-in points (cadence, scheme, targets, record format) and how L2 reads them; reconcile with the existing vault/institutional-memory architecture (VAULT-ARCH) for step 7.
- **Then** file the refactor tasks: strip policy from L2 DM, add the L3 skill-dev variant, move SquidSquad specifics + counter to L4, remove the status-bar counter, move the bump-counter increment off the verifier onto the DM.

## Revision log

- **2026-06-17 (DRAFT kickoff)** — Created from operator+PM discussion. Captured: the layering principle (L2 parameterizes, never hardcodes), the L2 lifecycle spine (with the operator's correction that *version* is not a spine step and *document the delivery / audit trail* is the universal step), the DM-as-deliverer+historian+knowledge-harvester conception, the verifier-counter-leak correction, and three open questions for the polish pass.
