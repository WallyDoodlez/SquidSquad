# FEAT-PM-1291 Phase 2 Prep — Multi-Model Subagents for SquidSquad

## Optimal Question Order

Questions should be resolved in this order (dependencies first, controversial last):

1. **Q5** (pip install experience) — Foundational: determines whether the external model approach is even viable without breaking the zero-dependency story. All other questions assume external models are usable.
2. **Q2** (multi-provider vs OpenAI-only) — Architectural: shapes the design of model_router.py and the adapter layer. Must be decided before implementation begins.
3. **Q3** (QA execution gap) — Behavioral: determines what QA execution looks like with external models. Depends on Q2 (provider choice affects available capabilities).
4. **Q1** (Research default model) — Scope: decides the default cost/quality trade-off for the highest-value spawn. Can be changed later without architectural impact.
5. **Q4** (quality scoring) — Performance/scope: most controversial, highest design surface area, and can be deferred to a follow-up task without blocking v1.

---

## Q5: What is the pip install experience for the `openai` package?

**Category**: Compatibility / Developer Experience

**Why it matters**: SquidSquad currently has zero Python package dependencies (all scripts use stdlib). Adding `openai` changes the install story and may introduce version conflicts, virtual environment requirements, or platform issues.

### Option A: Lazy import with inline `pip install` fallback (Recommended)

model_router.py attempts `import openai` at call time. If missing, runs `pip install openai` automatically (or prompts the user), then retries the import.

- **Pros**: Zero setup burden for users who enable external models. No impact on users who stay Claude-only (import never triggers). Self-healing — works even if the user forgot the install step.
- **Cons**: Auto-installing packages is surprising behavior. Could install into wrong environment. pip may not be on PATH. Version pinning is harder to enforce.

### Option B: Document as a prerequisite, fail with clear error

model_router.py attempts `import openai`. If missing, prints a clear error message ("To use external models, run: pip install openai>=1.0") and exits with code 2. Parent falls back to Claude.

- **Pros**: Explicit, no surprises. User controls their Python environment. Clean separation — SquidSquad stays zero-dep by default. Error message is actionable. Graceful degradation (Claude fallback works).
- **Cons**: Extra manual step for users who want external models. Could cause confusion if the user sets a model in config.md but forgets the install.

### Option C: Bundle a requirements-optional.txt and add wizard step

Add `references/requirements-optional.txt` with `openai>=1.0`. Wizard prompts: "Install external model dependencies? (y/n)". If yes, runs `pip install -r requirements-optional.txt`.

- **Pros**: Guided experience. Version pinning is explicit. Wizard already exists — natural extension. Clear separation between required (none) and optional deps.
- **Cons**: Another file to maintain. Wizard step adds complexity. Users who skip the wizard still hit the import error. requirements-optional.txt may go stale.

**Recommendation**: **Option B** — fail with a clear error. It preserves the zero-dependency guarantee, requires no magic, and the fallback-to-Claude behavior means nothing breaks. The wizard can mention it as an optional step without adding formal dependency management.

---

## Q2: Should model_router.py support multiple external providers from day 1?

**Category**: Scope / Architecture

**Why it matters**: Supporting OpenAI-only is simpler to build, test, and document. Supporting multiple providers (Gemini, Anthropic API direct, local models) from day 1 adds complexity but future-proofs the architecture.

### Option A: OpenAI-only, monolithic (Recommended)

model_router.py supports only OpenAI-compatible APIs. The adapter layer is a single file. Config values are `claude` or `gpt-5.2` (or other OpenAI model names).

- **Pros**: Simplest to build, test, and ship. Covers the primary cost-saving use case (GPT is cheaper than Claude Agent tool). One API format to handle. Fewer failure modes. Can ship in 1-2 days.
- **Cons**: Adding a second provider later requires refactoring. Users with Gemini or local model preferences must wait. May need to redo the adapter architecture if the monolithic approach doesn't generalize.

### Option B: Multi-provider with adapter interface from day 1

model_router.py defines a `ModelAdapter` interface. Ship with two adapters: `openai.py` and a stub `anthropic_direct.py`. Config values use `provider:model` format (e.g., `openai:gpt-5.2`, `google:gemini-2.5-pro`).

- **Pros**: Architecture is future-proof from the start. Adding new providers is a single file. Config format is clean and extensible. Users can bring their own provider.
- **Cons**: More code to write and test on day 1. Adapter interface may be wrong (designed without real usage feedback). The anthropic_direct adapter is a stub — confusing. More surface area for bugs.

### Option C: OpenAI-only with pre-planned adapter seams

model_router.py supports only OpenAI but the code is structured so that extracting an adapter interface later is trivial (e.g., all API calls go through a single `call_model()` function). No formal interface, no stubs, no multi-provider config format.

- **Pros**: Ship fast like Option A. Internal structure makes future refactoring easy. No premature abstraction. Config stays simple. Real usage informs the eventual adapter interface.
- **Cons**: Still requires a refactor when the second provider arrives. "Pre-planned seams" can be illusory — the refactor may be just as hard.

**Recommendation**: **Option A** — OpenAI-only, monolithic. The primary use case is GPT for cost savings. Ship it, validate the approach, then generalize if/when a second provider is needed. YAGNI applies strongly here.

---

## Q3: How to handle the QA execution gap?

**Category**: Behavior / Compatibility

**Why it matters**: QA test execution (Spawn 4) needs to run verification commands via Bash. External models cannot execute commands. This creates a gap: either QA stays Claude-only, or model_router.py must pre-run commands somehow.

### Option A: QA execution always stays Claude-only (Recommended)

QA execution is locked to `claude` in config. The config field exists but the value is fixed (or strongly defaulted). Research shows QA execution is 30-100k tokens — significant but not the largest spawn.

- **Pros**: Zero risk of broken verification. No architectural complexity for command pre-execution. Comprehension testing (already Claude-locked) and QA execution use the same path. Simplest to implement. QA results are trustworthy.
- **Cons**: Misses cost savings on the second-most-expensive spawn. Users cannot opt into cheaper QA even for file-inspection-only test plans. Less flexibility.

### Option B: Hybrid — classify test cases, route per-case

model_router.py reads the TEST-PLAN.md and classifies each test case as "file-only" (no Bash commands needed) or "command-required". File-only cases go to the external model with file contents embedded. Command-required cases go to Claude.

- **Pros**: Maximizes cost savings — file-only test cases (often 30-60% of a plan) use the cheaper model. Command-based tests still get full Bash access. Per-case routing is granular.
- **Cons**: Complex implementation — must parse TEST-PLAN.md structure, classify cases, split execution, merge results. Two different models producing parts of the same QA-RESULTS.md. Edge cases in classification (what if a "file-only" case actually needs a command?). Harder to debug failures.

### Option C: Pre-run commands in model_router.py, embed output

model_router.py reads the TEST-PLAN.md, extracts all verification commands, runs them locally, captures output, and embeds the command outputs in the prompt sent to the external model. The external model analyzes the pre-captured output.

- **Pros**: External model gets all the data it needs. Single model produces the full QA-RESULTS.md. Potentially cheaper than Claude for analysis-heavy test plans.
- **Cons**: model_router.py becomes a command executor — significant security and reliability concerns. Commands may have side effects. Command output may be enormous. The external model is analyzing stale output (commands ran before the model sees them). If a command fails, the model cannot retry or adapt. Verification commands may depend on each other's output.

**Recommendation**: **Option A** — QA execution stays Claude-only. The complexity of Options B and C is not justified for a v1. QA verification is safety-critical — using the same model that has tool access produces more reliable results. Cost savings should come from the other 3 offloadable spawns (Research, Discussion Prep, Test Plan) which together represent 75-220k tokens per task.

---

## Q1: Should Research (Phase 1) default to Claude or external model?

**Category**: Scope / Quality vs Cost

**Why it matters**: Research is both the most expensive spawn (50-150k tokens) and the highest-value one — it shapes all downstream decisions (discussion, test plan, implementation). Getting research wrong cascades through the entire task lifecycle.

### Option A: Default to Claude, user opts into external

Config ships with `Research Model: claude`. Users who want cost savings change it to `gpt-5.2`. Documentation explains the trade-off.

- **Pros**: Safe default — highest quality for the most important spawn. Users who care about cost can opt in explicitly. No quality regression on upgrade. Matches the "all-claude defaults" upgrade story.
- **Cons**: Users who want maximum cost savings must manually change the config. The biggest cost-saving opportunity is not realized by default.

### Option B: Default to external model (Recommended)

Config ships with `Research Model: gpt-5.2`. Users who want maximum quality change it back to `claude`.

- **Pros**: Maximizes cost savings by default — this is the whole point of the feature. GPT 5.2 is strong at code analysis and long-context reasoning. Users who upgrade are presumably doing so for cost savings. Fallback to Claude exists if the API fails.
- **Cons**: Quality risk on the most important spawn. Users may not notice quality degradation until a bad research document leads to a bad implementation. "Default to cheaper" may not match user expectations.

### Option C: Default to Claude, with cost estimate prompt (Recommended)

Config ships with `Research Model: claude`. During the first research spawn after upgrade, model_router.py prints an estimate: "This research would cost ~$X with Claude, ~$Y with GPT 5.2. To use GPT 5.2 for research, set 'Research Model: gpt-5.2' in config.md." One-time informational message.

- **Pros**: Safe default with informed opt-in. User sees the cost difference and makes a conscious choice. No quality risk by default. Educational — helps users understand the cost/quality trade-off.
- **Cons**: Requires token cost estimation logic in model_router.py (adds complexity). One-time messages can be annoying. Cost estimates may be inaccurate.

**Recommendation**: **Option A** — default to Claude. The research spawn shapes everything downstream. Users who want cost savings will find the config option. The "all-claude defaults, opt in to external" story is clean and safe. Option C is appealing but adds implementation complexity for a one-time message.

---

## Q4: Should there be a quality scoring mechanism to auto-detect inferior output?

**Category**: Performance / Scope

**Why it matters**: Without quality scoring, the only check on external model output quality is PM/QA review — which happens after the output is already consumed. A bad research document could lead to a bad test plan, which leads to a missed bug.

### Option A: No quality scoring in v1 — rely on existing review (Recommended)

PM already reviews RESEARCH.md, CONTEXT.md, and TEST-PLAN.md. QA already reviews QA-RESULTS.md. These human-in-the-loop checks catch quality issues. Add quality scoring in a follow-up if quality problems are observed in practice.

- **Pros**: Zero additional complexity. Ships faster. Existing review workflow is the quality gate. Avoids building a scoring system that may not correlate with actual quality. Lets real usage data inform what "quality" means for each task type.
- **Cons**: Quality issues are caught late (after PM reads the document). No automated feedback loop. If quality is consistently bad for a task type, the user must manually notice and change the config.

### Option B: Length-based sanity check

model_router.py checks if the output meets a minimum length threshold (configurable per task type, e.g., Research: 200 lines, Test Plan: 50 lines). Below threshold = treat as failure, fall back to Claude.

- **Pros**: Simple to implement (5 lines of code). Catches obvious failures (empty responses, truncated output, API errors that return garbage). No false positives for reasonable output. Low overhead.
- **Cons**: Length is a poor proxy for quality. A long but wrong document passes. A concise but correct document might fail. Thresholds are arbitrary and task-dependent.

### Option C: Structure validation — check for required sections

model_router.py parses the output markdown and verifies required sections exist (e.g., Research must have Summary, Impact Analysis, Side Effects, Edge Cases, etc.). Missing sections = failure, fall back to Claude.

- **Pros**: Catches structural issues (model didn't follow the template). More meaningful than length alone. Required sections are already defined in the prompt templates. Medium implementation effort.
- **Cons**: Presence of a section header doesn't mean the content is good. Could be gamed by a model that produces headers with empty or shallow content. Regex-based section detection is fragile. Different models may use slightly different header formatting.

**Recommendation**: **Option A** — no quality scoring in v1. The existing PM/QA review is the quality gate. Add Option B (length check) as a trivial safety net if desired — it is 5 lines of code and catches catastrophic failures. Full quality scoring (Option C or beyond) should be informed by real usage data, not designed speculatively.
