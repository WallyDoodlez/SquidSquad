# iter-362 — 2026-06-19 09:48 (POLLING /loop tick)

**Productive cycle (after a 15-tick quiet stretch). #12820 VERIFIED → PASS (zero gaps) → pending-ship.**
★ The fix for qa's OWN permanent-POLLING condition. ★

## Pickup
- `git pull` brought new vault learnings (PM/skill active again). PT scan → #12820 surfaced
  (type:issue, medium, auto-approved).

## Work — #12820 (clone .harness-port desync → permanent polling)
- PR #12883, branch squidsquad/task/12820 @ bed381e9d. Root cause (skill RCA, confirmed):
  find_free_port silent ephemeral fallback → 2nd harness poisons clone .harness-port.
- Fix: production path probes /status → refuse exit(1) if live (never poison); free → claim
  canonical (SO_REUSEADDR for #12825 restart); --port 0 keeps ephemeral for the test harness.
- **Independent live/unmocked check:** real /status server → (A) refuse exit(1); (B) claim free;
  (C) --port 0 → ephemeral. All 3 PASS.
- new 8/8 + regression 301 + integration test_9398 8/8 + post-merge-equivalent gate 4612, 0 fail.
- No CQ (harness code + fixture). Merge deferred to DM (PR has no closing keyword; mergeable UNKNOWN
  → DM sync+refresh). Counter NOT bumped. Artifacts on main (91bbe56ee).

## Orthogonal defect found + fixed (mine)
- First gate run flagged test_galaxy_notes_have_frontmatter: my own cy345/cy346 galaxy notes lacked
  YAML frontmatter (started with `#`). Fixed both on main (name/desc/metadata.type) → test_vault
  15/15, main gate green 4604. Memory: feedback_galaxy_notes_need_yaml_frontmatter.

## Notable
- #12820 is the root cause of qa being stuck in POLLING every session. Once it ships, the next qa
  fresh session should reach EVENT mode (no more dead-ephemeral-port poisoning) — CONFIRM at restart.

## Next
- DM to ship #12820 (sync branch w/ main first). Otherwise idle.
