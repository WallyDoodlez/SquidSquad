# FEAT-PM-5868 Discussion Prep

## Already Locked (from prior discussion)

- Event Reactions config lives in `config.md` (new `## Event Reactions` section), not a separate file
- Section covers both **emits** and **reacts-to** per role (pm, skill, qa, dm)
- Existing mechanical emissions in `tracker.py`, `git_ops.py`, `cycle_pre.py`, `cycle_post.py` stay hardcoded — no migration of emission sites
- `compose.py` creative LLM step (`agent_compose()`) derives event contract from L1-L4 instructions
- Cross-agent validation runs after **every** compose, including single-role deploys
- Interactive fix loop on validation failure
- Graceful degradation: no-events mode when `Event Reactions` section absent, falls back to hardcoded `_ROLE_EVENT_TYPES`
- Compose is its own skill (`/squidsquad-compose`) — already shipped as #5888

---

## Open Questions

### Q1: When does the LLM derivation of event contracts run?

**Why it matters**: If derivation never runs automatically, `config.md` stays empty until a human manually enables `agent-compose: yes`. That means new installs have no event contracts until an explicit manual step — and the cross-agent validation (which runs every compose) has nothing to validate. If derivation runs too eagerly, it blocks deterministic CI paths that intentionally skip Claude calls.

| Option | Pros | Cons |
|--------|------|------|
| A: Only when `agent-compose: yes` (LLM gate) | Deterministic CI path unaffected; no surprise Claude calls; consistent with existing `agent_compose()` behavior | Config stays empty on new installs; must remember to enable `agent-compose: yes` once; validation passes vacuously until section is populated |
| B: Always derive (every compose) | Contracts always fresh; no opt-in required; cross-agent validation always has data | Every compose calls Claude — slow, burns tokens, breaks offline/CI use; increases hallucination surface per compose frequency |
| C: First-time only — derive during setup, validate-only thereafter ⭐ | Contracts populated at install time (when `agent-compose` is typically enabled); subsequent composes are deterministic (validate, don't derive); easy upgrade path | Contracts go stale if roles gain new behaviors; requires manual trigger or re-setup to refresh; slightly more complex compose logic |

**Recommended**: Option C. Derivation runs once during `/squidsquad-setup` (where `agent-compose: yes` is the norm) and writes the initial `Event Reactions` section. All subsequent composes run validation-only against the existing section. If the human wants to refresh contracts (e.g., after adding a new role or sub-skill), they re-enable `agent-compose: yes` for one compose pass. This matches the research recommendation and protects the deterministic compose path.

---

### Q2: What is the authoritative source when LLM-derived contracts conflict with hardcoded emission sites?

**Why it matters**: The LLM may derive that PM emits an event type that no script actually emits, or miss a real emission. If the LLM wins, the contract is wrong and downstream reactions fire on phantom events. If the hardcoded catalog always wins, the LLM derivation adds no value for gaps the catalog doesn't cover (e.g., L4 project-specific events). Getting this wrong means either silent broken contracts or blocked deploys on false positives.

| Option | Pros | Cons |
|--------|------|------|
| A: Hardcoded catalog is ground truth — LLM extras are errors, LLM gaps are warnings | Direct/mechanical (matches human preference); prevents phantom event types; easy to implement | LLM-derived L4 custom events are always errors even when legitimate; catalog must be kept up-to-date manually |
| B: LLM output wins — hardcoded catalog is advisory only | Allows L4 custom events freely; LLM can capture context the catalog doesn't | Hallucinated event types silently enter contracts; no enforcement backstop; fragile |
| C: Tiered authority — catalog events are hard constraints (extras = error, gaps = warning); L4 custom events are allowed with a warning ⭐ | Catches hallucinations on known event types while allowing legitimate L4 extensions; surfaced as warnings for human review; aligns with "prefers direct checks" preference | Slightly more complex validation logic; must distinguish L4 events from hallucinated ones (heuristic: event not in catalog AND appears in L4 source text = allowed) |

**Recommended**: Option C. Known event types (those emitted by the four hardcoded scripts) are hard constraints — LLM cannot invent or drop them. L4-sourced custom events are allowed with a warning so the human can review. This gives safety on the known surface while not blocking legitimate project-specific extensions.

---

### Q3: How does the interactive fix loop behave when validation fails?

**Why it matters**: If the fix loop requires human input and the human is offline (CI run, automated upgrade, night cycle), the compose blocks indefinitely. If it self-corrects too aggressively, the agent may patch config.md with wrong data and silently corrupt event contracts. The right scope determines whether this feature is safe to enable in unattended deployments.

| Option | Pros | Cons |
|--------|------|------|
| A: Always require human input — pause and wait | Safest for contract correctness; human reviews every fix | Blocks CI/unattended deploys completely; useless in automated contexts |
| B: Full agent self-correction — agent patches any gap autonomously | Never blocks; fully automated | High risk of wrong auto-patches; LLM fixes LLM mistakes, compounding errors; no human visibility |
| C: Two-tier with timeout ⭐ — Tier 1: auto-fill missing `emits` from hardcoded catalog (deterministic, safe); Tier 2: propose reaction fixes and ask human; 2-minute timeout falls through with logged warnings | Safe subset of fixes are automatic (catalog fills are deterministic); human reviews creative fixes; timeout prevents indefinite blocking; aligns with self-healing sentinel pattern | Tier 2 still blocks if human is present but slow; logged warnings may be missed in unattended runs |

**Recommended**: Option C. Auto-fill only what can be derived deterministically (missing `emits` entries from the hardcoded catalog). For anything requiring judgment (reaction patterns, reacts-to entries), propose and ask. 2-minute timeout falls through so CI is never permanently blocked — it deploys with a logged warning that contracts are incomplete. This matches the two-tier self-healing pattern already in use elsewhere.

---

### Q4: Does the `Event Reactions` config section cover creative-phase reactions, mechanical reactions, or both?

**Why it matters**: `cycle_pre.py` reads config.md mechanically (Python script, deterministic). Agent creative-phase guidance is delivered via sub-skills (markdown, LLM-consumed). Mixing both into one config.md section creates a document that serves two incompatible consumers: a Python parser and an LLM. Getting this wrong either overloads `cycle_pre.py` with prose it can't parse, or forces agents to parse terse mechanical config for creative guidance.

| Option | Pros | Cons |
|--------|------|------|
| A: Config.md covers mechanical only — creative guidance in `event-reactions.md` sub-skill exclusively | Clean separation of concerns; each consumer reads only what it understands; config.md stays compact | Two places to maintain; slight duplication of event type names; agent must know to check both |
| B: Config.md covers both — one section, two audiences | Single source; nothing to cross-reference | Config becomes prose-heavy and unparseable by `cycle_pre.py`; or sub-skill is redundant; or format compromise satisfies neither consumer well |
| C: Config.md covers mechanical (emits + reacts-to per role, terse format); sub-skill covers creative interpretation (what events mean for creative work, how to respond in Ralph Loop) ⭐ | Canonical separation matching the existing mechanical/creative split in the Ralph Loop; `cycle_pre.py` reads compact structured data; agents read prose guidance; no mixed consumers; mirrors the two-tier reaction config pattern worth vaulting | Requires both artifacts to exist and stay consistent; first-time authors must know to update both |

**Recommended**: Option C. The research already documents this as the intended design and flags it as a vault-worthy pattern ("Two-tier reaction config: mechanical vs creative"). Config.md `Event Reactions` section = terse structured data for `cycle_pre.py`. `event-reactions.md` sub-skill = prose guidance for agent creative phase. They serve different consumers and should not be merged.

---

## Suggested Question Order

**Ask Q4 first** — it sets the scope boundary for what goes into config.md. Without this answer, Q1 and Q2 discussions are ambiguous (are we deriving mechanical contracts, creative guidance, or both?).

**Ask Q2 second** — it defines the ground-truth authority model, which directly shapes how validation works (Q1 and Q3 depend on what "validation failure" means).

**Ask Q1 third** — once Q2 is settled (what counts as valid), Q1 (when to derive) is a deployment logistics question with a clear recommended answer.

**Ask Q3 last** — the fix loop behavior is a UX/safety question that can only be scoped correctly once you know what gets validated (Q2) and when (Q1). It's also the least likely to require extended discussion given the two-tier pattern is already established.
