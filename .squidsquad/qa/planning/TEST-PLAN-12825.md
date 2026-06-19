# TEST-PLAN-12825 — Supervised harness launcher + agent-triggerable harness restart

**Derived independently from the AC list in issue #12825 (not from the worker's PR diff).**
PR #12860 · branch `squidsquad/task/12825` · type:task · priority:high · role:skill

## Scope

Adds a SUPERVISOR layer above the harness: a relaunch wrapper (`restart-harness.bat`/`.sh`)
that owns harness lifecycle, an agent-callable `POST /restart` endpoint, a new
LLM-consumed sub-skill teaching the capability, catalog + installer + compose wiring.

## Test cases (one per AC, executed against live instance)

- **TC1 (AC1) — Supervised launcher, cross-platform.** Run `restart-harness.sh` and
  `restart-harness.bat` against a scripted stub harness: (a) exit 42 → relaunch; (b) exit 0
  / clean stop → do NOT relaunch; (c) abnormal exits → crash-loop guard stops after N
  consecutive. Verify real subprocess relaunch counts.
- **TC2 (AC2) — Agent-triggerable restart.** Live `POST /restart` via TestClient: returns
  202 `{"status":"restarting"}`, tears down agents, exits with `HARNESS_RESTART_EXIT_CODE`
  (42), KEEPS the port file. Confirm distinct from `/shutdown` (exit 0, deletes port file).
  Confirm concurrent-teardown guard (DS-F2): second teardown → 409.
- **TC3 (AC3) — New sub-skill, v2-wired.** `references/sub-skills/common/harness-restart.md`
  exists; reactive `→ run sub-skill: harness-restart` marker wired into all 4 role
  `instructions.md` (not via includes.yml). Documents WHEN / HOW / EXPECT / post-restart
  verification.
- **TC4 (AC4) — Catalog.** Row for `harness-restart` present in `docs/sub-skill-catalog.md`,
  correct section, accurate description + role coverage.
- **TC5 (AC5) — Deployment default.** `installer-files.txt` ships the 2 launchers + the
  sub-skill (count bumped); README points to the supervised launcher as default;
  `squidsquad_cli._harness_launch_tail` runs the harness UNDER the wrapper when present, with
  graceful fallback to bare `harness.py` when absent. Per-OS (windows/darwin/linux) path.
- **TC6 (AC6) — Compose-consumption.** Run `compose.py deploy-all`; confirm the
  `→ run sub-skill: harness-restart` marker reaches the composed `.squidsquad/<role>/CLAUDE.md`
  of pm / verifier / dm / skill (verify deployed output, not just source).
- **TC7 (AC7) — Comprehension (HARD GATE).** Author `tests/comprehension/12825_spec.json`;
  spawn a fresh sonnet agent given ONLY the sub-skill text; answers must be correct from the
  file alone (when restart is right vs operator/code-fix; how = POST /restart; own session
  ends; prefer routing to PM; post-restart verification).
- **TC8 (AC8) — No-regression + DS audit.** Full `#12825` suite + harness/route-contract
  regression + static gate all green; DS-audit findings verified applied in code.

## Verdict rule

Zero-gap gate: every AC must show observable PASS evidence. Any gap → back to in-progress (skill).
