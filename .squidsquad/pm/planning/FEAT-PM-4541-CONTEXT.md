# FEAT-PM-4541 Context — Agent-Driven Composition

## Scope

Replace mechanical concatenation with an agent-driven coherence layer. Deterministic compose stays (markers, code blocks, directives). An agent then polishes the output for coherence, deduplication, and natural flow. Verified by CQ sub-agent.

## Locked Decisions (human decided)

- **Compose mode**: Polish deterministic draft. Deterministic compose.py runs first (preserves markers, code blocks, directives, placeholders). Agent then rewrites prose for coherence — deduplicates, resolves contradictions, ensures natural flow. All exact-match content (code, markers, commands) preserved verbatim.
- **Same model**: Compose agent AND verification sub-agent are both Claude (same model that runs as the agent). The model that writes the instructions is the same model that reads them. Not a cost optimization target — quality target.
- **Trigger rules**:
  - L4 changes (PM directive, human edit) → compose immediately at end of that cycle + reboot affected agent
  - L1-L3 changes (repo owner provides these) → compose only on upgrade or fresh install
  - No auto-detection file watchers — explicit triggers only
- **CQ failure handling**: Self-correct up to 2 retries with specific gap feedback. If still failing after 2 retries → flag human for help. Never silently deploy broken/incomplete output.
- **CQ source**: Dynamically generated from layer source headings and key items. If L4 adds a new directive, a CQ for it is auto-generated. Always up-to-date, no manual maintenance.
- **Consistency**: Accept wording variance between composes. Verify INTENT/behavior equivalence via CQs, not exact text match. Same inputs may produce different phrasing — that's fine as long as behavioral meaning is preserved.

## Architecture

```
Layer sources (L1+L2+L3+L4)
    ↓
Deterministic compose (markers, code, directives, placeholders — exact)
    ↓
Coherence agent (Claude — rewrites prose, deduplicates, resolves contradictions)
    ↓
CQ verification agent (Claude — fresh context, quizzes the output)
    ↓ pass
Deploy (write to .squidsquad/<role>/instructions.md + SOUL.md)
    ↓ fail (up to 2 retries)
Re-prompt with specific gaps → retry
    ↓ still fail
Flag human for help
```

## Dev Discretion

- Compose prompt engineering (what instructions the coherence agent gets)
- How dynamic CQs are extracted from source files (headings? key phrases? markers?)
- Whether compose runs as inline code or spawns a subagent
- How "flag human for help" manifests (tracker issue? PM comment? file sentinel?)
- Token budget optimization (can we pass only the prose sections to the coherence agent, not the code blocks?)
- Whether SOUL.md and instructions.md are composed in one call or two

## Side Effect Mitigations (required)

- Deterministic compose must remain as fallback (no API key or config disabled = concatenation only)
- Gate behind config.md flag: `Agent Compose: no` (default off, enable progressively)
- Code blocks, bash commands, file paths, markers must NEVER be rewritten by the coherence agent — preserved verbatim
- Compose must not block setup/upgrade — if API fails, fall back to deterministic
- Existing compose.py deploy-all must continue working for users without the feature enabled

## Out of Scope

- Changing layer source file format
- Auto-detection file watchers (explicit triggers only)
- Using different models for compose vs verification (same model, locked)
- Cost optimization of compose calls (quality target, not cost target)
