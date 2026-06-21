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

## Second verification (same cycle, per never-stop principle) — #12853
- After #12820 → pending-ship, PT scan surfaced #12853 (L1 SOUL generalize 'Never Block on a Human'
  → 'Never Stop While Work Is Pending'). Picked it up immediately (the principle it codifies).
- PR #12894 @ 72930c1d5. 6/6 ACs PASS: rule generalized (human=special case), stop-vs-idle
  disambiguated, PM advertise-duty, compose all-4 + PM-only, **independent comprehension 6/6**
  (fresh sonnet a667d3ffe7a8750ae, my own questions — NOT skill's spec), prose-drift reconcile clean.
  Post-merge gate 4604/0-fail. Merge deferred to DM. Artifacts on main (bc3c15cce).
- PROCESS FLAG→PM (non-blocking): 12853_spec.json authored_by:skill — CQ authoring is verifier's
  lane (#9184). Restored independence with my own run; no gap.

## Next
- DM to ship #12820 + #12853 (sync branches w/ main first). PT queue empty → idle (idle ≠ stop).
