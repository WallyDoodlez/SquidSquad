Based on my thorough review of all four changed files and extensive searching for other code paths that might read vault enable/disable config, here is my assessment:

---

**Check 1: Other code paths that read vault enable/disable config**

- `config.py:101,105` — key-map entries for `vault-remember` and `vault-optimize`. These are intentionally-left harmless dead keys (per task context). Nothing live reads them via `config.py get vault-remember` or `config.py get vault-optimize`.
- `vault_remember.py` — reads `vault-writes-per-cycle` (line 124) and `interval` (line 77) from config, but never reads a `vault-remember` enable/disable field. It has no `_is_config_enabled()` equivalent.
- `wizard.py:1533,3411` — hardcodes `vault_remember: True` in generated config, already consistent with always-on.
- `vault_optimize.py` — `_is_config_enabled()` (line 96) now unconditionally returns `True`. Both callers (`_check_guards()` line 139, `run_optimize()` line 531) are internal to this file.
- No other Python module imports `vault_optimize` or reads `vault-remember`/`vault-optimize` enable/disable from config.

**Conclusion: No inconsistent code path exists.**

**Check 2: Downstream consumers of cycle-input.json's vault_remember/vault_optimize keys**

The keys appear in `cycle-input.json` under `config.vault_remember` and `config.vault_optimize`. The consumers are the LLM agent's creative phase (via sub-skill markdown). Both `references/sub-skills/common/vault-remember.md:13` and `references/sub-skills/common/vault-optimize.md:10` already declare "always-on — there is no enable/disable toggle," with activation gated by quiet-cycle, note-count, and cooldown. Hardcoding `True` in cycle-input.json is consistent with the always-on intent.

**Conclusion: No breakage.**

**Check 3: Test correctness**

- `test_vault_flags_always_on_regardless_of_config` — correctly patches `_config_get` to return `"no"` and then `""` for all fields, and asserts `vault_remember`/`vault_optimize` are `True` in both cases. This directly verifies the hardcoding in `_read_config_flags()` and would catch a regression if the function were changed back to reading config (since `"no" in _YES` → `False`).

- `test_config_enabled_field_is_ignored_always_on` — writes `Enabled: no` to config.md, then calls `_check_guards()`, and asserts the guards pass (`ok=True`). This verifies that `_is_config_enabled()` does not gate on config content. The `patched_vault` fixture provides 25 notes (above the 20-note threshold), so the other guards also pass. If `_is_config_enabled()` were reverted to read config, this test would fail (config says "no" → disabled → guards return False).

Both tests are deterministic and correctly verify the always-on behavior.

**Conclusion: Tests are correct.**

---

NO_FINDINGS