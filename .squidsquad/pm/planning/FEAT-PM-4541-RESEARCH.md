# FEAT-PM-4541 Research — Replace Deterministic compose.py with Agent-Driven Composition

## Summary

Current compose.py does more than concatenate — it resolves directives, handles manifests, substitutes placeholders, manages SOUL.md layer markers, and generates boot scripts. The "concatenation is incoherent" problem is real but narrowly scoped: the output is structurally correct but reads as 4 appended chunks with no prose transitions. An agent compose pass can solve the coherence problem while keeping all the mechanical infrastructure intact. The design is feasible. Key constraint: the full PM input stack (L1+L2+sub-skills) is ~98KB / ~25K tokens — this fits a single call but is expensive. DeepSeek is a viable compose model; verification must stay Claude (CLAUDE_LOCKED_TASKS).

**Recommendation**: Viable. Design compose agent as a coherence-rewriting layer that runs after the deterministic compose, not as a replacement for it. Keep all mechanical logic. The agent rewrites the flat output into a coherent document; a CQ verifier then checks completeness. Fallback to deterministic output when no API key is available.

---

## 1. Current compose.py Scope — What It Actually Does

### Mechanics (beyond concatenation)

`compose.py` has these distinct responsibilities:

**Layer assembly** (`_assemble_claude`, `_assemble_soul`): Reads L1/L2/L3 instructions.md files and concatenates them in order. This is the "4 chunks stapled together" problem.

**Directive resolution** (`_resolve_includes`, `_resolve_includes_with_manifest`): Parses `{{include: path}}`, `{{runtime: path}}`, `{{capability: id}}` directives. Wraps each included sub-skill in `<!-- sub-skill: name -->` / `<!-- /sub-skill: name -->` markers. Manifest-driven: `includes.yml` per role controls which sub-skills are included, in what order, and allows variant substitution (e.g. `vault-protocol-slim` instead of `vault-protocol`).

**Placeholder substitution** (`_substitute_placeholders`): Replaces `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`, `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]` — some read live from `config.md`.

**SOUL.md layer management** (`_assemble_soul`, `upgrade_soul`, `extract_project_adaptation`): Embeds `<!-- layer: base -->` / `<!-- /layer: base -->` markers so `upgrade_soul` can surgically replace the L1 base portion without clobbering the role personality or Project Adaptation section. This is a critical preservation mechanism.

**Variant resolution** (`_resolve_variant`): Maps `dev-skill` → `("dev", "skill")`, navigates nested role directories.

**Boot script generation** (`boot_role`, `boot_all`): Reads `references/templates/start-role.sh` and `.ps1`, substitutes `{{ROLE}}`, writes to `.squidsquad/start-<role>.sh/.ps1`.

**Local config generation** (`generate_local_config`): Writes `.squidsquad/.local-config` with clone paths for all agents.

**Full deploy pipeline** (`deploy_role`): Wires together compose + substitute + write CLAUDE.md + conditionally write SOUL.md. This is what wizard.py and PM's `deploy-all` call.

### What STAYS deterministic regardless of new design

- Manifest validation (missing sub-skill files = hard error, not LLM hallucination)
- Placeholder substitution (`[ROLE]`, `[INTERVAL]`, etc.) — these must be exact strings from config
- `<!-- sub-skill: name -->` markers — upgrade_soul and future tooling depend on them
- SOUL.md layer markers (`<!-- layer: base -->`) — critical for surgical upgrades
- Boot script generation (purely templated, no coherence problem)
- `.local-config` generation (structured data, not prose)
- `upgrade_soul` (preserves Project Adaptation section — must remain deterministic)

### What the agent replaces

- The prose flow of the assembled L1+L2+L3 instructions (the "4 chunks stapled" problem)
- The transition sentences between sub-skill sections (currently: none)
- Deduplication of redundant content across layers (e.g. L1 says "use atomic writes", L4 project says it again)
- Section ordering that currently follows manifest order regardless of logical flow

---

## 2. Compose Agent Prompt Design

The compose agent should receive the **already-resolved deterministic output** as its input, not the raw source files. This is cleaner than reading 4 layers independently and avoids re-implementing directive resolution.

### Input to compose agent

- The deterministic flat output from `compose_role()` (CLAUDE.md with all sub-skills inlined and markers present)
- The agent's role name and identity context
- A constraint document specifying what must be preserved verbatim

### Compose agent prompt structure

```
You are a document coherence editor for SquidSquad agent instructions.

## Task
Rewrite the following agent instruction document to be coherent and readable.
The document was mechanically assembled from multiple source files.

## Hard constraints (MUST preserve exactly)
- Every <!-- sub-skill: name --> and <!-- /sub-skill: name --> marker, in its current position
- Every placeholder already substituted: role name, interval, active agents
- Every code block (bash commands, JSON, templates) — verbatim
- All SOUL layer markers (<!-- layer: base --> / <!-- /layer: base -->)
- All behavioral rules, commands, and procedural steps — none may be omitted or softened

## What you may change
- Transition sentences between sections
- Section intro paragraphs (add 1-2 sentences of context)
- Remove exact duplicate paragraphs that appear in multiple layers
- Reorder sub-sections within a section for logical flow (do not move sub-skill blocks)
- Add a brief role overview at the top if missing

## Input document
[FULL DETERMINISTIC OUTPUT]

## Output
Write the rewritten document in full. Do not truncate. Do not add markdown fences.
```

### Key constraint: sub-skill markers must stay in place

The `<!-- sub-skill -->` markers are load-bearing — they are used by `upgrade_soul` and potentially by future tooling to identify section boundaries. The compose agent must not remove or move them.

---

## 3. Token Budget Analysis

### PM agent (largest case)

| Source | Size |
|--------|------|
| L1 base instructions.md | 1,104 bytes (~280 tokens) |
| L2 pm/instructions.md | 7,743 bytes (~1,940 tokens) |
| L2 pm/SOUL.md | 7,372 bytes (~1,840 tokens) |
| L1 SOUL.md | 1,716 bytes (~430 tokens) |
| L4 project sub-skills (all) | 23,105 bytes (~5,780 tokens) |
| L2/L3 sub-skills (inlined, PM manifest) | ~58,000 bytes (~14,500 tokens) |
| **Total input (deployed CLAUDE.md)** | **98,052 bytes (~24,500 tokens)** |

Estimated output (rewritten, roughly same length): ~24,000 tokens.

**Total per compose call: ~48,500 tokens** (input + output combined).

At DeepSeek pricing this is very cheap. At Claude Sonnet pricing (~$3/Mtok in, ~$15/Mtok out) it's ~$0.43 per compose call. For skill agent (~54KB): ~$0.24 per call.

Compose only fires on change (setup, upgrade, L4 edit, PM directive push) — not every cycle. Total cost is low.

**Conclusion: Feasible for one call. No chunking needed.**

---

## 4. Model Routing

### Current routing config (`.squidsquad/config.md`)

```
- Research Model: deepseek-v4-pro
- Comprehension Model: claude   (locked — cannot be overridden)
- QA Execution Model: claude    (locked — cannot be overridden)
- Default Model: claude
```

### How model_router.py works

`get_model_for_task(task_type)` checks `CLAUDE_LOCKED_TASKS = {"comprehension", "qa-execution"}` first. If the task type is in this set, returns `"claude"` regardless of config. Otherwise reads `## Model Routing` section from `config.md`.

The router maps task types to config keys via `key_map`. A new `compose` task type would need:
1. A new entry in `key_map`: `"compose": "compose-model"`
2. A new config line: `- **Compose Model**: deepseek-v4-pro` (or `claude`)
3. The compose task type must NOT be added to `CLAUDE_LOCKED_TASKS` — we want it routable to DeepSeek

### Verification agent model

Verification (CQ runner) uses the existing `run_comprehension_test.py` pipeline which calls `claude` CLI directly — it does not go through model_router. It is inherently Claude-only. This is correct: the verifier needs the full tool suite and judgment quality of Claude.

### Recommended routing

- **Compose agent**: `deepseek-v4-pro` (or configured `compose-model`) — cheap, large context, sufficient for rewriting
- **Verify agent**: `claude` via existing `run_comprehension_test.py` pipeline
- **Fallback**: If compose-model not configured or API key missing → skip compose agent, use deterministic output as-is

---

## 5. CQ Design for Compose Verification

Compose CQs differ from feature CQs. They verify the output document, not implementation behavior. The verifier reads ONLY the composed output file and answers questions about its completeness.

### CQ spec structure (JSON)

```json
{
  "files": [".squidsquad/<role>/CLAUDE.md"],
  "questions": [
    {
      "id": "soul-marker",
      "question": "Does the document contain a {{runtime: souls/<role>}} or equivalent Soul section that directs the agent to read SOUL.md?",
      "expected": "Yes — a Soul section or runtime directive must be present near the top"
    },
    {
      "id": "tracker-protocol",
      "question": "Does the document contain tracker protocol instructions covering gh CLI usage, status transitions, and issue creation?",
      "expected": "Yes — full tracker protocol must be present, covering list-tasks, create-issue, transition commands"
    },
    {
      "id": "ralph-loop",
      "question": "Does the document define the Ralph Loop with numbered cycle steps?",
      "expected": "Yes — the Ralph Loop with all cycle steps must be present"
    },
    {
      "id": "role-name",
      "question": "Is the role name [ROLE] substituted throughout (no literal '[ROLE]' placeholder remaining)?",
      "expected": "No literal [ROLE] placeholders — all substituted with the actual role name"
    },
    {
      "id": "sub-skill-markers",
      "question": "Are <!-- sub-skill: --> and <!-- /sub-skill: --> markers present and paired?",
      "expected": "Yes — every open marker has a matching close marker"
    },
    {
      "id": "no-truncation",
      "question": "Does the document appear complete, not ending mid-section or mid-sentence?",
      "expected": "Document ends at a natural boundary, not truncated"
    },
    {
      "id": "prohibitions",
      "question": "Does the document contain a Prohibitions or similar section listing forbidden agent behaviors?",
      "expected": "Yes — prohibitions or hard constraints section must be present"
    }
  ]
}
```

### What makes compose CQs different from feature CQs

- Feature CQs ask "does the agent know how to do X?" — they test behavior instructions
- Compose CQs ask "is X present in the document?" — they test document completeness
- The eval agent can answer compose CQs without running anything — purely document reading
- Compose CQs must be role-specific (PM has different required sections than skill)

### Per-role required section checklist (generates CQ questions)

The CQ spec should be generated from a required-sections manifest per role, not hardcoded. This manifest lists: section name, presence pattern (string to grep), required/optional.

---

## 6. Failure and Retry Loop

### Proposed retry protocol

```
1. Run compose agent → writes CLAUDE.md.candidate
2. Run CQ verifier against CLAUDE.md.candidate
3. If all CQs pass → mv CLAUDE.md.candidate CLAUDE.md, write cache hash
4. If CQs fail:
   a. Extract failed question IDs and reasons
   b. Build feedback: "Q-tracker-protocol FAILED: answer did not contain transition commands"
   c. Re-prompt compose agent with: original input + failed sections from deterministic output + "You omitted the following sections. Include them verbatim: [list]"
   d. Retry once
5. If retry still fails → fall back to deterministic output, log warning
```

### Max retries: 1

A second compose attempt with explicit "you must include these sections verbatim" almost always succeeds. If it doesn't, the deterministic output is safe. Do not loop more than twice — compose failures that need 3+ retries indicate a prompt design problem, not a transient issue.

### Feedback format for recompose prompt

```
COMPOSE VERIFICATION FAILED for [role].
The following required sections were missing or incomplete:

MISSING: tracker-protocol
  Required: Full tracker protocol with gh CLI commands, status transitions, issue creation
  Include this section verbatim from the source:
  [paste the tracker-protocol sub-skill content]

MISSING: prohibitions
  Required: Prohibitions section with forbidden behaviors
  Include this section verbatim from the source:
  [paste the prohibitions sub-skill content]

Rewrite the document again with these sections present.
```

---

## 7. Backward Compatibility

### Fallback to deterministic compose

The new agent compose is a post-processing step applied to the deterministic output. The fallback is trivially: skip the post-processing step and use the deterministic output as-is. Trigger conditions for fallback:

- `compose-model` config key is missing or set to `claude` with no external provider configured
- External model API key not present
- API call fails or times out
- CQ verification fails after 1 retry

The deterministic output is always valid — just less coherent. The fallback is not a degraded state, it's the current state.

### Migration path

No breaking changes to wizard.py, upgrade scripts, or PM's `deploy-all` step. The compose agent is called as an optional final step inside `deploy_role()`, gated by config.

### Config flag

```
## Agent Compose

- **Enabled**: no          (default: disabled until stable)
- **Compose Model**: claude  (set to deepseek-v4-pro to use external model)
```

---

## 8. What Stays Deterministic

The following must never be delegated to an agent:

| Responsibility | Why deterministic |
|---------------|-------------------|
| Manifest validation (includes.yml) | Missing sub-skill file = hard error, must exit 1 |
| Placeholder substitution ([ROLE], [INTERVAL], etc.) | Must match config values exactly |
| `<!-- sub-skill -->` marker embedding | Position must match source section boundaries |
| `<!-- layer: base -->` SOUL markers | upgrade_soul depends on exact position |
| `upgrade_soul` base re-render | Must preserve Project Adaptation section exactly |
| Boot script generation | Templated, no prose |
| `.local-config` generation | Structured data |
| `extract_project_adaptation` | String extraction from known marker positions |

The compose agent only touches: transitions, section intros, deduplication, and light reordering within sections. Code blocks and commands are fully protected by the "preserve verbatim" constraint.

---

## 9. Integration with Existing Triggers

### Setup (wizard.py)

Current: `wizard.py` calls `deploy_role(compose_name, target_root, output_name)`.

New: After `deploy_role()` writes CLAUDE.md, optionally call `compose_agent(role_name, output_path)` which:
1. Reads the deterministic CLAUDE.md
2. Calls model_router with task_type="compose"
3. Writes candidate, runs CQ, promotes or falls back
4. All within the existing setup flow (blocks, shows progress)

If compose fails during setup, wizard logs a warning and proceeds with deterministic output — setup is not blocked.

### Upgrade (`squidsquad-upgrade` skill)

Current: Upgrade runs `compose.py deploy-all` (confirmed in PM's post-merge-recompose sub-skill).

New: After `compose.py deploy-all` completes, optionally run compose agent for each changed role. This should be parallelized (one subagent per role).

### PM directive push (post-merge-recompose)

Current: PM runs `python references/scripts/compose.py deploy-all` on branch merge touching `references/`.

New: Same trigger, but PM also calls compose agent. PM's `post-merge-recompose` sub-skill would need a new step:

```bash
# After deploy-all succeeds:
python references/scripts/compose_agent.py deploy-all  # new script or flag
```

Alternatively: PM calls `compose.py deploy-all` (unchanged), then spawns a subagent to run compose_agent for each role in parallel.

---

## 10. Implementation Approach

### New script: `references/scripts/compose_agent.py`

Does NOT replace compose.py. Wraps it:

```python
def compose_with_agent(role_name, target_root=None):
    """Deploy role deterministically, then optionally run agent coherence pass."""
    # Step 1: deterministic compose (unchanged)
    output_path = deploy_role(role_name, target_root)

    # Step 2: agent compose (optional, gated by config)
    if not _agent_compose_enabled():
        return output_path

    deterministic_content = output_path.read_text()
    candidate = _run_compose_agent(role_name, deterministic_content)

    if candidate and _verify_compose(candidate, role_name):
        output_path.write_text(candidate)
        _write_compose_cache(role_name, deterministic_content)
    else:
        # Fallback: log and keep deterministic output
        print(f"[compose_agent] Coherence pass failed for {role_name}, using deterministic output")

    return output_path
```

### Cache strategy

Hash the deterministic compose output. If hash unchanged since last successful agent compose, skip the agent pass. Cache lives in `.squidsquad/diagnostics/compose-cache.json`.

### CQ spec location

Per-role specs: `tests/comprehension/compose-<role>.json`
Generated at setup time from role's includes manifest + required-sections template.

---

## Key Risks

1. **Token cost during upgrade**: If deploy-all runs for 5 agents and each is ~48K tokens in/out, one upgrade cycle costs ~240K tokens externally. At DeepSeek pricing this is negligible; at Claude pricing this would be ~$1.20/upgrade. Acceptable.

2. **Compose agent truncates output**: Mitigation — the CQ "no-truncation" question catches this. The no-truncation check should also verify output length is within 10% of input length.

3. **Sub-skill marker drift**: If the agent moves a `<!-- sub-skill -->` marker, upgrade_soul may break. Mitigation — add a CQ that checks markers are present and paired; add a post-compose script that diffs marker positions between deterministic and agent outputs and rejects if any markers moved.

4. **Recompose feedback loop in PM**: PM's post-merge-recompose already runs synchronously. Adding compose agent adds latency (~30-60s per role for external model). PM should run compose in a background subagent and not block on it.

5. **Prompt injection via sub-skill content**: Sub-skill files are authored by the project team but could contain adversarial content. Mitigation — compose agent only has Read tool access to the pre-composed file, not arbitrary file access. The input is already post-resolution.
