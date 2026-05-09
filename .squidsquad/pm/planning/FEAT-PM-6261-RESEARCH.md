# FEAT-PM-6261 Research — Fixed Team Architecture: PM+QA+DM+Workers Always Present, Tracker-Protocol into L1

## Summary

This research analyzes the impact of three tightly-coupled architectural simplifications: (1) merging the `tracker-protocol` common sub-skill into the Layer 1 base agent definition, (2) stripping all role-absence fallback logic from agent instructions and scripts, and (3) removing QA from DM's delivery path. These changes codify the post-#6055 reality that every SquidSquad team has a fixed roster of PM+QA+DM+workers — no role is ever absent, so every fallback path is dead code that adds complexity and risks subtle bugs.

The changes touch ~18 files across templates, sub-skills, includes manifests, and Python scripts. Primary risk is mechanical: ensuring all `{{include: common/tracker-protocol}}` references are removed from 4 role entry templates + 24 includes.yml manifests without breaking compose. Secondary risk is ensuring the tracker.py authority model still works correctly when PM no longer holds a "combined PM/QA" identity. Overall assessment: **straightforward**, mostly deletions and content moves, with one behavioral change in DM's PR merge gate.

## Vault Context

- **BRIEFING.md priorities**: #6055 (Enforce role separation — PM/QA/DM mandatory) is listed as shipped. This task is a direct follow-on cleanup from that decision.
- **Related decisions**: [[decision-sub-skill-architecture]] — defines the current 5-layer architecture (L1 base → L2 role → L3 domain → L4 project → L5 capabilities). Tracker-protocol currently sits at Layer 2 (common sub-skill), this task promotes it to Layer 1 (base agent definition).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the tracker-protocol content is a mix of deterministic script invocations and prose instructions. When merging to L1, the deterministic script contracts must be preserved verbatim.
- **Human preferences**: Prefers direct/mechanical checks over indirect state files. The removal of fallback logic (which checks for role presence through directory scans) aligns with this: the team is fixed, no need to check. Prefers agents to act first on clear requirements — this task's requirements are unambiguous.
- **Related learnings**: [[learning-atomic-migration-strategy]] — #6055 was shipped in one atomic pass. This follow-up cleanup should follow the same pattern: all changes in one dev cycle to avoid mixed-state agents.

## Impact Analysis

### Files touched

**Sub-skills to modify or delete:**
- `references/sub-skills/common/tracker-protocol.md` — content moved to L1, file deleted (or emptied with redirect notice)
- `references/sub-skills/roles/pm/delivery-fallback.md` — deleted (already says "PM never does delivery"; file itself is vestigial)
- `references/sub-skills/roles/pm/testing-and-verification.md` — line 3, 5, 7: remove "PM does not verify" language, replace with "QA owns verification" (already mostly there, just need to strip the implied fallback framing)
- `references/sub-skills/roles/dm/delivery-packaging.md` — lines 44-46: remove the `isDraft` QA gate; DM merges PRs regardless of draft status (see DM Skips QA below)
- `references/sub-skills/manifest.md` — update: remove tracker-protocol from all composition order listings, remove delivery-fallback entry, remove manifest file inventory entries

**Role entry templates:**
- `references/roles/pm/instructions.md` — line 5: remove "When QA is absent, you fall back to combined PM/QA duties."; line 11: remove `{{include: common/tracker-protocol}}`; line 105: remove "If DM is absent, PM handles version bumps in Step 6d."; remove `{{include: roles/pm/delivery-fallback}}` (line 107)
- `references/roles/qa/instructions.md` — line 19: remove "If DM absent, PM's delivery fallback handles it."; line 27: remove `{{include: common/tracker-protocol}}`
- `references/roles/dm/instructions.md` — line 25: remove `{{include: common/tracker-protocol}}`
- `references/roles/dev/instructions.md` — line 21: remove `{{include: common/tracker-protocol}}`

**Layer 1 base:**
- `references/roles/instructions.md` — append tracker-protocol content (after the existing "Agent Foundation" section)

**Includes manifests (all 24 files):**
- Remove `common/tracker-protocol` from the `includes:` list in:
  - `references/roles/dev/includes.yml` (line 4)
  - `references/roles/pm/includes.yml` (line 4)
  - `references/roles/qa/includes.yml` (line 5)
  - `references/roles/dm/includes.yml` (line 5)
- Remove `roles/pm/delivery-fallback` from `references/roles/pm/includes.yml` (line 11)
- All 20 variant includes.yml files inherit from these 4 base manifests via `base_role:` — they get the change automatically through inheritance

**Python scripts:**
- `references/scripts/tracker.py` — lines 22-23 (docstring): remove "PM/QA combined identity" and "pending-test → pending-ship (PM/QA combined identity)" language; lines 182-186 (ROLE_AUTHORITY comment): rewrite to say "PM is authorized alongside QA for pending-test transitions as a coordination backstop" rather than "combined PM/QA identity in deployments without a dedicated QA agent"
- `references/scripts/config.py` — lines 394-401: remove the `if "PM/QA" in agents_text` block that injects a synthetic QA entry from the legacy combined identity; lines 522-525: remove PM/QA combined identity output; line 396: ensure QA always emits as a first-class entry regardless of PM/QA legacy text
- `references/scripts/compose.py` — line 1178: update error message (already says "PM, QA, and DM" — correct); line 1112: `MANDATORY_ROLES` is already correct. No changes needed here.

**Other:**
- `references/sub-skills/roles/pm/status-line.md` — line 7: change "DM if present" → "DM"
- `references/sub-skills/common/cycle-runner.md` — line 83 already says "deprecated (DM always present)" — correct, no change needed

### Behavior changes

1. **Tracker protocol moves from L2 to L1**: All agents now receive tracker-protocol instructions from the base layer, not through per-role includes. This means tracker-protocol can never be accidentally omitted from a role. Content is identical — only the composition source changes.

2. **PM no longer has a "combined PM/QA" identity**: PM still has pending-test transition authority (retained in tracker.py ROLE_AUTHORITY), but the framing changes from "PM fills in when QA absent" to "PM has coordination authority to route items back when QA is stalled." This is a documentation change — the actual authority mappings in tracker.py are unchanged.

3. **DM ships without waiting for QA**: The `isDraft` check in Step 0b of DM's delivery-packaging (line 45) is removed. DM merges PRs and ships regardless of whether QA has converted a PR from draft to ready. This means DM could theoretically ship code QA hasn't verified — but since `pending-ship` status can only be set by QA (or PM as coordination backstop), items only reach DM after QA has completed `pending-test → pending-ship` in `roles/qa/verification.md`, where QA already converts the PR from draft to ready (lines 104-108). The DM gate was therefore redundant: if an item is at `pending-ship`, QA has already approved it. Removing the gate eliminates a false negative where DM skips an item QA has already verified but the draft status is stale.

4. **Delivery-fallback sub-skill removed entirely**: PM's includes manifest no longer references `roles/pm/delivery-fallback`. The sub-skill file is deleted or archived.

5. **Fixed team language**: All "if X absent" conditional language replaced with definitive statements. Team is PM+QA+DM+workers — always.

### Dependencies

- **Depends on #6055** (already shipped) — mandatory roles enforcement in compose.py must be active
- **Depends on compose system** — `compose.py deploy-all` must be run after template changes to regenerate all agent CLAUDE.md files
- **No new script dependencies** — all changes are to existing files
- **No capability dependencies** — no new external tools needed

## Side Effects

- **Risk 1: Stale composed CLAUDE.md files after template changes** — Severity: M — Mitigation: `compose.py deploy-all` is part of the upgrade sequence. The mandatory-role check already blocks deploy-all if pm/qa/dm are missing, so the fixed team invariant is enforced at composition time. Document in upgrade steps.

- **Risk 2: PM losing pending-test authority would break coordination** — Severity: L — Mitigation: This task does NOT remove PM's pending-test authority from tracker.py. PM retains `("status:pending-test", "status:in-progress"): {"qa", "pm"}` and `("status:pending-test", "status:pending-ship"): {"qa", "pm"}`. The change is only to the comment/narrative framing.

- **Risk 3: DM shipping unverified code if QA somehow marks pending-ship without verifying** — Severity: L — Mitigation: The removal of the DM draft gate is safe because QA's verification sub-skill already converts PRs to ready before transitioning to pending-ship (verification.md lines 104-108). If QA is malfunctioning, that's a QA bug, not a DM gate problem. The existing tracker transition authority already prevents DM from shipping items that haven't passed QA (DM can only transition `pending-ship → shipped`, and only QA/PM can set `pending-ship`).

## Edge Cases

- **What if a compose is run on a repo created before #6055 (pre-mandatory-role era)?**: compose.py deploy-all exits with error if pm/qa/dm are missing. The wizard setup flow creates all three roles. This is already enforced — no new edge case.

- **What if tracker-protocol content diverges between L1 copy and old common sub-skill during migration?**: The atomic migration approach means both sources exist briefly during development. The old file should be emptied (with a redirect comment) or deleted in the same commit that adds the content to L1. Verification: run `compose.py deploy-all` and diff the output against the previous composed CLAUDE.md — only the fallback-language removals should differ.

- **What if a variant role (e.g., dev-skill) has its own tracker-protocol override?**: No variant overrides tracker-protocol. All variants inherit from their base role's includes.yml, which simply includes `common/tracker-protocol`. Since the content will now come from L1, variants automatically get it with no special handling.

- **What about the tracker-protocol reference in Step 6c of PM instructions (version bumps)?**: PM's instructions.md line 105 currently says "If DM is absent, PM handles version bumps." This line is removed in the cleanup. The actual version bump logic is in DM's `roles/dm/version-bumps.md` — PM never performs it.

## Integration Risks

- **Config.md agent detection**: `config.py` currently parses the `## Agents` section and treats `**PM/QA**` as a combined identity. After this change, config.md should always list PM, QA, and DM as separate entries. The `_parse_agents_v1` function (line 394) needs updating to stop synthesizing QA from the PM/QA legacy string. If an existing install still has `**PM/QA**: always present` in their config.md, the `update_agents_section` function must be called to rewrite it. Mitigation: include a config.md migration in compose.py deploy-all or in the upgrade sequence.

- **Wizard.py setup flow**: The wizard currently writes `**PM/QA**: always present` (config.py line 524-525). This must be changed to write separate PM and QA entries. Check `references/scripts/wizard.py` for config.md writing logic.

- **Health check / boot-remote-agents**: These sub-skills currently reference "DM if present" or loop over agents from config. Since DM is always present, the conditional logic is harmless but should be cleaned for consistency.

- **Event bus contracts**: Deriving event contracts (compose.py `derive_and_write_event_contracts`) reads composed CLAUDE.md content. Since tracker-protocol instructions now come from L1 instead of L2, LLM-derived contracts may produce slightly different output. This should only affect the "emits" list (tracker operations trigger status-transition events) — verify after composition.

## Upgrade & Migration

- **New config values**: none
- **New files**: none (tracker-protocol content moves into existing `references/roles/instructions.md`; `delivery-fallback.md` is deleted)
- **Template changes**:
  - `references/roles/instructions.md` — gains tracker-protocol content (~140 lines)
  - All 4 role `instructions.md` files — lose `{{include: common/tracker-protocol}}` directive
  - All 24 includes.yml files — lose `common/tracker-protocol` entry
  - PM's includes.yml — loses `roles/pm/delivery-fallback` entry
  - `references/sub-skills/roles/pm/delivery-fallback.md` — deleted
  - `references/sub-skills/roles/dm/delivery-packaging.md` — lines 44-46 removed (isDraft gate)
- **Upgrade steps**:
  1. Stop all agents (harness `INTENT_STOPPED`)
  2. `git pull` the new references
  3. Run `python references/scripts/compose.py deploy-all` to regenerate all CLAUDE.md files
  4. Run `python references/scripts/compose.py upgrade-soul <role>` for each role to pick up L1 base changes in SOUL.md
  5. Run `python references/scripts/config.py update-agents-section` to rewrite config.md from PM/QA legacy format to separate entries
  6. Start agents via harness
- **Graceful degradation**: If user skips upgrade, composed CLAUDE.md files will still contain the old tracker-protocol include (since they were generated before the change). The old `common/tracker-protocol.md` file will be deleted from the repo — this will cause `compose.py` to ERROR on the next deploy-all, forcing the upgrade. This is an acceptable hard break per the atomic migration pattern.

## Open Questions

- **Q1**: Should the tracker-protocol content live inline in `references/roles/instructions.md` or in a separate L1 file (e.g., `references/roles/base/tracker-protocol.md`) that is {{include}}-d by the L1 base? — **Why**: Inline is simpler (one less file) but creates a ~140-line base file. A separate L1 file keeps the base lean but introduces another include. Recommendation: inline — the base is only ~20 lines today, 140 more is manageable, and it avoids the irony of using an include for content we're trying to promote out of the include system.

- **Q2**: Should the `delivery-fallback.md` file be deleted entirely or kept as a 3-line stub redirecting to DM's delivery-packaging? — **Why**: Deleting is cleaner but requires removing the include from PM's instructions.md and includes.yml. A stub is harmless if downstream references are missed. Recommendation: delete the file and remove all references — the atomic migration pattern requires finding all references anyway.

- **Q3**: What should DM do if a PR exists but can't be merged (conflict)? Currently there's no merge conflict handling in DM's delivery-packaging for the PR merge gate (Step 0b). — **Why**: With the draft gate removed, DM will always attempt to merge PRs. Merge conflicts currently only handled in QA's verification path. DM should handle conflicts by commenting on the issue and skipping, same as the existing `pr-merge` failure path.

## Recommendation

**Straightforward.** This is a cleanup task that removes dead code and consolidates a shared protocol into the base layer. The changes are mostly deletions and one content relocation. The only behavioral change (DM removing the isDraft check) is safe because the tracker transition authority already enforces that DM only sees items QA has approved. The integration risk with config.md's legacy PM/QA format is manageable with an explicit migration step.

## Vault Candidates

- **Type**: decision — "tracker-protocol is L1, not a common sub-skill" — **Why**: This represents a permanent architectural decision about what belongs in the base agent definition vs. common sub-skills. The tracker protocol is universal (every agent uses it), making it a natural L1 concern. Future protocol-like content that every agent needs should also be L1.
- **Type**: pattern — "fixed team eliminates all role-absence fallbacks" — **Why**: After #6055, any code path that checks whether PM/QA/DM is present is dead code. This pattern should inform future feature work: never add "if role absent" logic for the fixed trio. Applies to any new sub-skill or script.
- **Type**: learning — "DM draft gate was redundant with tracker authority" — **Why**: The isDraft check in DM's delivery path was a second layer of enforcement that tracker.py's transition authority already provided (DM can only transition pending-ship→shipped, and only QA/PM can set pending-ship). This is a general lesson: when the state machine already enforces a constraint, don't duplicate it in agent instructions — it creates false negatives when state machine outcomes and instruction-level checks go out of sync.
```