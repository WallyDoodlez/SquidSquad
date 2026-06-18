# Iteration 323 — 2026-06-18 13:41 (POLLING)

**Cron tick** (job 15bbd977). PT scan surfaced **#12506** pending-test (severity:high, role:skill) — event-mode periodic driver / improvement-subloop dormancy fix. PR #12812, branch `squidsquad/task/12506`. Locked design AGENT-RUNTIME §8.6.1.

## Verification (TEST-PLAN derived independently from 12 ACs + §8.6.1)

Checked out PR branch; read §8.6.1, subloop_driver.py, idle-cooldown-loop.md; ran live CLI walk + full suite + fresh-agent comprehension.

**Verdict: FAIL — 11/12 ACs PASS, AC11 FAIL → in-progress (skill).**

- **AC11 FAIL (ship-blocking):** new runtime script `references/scripts/subloop_driver.py` absent from `references/installer-files.txt` (npx-squidsquad fetch manifest, 39 scripts listed). Shipped `idle-cooldown-loop.md` invokes it on every event-mode agent → fresh installs hit a missing script → #12506 dormancy reproduces. Fix = 1 manifest line + `# Total: 202`→203.
- **AC1-AC6 PASS** — live CLI walk of subloop_driver.py: lazy arm→schedule/already-armed; idle tick→scan; record-scan×3→at_cap→tick cancel(at-cap); cancel→reidle→schedule rearmed+scan_count0; reidle preserves last_run (throttle holds); tick not-drained→absorb-work; config status burst3/cooldown30 + 30m-parse + default-3.
- **AC7 PASS** — sub-skill reconcile: false Monitor fixed-cadence claim removed, §8.6.1 driver named, NUDGE branch + cooldown eligibility kept, Idle Scan Burst documented.
- **AC8 PASS** harness.py untouched. **AC9 PASS** idle-cooldown-loop referenced in all 4 composed CLAUDE.md. **AC10 PASS (HARD GATE)** fresh sonnet agent, file-only, named periodic cron driver (not Monitor) as cadence source; spec tests/comprehension/12506_spec.json. **AC12 PASS** DS-review unit1+unit3.
- **No regression:** `python tests/run_tests.py` 53 OK; `pytest` driver+config 119 passed.

## Process
- Posted FAIL verdict comment BEFORE transition (clears unread-feedback guard), then `transition 12506 pending-test in-progress --role verifier-lead`.
- Counter NOT involved (no ship). Merge not done (rejected).
- **Hazard noted:** checking out the PR branch reverted working-tree config.md to the branch's `30`/no-burst version; it carried across `git checkout main`. Restored main's committed `30m`+`Idle Scan Burst:3` via `git checkout -- config.md` BEFORE writing any artifacts. No pollution committed.
- Artifacts on main: TEST-PLAN-12506.md, QA-RESULTS-12506.md, tests/comprehension/12506_spec.json (preserved).
