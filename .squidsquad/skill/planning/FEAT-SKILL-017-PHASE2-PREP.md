# FEAT-SKILL-017 Phase 2 Discussion Prep — Externalize Agent Templates

Prepared by: subagent (discussion-prep)
Date: 2026-03-28

---

## Open Questions Analysis

### Q1: Should placeholder substitution happen at build-time or runtime?

**Category**: Behavior / Architecture (core design decision — all other questions depend on this)

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Build-time substitution (one template per role)** | Setup copies template from `references/agent-instructions.md`, substitutes all `[ROLE]` placeholders, writes result to `templates/dev-agent-fe.md`, `dev-agent-be.md`, etc. | Proven safe — same mechanism as current setup. Zero runtime risk. Agent reads final instructions with no interpretation needed. | Generates N template files for N dev agents — partially negates deduplication goal. Upgrades must regenerate all per-role templates. |
| **B. Runtime substitution (shared template + config block)** | Single `templates/dev-agent.md` with `[ROLE]` placeholders. Bootstrapper provides config values. Agent mentally applies ~6 substitutions. | True deduplication — one template for all dev agents. Cleanest architecture. Simplest upgrades (regenerate one file). | Claude may miss substitutions under context pressure. Adds cognitive load every session. Substitution errors could cause agents to read/write wrong files. |
| **C. Build-time substitution, shared when possible** | Generate one template per role. But if multiple roles share identical substituted output, share the file. Typically `fe` and `be` differ (test commands), so this usually means one per role anyway. | Safe like Option A. Shares when truly identical. Clear upgrade path. | Almost always degenerates to Option A in practice. Added complexity for marginal benefit. |

**Recommended: Option A.** Safety outweighs deduplication elegance. The research doc's own recommendation aligns with this. The number of template files (typically 2-3) is small enough that duplication is not a real maintenance burden. Upgrades regenerate templates from the single source in `agent-instructions.md`, which is straightforward.

---

### Q2: Should the template use raw `[ROLE]` placeholders or generic language?

**Category**: Behavior / Clarity

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Keep `[ROLE]` placeholders, substitute at build-time** | Templates retain current placeholder syntax. Setup substitutes them, producing concrete file paths like `be/bugs.md`. | Minimal change to existing template language. Agents see explicit, unambiguous file paths. Easy to verify correctness (grep for leftover `[`). | Requires build-time substitution (ties to Q1 Option A). Templates are not human-readable until substituted. |
| **B. Rewrite to generic language ("your role's bugs.md")** | Templates use relative references. Bootstrapper config provides concrete paths. Agent resolves "your bugs file" to the path in the config block. | No substitution needed at all. Templates are human-readable. Elegant separation of concerns. | Large rewrite of existing templates. "Your role's bugs.md" is ambiguous — agent must cross-reference config block every time. Higher risk of wrong-file navigation. More error-prone than explicit paths. |
| **C. Hybrid — generic language for prose, explicit paths in action items** | Prose sections use natural language. Step-by-step instructions use config variables like `${bugs_file}` with a legend at the top. | Readable prose. Explicit action paths. Clear variable resolution. | Invents a new variable syntax Claude must learn. More complex than either pure approach. Parsing `${var}` is not a standard Claude pattern. |

**Recommended: Option A.** The current placeholder syntax works and is well-understood. Combined with Q1 Option A (build-time substitution), agents never see placeholders at all — they get fully resolved instructions. This is the lowest-risk path with the least template rewriting.

---

### Q3: How should the bootstrapper reference the template — file path to Read, or include directive?

**Category**: Compatibility / Implementation

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Natural-language Read instruction** | Bootstrapper says: "You MUST read `.squidsquad/templates/dev-agent-be.md` NOW before proceeding. Follow those instructions exactly." | Proven pattern — root CLAUDE.md already does this successfully. No tooling changes needed. Works today. | One more indirection hop (root -> bootstrapper -> template). Adds ~1-2s latency. Could theoretically be skipped by a confused agent. |
| **B. Inline the template path as a structured field** | Bootstrapper has a YAML-like `template: .squidsquad/templates/dev-agent-be.md` field, plus a natural-language instruction to read it. Combines machine-parseable reference with human-readable directive. | Structured and readable. Easy to extract programmatically during upgrades. Still relies on proven Read pattern. | Marginally more complex bootstrapper format. No real benefit over Option A unless tooling parses the field. |
| **C. Wait for native Claude Code include mechanism** | Defer this feature until Claude Code supports `#include` or similar in CLAUDE.md files. | Would be the cleanest solution. Zero risk of skipped reads. | No timeline for this feature. Could be months or never. Blocks useful work indefinitely. |

**Recommended: Option A.** The natural-language Read instruction is battle-tested in this project. The root CLAUDE.md chain already proves this works reliably. Option B adds minor structure but no meaningful safety improvement. Option C is not viable as a blocking dependency.

---

### Q4: Should the upgrade migration be a one-time flag or auto-detected?

**Category**: Scope / Upgrade UX

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Auto-detect by content heuristic** | Check if CLAUDE.md contains `## The Ralph Loop` (inline format) or `## Template Reference` / is under 50 lines (bootstrapper format). Migrate automatically if inline detected. | Zero user action required. Works on any existing setup. No config pollution. | Could misfire on heavily customized CLAUDE.md files. Heuristic may need updating if template content changes. Edge case: user added `## The Ralph Loop` as a custom section heading. |
| **B. Explicit config flag** | Add `template_format: inline | bootstrapper` to `config.md`. Upgrade checks this flag. Migration sets it to `bootstrapper` after converting. | Unambiguous. No false positives. Easy to reason about. | Requires manual flag for existing setups (or first upgrade sets it). One more config field to maintain. |
| **C. Hybrid — auto-detect with confirmation** | Auto-detect format, but during upgrade, print what was detected and ask for confirmation before migrating. If detection is wrong, user can override. | Safe — auto-detect convenience with human verification. Handles edge cases gracefully. | Adds an interactive step to an otherwise automated upgrade. Breaks fully autonomous upgrade flow. |

**Recommended: Option A.** The heuristic (`## The Ralph Loop` presence) is robust — this heading is a core part of the template that users would not independently add. The research doc identifies this same heuristic. False positives are extremely unlikely in practice. Option B adds config overhead for a one-time migration. Option C breaks automation.

---

## Recommended Question Order

Discussion should proceed in dependency order, with the most foundational decision first and the most independent/lower-stakes decision last.

### 1. Q1 — Build-time vs runtime substitution (FIRST)
**Rationale**: This is the foundational architecture decision. Q2 (placeholder syntax) and Q3 (bootstrapper format) both depend on how substitution works. If runtime substitution is chosen, Q2 becomes critical. If build-time, Q2 is largely settled. Resolve this first.

### 2. Q2 — Placeholder syntax vs generic language (SECOND)
**Rationale**: Directly follows from Q1. If Q1 = build-time, then Q2 Option A (keep placeholders) is the natural choice and this is a quick confirmation. If Q1 = runtime, Q2 requires deeper discussion about template rewriting.

### 3. Q3 — Bootstrapper reference mechanism (THIRD)
**Rationale**: Independent of Q1/Q2 but lower stakes. The proven pattern (natural-language Read instruction) is uncontroversial. Quick decision expected.

### 4. Q4 — Upgrade migration strategy (LAST)
**Rationale**: Fully independent of Q1-Q3. Implementation detail that can be decided after the core architecture is locked. Also the least controversial — auto-detection is the clear winner.

---

## Summary of Recommendations

| Question | Recommended | Category | Expected Controversy |
|----------|-------------|----------|---------------------|
| Q1 | Build-time substitution (Option A) | Behavior/Architecture | Low — research doc already leans this way |
| Q2 | Keep `[ROLE]` placeholders (Option A) | Behavior/Clarity | Low — follows naturally from Q1 |
| Q3 | Natural-language Read instruction (Option A) | Compatibility | Very low — proven pattern |
| Q4 | Auto-detect by content heuristic (Option A) | Scope/Upgrade UX | Low — robust heuristic available |

All four recommendations align with the research document's own recommendation section. The discussion should be efficient if PM agrees with the build-time substitution direction. The main potential debate point is Q1 if someone argues strongly for runtime substitution's architectural elegance — but the safety argument is compelling.
