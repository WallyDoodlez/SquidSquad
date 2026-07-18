# FINDINGS — #12527 Greenfield installer smoke on a foreign repo

**Author**: skill-lead
**Date**: 2026-07-18
**Task**: #12527 (PRD greenfield installer validation)
**Method**: safe local exercise of the core install path against a throwaway FOREIGN target repo (a trivial JavaScript app, `widget-foundry`, clean git history, no GitHub remote), plus static audit of the outward-facing steps that are unsafe to run unattended from this self-hosted clone.

## What was executed (safe, local, no side effects)

Drove the core install path directly against the throwaway target — `repo_scan.scan(target)` → `wizard.generate_default_spec(scan, repo_info)` → `wizard.scaffold_install(spec, target, overwrite_existing=True)` — with NO gh calls, NO label creation, NO commit, NO harness boot. Driver: `scratchpad/greenfield_driver.py`.

### Results — the core path WORKS for a foreign target, with one caveat found on verification (see #13595)
- `repo_scan` detected the JS project cleanly (languages, frameworks, package_managers, test_strategy).
- `scaffold_install` composed successfully — **0 roles FAILED to compose**.
- Composed output was **literal-string** clean of this-repo leakage: both aliases produced a valid CLAUDE.md (76 KB / 75 KB) with **zero** occurrences of `SquidSquad-2`, `D:/Dev/Dev`, `WallyDoodlez/SquidSquad`, or the sibling clone names. **Correction (verifier-caught, #13595):** literal-string cleanliness does NOT mean the engine is foreign-repo-safe. `compose.deploy_role_v2`'s placeholder substitution (`_read_config_value` → `config.get_field`) reads `config.CONFIG_PATH`, which is hardcoded to the **installing clone's own repo root** — not `target_root`. This run's `workers` placeholder happened to read this clone's real config value, which coincidentally matched the target spec's own hardcoded worker id (FG-1), so no leak was visible in the string check. The same read path affects workers/aliases/test-commands/project-name — at least 7+ placeholder fields, not just one. My check only covered literal path/name strings and missed this whole config-value-substitution leak class. See #13595 (high) for the full trace.

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

### FG-3 — ~~scaffolded config.md carries the deprecated `Dev Agents:` field~~ — FALSE, corrected by verifier; see FG-4
Originally diagnosed as `build_config_md` emitting a deprecated `Dev Agents:` field. **Verifier reproduced this live and the stated root cause is FALSE**: `build_config_md` never emits `Dev Agents:` (v2 `## Agents` schema only, confirmed by printing the full generated text). The actual source of the observed warning is FG-4 below. Filed as #13594, closed as `superseded_by:13595` per verifier's correction.

### FG-4 — config-value placeholder substitution reads the INSTALLING clone's config.md, not the target's (supersedes FG-3/#13594)
Traced by verifier via a monkeypatched `config.get_field` stack trace: `compose.deploy_role_v2` → `_substitute_placeholders` → `_read_config_value('workers')` → `config.get_field` → `config.CONFIG_PATH`, which is hardcoded at import time to the **installing clone's own repo root** (`config.py:39-40`), ignoring `target_root`. The `Dev Agents: skill` warning this task originally saw was this clone's own real config value leaking into the foreign target's compose — not anything the scaffolder itself writes. Affects every config-value-substituted placeholder (workers/aliases/test-commands/project-name — at least 7+ fields), not just one. This is a broader-severity leak class than FG-1/FG-2/FG-3 and directly falsifies this task's original AC4 "zero self-references" claim (see Verdict).
→ Filed by verifier as **#13595** (high) during verification. Fixing #13595 is a separate task, not required to close #12527.

## Not executed (requires an attended foreign-repo run — outward-facing)
Runbook steps 1 (create foreign GitHub repo), 2-3's gh/label/commit side effects, and 4-5 (start a real harness + boot agents) perform outward-facing / hard-to-reverse actions and, run from this self-hosted clone, risk polluting THIS repo (FG-2). These are the human-operator-attended portion — mirroring sibling task #10686's by-design "manual, with human-operator participation" shape. They should be run against a genuinely separate foreign repo + remote with an operator present.

## Filed bugs (AC3)
- FG-1 → **#13592** (medium): default spec hardcodes `[pm, skill]` — self-named worker + no verifier/dm.
- FG-2 → **#13593** (medium): `setup-yes [target_dir]` gh ops use ambient CWD context, not target_dir.
- FG-3 → **#13594** (low, CLOSED superseded_by:13595): diagnosis was false; see FG-4.
- FG-4 → **#13595** (high, filed by verifier): `config.CONFIG_PATH` hardcoded to the installing clone — config-value-substitution leak class across 7+ placeholder fields.

## Verdict (AC4) — corrected per verifier
**Greenfield core install (scan → spec → scaffold → compose) mechanically WORKS for a foreign target** (0 roles failed to compose, valid CLAUDE.md for both aliases) but is **NOT foreign-repo-safe as originally claimed** — the "zero self-references" result was a literal-string check that missed a config-value-substitution leak class (#13595, high): `deploy_role_v2` reads placeholder values (workers/aliases/test-commands/project-name) via `config.get_field`, which is hardcoded to the *installing* clone's `config.md`, not the target's. This run's leak was invisible only by coincidence (the leaked `workers` value happened to match the target spec's own hardcoded worker id, FG-1). **Blocked for unattended completion at the gh/label/commit + harness-boot steps** (outward-facing; FG-2 makes an in-this-clone run unsafe). Four concrete foreign-repo defects found: #13592 (agent-set), #13593 (gh-context), #13595 (config-value leak, high — the load-bearing correction), and #13594 (closed, superseded by #13595). Fixing #13595 is a separate task, not required to close #12527. The remaining live attended run (real foreign remote + harness boot) is the human-operator step — matching sibling task #10686's by-design attended shape.
