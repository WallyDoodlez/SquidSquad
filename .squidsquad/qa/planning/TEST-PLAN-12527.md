# TEST-PLAN-12527 — Greenfield installer smoke test (foreign repo)

**Source**: GitHub task #12527 body (Runbook + ACs), independent of skill's FINDINGS-12527.md.
**Derived without reading the doc's conclusions as ground truth — re-derived and independently re-checked.**

## Acceptance Criteria (from issue body)

- **AC1**: Installer run to completion on a foreign repo, OR a precise list of where/why it blocked.
- **AC2**: Findings doc committed under `.squidsquad/` planning.
- **AC3**: Each blocking breakage filed as a discrete bug, linked to this issue.
- **AC4**: Explicit verdict — "greenfield install works with N manual steps" OR "blocked at step X".

## Test Cases

### TC-1 (covers AC1): Precise blocked-at-step account, safety-justified
- **Steps**: Confirm skill's stated blocker (gh/label/commit + harness-boot steps declined as unsafe from this self-hosted clone due to FG-2) is a REAL, code-confirmed reason, not an excuse.
- **Verification**: Read `wizard.py`'s `_run(["gh", "repo", "view", ...])` and `ensure_labels()` call sites — confirmed no `cwd=` kwarg threading `target_dir`; both inherit ambient process CWD. FG-2's claim is accurate.

### TC-2 (covers FG-1 / #13592): Default spec hardcoding
- **Verification**: Read `wizard.py` `generate_default_spec` (~line 3638) — `agents` list hardcodes `id="pm"` and `id="skill", alias="skill", role="worker"` regardless of detected stack; no `verifier`/`dm` entries. Confirmed accurate.

### TC-3 (covers FG-3 / #13594): Deprecated-field claim — INDEPENDENT RE-DIAGNOSIS
- **Steps**: (1) Call `wizard.build_config_md(spec)` directly and inspect raw text for `Dev Agents`. (2) Run the real `wizard.scaffold_install(spec, target, overwrite_existing=True)` against a fresh throwaway target and capture stderr + inspect the written config.md. (3) Trace the actual call site with a monkeypatched `config.get_field` printing a stack trace.
- **Result**: `build_config_md` output does NOT contain `Dev Agents` (confirmed both ways). The warning DOES fire (twice), but traced to `compose.deploy_role_v2` → `_substitute_placeholders` → `_read_config_value('workers')` → `config.get_field` → `config.CONFIG_PATH`, which is hardcoded to the INSTALLING clone's own repo root (`config.py:39-40`, computed at import time, ignores `target_root`). The leaked value is MY OWN qa clone's `Dev Agents: skill`.
- **#13594's stated root cause is FALSE** ("scaffolded config.md uses deprecated field" — the scaffolded file never contains it). The actual defect is broader and more severe: source-clone config values leak into ANY `_read_config_value()` call during a foreign `deploy_role_v2` compose (workers, aliases, test commands, project-name — not just one field). Filed as #13595 (high), corrected #13594 via comment.

### TC-4 (covers AC1's "compose engine is foreign-repo-safe" claim): Falsified
- **Steps**: Reproduced skill's positive claim methodology (literal self-reference string search) — confirmed it passes (no `SquidSquad-2`/path/sibling-clone strings in composed output). But TC-3's trace proves a DIFFERENT leakage class (config-value substitution) that a literal-string check cannot detect, and which coincidentally doesn't manifest as a visible string mismatch in THIS test run only because the leaked `workers` value ("skill") happens to match the target spec's own hardcoded worker id (FG-1).
- **Result**: The "zero self-references, foreign-repo-safe" claim is incomplete — it holds for path/name literals but not for config-value substitution. This is a material correction to AC4's positive verdict.

## Coverage matrix
- AC1 → TC-1 (PASS)
- AC2 → doc exists, committed (PASS as a mechanical fact) — but content needs correction, see verdict
- AC3 → TC-2 (accurate), TC-3 (INACCURATE, corrected), #13593 spot-checked accurate via code read
- AC4 → TC-4 (positive claim falsified by TC-3's evidence)

No LLM-consumed instructions touched by this task (all findings are code-level) — no Comprehension Questions section required.
