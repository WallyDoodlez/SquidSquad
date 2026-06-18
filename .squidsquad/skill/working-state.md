# Working State

- **Task**: idle. **#12749 DM-ARCH → SHIPPED** (PR #12689 merged to main 2026-06-18 01:01, by DM). Source + docs landed via PR; **main-landing of `.squidsquad/` state COMPLETED this session** (the merge-window trigger fired via `pr-merged` event).
- **#12749 MAIN-LANDING (DONE 2026-06-18 ~01:05):** on `main` — re-applied `.squidsquad/config.md` `**dm**: dm/skill`; L4 `.squidsquad/project/dm.md` Release-policy section carried over; `compose.py deploy-all` (dm 730 / pm 732 / qa 654 / skill 816); landed `.squidsquad/statusline.sh` live copy (PM ship-counter block gone). Verified: `config.py alias dm`→`dm` (tracker identity intact), registry `dm→('dm','skill')` (L3 skill domain composes), DM composed has bare-H3 spine (detect-ready/package/publish) + delivery-packaging/version-bumps markers + L4 Release policy @ line 663. No fiction window — docs+code+state all consistent on main.
- **OPEN follow-up after this landing:**
  - **restart-required (l4-recompose event):** composed CLAUDE.md changed (dm grew with spine, qa lost counter increment). Per operator's standing "reboots deferred", NOT self-restarting — surface to operator; affected agents (esp. dm, qa) need reboot to pick up new instructions.
  - **#12511** (PM-assigned "next after #12749 settles"): test-isolation leak — force-transition tests emit real #999/#42 status events to live bus; needs `event_bus.emit` stub.
  - **#12585** (approved, high, role:skill): L1 Soul "Health & Diagnostics — Facts Over Context" — high-blast-radius, CQ-gated; deserves fresh context.
- **KEY LESSONS (this cycle):**
  - Main-landing across the merge window: `git checkout main` is blocked by committed-divergent .squidsquad files (config.md, working-state.md) — discard those 2 working-tree mods (content captured) + carry the rest; pull blocked by untracked stale-lock `.claude/scheduled_tasks.lock.stale-bak` (rm it, merge brings its own).
  - **Validator vs op-processor anchor levels:** `link_stage_validator._SOURCE_STEP_HEADING_RE` matches step anchors at **bare H3 `### step:cycle/<id>` ONLY** → only bare-H3 anchors are R5-targetable by L4 ops. Op processor tolerates H3-H6 + numbering prefix. Targetable spine must be bare-H3. (vault: learning-targetable-step-anchors-must-be-bare-h3.md)
  - **dm alias needs L3 domain** (`dm→('dm','skill')`) via bullet-form `<class>/<domain>` + `get_alias` `/domain` strip (else tracker identity corrupts to `dm/skill`).
- **DEFERRED follow-up (flagged, not done):** monolithic `delivery-packaging.md`/`version-bumps.md`/`issue-triage.md` sub-skills could be DECOMPOSED across the new spine steps (currently wired whole into package/L4). Out of #12749 scope; #6126/#3296 tests pin delivery-packaging content.
- **Status**: #12749 SHIPPED. #12420 pending-test (PR #12596). Approved queue: #12585 (L1 Soul, fresh context), #12527/#12450 (blocked on #12420 merge), #12511 (test-isolation, PM-next).
- **Updated**: 2026-06-18 01:05 (skill — event-mode, post-#12749-ship main-landing)
- **Quiet Cycle Counter**: 0

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
