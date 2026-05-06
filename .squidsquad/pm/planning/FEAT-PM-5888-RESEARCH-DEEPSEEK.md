Now I have a complete picture. Let me compile the audit.

---

# FEAT-PM-5888-AUDIT Research — Routing ALL Composition Through /squidsquad-compose Skill

## Summary

This audit re-examines the proposal that **wizard.py and add_role.py stop calling compose.py directly and instead delegate ALL composition to a `/squidsquad-compose` Claude Code slash command**. The previous FEAT-PM-5888 research (`.squidsquad/pm/planning/FEAT-PM-5888-RESEARCH.md`) correctly concluded that wizard.py and add_role.py should **not** be forced through the skill wrapper — they use compose.py's Python API and subprocess interface respectively, which is intentional and necessary. This audit confirms that conclusion and identifies **four hard blockers** that would break if wizard.py/add_role.py were forced through a slash command: a bootstrap deadlock during first-ever setup, broken CI/headless support, circular dependency on LLM context that doesn't exist during setup, and broken test suites that depend on direct Python imports.

**Recommendation**: Narrow the scope to what the original #5888 research described: create `/squidsquad-compose` as a Claude Code slash command for **LLM-orchestrated flows only** (upgrade, post-merge recompose, manual recompose requests). wizard.py and add_role.py must continue to call compose.py directly. The mechanical (Python) and creative (LLM) paths are complementary, not mutually exclusive.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is the driver for the compose skill wrapper. #5557 "Composed CLAUDE.md edit prohibition + compose.py guard" establishes that compose.py is the authoritative regeneration path.
- **Related decisions**: [[decision-sub-skill-architecture]] — composition is build-time concatenation from `references/sub-skills/`. The proposed skill is an orchestrator wrapping compose.py, not a replacement for the composition engine. [[decision-local-config-priority]] — `generate_local_config()` in compose.py writes `.local-config`; wizard.py imports this function directly (line 1049) and must continue to do so.
- **Related patterns**: [[pattern-windows-utf8-subprocess]] — subprocess calls (including those in add_role.py → compose.py) need `encoding="utf-8"` on Windows. Any new subprocess invocation path must follow this pattern. [[learning-atomic-migration-strategy]] — infrastructure changes that affect running agents must ship atomically.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — compose.py's deterministic output is the direct/mechanical path; a skill wrapper adds indirection. The Python API path (wizard.py → compose.deploy_role) should be preserved as the most direct verification method.
- **Related learnings**: [[learning-atomic-migration-strategy]] — atomic delivery of infrastructure changes prevents coordination breakage.

## Impact Analysis

- **Files touched** (if proposal accepted as stated — ALL paths through skill):
  - `references/scripts/wizard.py` lines 880-887, 1049, 1059 — would need to replace `from compose import deploy_role` with subprocess call to `claude` triggering `/squidsquad-compose`
  - `references/scripts/add_role.py` lines 263-266, 270-273 — would need to replace `compose.py deploy` subprocess with `claude` subprocess triggering `/squidsquad-compose`
  - `references/scripts/compose.py` — `deploy_role()`, `generate_local_config()`, `boot_role()` would need to remain importable but the skill must wrap them
  - `tests/test_wizard.py` — every test that mocks compose (lines 1701, 1726, 1753) would need rewriting
  - `tests/test_compose.py` — would need to account for skill invocation vs. direct function call
  - **NEW**: `.claude/commands/squidsquad-compose.md` — the slash command definition
  - `.claude/commands/squidsquad-upgrade.md` — already stale (describes pre-compose.py parallel-subagent flow), must be rewritten regardless

- **Behavior changes**:
  1. First-ever setup would fail — wizard.py scaffolds `.claude/commands/` and can't invoke a command it hasn't created yet
  2. CI pipelines (`wizard.py setup-yes`) would break requiring `claude` CLI and Anthropic API key
  3. `add_role.py` would become ~10-30x slower (LLM invocation vs. subprocess)
  4. Test suites would lose the ability to test composition deterministically
  5. Upgrade flow would route through the skill (this part is fine)

- **Dependencies**:
  - `claude` CLI (must be on PATH for skill invocation)
  - Anthropic API key (must be configured for the Claude session)
  - `.claude/commands/squidsquad-compose.md` (must exist before wizard.py can run — circular)
  - compose.py (unchanged engine)

## Side Effects

- **Risk 1: Bootstrap deadlock during first-ever setup** — Severity: **CRITICAL** — wizard.py's `scaffold_install` (line 831) is the function that creates the `.claude/commands/` directory and writes the initial agent CLAUDE.md files. If it must invoke `/squidsquad-compose` to compose, but `/squidsquad-compose` doesn't exist yet because the wizard hasn't scaffolded it, setup is impossible. The `squidsquad-setup.md` slash command (`.claude/commands/squidsquad-setup.md`) is a one-liner that delegates to wizard.py — so even the setup skill can't help here. Mitigation: wizard.py MUST retain its direct Python import of `compose.deploy_role`.

- **Risk 2: CI/headless environments broken** — Severity: **HIGH** — `wizard.py setup-yes` (line 2124) and `compose.py deploy-all` are used in CI, test suites, and dogfooding. These require no LLM. Forcing them through a Claude Code slash command would require: (a) `claude` CLI installed, (b) valid Anthropic API key, (c) internet access, (d) 10-30s+ latency per invocation, (e) non-deterministic output (the LLM might change wording). Mitigation: keep the deterministic Python path; `/squidsquad-compose` is for LLM-orchestrated contexts only.

- **Risk 3: add_role.py becomes expensive and fragile** — Severity: **HIGH** — `add_role.py` (line 263) calls `compose.py deploy <role>` as a subprocess that completes in milliseconds. Routing through a Claude Code slash command would spin up a Claude session, consume API tokens, and add 10-30s latency per role. The `claude` CLI can also fail (network errors, auth issues, rate limits) for what is currently a deterministic file-copy operation. Mitigation: add_role.py must continue calling compose.py directly.

- **Risk 4: Recursive agent invocation** — Severity: **MEDIUM** — If `/squidsquad-compose` is invoked from within a Claude session (e.g., during upgrade), and compose.py's `agent_compose()` (line 550-637) is enabled, compose.py itself spawns a `claude -p` subprocess to polish output. This means Claude calling compose.py calling Claude — a potential recursive deadlock if the inner Claude call times out or consumes the outer session's context. The `agent-compose` config flag (line 66 of config.py) gates this, but the skill wrapper must detect when it's already inside Claude and disable `agent_compose`. Mitigation: the `/squidsquad-compose` skill should set `agent-compose: no` before invoking compose.py and restore it afterward.

- **Risk 5: Stale `.claude/commands/squidsquad-upgrade.md`** — Severity: **MEDIUM** — This file (`.claude/commands/squidsquad-upgrade.md` lines 19-31) still describes the obsolete parallel-subagent flow. If an agent reads this file instead of SKILL.md's updated upgrade section (line 329), it will attempt the wrong workflow. This was also flagged in the previous #5888 research. Mitigation: fix `squidsquad-upgrade.md` in the same atomic change as the skill wrapper creation.

## Edge Cases

- **First-ever setup on a machine with no `claude` CLI**: wizard.py currently only requires `gh` and `git`. Adding a `claude` dependency for composition would make setup impossible on machines that only have `gh` + `git`. The wizard's `check_gh()` function (line 107) explicitly only checks for `gh` — there is no `claude` check anywhere in wizard.py. **Handle by**: wizard.py must not require `claude`.

- **setup-yes in CI with no Anthropic API key**: CI runners have `gh` tokens but not Anthropic keys. `setup-yes` (line 2124) calls `scaffold_install` which calls `compose.deploy_role` — all deterministic. If this path required an LLM, every CI run would fail. **Handle by**: keep the deterministic path; `/squidsquad-compose` is for interactive/LM-driven use only.

- **add_role.py invoked from a non-Claude terminal**: Users can run `python references/scripts/add_role.py qa` from a regular terminal without Claude running. If add_role.py tried to invoke a Claude Code slash command, it would fail because there's no Claude session to receive it. **Handle by**: add_role.py must continue using subprocess to call compose.py.

- **Tests that mock compose.py**: `test_wizard.py` patches `sys.modules["compose"]` with a MagicMock (lines 1701-1704, 1726-1729, 1753-1756) to isolate wizard from compose. If wizard called a slash command instead of importing compose, these tests would break — they'd need to mock `subprocess.run` for `claude` invocations, which is inherently harder to verify. **Handle by**: wizard.py retains direct import.

- **agent_compose already provides LLM validation**: compose.py's `agent_compose()` function (line 550) is a carefully designed LLM polish step with code-block preservation, marker verification, and graceful fallback (returns deterministic output on any failure). It's gated by the `agent-compose` config flag. This is the "creative validation" the proposal wants — it already exists, opt-in, with safeguards. The `/squidsquad-compose` skill can simply call `compose.py deploy-all` with `agent-compose: yes` in config to achieve both mechanical and creative validation.

## Integration Risks

- **Dual-use pattern preservation**: compose.py serves as both a Python library (imported by wizard.py) and a CLI tool (invoked by add_role.py, SKILL.md prose). The skill wrapper adds a third interface: a Claude Code slash command. These three interfaces must coexist — removing the Python API path would break the wizard. The previous #5888 research identified this as a pattern worth vaulting.

- **SKILL.md vs slash command sync drift**: The upgrade flow is described in two places: SKILL.md (line 329, orchestrator-driven) and `.claude/commands/squidsquad-upgrade.md` (line 19, stale parallel-subagent). Adding `/squidsquad-compose` creates a third place that could drift. The vault learning candidate from #5888 — "slash command files can drift from SKILL.md" — is confirmed and relevant.

- **#5868 event contracts**: The compose skill wrapper needs extension points for validation hooks. compose.py's `deploy_role()` already has a clear pipeline (compose → substitute → agent_compose → write → guard check). The skill wrapper should wrap this rather than duplicate it.

## Upgrade & Migration

- **New config values**: none required for the skill wrapper itself. The existing `agent-compose` flag (config.py line 66) controls whether the LLM polish pass runs; the skill wrapper should respect but not require it.
- **New files**: `.claude/commands/squidsquad-compose.md` (slash command definition)
- **Template changes**:
  - `SKILL.md` — Upgrade Instructions Step 3 (line 347) changes from inline `compose.py deploy-all` to skill invocation
  - `.claude/commands/squidsquad-upgrade.md` — full rewrite required (currently stale)
  - `references/sub-skills/roles/pm/post-merge-recompose.md` line 25 — change inline `compose.py deploy-all` to skill invocation
  - `references/sub-skills/common/prohibitions.md` line 14 — update to mention both `compose.py deploy` and `/squidsquad-compose` as regeneration methods
  - `references/sub-skills/roles/pm/prohibitions.md` line 13 — same update
  - `references/sub-skills/roles/dm/prohibitions.md` line 13 — same update
  - `references/sub-skills/roles/qa/prohibitions.md` line 13 — same update
- **Upgrade steps**:
  1. New slash command arrives via `git pull` into `.claude/commands/`
  2. Agent runs `/squidsquad-upgrade` which reads updated SKILL.md and invokes `/squidsquad-compose`
  3. No config changes, no data migration, no schema bump
  4. Stale `squidsquad-upgrade.md` must be fixed atomically (see Risk 5)
- **Graceful degradation**: If `/squidsquad-compose` is unavailable (old install), the skill wrapper should fall back to `python references/scripts/compose.py deploy-all` and warn. The wrappers in SKILL.md prose can document both paths.

## Open Questions

- **Q1**: Should `/squidsquad-compose` enable `agent-compose` by default when invoked as a slash command? — **Why**: The proposal mentions "both mechanical and creative (LLM) validation." The creative pass already exists as `agent_compose()` in compose.py. Enabling it from the skill means every recompose through the skill gets LLM polish. But it adds latency, cost, and the recursive-invocation risk. Should it be opt-in per invocation (e.g., `/squidsquad-compose --polish`)?
- **Q2**: Should the skill wrapper handle the case where `claude` CLI is unavailable and fall back to direct `compose.py`? — **Why**: If the skill is invoked in a context where Claude isn't available (headless CI, or a user running skill prose manually), graceful fallback prevents breakage. This directly affects the "CI/headless" concern.
- **Q3**: Does the skill wrapper run `deploy-all` or allow per-role deployment? — **Why**: `add_role.py` deploys a single role (`compose.py deploy <role>`). If add_role.py keeps its direct subprocess (recommended), the skill only needs `deploy-all`. But if the skill is meant to be the universal entry point, it needs to support single-role compose too.
- **Q4**: How should the recursive agent invocation risk be mitigated at the skill level? — **Why**: If `/squidsquad-compose` runs inside a Claude session and compose.py's `agent_compose()` spawns another Claude, the inner call could consume context tokens, timeout, or deadlock. Options: the skill could set `agent-compose: no` before calling compose.py, or compose.py could detect it's already inside Claude (env var check). The current `agent_compose()` already has a 120s timeout and graceful fallback, but the outer Claude session might still be affected.

## Recommendation

**Needs rethinking — scope must be narrowed.** The proposal to route ALL composition paths through `/squidsquad-compose` cannot be implemented as stated. wizard.py and add_role.py MUST continue to call compose.py directly. The correct architecture is:

1. **Keep compose.py as the mechanical engine** with its existing Python API (`deploy_role()`, `generate_local_config()`, `boot_role()`) and CLI interface (`deploy`, `deploy-all`, `boot`)
2. **Create `/squidsquad-compose` as a Claude Code slash command** for LLM-orchestrated contexts: upgrade, post-merge recompose, and manual "recompose my agents" requests
3. **wizard.py continues to import compose.py directly** — it is explicitly designed as a mechanical script ("testable without talking to an LLM")
4. **add_role.py continues to call compose.py as a subprocess** — it runs in non-Claude terminals and CI
5. **The skill wrapper optionally enables `agent-compose`** for LLM polish when the context supports it (inside a Claude session, not in CI)

This preserves the dual-use pattern identified in the original #5888 research, avoids the bootstrap deadlock, keeps CI working, and maintains testability. The new `/squidsquad-compose` skill provides the single LLM-orchestrated entry point for future #5868 validation hooks without breaking any existing path.

## Vault Candidates

- **Type**: decision — "compose.py dual-use pattern: Python API (wizard import) + CLI (agent invocation) + skill wrapper (Claude Code slash command) are three intentionally distinct interfaces" — **Why**: The original #5888 research identified this as a pattern worth vaulting. This audit confirms it's architecturally necessary, not just convenient. Three callers with three different constraints (setup/no-LLM, CI/deterministic, interactive/LLM-orchestrated) require three interfaces. Formalize to prevent future proposals from collapsing them.
- **Type**: learning — "Bootstrap deadlock: infrastructure scaffolding tools cannot depend on infrastructure they haven't scaffolded yet" — **Why**: wizard.py scaffolds `.claude/commands/` and `.squidsquad/`. Any proposal that makes wizard.py depend on artifacts that wizard.py itself creates is a bootstrap deadlock. Applies to any future "make the setup script use SquidSquad skills" proposals.
- **Type**: learning — "Slash command files can drift from SKILL.md when both describe the same workflow" — **Why**: `.claude/commands/squidsquad-upgrade.md` still describes the pre-compose.py parallel-subagent flow while SKILL.md (line 329) has been updated. This is a process gap with no sync mechanism. Already flagged in #5888 research but not yet vaulted.
- **Type**: pattern — "Graceful fallback: LLM-enabled paths must degrade to deterministic equivalents when LLM is unavailable" — **Why**: `agent_compose()` in compose.py (line 634-637) is an exemplar: if Claude subprocess fails, times out, or is not installed, return the deterministic output unchanged and emit a warning. Every new LLM-dependent path should follow this pattern. The `/squidsquad-compose` skill wrapper should apply the same pattern: if `claude` isn't available, fall back to `python compose.py deploy-all`.
- **Type**: learning — "The `setup-yes` path proves CI compatibility must be designed in, not bolted on" — **Why**: `wizard.py setup-yes` (line 2124) demonstrates a fully non-interactive, LLM-free setup path. Any proposal that would break this path reveals a misunderstanding of the system's operational requirements. This applies to all future "make X use an LLM" proposals — always check whether X is used in CI/headless contexts first.