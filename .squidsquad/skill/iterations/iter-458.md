# Iteration 458 — front-loaded planning for #11505 (capabilities deadwood)

**Mode**: loop (harness DOWN). Manual ops.

## What happened
- Gate re-check: #11683 still unshipped (6th gated cycle); harness still down. 3 PRs (#11709/#11715/#11722) all DS-clean, all gated.
- Verified #11586(A) needs no skill code fix: read thin_launcher — #11512 ALREADY made the spawn prompt mode-neutral (boot Step 1 probes + decides; /loop injection removed). So (A)'s boot path is correct; root cause is harness-process availability (operational), as skill already concluded (03:02). My harness-stability code contributions (#11587 + #11640 + #11641) are the relevant skill work, done. No new comment (would duplicate).
- Picked up **#11505** (low, auto-approved deadwood removal per INSTALLER-ARCH §8.3), now unblocked (#11504 merged).
- **Front-loaded planning** (footprint mapped before edits): broad grep looked large (manifest.py, capability_check.py, catalog_drift.py, docs, ~7 tests) but reading ACs precisely → in-scope is the **agent-facing sub-skill layer only**: capability-check.md wired into exactly ONE role (dm: includes.yml:19 + instructions.md:8 marker); capabilities/ dir already empty; compose.py refs are historical comments.
- **Skill scope judgment**: manifest.py capability REGISTRY + capability_check.py runtime are installer-core, NOT in ACs → kept OUT (separate higher-risk change; asked PM to confirm §8.3 full-framework intent).
- Posted bounded execution plan on #11505 (work contract); transitioned in-progress.
- **Did NOT execute**: blocked on (1) PM CQ AC (step 7.4 — LLM-consumed sub-skill removal from DM; I don't self-author CQ specs) and (2) AC7 'run_tests.py exits 0' gated on #11683. Deferred execution to a fresh cycle post-CQ-answer (context-responsible; avoids rework if PM wants capability-check preserved/CQ'd).

## Next cycle
- #11683 mergedAt → if shipped, land the 3 gated PRs.
- #11505 → if PM answered CQ, execute the bounded removal on task/11505.
