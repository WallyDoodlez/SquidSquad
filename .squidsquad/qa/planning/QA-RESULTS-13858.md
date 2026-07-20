# QA-RESULTS-13858

**Verdict: PASS → pending-ship**

PRD-VAULT-V2 P2 — structure: `vault-schema.json` registry, `systems/` hub layer, registry-derived templates (S2.1–S2.3), PR #14036 + main-side prepopulation. TEST-PLAN derived independently from the issue body + PRD-VAULT-V2.md §P2 + VAULT-ARCH.md §3, not from skill's PR description.

## TC Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | S2.1 | PASS | Isolated scratch vault (outside the real repo), custom type `runbook` (folder `runbooks`, budgeted, weight 5.0, prefix `rb-`) registered in `vault-schema.json`. Live `vault-query.mjs` invocation (`--no-write`) surfaces the note in the custom folder via filename-tier match, `score: 1.25` confirming the custom weight (5.0) dominates the ranking formula (5.0 × recency 1 × tieBreakWeights.recency 0.25). |
| TC2 | S2.1 | PASS | Same scratch vault, a note dropped in `galaxy/` (NOT in this taxonomy's registry) is genuinely invisible to search even on an exact-slug substring match — confirmed by querying its exact slug and getting zero results. |
| TC3 | S2.1 | PASS | A second scratch vault with no `vault-schema.json` present at all: search still works and correctly applies the P1 default profile (PARAG `galaxy` scanned, `pattern` type weight 1.0 → score 0.25 = 1.0 × 1 × 0.25 recency) — confirms fail-open degrade to pre-#13858 behavior. |
| TC4 | S2.2 (framework) | PASS | Third scratch vault: registering `system` (hub, folder `systems`) + `learning` (budgeted); `vault_check.check_structure()` (invoked directly, module-level `VAULT_DIR` pointed at the scratch vault — no CLI `--vault` flag exists for this function) returns `OK: Vault structure valid` once `systems/` exists. |
| TC5 | S2.2 (framework) | PASS | Same scratch vault: `check_hub_links()` flags `learning-orphaned-from-hub.md` (zero hub wikilinks) as `WARN: ... graph-orphaned` and does NOT flag `learning-linked-to-hub.md` (links to `[[widget]]`, a hub-type note). Both calls exit 0 — advisory only, never blocking, per §3.3/§9.9. |
| TC6 | S2.2 (prepopulation) | PASS | Live, non-mocked, against this repo's real `.squidsquad/vault/`: `node .claude/skills/vault-search/scripts/vault-query.mjs --entities pr-merge --no-write` returns a direct filename-tier hit on `systems/pr-merge.md` (the hub), and `traversed[]` includes 4 galaxy leaves with `walkedFrom: ["pr-merge"]` directly (e.g. `decision-branch-per-feature-workflow`, `learning-config-merge-ours-drops-concurrent-changes`) — confirming the hub hop cost 0 traversal budget (the budgeted galaxy hop consumed 1 of 2, well within budget). Exceeds skill's claimed "2 galaxy leaves" (4 found). |
| TC7 | S2.3 | PASS | `vault_entity.resolve_template('system', ...)` resolves the dedicated `system.md` template (non-generic); `resolve_template('bogus-type', ...)` raises `ValueError` naming the registered set. `create_note('system', 'widget2', ...)` materializes correctly with stamped `type`/`created`/`updated`. |
| TC8 | S2.3 | PASS | Custom type `runbook` (no dedicated `references/vault-templates/runbook.md`) resolves to `_generic.md` (`is_generic: True`); `create_note('runbook', 'onboarding', ...)` produces a note with `type: runbook` frontmatter correctly stamped from the generic skeleton. Prefix auto-prepend confirmed: slug `incident-response` (no `rb-` prefix) → file `rb-incident-response.md`. |
| TC9 | S2.3 | PASS | `create_note()` rejects `''`, `'../evil'`, `'.hidden'`, `'/abs'` (all `ValueError`, re-confirms the external-review slug-validation fix); accepts `rb-onboarding`; a second `create_note()` call for an already-existing slug raises `FileExistsError` (refuses overwrite). |
| TC10 | — (CQ, #9184) | PASS | Authored `tests/comprehension/13858_spec.json` independently — fresh sonnet agent, given ONLY the "Creating Notes" excerpt of `vault-protocol.md`, no other context: 2/2 correct (template resolved by TYPE not folder; unregistered-template custom type falls back to `_generic.md`). Baseline refreshed in-branch (same-PR spec+file pair, per the #13575 gate's own remedy — mirrors the #13857-round-2 precedent, not the separate "verifier bookkeeping" learning about *other* PRs' drift). |
| TC11 | — | PASS | `test_vault_engine_13857.py` + `test_vault_check_13858.py` + `test_vault_templates_13858.py` + `test_vault_check_unit.py` + `test_vault_engine_installer_13857.py` + `test_vault.py` + `test_vault_check.py`: **160/160**. |
| TC12 | — | PASS | See "Ship gate" below. |

## Ship gate

- Official static gate (`tests/run_tests.py static`): **PASS — 6205 gated test(s) passed (0 failures, 0 errors)** — matches skill's claimed number exactly. Re-ran after adding TC10's CQ spec + baseline entry; still clean.
- Integration suite (`tests/run_tests.py`, full): first run showed 4 failures + 9 errors, all `gh issue edit ... returned non-zero exit status 1`. Root-caused (not hand-waved as "load"): `gh auth status` showed the machine's *active* account was **`Naahtec` (read-only — token lacks the `AddLabelsToLabelable` GraphQL mutation permission)**, not `WallyDoodlez`. This is the same class of machine-global gh-identity flip documented from #13863/#13865 sessions, unrelated to this PR's diff (no file in this PR touches gh-identity code). Ran `gh auth switch --user WallyDoodlez` (reversible, restores the fleet's canonical write-capable identity — the one `#13863`'s credential-helper pinning already targets) and re-ran: **54/54 OK**, confirming the failures were purely environmental, not a regression from #13858.

## PM-flagged deviations (informational, non-blocking)

Skill flagged two deviations from the TRD's literal §3.2 text for PM's judgment; neither fails any tested AC, and both have sound, documented rationale — independently reviewed, not just trusted:

1. **Seed carries an `archive` type** not present in TRD §3.2's literal JSON snippet. Verified this is load-bearing, not decorative: this repo's `.squidsquad/vault/archives/` genuinely still holds 5 pre-migration `type: archive` notes (dated 2026-05-25 to 2026-07-19, predating #13858 entirely — the M-track migration that would retire this folder per §3.4 hasn't run yet). Without registering `archive`, `check-structure` would WARN on all 5 as "type not in vault-schema.json" and the search engine would silently exclude them (structurally excluded folder) — a real regression against the PRD's own "near-zero migration cost" promise for pre-existing content. `consumption.mjs`'s `DEFAULT_CONFIG` and `vault_check.py`'s hardcoded last-resort fallback both also carry `archive`, so the three tiers (seed / JS default / Python hardcoded) are mutually consistent.
2. **`BRIEFING.md` template keeps its v1 (uppercase) filename** rather than the TRD prose's lowercase `briefing.md`. The live artifact it seeds is genuinely `BRIEFING.md` (uppercase) everywhere in the codebase (`vault-protocol.md`'s own `vault-init` step names it uppercase) — a template rename would be pure casing churn with no functional value and a real risk of breaking every consumer expecting the actual filename.

Both are reasonable interim engineering calls, transparently disclosed by skill in Discussion rather than silently made. Recommend PM close these out as "confirmed, no change needed" or override at their discretion — neither blocks this verification.

## Conclusion

All 3 stories (S2.1, S2.2 framework + prepopulation, S2.3) verified with live, non-mocked, independently-derived evidence — not trusted from skill's PR description or test claims. Zero gaps. → **pending-ship**.
