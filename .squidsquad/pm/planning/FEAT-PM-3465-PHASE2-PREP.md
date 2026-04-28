# FEAT-PM-3465 Discussion Prep

## Question Order (recommended)

Tackle in this order — earlier answers constrain later ones:

1. **Q2** — SOUL.md runtime model (architectural foundation; answer determines what "layering" even means at runtime)
2. **Q1** — Layer 2 concrete content (validates the feature has real value; if answer is "nothing new", scope collapses)
3. **Q3** — PM's general role (hardest edge case; must be resolved before dev can scope Layer 2 authoring)
4. **Q5** — Dev variant inheritance (mechanical, but must be resolved before dev touches `_load_manifest()`)
5. **Q4** — Comms-layer interaction with #3415 (coordination question; affects Layer 2 directory design but not the core architecture)

---

## Q2: How does SOUL.md layering work at runtime — single assembled flat file or multi-file read?

### Why This Matters
If agents read 3 separate SOUL.md files at boot, the `{{runtime:}}` directive must change, boot-sequence instructions must change, and `soul_adaptation.py`'s `render_soul()` marker-replacement logic breaks. Getting this wrong means either (a) broken agent identity at boot or (b) wasted compose complexity building a mechanism that already exists.

### Option A: Deploy-time flat assembly (recommended)
- **Description**: `compose.py deploy_role()` concatenates Layer 1 + Layer 2 + Layer 3 SOUL.md sources into a single flat `.squidsquad/<role>/SOUL.md` at deploy time. The assembled file is structurally identical to the current single-file SOUL.md. `{{runtime: souls/<role>}}` directive is unchanged. `soul_adaptation.py` is unchanged — it still finds `## Project Adaptation` and `<!-- /project-adaptation -->` in the flat file.
- **Pros**:
  - Zero changes to agent boot sequence or `{{runtime:}}` directive
  - `soul_adaptation.py` requires no modification (Risk 1 from research fully mitigated)
  - Atomic write at deploy time prevents mid-cycle SOUL.md inconsistency (Risk 4 mitigated)
  - Consistent with [[learning-atomic-migration-strategy]] — one assembled artifact, no new runtime mechanism
  - `health_check.py` and `diagnostics.py` require no changes (they check for presence of `.squidsquad/<role>/SOUL.md`, which still exists)
- **Cons**:
  - Upgrade must re-render Layer 1+2 sections without clobbering Layer 3 — requires a new `upgrade_soul(role)` function in compose.py
  - The assembled SOUL.md hides the layer boundaries — a developer reading the file cannot tell where Layer 1 ends and Layer 2 begins without checking source templates

### Option B: Runtime multi-file read
- **Description**: The agent's boot instructions are updated to read `souls/base.md`, `souls/general/<category>.md`, and `souls/<role>.md` in sequence. `{{runtime:}}` gains multi-target syntax. Each file is read separately at boot.
- **Pros**:
  - Layer boundaries are explicit at runtime — the agent can introspect which layer an instruction came from
  - No deploy-time assembly step needed
- **Cons**:
  - `{{runtime:}}` directive must be extended — compose.py code change required
  - `soul_adaptation.py` breaks immediately — it reads one flat file, not three (Risk 1: Severity H)
  - Boot sequence grows more complex — 3 reads instead of 1
  - Token budget inflation is uncontrolled — Layer 1 and Layer 2 are both injected verbatim at every boot
  - Breaks [[pattern-deterministic-scripts-over-prose]] — runtime behavior becomes harder to audit

### Option C: Structured sections in a single SOUL.md template (no assembly)
- **Description**: Each role's SOUL.md template gains clearly delimited sections (`## Layer 1 — Base Agent`, `## Layer 2 — General Role`, `## Layer 3 — Specific Role`). Content is copy-pasted into each template manually. No new compose mechanism.
- **Pros**:
  - Zero changes to compose.py, soul_adaptation.py, or the `{{runtime:}}` directive
  - No migration complexity — SOUL.md templates are just more structured
- **Cons**:
  - Layer 1 and Layer 2 content is duplicated across all 5 role templates — future updates to shared identity require editing every template (the exact problem this feature is trying to solve)
  - Defeats the purpose of the layered architecture — "layers" are editorial convention, not structural
  - Does not support the general-purpose vision: a new "marketing-analyst" role must manually copy Layer 1 content, with no enforcement

### PM Recommendation
**Option A.** Deploy-time flat assembly is the only approach that keeps `soul_adaptation.py` unchanged (Severity H risk), preserves the `{{runtime:}}` directive contract, and is consistent with how the existing 5-layer CLAUDE.md composition works (includes.yml ordering + build-time concatenation). The `upgrade_soul()` function is a real engineering cost, but it is bounded and mechanical — a standard "merge Layer 1+2 updates, preserve Layer 3 and Project Adaptation" function. Option B introduces too many high-severity breaks. Option C delivers no structural value.

---

## Q1: What content actually belongs in Layer 2 (general role) vs. is already adequately covered by `common/` sub-skills?

### Why This Matters
If Layer 2's CLAUDE.md would contain only content already present in `common/tracker-protocol`, `common/cycle-runner`, etc., the feature adds zero operational value — it is a structural concept with no concrete content. The value proposition must be demonstrated with content that is not already shared. If this question cannot be answered with at least 3 concrete content examples per general role category, the feature should be deferred.

### Option A: Layer 2 owns role-family identity and coordinator vs. executor distinction (recommended)
- **Description**: Layer 2 general roles are defined around the "what kind of agent am I?" axis that currently has no home. Concrete Layer 2 content examples:
  - **developer** (`dev`, `skill`, `be`, `fe`): code-change protocol, branch workflow behavior, PR authoring conventions, "never touch files outside your domain" prohibition — things shared by all code-writing agents but not by verifiers or coordinators
  - **verifier** (`qa`): verification quality bar, zero-gap gate philosophy, test coverage requirements, "never ship with gaps" — things shared by all verification-type agents; currently embedded in QA's specific role but generalizable
  - **coordinator** (`pm`): pipeline oversight mandate, "investigate anomalies not just your queue" philosophy, human check-in cadence — currently embedded in PM-specific template but would generalize if a "scrum master" or "tech lead" general role were added
  - **delivery** (`dm`): version bump protocol, CHANGELOG management, "atomicity before convenience" — generalizes if a "release engineer" general role existed
  - **creative-specialist** (`designer`): capability-check behavior, HITL loop protocol, design brief format — generalizes if a "UX researcher" or "content designer" were added
- **Pros**:
  - Each general role category has genuine new content that is not in `common/` today
  - Makes the dev variant inheritance (Q5) natural: `skill` is a developer-type agent, gets Layer 2 developer content without duplication
  - Supports the general-purpose vision: a "marketing-analyst" would inherit the "analyst" Layer 2 without anyone copying boilerplate
  - Justifies the feature's scope and complexity
- **Cons**:
  - Requires PM and the human to audit all 5 current role CLAUDE.md templates to identify what moves to Layer 2 vs. stays in Layer 3 — this is editorial work that must happen before dev can start
  - Some Layer 2 content (e.g., verifier quality bar) is subtle to separate from Layer 3 role-specific content

### Option B: Layer 2 owns only shared configuration mechanics (no identity content)
- **Description**: Layer 2 is limited to structural/mechanical shared content: timestamp protocol, atomic-write requirement, `{{runtime:}}` SOUL reference instruction, sub-agent model preference, and status bar format. Identity content stays in Layer 3.
- **Pros**:
  - Easy to scope — the list is finite and already partially in `references/roles/base/` conceptually
  - No risk of incorrect content attribution between layers
- **Cons**:
  - This is exactly what `common/` sub-skills already do — Layer 2 would be an empty category with no new value
  - Does not address the general-purpose vision (a new non-dev role still needs to copy identity boilerplate)
  - The "general role" concept becomes a fiction — there is no meaningful "developer" vs. "verifier" distinction at Layer 2, just configuration snippets

### Option C: Layer 2 owns comms and collaboration protocols only
- **Description**: Layer 2 is the home for collaboration-layer content: `common/chat-etiquette`, `common/mention-protocol`, `common/consensus-protocol` — things that are role-family-specific but not universal. General roles become "collaborative-agent" subtypes.
- **Pros**:
  - Removes comms content from `common/` (where it does not belong universally — not every installation uses Telegram)
  - Clean boundary: Layer 1 = universal mechanics, Layer 2 = collaboration layer, Layer 3 = specific behavior
- **Cons**:
  - Interacts with #3415 feature-flag gating — moving comms sub-skills to Layer 2 could break the opt-in mechanism that controls their inclusion (see Q4)
  - Does not address the identity/coordinator/executor distinction — the "why does Layer 2 exist?" question still goes unanswered
  - Requires resolving Q4 first, creating a dependency that delays this feature

### PM Recommendation
**Option A.** Role-family identity is the only content bucket that (a) is genuinely not in `common/` today, (b) has concrete examples for all 5 current roles, and (c) extends naturally to the general-purpose vision. The editorial audit of role templates is the right pre-work — it must be done before dev can scope this task. The PM should request that the dev agent produce a Layer 2 content inventory as Phase 1 of implementation, before touching any code.

---

## Q3: What is the Layer 2 general role for PM?

### Why This Matters
PM combines coordinator + verifier duties (verifier fallback when QA is absent). If "verifier" is Layer 2, PM and QA would share a Layer 2 — but PM's verification is conditional (only when QA is absent), which cannot be expressed in a static Layer 2. If this is unresolved, dev cannot scope what goes in PM's Layer 3 vs. Layer 2, and the feature's most important role gets zero benefit.

### Option A: PM's Layer 2 is "coordinator"; verifier fallback stays in Layer 3 PM-specific (recommended)
- **Description**: Layer 2 "coordinator" SOUL.md and CLAUDE.md contain: pipeline oversight mandate, human check-in cadence, "investigate anomalies not just your queue" philosophy, task intake authority, approval gate ownership. PM's Layer 3 retains: QA fallback verification behavior (conditional — only when `.squidsquad/qa/` absent), PM-specific check-in style, the full Ralph Loop structure. QA's Layer 2 is "verifier" (pure, unconditional): zero-gap gate, test coverage requirement, verification quality bar.
- **Pros**:
  - Clean separation: coordinator identity is always active, verifier identity is a conditional Layer 3 exception
  - QA gets a pure "verifier" Layer 2 with no PM contamination
  - The conditionality ("if QA absent") stays in `pm-specific/testing-and-verification.md` where it already lives — no change to SOUL.md layering for this edge case
  - Avoids the impossible problem of conditional SOUL.md content at Layer 2
- **Cons**:
  - PM's Layer 2 does not capture the full truth of PM's identity (PM IS also a verifier, sometimes)
  - A future "tech lead" or "scrum master" general role would inherit "coordinator" Layer 2 — but if they also need verifier fallback, they would face the same problem

### Option B: PM's Layer 2 is "coordinator+verifier" (dual role)
- **Description**: Layer 2 for PM is a combined "coordinator+verifier" general role that includes both identities. QA's Layer 2 is a separate pure "verifier". The two Layer 2 categories overlap in verifier content.
- **Pros**:
  - Captures PM's actual identity at Layer 2 — no "missing piece" in Layer 3
- **Cons**:
  - Content duplication: coordinator+verifier Layer 2 and verifier Layer 2 share verification quality bar content; updates must be made in two places
  - Breaks the "each general role has one home" principle — verification quality bar is either at Layer 2 verifier or Layer 2 coordinator+verifier, not both
  - Makes Layer 2 harder to reason about for future role authors

### Option C: PM has no Layer 2 (singleton exception)
- **Description**: PM's `manifest.yaml` has `general_role: none`. PM composes as Layer 1 → (no Layer 2) → Layer 3. The general-purpose vision applies to developer/verifier/designer families; PM is treated as a singleton like DM.
- **Pros**:
  - Avoids the conditionality problem entirely
  - Simpler compose.py logic: `general_role: none` means skip Layer 2 includes
  - DM already has this problem (Q5 edge case in research: "DM has no general role analog")
- **Cons**:
  - PM and DM both get zero benefit from Layer 2 — the feature only benefits dev/qa/designer roles
  - If a future "tech lead" coordinator role is added, it has no Layer 2 ancestor to inherit from
  - Weakens the value proposition of the feature

### PM Recommendation
**Option A.** The key insight from the research is that PM's verifier behavior lives in `pm-specific/testing-and-verification.md` (a CLAUDE.md sub-skill), not in SOUL.md. The conditional "if QA absent" check is runtime logic in a sub-skill — it has nothing to do with Layer 2 SOUL identity. PM's SOUL identity is coordinator first. The verifier fallback is a capability PM happens to have, not a core identity. Keeping "coordinator" as Layer 2 is architecturally correct and avoids the impossible conditional-SOUL problem.

---

## Q5: How does the "skill" dev variant (no own role directory) map to Layer 2?

### Why This Matters
`skill`, `be`, and `fe` agents have no `references/roles/skill/` directory — they inherit from `dev/includes.yml` via `_load_manifest()` fallback logic. If Layer 2 is introduced and `_load_manifest()` is not updated to resolve the "developer" general role for these variants, variant agents silently compose with no Layer 2 content. The research identifies this as a Severity M risk (Risk 2).

### Option A: Layer 2 is derived from the parent role's manifest, not the variant (recommended)
- **Description**: `_load_manifest()` already falls back from `skill` → `dev` when no `references/roles/skill/` exists. The `dev/manifest.yaml` declares `general_role: developer`. When composing a `skill` agent, `_load_manifest()` reads `dev/manifest.yaml` (via the existing fallback) and gets `general_role: developer` from there. No new logic needed for variants — they inherit Layer 2 from their parent role manifest.
- **Pros**:
  - Zero new logic in `_load_manifest()` for variants — the existing fallback chain already handles it
  - `skill`, `be`, `fe` all get Layer 2 "developer" content automatically via the `dev` parent
  - Consistent with the existing inheritance design
- **Cons**:
  - If a variant needs a *different* Layer 2 than its parent (e.g., a specialized `be` that is more "architect" than "developer"), there is no mechanism to override
  - Must be explicitly tested — the research calls out this exact case as needing a dedicated test

### Option B: Each variant gets its own `manifest.yaml` with explicit `general_role` field
- **Description**: Create `references/roles/skill/manifest.yaml` (and `be/`, `fe/`) with a minimal manifest declaring `general_role: developer`. The variants stop relying on the fallback for general role resolution.
- **Pros**:
  - Explicit over implicit — each role's general role is declared in its own manifest
  - Allows future variants to declare a different general role if needed
- **Cons**:
  - Creates new files for roles that currently have none — adds maintenance surface
  - If `dev/includes.yml` changes, variant manifests must also be updated or diverge silently
  - Contradicts the current "variants inherit from parent via fallback" philosophy

### Option C: Add a `variant_of` field to the base manifest and resolve Layer 2 transitively
- **Description**: `dev/manifest.yaml` gains `variants: [skill, be, fe]`. `_load_manifest()` is updated to walk the `variant_of` → `general_role` chain for these roles. General role is resolved transitively.
- **Pros**:
  - Explicit declaration of the variant relationship in the parent manifest
  - `_load_manifest()` gains a canonical resolution algorithm for variants
- **Cons**:
  - New manifest schema field (`variants`) — requires backward-compat handling in all manifest-reading code (compose.py, wizard.py, add_role.py, capability_check.py)
  - More complex than Option A for the same outcome
  - Manifest schema v3 bump for a field that only helps with Layer 2 resolution

### PM Recommendation
**Option A.** The existing `_load_manifest()` fallback chain (`skill` → `dev`) already does the right thing — it reads `dev/manifest.yaml` when no `skill/manifest.yaml` exists. Adding `general_role: developer` to `dev/manifest.yaml` automatically propagates to all dev variants with zero new code. The risk is implicit rather than explicit, but the research's mitigation ("update `_load_manifest()` and `_get_entry_file_for_role()` as part of the same PR") is met by Option A — the update is to add `general_role` to `dev/manifest.yaml`, not to change resolution logic. Must include an explicit integration test for the `skill` variant's Layer 2 content as part of the test plan.

---

## Q4: Does this interact with the #3415 comms layer (Telegram adapter sub-skills)?

### Why This Matters
`common/chat-etiquette`, `common/mention-protocol`, and `common/consensus-protocol` are currently in `common/` with optional inclusion controlled by feature-flag gating. If Layer 2 is introduced and these sub-skills are moved to Layer 2, the feature-flag mechanism that controls their opt-in inclusion must be preserved. Misplacing them into Layer 2 as unconditional includes would break projects that do not use Telegram.

### Option A: Comms sub-skills stay in `common/` — Layer 2 does not touch them (recommended)
- **Description**: Layer 2 general roles include only identity content (per Q1 Option A recommendation). Comms sub-skills remain in `common/` with their existing optional inclusion mechanism. Layer 2 and #3415 are independent. Comms inclusion is still controlled by the feature flag in `includes.yml` — Layer 2 includes come before comms includes in the ordering, so there is no conflict.
- **Pros**:
  - Zero risk to #3415 feature-flag gating — comms sub-skills are untouched
  - Layer 2 and #3415 can ship independently without coordination
  - Simpler: one concern per change
- **Cons**:
  - Comms sub-skills remain in `common/` even though they are arguably role-family-specific (a coordinator-type agent handles consensus differently than a developer-type agent) — this is a real architectural impurity that is left unresolved
  - Future migration of comms to Layer 2 would require revisiting this decision

### Option B: Comms sub-skills move to Layer 2 as part of this feature, gating preserved
- **Description**: `common/chat-etiquette` and related sub-skills move to `references/roles/general/<category>/`. The feature-flag mechanism is replicated at Layer 2 — `includes.yml` for each general role category has a conditional include block for comms sub-skills.
- **Pros**:
  - Resolves the architectural impurity in `common/` — comms sub-skills find their correct home
  - Coordinator-type and developer-type agents can have different comms behaviors at Layer 2
- **Cons**:
  - Adds #3415 dependency to this feature — both must coordinate, increasing blast radius
  - Replicating the feature-flag mechanism across Layer 2 category includes.yml files adds complexity
  - If #3415 is deferred or changes direction, this feature must be revisited
  - Comms sub-skills currently in `common/` are used by specific roles today — moving them requires updating all existing `includes.yml` files that reference them

### Option C: Comms sub-skills move to Layer 2, gating removed (always-on for relevant roles)
- **Description**: Comms sub-skills are unconditionally included in Layer 2 general roles that use them (e.g., "coordinator" always gets `chat-etiquette`). Feature-flag opt-in is abandoned for comms.
- **Pros**:
  - Simplest Layer 2 authoring — no conditional include complexity
- **Cons**:
  - Breaks the opt-in contract for projects that do not use Telegram — all coordinator-type agents would load comms instructions even if irrelevant
  - Token budget inflation for all coordinator-type agents on non-Telegram projects
  - Violates [[pattern-deterministic-scripts-over-prose]] spirit — behavior changes based on project type, but the include is now static

### PM Recommendation
**Option A.** The architectural impurity of comms sub-skills in `common/` is a real problem, but it is #3415's problem to solve, not this feature's. The correct sequencing is: (1) ship this feature with comms sub-skills untouched in `common/`; (2) after #3415 ships and the comms layer is stabilized, evaluate whether comms belongs in Layer 2 as a follow-up. Combining the two changes increases blast radius and creates a dependency that could delay both. Keep them independent.

---

*Generated for FEAT-PM-3465 discussion. Delete after CONTEXT.md is finalized.*
