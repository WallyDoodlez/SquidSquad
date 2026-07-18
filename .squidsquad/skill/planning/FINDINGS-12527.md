# FINDINGS — #12527 Greenfield installer smoke on a foreign repo

**Author**: skill-lead
**Date**: 2026-07-18
**Task**: #12527 (PRD greenfield installer validation)
**Method**: safe local exercise of the core install path against a throwaway FOREIGN target repo (a trivial JavaScript app, `widget-foundry`, clean git history, no GitHub remote), plus static audit of the outward-facing steps that are unsafe to run unattended from this self-hosted clone.

## What was executed (safe, local, no side effects)

Drove the core install path directly against the throwaway target — `repo_scan.scan(target)` → `wizard.generate_default_spec(scan, repo_info)` → `wizard.scaffold_install(spec, target, overwrite_existing=True)` — with NO gh calls, NO label creation, NO commit, NO harness boot. Driver: `scratchpad/greenfield_driver.py`.

### Results — the core path WORKS for a foreign target
- `repo_scan` detected the JS project cleanly (languages, frameworks, package_managers, test_strategy).
- `scaffold_install` composed successfully — **0 roles FAILED to compose**.
- Composed output is clean of this-repo leakage: both aliases produced a valid CLAUDE.md (76 KB / 75 KB) with **zero** self-references to `SquidSquad-2`, `D:/Dev/Dev`, `WallyDoodlez/SquidSquad`, or the sibling clone names. Compose does NOT hardcode the source clone's identity into a foreign install's output. This is the load-bearing positive result: the compose/scaffold engine is foreign-repo-safe.

## Findings (foreign-repo assumptions the installer got wrong)

### FG-1 — default spec hardcodes `agents=[pm, skill]`: self-named worker + no verifier/dm
`generate_default_spec` (wizard.py:3638-3649) hardcodes the agent list to exactly two agents: `pm` and a worker with `id="skill"`. Two problems for a foreign target:
- The worker alias is literally `skill` — SquidSquad's OWN self-dev specialization — regardless of the detected stack. The `stack` field IS set correctly (`javascript`), but the alias is not derived from it; a foreign JS repo should get a stack-appropriate worker alias (e.g. `web`), not `skill`.
- No `verifier` and no `dm`. The `--yes` greenfield install therefore produces a **non-functional pipeline**: nothing to verify pending-test work and nothing to ship pending-ship work. Since `--yes` mode is non-interactive, the operator gets no chance to add them.
→ Filed as a discrete bug (see verdict). Severity medium — greenfield `--yes` yields a mis-named + incomplete squad.

### FG-2 — `setup-yes [target_dir]` honors target_dir for scaffold but NOT for gh
`non_interactive_setup` (wizard.py:4227) accepts a `target_dir` and scaffolds into it, but its GitHub operations ignore it:
- `gh repo view` (4251) runs in the ambient process CWD, so `repo_info["repo"]` (→ config.md project URL) reflects whatever repo the CWD points at, not `target_dir`.
- `ensure_labels(dry_run=False)` (4298) creates labels in the ambient gh context, not against `target_dir`'s remote.
Run as documented ("as a normal user would, NOT from this repo's context" — i.e. cd'd into the foreign repo) it happens to work because CWD == target. But `wizard.py setup-yes /path/to/foreign` invoked from any other CWD scaffolds into the foreign repo while reading identity + creating labels for the CWD repo — a parameter/behavior mismatch that can silently pollute the wrong repo. This is exactly why the full `setup-yes` was NOT run unattended from this self-hosted clone.
→ Filed as a discrete bug. Severity medium.

### FG-3 — scaffolded config.md carries the deprecated `Dev Agents:` field
`build_config_md` (invoked by scaffold) emits a config.md whose worker section still uses `Dev Agents:`; the runtime warns "config.md uses deprecated field `Dev Agents:` — rename to `Workers:` before #6274.3 cutover." Every NEW install (foreign or self) is therefore born with a field slated to break at the #6274.3 rename cutover.
→ Filed as a discrete bug (linked to #6274.3). Severity low (latent until cutover).

## Not executed (requires an attended foreign-repo run — outward-facing)
Runbook steps 1 (create foreign GitHub repo), 2-3's gh/label/commit side effects, and 4-5 (start a real harness + boot agents) perform outward-facing / hard-to-reverse actions and, run from this self-hosted clone, risk polluting THIS repo (FG-2). These are the human-operator-attended portion — mirroring sibling task #10686's by-design "manual, with human-operator participation" shape. They should be run against a genuinely separate foreign repo + remote with an operator present.

## Filed bugs (AC3)
- FG-1 → **#13592** (medium): default spec hardcodes `[pm, skill]` — self-named worker + no verifier/dm.
- FG-2 → **#13593** (medium): `setup-yes [target_dir]` gh ops use ambient CWD context, not target_dir.
- FG-3 → **#13594** (low): scaffolded config.md uses deprecated `Dev Agents:` field (breaks at #6274.3).

## Verdict (AC4)
**Greenfield core install (scan → spec → scaffold → compose) WORKS for a foreign target** and is free of source-clone leakage. **Blocked for unattended completion at the gh/label/commit + harness-boot steps** (outward-facing; FG-2 makes an in-this-clone run unsafe). Three concrete foreign-repo defects found and filed (#13592 agent-set, #13593 gh-context, #13594 deprecated config field). The remaining live attended run (real foreign remote + harness boot) is the human-operator step — matching sibling task #10686's by-design attended shape.
