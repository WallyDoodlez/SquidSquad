Now I have a complete picture. Here are my findings:

---

### Finding 1

- **File**: `references/scripts/config.py`
- **Line**: 235–269
- **Severity**: warning
- **Issue**: `vault-engine` is registered in `FIELD_MAP` (line 127) but has no graceful default in `_FIELD_DEFAULTS`. If any runtime consumer calls `config.get_field("vault-engine")` against a pre-#13857 `config.md` that lacks the `## Flags / Vault Engine` line, the call hits `sys.exit(1)` at line 343.

- **Evidence**: Every other flag that could be absent from legacy configs carries a graceful default (e.g. `pr-flow`: `"yes"`, `auto-merge`: `"no"`, `verbose-mode`: `"no"`, `event-driven`: `"no"` — see lines 236–268). `vault-engine` is the only flag field added since those defaults were established that lacks one. This violates the project's "graceful degradation everywhere, никогда not blocking (9.9)" principle: a `SystemExit` is a `BaseException` that escapes `except Exception` handlers, silently killing harness pollers (the exact problem #13335 solved by adding `context-threshold`'s default). No runtime code currently reads `vault-engine`, but the field is wired for consumption — the gap exists now and will cause a crash the moment a consumer is added.

- **Suggested fix**: Add `"vault-engine": "yes"` to `_FIELD_DEFAULTS` (line ~268-269), consistent with the `generate_default_spec` default (`vault_engine: True`) and the shipped `build_config_md` rendering.

---

### Finding 2

- **File**: `references/skills/vault-search/scripts/record-consumption.mjs`
- **Line**: 88–89 (parseArgs) and 120–122 (main validation)
- **Severity**: warning
- **Issue**: `--task 0` passes validation because the check is only `args.task === null`. `Number.parseInt("0", 10)` returns `0` (finite, not null), so the validator accepts it — but GitHub issue numbers start at 1; task 0 is semantically invalid and would attribute consumption to a non-existent tracker issue.

- **Evidence**: In `parseArgs` (line 88-89): `const n = Number.parseInt(argv[++i], 10); out.task = Number.isFinite(n) ? n : null;` — `Number.isFinite(0)` is `true`. In `main` (line 120): `if (args.task === null)` — `0 !== null` so the guard passes. Vault-query.mjs has the same pattern (line 440-441) but task is optional there so it doesn't matter. For record-consumption, where task is required (per-task attribution is the whole point of the record op per §8.5), allowing `0` is a gap.

- **Suggested fix**: Change the validation in `main` to `if (args.task === null || args.task < 1)` — or equivalently, change the parseArgs coercion from `Number.isFinite(n) ? n : null` to `Number.isFinite(n) && n >= 1 ? n : null`.

---

### Finding 3

- **File**: `references/skills/vault-search/scripts/vault-query.mjs`
- **Line**: 466–485
- **Severity**: warning
- **Issue**: The public output (`toPublic`) omits the `updated` frontmatter date that the engine already parses internally for recency scoring. The `rankedEntry` function (line 326) extracts `updated` from frontmatter and passes it to `tieBreakScore` for the recency term — but `toPublic` strips it, exposing only `lastUsed` (derived from telemetry, not the note's own modification date). An agent consuming the metadata-only output has no way to see when a surfaced note was last modified without an additional Read call.

- **Evidence**: `rankedEntry` line 326: `const updated = parseField(n.content, 'updated');` and line 334: `updated` is stored on the entry object. `toPublic` (lines 467–484) enumerates every entry field except `note` and `updated`. The documented output format in SKILL.md (lines 53–67) doesn't list `updated` either. The agent can still Read the note to get the date, but the engine already parsed it — the omission means the agent makes an extra Read for data the engine already has. This is not a lock violation but reduces the utility of the metadata-only contract.

- **Suggested fix**: Add `updated: item.updated || ''` to the `toPublic` return object and document it in SKILL.md's output format example.

---

### Finding 4

- **File**: `tests/test_vault_engine_installer_13857.py`
- **Line**: 68–72 (`test_deploys_skill_packages_to_claude_skills`)
- **Severity**: warning
- **Issue**: The test fixture `make_target` does not create `record-consumption.mjs` in the source skill directory — it only creates `SKILL.md`, `vault-query.mjs`, and `lib/consumption.mjs`. The `copytree` in `install_vault_engine` will therefore deploy only those 3 files, not the full 4-file engine package. The test then asserts that `vault-query.mjs` and `lib/consumption.mjs` are deployed but never asserts `record-consumption.mjs` is deployed. This means the test would keep passing even if `record-consumption.mjs` were accidentally dropped from the installer files manifest — the fixture itself doesn't include it.

- **Evidence**: `make_target` at lines 48–55 creates only `SKILL.md`, `vault-query.mjs`, and `consumption.mjs`. `test_deploys_skill_packages_to_claude_skills` at lines 67–77 asserts only `SKILL.md`, `vault-query.mjs`, and `consumption.mjs` exist at the destination. `TestEnginePresence.test_engine_package_carries_the_ops` (in the boundary test file) verifies the committed source, but the installer-wiring test only verifies 3 of 4 files reach the deployed destination.

- **Suggested fix**: Add `(skill / "scripts" / "record-consumption.mjs").write_text("// record\n", encoding="utf-8")` to `make_target` and add `assert (dest / "scripts" / "record-consumption.mjs").is_file()` to the deploy assertion.