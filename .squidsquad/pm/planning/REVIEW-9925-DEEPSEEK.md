Now I have a complete understanding of the repository. Let me compile my findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: AC4 (line ~44)
- **Severity**: error
- **Issue**: AC4 states that `compose.py deploy <role>` produces a `.squidsquad/<role>/CLAUDE.md` that includes the L1 boundary table, but the spec omits the prerequisite steps required for compose.py to actually do so. The new L1 fragment at `references/sub-skills/common/agent-boundaries.md` must be added to each role's `includes.yml` (and `includes-events.yml`) manifest AND each role's `instructions.md` entry file must contain an `{{include: common/agent-boundaries}}` directive. Without both, compose.py will never inline the fragment — per `_resolve_includes_with_manifest` at `references/scripts/compose.py` lines 293–327, an include is skipped if not present in the manifest.
- **Evidence**: The existing pattern: the manifest (e.g. `references/roles/pm/includes.yml` line 32) declares `roles/pm/prohibitions`, and the entry file (`references/roles/pm/instructions.md`) contains `{{include: roles/pm/prohibitions}}`. Both are required. The task spec only says to "Update `compose.py` if needed" (line 36 in Scope) but gives no AC or explicit instruction to add the manifest entry or the include directive. A developer implementing per the ACs verbatim would create the file but never wire it into compose.
- **Suggested fix**: Add an explicit AC (or expand AC4) requiring: (a) `common/agent-boundaries` added to the `includes` list in each role's `includes.yml` and `includes-events.yml` manifest, and (b) `{{include: common/agent-boundaries}}` added to each role's `instructions.md` entry file (or the entry in instructions.md is validated as present).

---

### Finding 2

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: L3 path reference (line ~19)
- **Severity**: error
- **Issue**: The L3 path `roles/<role>/<variant>/` is ambiguous. The repo has two directory trees: `references/sub-skills/roles/<role>/` (L2 location per locked design decision 1) and `references/roles/<role>/<variant>/` (where variants actually live, e.g. `references/roles/dev/skill/` with `instructions.md`, `includes.yml`, `SOUL.md`). The L3 path in the spec drops the root prefix entirely, making it unclear whether the stub belongs at `references/sub-skills/roles/<role>/<variant>/` (consistent with L2's base) or `references/roles/<role>/<variant>/` (where compose.py resolves variants via `_resolve_variant` at `compose.py` line 966–991).
- **Evidence**: Locked decision 1 says L2 is at `references/sub-skills/roles/<role>/`. Variant directories with `instructions.md` and `includes.yml` exist at `references/roles/<role>/<variant>/` (20 directories confirmed via glob: dev/{android,fullstack,ios,skill,web}, dm/{...}, pm/{...}, qa/{...}). The `compose.py` `_resolve_variant` function at line 985 references `ROLES_DIR / base / variant` where `ROLES_DIR = REPO_ROOT / "references" / "roles"`. No variant subdirectories exist under `references/sub-skills/roles/`.
- **Suggested fix**: Disambiguate the L3 path. Either: (a) state `references/roles/<role>/<variant>/` to match the compose.py variant resolution path, and note that L3 lives in a different root than L2 for architectural reasons, OR (b) if the intent is to keep L2/L3 in the same tree, specify `references/sub-skills/roles/<role>/<variant>/` and document that compose.py variant resolution needs updating. Also specify the exact stub filename (e.g., `boundaries.md`, `boundaries-stub.md`).

---

### Finding 3

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: AC2 (line ~42)
- **Severity**: warning
- **Issue**: AC2 requires "the top 5 most common cross-boundary mistakes for that role" but provides no method to determine what is "most common." This is subjective and cannot be deterministically verified by QA. Two different implementers (or the same implementer at different times) would produce different lists with no way to adjudicate correctness.
- **Evidence**: The Background section lists some repeat memory entries (`feedback_dont_do_qa_job`, `feedback_bugs_behavior_only`, `feedback_test_workflow_separation`, `feedback_dm_optional`, `feedback_fix_pm_bugs_immediately`) but AC2 doesn't require covering these specific items — it delegates to "most common" as an untestable heuristic. Compare with AC1 which defines a concrete deliverable (a table with specific columns and row coverage "at minimum").
- **Suggested fix**: Either: (a) define "most common" operationally — e.g., "the top 5 boundary mistakes documented in the 6 memory entries listed in the Background section and any additional cross-boundary violations observed in iteration logs from the last 30 days," or (b) make the list deterministic by explicitly enumerating the required seams from the Scope section (PM↔QA verification overlap, PM↔dev RCA depth, DM↔skill template ownership, direct-to-main workflow ownership) plus at least one additional role-specific boundary mistake.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: AC5 (line ~45)
- **Severity**: error
- **Issue**: AC5 says "Existing memory entries listed in Background section are referenced (or absorbed) so future agents see them at compose time, not by erroring first." The "referenced (or absorbed)" language creates two mutually incompatible acceptance criteria with no decision rule. "Referenced" means the boundary contract cites them by name (they remain in human/agent memory). "Absorbed" means the rules are inlined into the L1/L2 contract (they become compose-time instructions). These produce different artifacts with different verification procedures. Additionally, the memory entries (`feedback_dont_do_qa_job`, `feedback_bugs_behavior_only`, etc.) exist only in agent iteration logs and conversation context — they are not discoverable files in the repo — so "referenced" would require a citation format that QA can trace, while "absorbed" would require extracting the rules from the memory entries' meaning.
- **Evidence**: Iteration log at `.squidsquad-state/pm/iterations/iter-1573.md` line 8 shows an agent referencing `feedback_dont_do_qa_job` and `feedback_test_workflow_separation` as "memory" tags in prose, not as files. The 6 named entries (`feedback_dont_do_qa_job`, `feedback_bugs_behavior_only`, `feedback_test_workflow_separation`, `feedback_dm_optional`, `feedback_fix_pm_bugs_immediately`, plus `feedback_manual_agents` referenced elsewhere) have no corresponding source files. If "referenced" is chosen, QA needs a way to find them. If "absorbed" is chosen, the implementer must extract the behavioral rule from each memory entry name.
- **Suggested fix**: Choose one path and specify it: (a) "The L1 boundary table or L2 per-role sections SHALL absorb the behavioral rule from each named memory entry into a 'DO NOT — route to <role>' directive" or (b) "The L1 boundary table SHALL include a column or footnote citing each memory entry by name so future agents can locate them." Also, clarify whether `feedback_manual_agents` (referenced at `.squidsquad/pm/CLAUDE.md` line 717) is in scope — the Background says "etc." which is ambiguous.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: Scope section (lines ~35-38)
- **Severity**: warning
- **Issue**: The Scope section explicitly lists four seams that "produced finger-pointing this cycle": "PM↔QA verification overlap, PM↔dev RCA depth, DM↔skill template ownership, direct-to-main workflow ownership." None of the six ACs directly verify that any of these specific seams are addressed. AC1 (the role × responsibility table) and AC2 (top 5 mistakes per role) could theoretically cover them, but nothing ties the ACs back to the named seams. A role-boundary table covering pm/qa/skill/dm could be produced that entirely omits the direct-to-main workflow ownership seam, and it would still pass all ACs.
- **Evidence**: The Scope section says "Cover the specific seams that produced finger-pointing this cycle: ... direct-to-main workflow ownership." This is a motivating requirement. But AC1 only requires "a role × responsibility table covering pm/qa/skill/dm" with no seam-coverage requirement, and AC2 requires "top 5 most common cross-boundary mistakes" with no requirement that the named seams appear. The direct-to-main workflow ownership seam is especially non-obvious (it's about who owns the `pending-test` → `pending-ship` transition when a fix lands directly on main without a PR, per Background item #9903/#9905).
- **Suggested fix**: Add an AC that explicitly verifies each named seam is resolved in the boundary contract. For example: "AC7: The L1 boundary table includes an explicit entry for each seam listed in the Scope section (PM↔QA verification, PM↔dev RCA depth, DM↔skill template ownership, direct-to-main workflow ownership), with a clear owning role and a 'route to <role> because <reason>' rule." Alternatively, inline these seams as mandatory entries in AC2's "top 5" list.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: Locked design decision 1 (line ~17)
- **Severity**: warning
- **Issue**: The L1 scope says coverage is "pm/qa/skill/dm at minimum" but "skill" is a dev variant (see `references/roles/dev/skill/`), not a standalone role. The locked design decision says "canonical N×N role boundary table — every agent reads every role's scope." If the table must be N×N covering "every role," it should also cover `dev` as the base role — agents who are dev variants (but not skill specifically) would have no entry. Conversely, if "skill" is listed because it's the active dev agent (per `.squidsquad/config.md` line 9: "Dev Agents: skill"), then the table is instance-specific, not canonical.
- **Evidence**: `.squidsquad/config.md` line 9 shows `Dev Agents: skill`. The compose.py variant resolution at line 966–991 resolves `dev-skill` / `skill` to the variant at `references/roles/dev/skill/`. The task lists `skill` as a separate entry alongside `pm`, `qa`, `dm`. But `skill` is a variant of `dev`, not a peer role. If the table is canonical (reusable across SquidSquad installs), it should cover `dev` abstractly. If it's instance-specific, the AC should clarify that the table covers "all roles active in this install's config.md."
- **Suggested fix**: Clarify whether the table is canonical (covering `dev` as the abstraction, with `skill` as a footnote/specialization) or instance-specific (covering the exact roles in config.md). If canonical, change "pm/qa/skill/dm" to "pm/qa/dev/dm" and add a note that dev variants (like skill) inherit the dev boundary. If instance-specific, change AC1 to require reading config.md to determine active roles.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/SPEC-9925.md`
- **Line**: AC3 (line ~43)
- **Severity**: warning
- **Issue**: AC3 says "Each variant directory under `roles/<role>/<variant>/` has at least a boundaries stub file (even if it just references L2)." There are 20 variant directories. The task doesn't specify: (a) the filename (e.g., `boundaries.md`? `boundaries-stub.md`?), (b) whether the stub should be wired into the variant's compose pipeline via `additional_includes` in the variant's `includes.yml`, (c) the minimum content of the stub beyond "just references L2" (what does a valid reference look like — a wikilink? a file path? a sentence?). Without these, QA cannot deterministically verify AC3.
- **Evidence**: Variant directories exist at `references/roles/dev/{android,fullstack,ios,skill,web}/`, `references/roles/dm/{...}`, etc. Each has `includes.yml` with `base_role` and `additional_includes`. A boundaries stub file would need a known name and optionally an include directive to be discoverable at compose time. The L3 design decision says "stub boundary file even if just a pointer to L2, so the layer exists for future per-variant overrides" — but "pointer to L2" is not defined.
- **Suggested fix**: Specify: (a) the stub filename (recommend `boundaries.md`), (b) the exact format of an acceptable pointer (e.g., "See `references/sub-skills/roles/<role>/boundaries.md` for role boundaries — no variant-specific overrides exist yet."), and (c) whether the stub must be listed in the variant's `includes.yml` `additional_includes` or should be left as a passive file for future use.