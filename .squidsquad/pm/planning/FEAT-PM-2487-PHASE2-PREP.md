# FEAT-PM-2487 Discussion Prep — Wire Cycle Runner Into Templates

## Recommended Question Order

1. **Q1: `[ROLE]` placeholder resolution** — This is the biggest integration risk and likely the reason cycle runner was never composed. Every other decision depends on knowing how commands/paths will be rendered per role.
2. **Q2: Replace vs coexist with existing sub-skills** — Once we know how placeholders work, we need to decide what the cycle runner actually *displaces* in the template. This shapes the template edits.
3. **Q4: Role-specific "always-run" steps under cycle runner** — Closely related to Q2 but narrower: even if we replace mechanical steps, some role-specific steps (pipeline sentinel) must survive. Decide this before schema work.
4. **Q3: Schema strictness in `cycle_post.py`** — With the replacement scope and always-run steps locked, we can decide how much the post-cycle script should validate per role.
5. **Q5: Rollout plan** — All design decisions feed into the rollout strategy. Discuss last so the plan accounts for all choices above.

## Q1: How should `[ROLE]` be resolved in PM/DM/designer templates for cycle runner commands/paths?
> Why this matters: If unresolved, PM/DM/designer agents will literally see `cycle_pre.py [ROLE]` and `.squidsquad/[ROLE]/cycle-input.json` in their instructions, which is unusable and will break adoption. The manifest explicitly warns `[ROLE]` is not substituted for PM/DM. This is likely why cycle runner was never composed.

### Option A: Composition-time substitution in `compose.py` (RECOMMENDED)
- Pros: Single `cycle-runner.md` source file; no per-role variants to maintain; composition is already the mechanism for building role templates; keeps the sub-skill generic and reusable
- Cons: Requires adding a substitution pass to `compose.py` (new behavior); must define which placeholders get substituted and which are literal; could introduce subtle bugs if other `[ROLE]` occurrences in templates are meant to stay as placeholders

### Option B: Role-specific cycle-runner variants (`cycle-runner-pm.md`, `cycle-runner-dm.md`, etc.)
- Pros: No changes to compose.py; each variant is explicit and testable in isolation; easy to add role-specific nuances without conditionals
- Cons: 5 near-identical files to maintain (pm, qa, dm, designer, skill); drift risk when the base cycle-runner logic changes; violates DRY; increases template maintenance burden significantly

### Option C: Runtime detection — cycle runner reads role from config/environment
- Pros: Zero template changes needed for role resolution; cycle-runner.md stays generic with instructions like "run `cycle_pre.py $(python references/scripts/config.py get role)`"; no compose.py changes
- Cons: Adds a runtime dependency (config must return role correctly); more complex instructions for agents to parse; agents may misinterpret the nested command; no existing `config.py get role` command today so new script work needed

## Q2: Should cycle-runner replace `common/pull-latest`, `common/git-commit`, `common/iteration-log`, and status-bar instructions when enabled, or coexist?
> Why this matters: Coexistence without explicit "skip these steps" will cause duplicated pulls, duplicated commits, duplicated iteration logs, and inconsistent tracker state. But full replacement removes fallback instructions if the feature flag is off.

### Option A: Conditional replacement with explicit skip markers (RECOMMENDED)
- Pros: Clean single path per mode — when enabled, agents see only cycle-runner instructions for mechanical steps; when disabled, agents see only manual instructions; no ambiguity or duplication
- Cons: More complex template composition (conditional includes); need to test both paths (flag on and off); template readability suffers with conditional blocks

### Option B: Full replacement — remove manual sub-skills entirely, cycle runner always on
- Pros: Simplest templates; no feature flag complexity; one path to test and maintain; forces adoption which validates the scripts faster
- Cons: No graceful degradation if scripts break; removes the proven manual path; users who prefer manual control lose the option; breaking change for existing installs; violates the research recommendation of "feature-flagged, default off"

### Option C: Coexist with "skip if cycle runner enabled" notes in each manual sub-skill
- Pros: Minimal template changes; manual sub-skills remain intact with a one-line note; easy to understand for agents reading the template top-to-bottom
- Cons: Dual-instruction confusion (research Risk 1, severity H); agents may miss the "skip" note and execute both paths; scattered skip markers across multiple sub-skills are fragile; testing burden doubles

## Q3: Do we want `cycle_post.py` to enforce additional required fields per role (PM pipeline sentinel results, QA verification summary, skill test results), or keep schema permissive?
> Why this matters: Too strict breaks agents when they cannot produce a field (e.g., QA has no test results on a quiet cycle). Too loose risks losing critical role outputs silently — the script succeeds but important data is never captured.

### Option A: Permissive base schema + optional role-specific warnings (RECOMMENDED)
- Pros: Agents are never blocked by schema validation failures; script logs warnings for missing role-specific fields so humans can spot gaps; matches the current minimal validation approach; easy to tighten later once patterns stabilize
- Cons: Missing data goes unnoticed unless someone reads the logs; no enforcement means agents may never learn to produce expected fields; "warning fatigue" if too many warnings fire

### Option B: Strict per-role schemas — role-specific required fields enforced
- Pros: Guarantees critical outputs are captured every cycle; forces agents to produce structured data; makes role-specific outputs contractual and testable
- Cons: Agents crash or get stuck when they cannot produce a required field; every new role-specific field requires a schema update and test; quiet/suppressed cycles need special handling to avoid false failures; increases coupling between script and role templates

### Option C: Two-tier schema — strict for cycle metadata, permissive for role outputs
- Pros: Core cycle tracking (role, cycle_number, cycle_type, transitions) is always validated; role-specific content is best-effort; balances reliability with flexibility
- Cons: Unclear where the boundary falls for some fields (e.g., is "summary" core or role-specific?); still risks losing important role outputs silently; adds schema design complexity without fully solving either problem

## Q4: How to handle role-specific "always-run" steps (e.g., PM pipeline sentinel, QA branch checkout) under cycle runner?
> Why this matters: If cycle runner suppresses cycles or changes step ordering, safety-critical steps like the pipeline sentinel might stop running, regressing guarantees the team depends on. The PM pipeline sentinel is explicitly marked "always runs" in current templates.

### Option A: Cycle runner defines "creative phase" boundaries — always-run steps live outside them (RECOMMENDED)
- Pros: Clear separation: cycle_pre runs before everything, always-run steps run next, creative work happens, cycle_post runs last; always-run steps are never suppressed even when the cycle is; matches the "mechanical shell / creative core" architecture decision
- Cons: Requires documenting which steps are "always-run" vs "creative" per role; adds a new concept (step classification) to the template architecture; some steps blur the line (e.g., health check is mechanical but not in cycle_pre)

### Option B: Encode always-run steps into `cycle_pre.py` itself
- Pros: Truly deterministic — scripts handle all always-run logic; agents cannot accidentally skip them; single point of control
- Cons: Pipeline sentinel is complex PM-specific logic that does not belong in a generic script; script becomes role-aware and harder to maintain; blurs the "mechanical shell" boundary; significant new script development needed

### Option C: Keep always-run steps in the role template, outside cycle runner scope
- Pros: No changes to cycle runner or scripts; role templates retain explicit control over safety steps; simplest implementation
- Cons: Agents must mentally reconcile two instruction sources (cycle runner + template); if cycle runner suppresses a cycle, the agent may still skip template steps by association; no enforcement that "always-run" steps actually run; fragile to template edits

## Q5: What is the rollout plan to avoid breaking agents mid-cycle when templates change?
> Why this matters: Agents may be in the middle of a manual cycle when templates are recomposed. Switching instructions mid-cycle could cause partial commits, missed tracker transitions, or duplicated operations. The feature flag helps but does not fully protect against mid-cycle recomposition.

### Option A: Recompose on next idle — DM waits for agent idle before deploying (RECOMMENDED)
- Pros: Leverages existing `reboot_agent.py` idle-wait mechanism; agent finishes current cycle cleanly before seeing new instructions; zero risk of mid-cycle instruction changes; aligns with the "never kill mid-work" lifecycle guarantee
- Cons: Delays rollout until all agents go idle (could be 30+ minutes per agent); if an agent is stuck, rollout stalls; requires DM coordination (or PM fallback) to orchestrate the sequence

### Option B: Feature flag only — recompose immediately, let agents discover the flag
- Pros: Instant rollout; agents read the flag at cycle start and branch accordingly; no coordination overhead; simple to implement
- Cons: If recomposition happens mid-cycle, the agent's in-memory instructions change but its cycle state does not; could cause partial mechanical + partial manual operations; race condition between compose and agent read; does not protect against the "dual instruction" window

### Option C: Staged rollout — one role at a time with canary validation
- Pros: Limits blast radius; validate on skill agent first (simplest role), then expand; can catch role-specific issues before they hit PM/QA; provides a rollback point per role
- Cons: Slower rollout; requires tracking which roles have been migrated; temporary state where some roles use cycle runner and others do not; increases coordination complexity; canary validation criteria need defining
