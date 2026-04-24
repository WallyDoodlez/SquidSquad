# FEAT-PM-2361 Discussion Prep — TC Coverage Gate

## Recommended Question Order

1. **Q1: TC syntax canonicalization** — This must be decided first because it determines the parser design, which is the foundation everything else builds on. If we get syntax wrong, the gate either misses TCs (false pass) or blocks valid work (false fail).
2. **Q2: Issue-to-artifact mapping** — Second because it determines how the gate integrates with tracker.py. The `--force` bypass question (Q3) only matters once we know how the gate is wired in, so mapping must come first.
3. **Q3: `--force` bypass behavior** — Last because it is a policy decision that layers on top of the mechanical design. Once we know how parsing and mapping work, we can make an informed call on whether bypass should exist.

---

## Q1: What is the canonical TC syntax across all TEST-PLAN/QA-RESULTS files?
> Why this matters: Parser strictness determines whether the gate blocks valid work (false negatives from unrecognized TC formats) or misses missing TCs (false positives from overly loose matching). Getting this wrong means the gate either becomes a nuisance that agents work around, or silently fails to catch gaps.

### Option A: Tolerant regex matching (RECOMMENDED)
Accept multiple formats: `TC-01`, `TC-1`, `TC 01`, `### TC-1:`, table rows with `TC-1` column. The parser normalizes all variants to a canonical `TC-N` form internally. A `--debug` flag prints unmatched lines so developers can diagnose parsing issues.

- Pros: Works with all existing files without migration. Resilient to minor formatting drift. Low friction for adoption. Matches the existing organic formatting across the repo (research found variant formats).
- Cons: More complex parser logic. Risk of false matches on strings like "TC-1" appearing in prose outside of actual TC markers. Requires good unit test coverage of edge cases.

### Option B: Strict single format — require `### TC-N:` heading syntax
All TEST-PLAN and QA-RESULTS files must use exactly `### TC-N: [title]` as the TC marker. Reject anything else.

- Pros: Simplest parser (one regex). Unambiguous — no false matches. Easy to validate and test.
- Cons: Requires migrating all existing planning artifacts to the new format. Creates friction for agents writing test plans. Any formatting typo blocks the pipeline.

### Option C: Template-enforced format with linter
Add a TC format linter that runs when TEST-PLAN/QA-RESULTS files are created. The linter enforces a specific format at write time; the coverage gate then uses the same strict parser.

- Pros: Catches format issues early (at creation, not at ship time). Strict parsing with high confidence. Self-documenting — template shows the expected format.
- Cons: Two tools to maintain (linter + gate). Existing files still need migration. Adds complexity to the test-plan creation workflow.

---

## Q2: How to map an issue/feature to the correct TEST-PLAN/QA-RESULTS pair during `pending-test -> pending-ship`?
> Why this matters: The tracker operates on GitHub issue numbers, but planning docs use various naming conventions (`FEAT-PM-1291-...`, `FEAT-SKILL-...`, `ISSUE-...`). If the gate cannot reliably find the right files, it either blocks everything (can't find docs) or checks the wrong docs (silent mismatches).

### Option A: Convention-based auto-discovery with CLI fallback (RECOMMENDED)
The script searches `.squidsquad/[role]/planning/` for files matching `*-[NUMBER]-TEST-PLAN.md` and `*-[NUMBER]-QA-RESULTS*.md`. For QA results revisions, it deterministically selects the highest `-RN` suffix. If auto-discovery fails or finds ambiguous matches, the transition command requires explicit `--test-plan` and `--qa-results` CLI args.

- Pros: Zero-config for the common case (naming conventions already exist). Explicit fallback prevents silent failures. Handles the revision selection problem (`-R2`, `-R3`) deterministically. Does not require any new metadata fields.
- Cons: Relies on naming conventions being followed — a mismatch silently falls through to the CLI fallback. Glob matching can be fragile if file paths change. Multiple roles may have planning dirs with the same issue number.

### Option B: Metadata field on GitHub Issue
Add a label or issue body field (`test-plan: path/to/file`, `qa-results: path/to/file`) that explicitly links the issue to its planning artifacts. The gate reads these fields directly — no guessing.

- Pros: Explicit and unambiguous. Works regardless of file naming conventions. Easy to verify — the link is visible in the issue.
- Cons: Requires modifying the issue creation workflow (tracker.py or manual). Adds maintenance burden — paths must be updated if files move. Extra boilerplate on every issue.

### Option C: Centralized manifest file
Maintain a `planning-manifest.json` in `.squidsquad/` that maps issue numbers to their TEST-PLAN and QA-RESULTS paths. The gate reads this manifest; agents update it when creating planning artifacts.

- Pros: Single source of truth for all mappings. Supports arbitrary file locations. Easy to query programmatically.
- Cons: Another file to maintain and keep in sync. Merge conflicts if multiple agents update simultaneously. Adds a new concept to the system that all agents must learn.

---

## Q3: Should `--force` in `tracker.py transition` bypass the TC coverage gate?
> Why this matters: The human preference is explicit — "never ship with failed/missing TCs." But disallowing any bypass removes the escape hatch for genuine emergencies (critical hotfix, infrastructure issue where TCs are irrelevant, etc.). This is a tension between safety and operational flexibility.

### Option A: No bypass — `--force` does NOT skip TC coverage (RECOMMENDED)
The `--force` flag on `tracker.py transition` continues to override role-authority checks but does NOT bypass the TC coverage gate. To ship without coverage, a human must manually close the issue via `gh issue close` outside the normal transition path.

- Pros: Aligns directly with the human preference ("never ship with failed TCs"). Prevents accidental bypasses — agents cannot circumvent the gate even with `--force`. The manual `gh issue close` escape hatch still exists for true emergencies but requires deliberate human action.
- Cons: No in-tool escape hatch — emergencies require going outside the normal workflow. Could frustrate agents if the gate has a false positive (parser bug, wrong file matched). Slightly less flexible than having a documented bypass.

### Option B: Bypass with audit trail
`--force` skips the TC coverage gate but logs a prominent warning and requires a `--reason` argument. The reason is recorded as a Discussion comment on the issue: `"OVERRIDE: TC coverage gate bypassed. Reason: [reason]."` A weekly audit scan flags all overrides.

- Pros: Provides an escape hatch for genuine emergencies. Full audit trail means overrides are visible and reviewable. Balances safety with operational flexibility.
- Cons: Contradicts the "never ship with failed TCs" preference — even with logging, it normalizes bypassing the gate. Agents may default to `--force` when the gate is inconvenient rather than fixing the underlying issue. Audit trail is reactive, not preventive.

### Option C: Separate `--skip-coverage` flag (distinct from `--force`)
Create a new `--skip-coverage` flag that is independent of `--force`. This flag requires both `--reason` and `--approver` (must be `human`). `--force` continues to handle role-authority overrides only.

- Pros: Separates concerns — authority bypass and coverage bypass are distinct operations. Requires explicit human approval (`--approver human`), not just any agent. Makes the override intentional and hard to invoke accidentally.
- Cons: Adds complexity to the CLI interface. Two override flags may confuse agents. Still contradicts the "never ship" preference, just with more ceremony. The `--approver human` check is unenforceable in practice (any agent can pass the flag).
