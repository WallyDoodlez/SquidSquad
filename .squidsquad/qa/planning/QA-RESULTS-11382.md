# QA-RESULTS-11382 — pm/github-issues.md:27 --role pm bare-alias deviation

**Issue**: #11382 (`type:issue`, severity:low, role:skill, improvement-scan)
**Fix commit**: `d1d62f67a` on `squidsquad/skill/compose-polish-session` (no PR — source-only 1-line edit per skill)
**Verifier**: verifier-lead
**Verified**: 2026-06-09 02:38
**Verdict**: **PASS**

## Implicit AC

Replace `--role pm` with `--role pm-lead` at `references/sub-skills/roles/pm/github-issues.md:27` to align with the canonical Reporter-naming-lock in `common/tracker-protocol.md`.

## Verification

- **TC-1 — Line 27 fixed**: PASS. `git show origin/squidsquad/skill/compose-polish-session:references/sub-skills/roles/pm/github-issues.md` line 27 now reads:
  ```
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "Triaged. Routed to [role]. Priority: Low (human can bump)."
  ```
- **TC-2 — Diff is minimal**: PASS. `git show d1d62f67a` reports `1 file changed, 1 insertion(+), 1 deletion(-)`. Zero scope creep.
- **TC-3 — No new `--role pm` bare-alias on the comment/transition surface**: PASS. Sweep `git grep -- "--role pm"` on bundle branch surfaces only legitimate target-role usages of `--role pm` in `create-task`/`create-issue` invocations (where `pm` is the role:label, not the calling agent identity):
  - `pm/vault-synthesis.md:73` — `Set --role pm, --priority low, --reporter pm-lead` (create-task target role)
  - `worker/implement-tasks.md:97` — `Set --role pm, --severity medium, --reporter [ROLE]-lead` (cross-role create-issue target role)
  These are correct per tracker.py grammar: `--role` on `create-*` sets the `role:*` label (bare alias is right); `--role` on `comment`/`transition` identifies the calling agent (uses `-lead` suffix).
- **TC-4 — Composed CLAUDE.md unaffected**: PASS by inspection. `pm/github-issues.md` is runtime-loaded by PM via `→ run sub-skill: github-issues` marker (Step 2.2 step:cycle/triage-external) — not inlined at compose time. Composed CLAUDE.md per role is byte-stable as skill claimed.

## Verdict

PASS — clean 1-line drift fix, no scope creep, no regressions. Transitioning #11382 to pending-ship.

Append-only after publication.
