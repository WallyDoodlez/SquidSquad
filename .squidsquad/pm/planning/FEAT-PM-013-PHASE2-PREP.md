# FEAT-PM-013 Phase 2 Prep -- Setup Flow Improvements

## Optimal Question Order

Questions should be discussed in this order based on dependency analysis:

1. **Q2** (scaffold location) -- foundational: determines the entire architecture boundary between Claude and CLI, all other questions depend on whether scaffold runs inside or outside Claude
2. **Q6** (tarball fetch) -- independent infrastructure: no dependencies on other questions, easy to resolve, builds momentum
3. **Q1** (spec JSON committed vs local) -- depends on Q2: if scaffold runs outside Claude, the spec JSON handoff mechanism matters more; also shapes Q4 (non-interactive mode)
4. **Q3** (repo scan surfacing) -- behavioral: depends on Q2 (what Claude's role is) to know how much scan data Claude needs to present
5. **Q5** (model routing key setup) -- behavioral: depends on Q2 (where interactive vs scripted boundaries are) to know how key setup integrates
6. **Q4** (non-interactive mode) -- scope extension: depends on Q1 (spec format stability) and Q2 (scaffold separation) being settled; most controversial as it expands scope significantly

Rationale: Q2 is the central architectural decision that shapes the entire restructure -- every other question references the CLI-vs-Claude boundary it defines. Q6 is orthogonal and easy to close quickly. Q1 and Q3 are mid-tier decisions that inform each other slightly but primarily depend on Q2. Q5 is a niche integration question. Q4 is last because it is a scope expansion that could derail discussion if tackled too early -- better to lock the core architecture first.

---

## Q2: Should Phase 5 (scaffold) run inside the Claude session or as a separate process after Claude exits?

**Category**: Architecture

> Running inside Claude means the wizard can show errors interactively. Running outside means less token usage and more reliability. A hybrid approach (Claude writes spec, CLI scaffolds, reports back) might be best.

### Option A: Scaffold runs entirely outside Claude (CLI orchestrates post-exit)

- **Pros**:
  - Zero token cost for deterministic scaffolding work
  - Scaffold failures produce clean script errors, not conversational debugging
  - Aligns perfectly with the transport-vs-behavior layering from #2070
  - Scaffold can be tested independently (unit tests on wizard.py scaffold)
  - If Claude crashes, nothing is partially written to disk
- **Cons**:
  - If scaffold fails, the user sees a CLI error with no interactive help -- they must re-run or debug manually
  - Two-phase install can leave user in limbo if terminal closes between Claude exit and scaffold completion
  - CLI must orchestrate Python script execution (adds cross-language orchestration complexity)

### Option B: Scaffold runs inside Claude but with a single script call (RECOMMENDED)

- **Pros**:
  - Claude can catch scaffold errors and explain them interactively ("label creation failed because gh auth lacks repo scope")
  - Single session experience -- user does not need to watch two phases
  - Claude can validate the output after scaffold (check that CLAUDE.md files exist, boot scripts parse, config.md round-trips)
  - If scaffold fails, Claude can retry or suggest fixes immediately
  - Simpler CLI -- it just launches Claude, no post-Claude orchestration needed
- **Cons**:
  - Some token cost for the scaffold step (but it is a single `wizard.py scaffold spec.json .` call, not multi-step)
  - Claude session must stay open through scaffold (minor -- it is fast)
  - Debugging scaffold bugs still requires reading Claude's output, though Claude can present errors clearly

### Option C: Hybrid -- Claude writes spec, CLI scaffolds, CLI reports status back to Claude

- **Pros**:
  - Scaffold is deterministic and outside Claude
  - Claude can still present results if re-invoked after scaffold
  - Best of both worlds in theory
- **Cons**:
  - Most complex architecture -- requires re-invoking Claude after scaffold or piping results back
  - Two Claude sessions (or one paused and resumed) adds latency and cost
  - Overengineered for the problem -- scaffold rarely fails, and when it does, the error is usually clear

---

## Q6: Should file fetching switch from 119 individual HTTP requests to a tarball/zip download?

**Category**: Performance

> Single HTTP request vs 119. Major UX improvement. Could use `gh api` to download a tar.gz of the `references/` subtree.

### Option A: Switch to tarball download via GitHub API (RECOMMENDED)

- **Pros**:
  - Dramatically faster install (1 request vs 119) -- likely 10-30x speedup for the fetch phase
  - Single point of failure instead of 119 (one request succeeds or fails, no partial downloads)
  - Less GitHub API rate limit pressure
  - `gh api repos/{owner}/{repo}/tarball/{ref}` is well-supported
- **Cons**:
  - Tarball includes the entire repo (or branch), not just `references/` -- need to extract only the relevant subtree
  - Requires tar extraction logic in the CLI (Node.js tar libraries exist but add a dependency)
  - If the repo is large, downloading the full tarball wastes bandwidth (mitigated by using sparse checkout or the Git Trees API for a subtree)

### Option B: Switch to GitHub Contents API with directory listing + parallel fetch

- **Pros**:
  - Can target exactly `references/` without downloading the entire repo
  - Parallel HTTP requests (e.g., 10 at a time) still faster than sequential 119
  - No tar extraction needed
- **Cons**:
  - Still multiple HTTP requests (fewer than 119 if directories are listed first, but still many)
  - More complex implementation than a single tarball
  - Rate limiting still a concern with parallel requests

### Option C: Keep current 119-file sequential fetch, optimize later

- **Pros**:
  - No code changes needed
  - Current approach works and is well-tested
  - Avoids introducing new failure modes
- **Cons**:
  - Slow UX remains -- first impression of SquidSquad is waiting for 119 files
  - Unnecessary API pressure
  - Known pain point that will keep surfacing in feedback

---

## Q1: Should the spec JSON be committed to the repo or kept local?

**Category**: Architecture / Compatibility

> If committed, it enables team-wide reproducibility but adds a file that might confuse users. If local-only, upgrade must reconstruct the spec from config.md every time.

### Option A: Commit as `.squidsquad/.install-spec.json` (RECOMMENDED)

- **Pros**:
  - Team-wide reproducibility -- any team member can re-scaffold from the same spec
  - Upgrade becomes trivial: read spec, bump version, re-scaffold
  - Reconfigure becomes trivial: read spec, edit interactively, re-scaffold
  - Spec is the single source of truth; config.md becomes a generated view
  - Git history tracks config changes over time
  - Enables `--non-interactive` mode (Q4) naturally -- just point at the spec file
- **Cons**:
  - One more file in `.squidsquad/` that users might be confused by (mitigated by a comment header explaining its purpose)
  - Spec must be kept in sync with config.md (or config.md must be generated from spec on every scaffold)
  - If a user manually edits config.md, the spec and config can drift (mitigated by always regenerating config.md from spec)

### Option B: Keep local only (e.g., `~/.squidsquad/specs/{repo-slug}.json`)

- **Pros**:
  - Cleaner `.squidsquad/` directory -- no extra file visible to users
  - No risk of spec/config drift in the repo
  - Users cannot accidentally edit the spec
- **Cons**:
  - Not portable across machines -- a team member on a different machine has no spec
  - Upgrade must reconstruct the spec from config.md every time (fragile, lossy -- config.md may not contain all spec fields)
  - No git history of spec changes
  - `--non-interactive` mode requires the spec to exist locally, which it may not

### Option C: Both -- commit to repo AND cache locally

- **Pros**:
  - Repo copy is the source of truth; local copy is a cache for faster access
  - Portable and reproducible
- **Cons**:
  - Two copies to keep in sync -- adds complexity for no clear benefit over Option A alone
  - Confusing mental model -- which copy wins?
  - Overengineered for the problem

---

## Q3: How much of the repo scan should be surfaced to the user?

**Category**: Behavior / UX

> Showing "I detected Next.js + TypeScript" builds trust. Showing a full JSON dump is overwhelming. The wizard should pick the top 3-5 most relevant detections to mention.

### Option A: Show top 3-5 detections in natural language, hide the rest

- **Pros**:
  - Builds trust ("I understand your project")
  - Not overwhelming -- user reads a 2-3 line summary, not a JSON dump
  - Focuses on what matters for setup decisions (stack, test framework, project structure)
  - Failures in detection are easy to catch ("that is wrong, we use Vitest not Jest")
- **Cons**:
  - May miss relevant detections that the user would have corrected if shown
  - Requires the wizard to rank detections by relevance (needs a heuristic)

### Option B: Show a structured summary with all detections, grouped by category (RECOMMENDED)

- **Pros**:
  - User sees everything the scan found -- full transparency
  - Grouped by category (Languages, Frameworks, Test Tools, CI/CD, Deploy) keeps it scannable
  - User can spot incorrect detections and correct them before they become defaults
  - Does not require relevance ranking -- show all, let the user skim
- **Cons**:
  - Slightly more verbose than Option A (but a well-formatted list of 8-12 items is still digestible)
  - Some detections may not be relevant to setup (e.g., CI/CD detection does not affect wizard questions directly)

### Option C: Show nothing -- use detections silently as defaults, let user correct during Q&A

- **Pros**:
  - Shortest wizard flow -- no scan presentation step
  - User only engages with detections when they appear as pre-filled answers
- **Cons**:
  - Feels opaque -- user does not know why "pytest" was suggested as the test command
  - Harder to correct wrong defaults if the user does not know what was detected
  - Misses the trust-building opportunity
  - If a detection is wrong and the user does not notice, the config is silently wrong

---

## Q5: How should model routing key setup integrate with the new flow?

**Category**: Behavior / Scope

> Key setup requires the user to edit `~/.squidsquad/secrets`, which is a side-channel action. The wizard currently guides this interactively. In a script-first flow, the script could open the secrets file and prompt.

### Option A: Keep model routing setup inside Claude's interactive phase

- **Pros**:
  - Claude can explain what model routing is and why the user might want it
  - Interactive Q&A about provider selection is natural in conversation
  - If the user says yes, Claude can guide them through editing `~/.squidsquad/secrets` step by step
  - No change to current UX for this specific question
- **Cons**:
  - Token cost for an advanced feature most users will skip (default is "No")
  - Side-channel file editing (opening secrets file) is awkward inside Claude

### Option B: Move provider discovery to pre-Claude phase, keep selection in Claude (RECOMMENDED)

- **Pros**:
  - Provider discovery (which providers are available, what models they offer) is mechanical -- run it in the CLI and save results
  - Claude reads the discovery results and presents them as options if the user wants model routing
  - Reduces Claude's work to one question: "Do you want model routing? Here are your available providers: [list]. Pick one."
  - If the user says no, zero additional token cost beyond the question
- **Cons**:
  - CLI must run `model_router.py list-providers` and save output (minor addition to Phase 3)
  - If discovery fails (no providers found), Claude must still handle the "no providers available" case gracefully

### Option C: Move entire model routing setup to CLI (post-Claude or during Phase 3)

- **Pros**:
  - Fully scripted -- no Claude involvement for an advanced feature
  - CLI can open the secrets file in the default editor if the user wants to configure keys
  - Simplest Claude wizard (one fewer question)
- **Cons**:
  - CLI-based Q&A for model routing is a poor UX -- it is an advanced topic that benefits from conversational explanation
  - If the user has questions about routing, they cannot ask the CLI
  - Loses the ability to tailor the explanation based on the user's project context

---

## Q4: Should the wizard support a `--non-interactive` mode for CI/scripted installs?

**Category**: Scope

> If the spec JSON format is stable, `npx squidsquad --spec spec.json` could skip the Claude session entirely. Useful for teams deploying SquidSquad to many repos.

### Option A: Yes, support `--non-interactive` as a first-class mode from the start

- **Pros**:
  - Enables CI/CD deployment of SquidSquad to many repos
  - Teams can standardize their SquidSquad config across projects
  - Forces the spec JSON format to be well-documented and stable early
  - Natural extension of "save install spec" (Q1) -- if the spec exists, why not use it directly?
- **Cons**:
  - Significant scope expansion -- spec format must be validated, documented, and versioned
  - Must handle all edge cases that Claude currently handles conversationally (missing fields, incompatible options, etc.)
  - Premature optimization -- how many teams are deploying SquidSquad to "many repos" today? Likely zero.
  - Adds testing surface area (every spec field combination must work without Claude)

### Option B: Defer to a future task -- design the spec format to allow it, but do not implement the CLI flag now (RECOMMENDED)

- **Pros**:
  - Keeps FEAT-PM-013 focused on the core restructure (pre-compute defaults, save spec, shorten wizard)
  - Spec JSON is saved (from Q1), so `--non-interactive` can be added later without re-architecture
  - Avoids premature spec format stability guarantees
  - Reduces scope and risk of the current task
- **Cons**:
  - Teams wanting scripted installs must wait
  - If spec format changes before `--non-interactive` ships, early adopters who relied on the format may be broken (mitigated by not promising stability yet)

### Option C: Support a minimal `--non-interactive` mode that only works with a previously generated spec (no from-scratch non-interactive)

- **Pros**:
  - Limited scope -- only the "re-scaffold from existing spec" path, not "generate spec without Claude"
  - Useful for the upgrade path (read spec, bump version, re-scaffold)
  - Does not require spec format documentation or validation for arbitrary inputs
- **Cons**:
  - Confusing UX -- "non-interactive" but only if you already ran interactive mode once
  - Still adds testing surface area, just less than Option A
  - The upgrade path already gets this behavior from `wizard.py scaffold` without a CLI flag
