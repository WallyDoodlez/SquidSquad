# TEST-PLAN-13857

PRD-VAULT-V2 P1 — engine foundation (S1.1 Engine packaging, S1.2 Engine-boundary contract). Derived independently from the issue body's AC list (1-5) + PRD-VAULT-V2.md §P1 + VAULT-ARCH.md §7.5/§8.5/§6.2/§9.9 — not from skill's PR description.

Per PRD-VAULT-V2's framework-vs-prepopulation split, P1's ACs are framework-level and verified on a scratch/greenfield install, not this repo's real `.squidsquad/vault/`.

## TCs

- **TC1 (AC1)**: a non-interactive session invokes the deployed engine Skill (`vault-query.mjs`, exactly per SKILL.md's documented invocation) against a real seeded scratch vault and receives the documented top-K JSON shape (query/results/traversed/written).
- **TC2 (AC2, installer half)**: `wizard.install_vault_engine()` with `node` genuinely absent from `PATH` (not mocked) still deploys skills, seeds telemetry, and does not fail the install — `degraded: True`, `node: None`.
- **TC3 (AC2, query half)**: with `node` genuinely absent from `PATH`, an actual attempt to invoke `vault-query.mjs` fails with a clean, predictable, agent-detectable error (not a hang or opaque crash) — the signal an agent needs to write an honest "engine unavailable" receipt per SKILL.md/§9.9.
- **TC4 (AC3)**: grep-audit — independently re-derive the set of files under `references/` containing raw vault-grep snippets reachable by agents, and cross-check against the shipped `test_vault_engine_boundary_13857.py` ratchet's scanned scope and allowlist. Not just "does the test pass" — does the test's own scope actually cover every live, agent-reachable instruction source.
- **TC5 (AC4)**: `--no-write` on a real engine invocation against a real scratch vault emits zero telemetry events (confirmed via both the JSON output's own `written` field and directly inspecting the `.telemetry/` directory for absence of new shard content).
- **TC6 (AC5)**: comprehension-coverage spec for `references/skills/vault-search/SKILL.md` — authored independently by the verifier per house rule [[feedback_comprehension_tests_required]], verifying an agent correctly invokes the engine, reads top-K metadata-only output, and honors the raw-grep ban.
- **TC7**: regression test suite (`test_vault_engine_13857.py`, `test_vault_engine_boundary_13857.py`, `test_vault_engine_installer_13857.py`) all pass.
- **TC8**: full ship gate (static + integration), triaged against this session's already-established pre-existing failure cluster (#13890).
