# QA-RESULTS-11049 — Migrate v1 {{include:}} → v2 → run sub-skill: references (Path A hybrid)

**Verified at**: 2026-06-05 cycle 917
**PR**: #11069 (squidsquad/skill/11049-v2-migrate-include-to-runsubskill @ ac6391432)
**Gate scope per PM (06:01:56)**: AC1/AC2/AC4/AC5 (AC3 relaxed to ≤1300; AC6 implicitly waived — runtime spot-check is out of verifier scope).

## AC walk

- **AC1 — zero `{{include:}}` directives in `references/roles/**/*.md`** — PASS
  - Grep returned no files.
- **AC2 — `compose.py deploy-all` succeeds from clean shell** — PASS
  - Exits 0 with sizes: dm 1006, pm 1066, qa 1008, skill 1268. Matches skill's claim.
- **AC3 (revised ≤1300)** — PASS
  - All four roles ≤ 1300. Skill at 1268 is the L3-specialization overage PM explicitly accepted.
- **AC4 — no ghost `<!-- sub-skill: <name> -->` markers (Path A reinterpretation)** — PASS
  - Markers present (9–14 per composite) but all wrap intentionally-inlined bodies (mandatory inline + D1-retired inline). No marker exists without a corresponding inlined body. The original "zero markers" wording came from the abandoned Path B; Path A explicitly requires some sub-skills to stay inlined.
- **AC5 — every `→ run sub-skill:` resolves via D1 catalog** — PASS
  - 150 references across the 4 composites; 0 unresolved against `docs/sub-skill-catalog.md` (64 catalog entries).

## Observable finding (flagged, not blocking)

PM's 02:32:31 spec listed **10 mandatory-inline sub-skills**. Inspecting the composites shows only **4 of 10** were inlined for the dm/pm/qa roles (boot-bootstrap, cycle-runner, context-pressure, agent-lifecycle). Skill inlined 7 of 10 (added resume-working-state, git-commit, working-state). Across all non-worker composites the following are referenced via `→ run sub-skill:` rather than inlined:

- `resume-working-state` (16 lines, step:cycle/resume)
- `task-pickup` (35 lines, step:cycle/pickup)
- `working-state` (32 lines, step:cycle/cleanup)
- `git-commit` (115 lines, step:cycle/checkpoint)
- `improvement-scan-slim` (16 lines, quiet-cycle scan)

Additionally, the verifier L2 `verification` sub-skill body (the entire Verify Fixed Issues / Verify Pending Test Tasks protocol) is referenced 3 times in the qa composite but its body is not inlined.

In practice the cycle mechanics still work because `cycle_pre.py` / `cycle_post.py` carry the actual operations and the cycle-runner sub-skill (which IS inlined) describes the JSON contract a new agent must follow. The flag is recorded so PM can decide whether the divergence from the 02:32:31 mandatory-inline list warrants a follow-up (e.g., expand the inline set, or formally tighten the list to what skill actually inlined) before #9968's runtime resolution lands.

This finding is NOT in the PM-defined gate (AC1/2/4/5) and is not used to block the transition per PM's explicit instruction.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

PM-gated ACs all observably satisfied. Mandatory-inline divergence flagged for PM follow-up consideration. AC6 runtime spot-check belongs to DM at ship time or to a post-merge live-cycle observation.
