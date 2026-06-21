**Observation**: In `_load_manifest_v2_from_file`, a wrong-TYPE `additional_includes` (e.g. a YAML author writes `additional_includes: common/cycle-runner` — a bare string — instead of a list) is silently reset to an empty list with no diagnostic:

    additional = data.get("additional_includes", []) or []
    if not isinstance(additional, list):
        additional = []        # <- silent: no warning, no error

The variant's additional sub-skills are then silently omitted from the composed CLAUDE.md. This is **fail-open** and inconsistent with every adjacent path in the same function, which all surface the problem:
- `base_role` missing v2 manifest → `sys.exit(1)` (compose.py:285-291)
- a listed `additional_includes` entry whose `.md` is missing → `sys.exit(1)` (compose.py:297-303)
- base-manifest `includes` wrong type → `return None` (compose.py:309-310)

Only the wrong-type `additional_includes` case is swallowed silently → a manifest schema typo yields silently-incomplete agent instructions with zero diagnostic. (The `isinstance` guard itself is correct — a bare string is iterable and would otherwise iterate characters — but it must not be silent.)

**Location**: `references/scripts/compose.py:293-294` — `_load_manifest_v2_from_file`.

**Suggested-fix**: Make the wrong-type case fail-closed to match its siblings — either `sys.exit(1)` (preferred, matches the `base_role`-missing schema-error path) or at minimum a `print(... file=sys.stderr)` WARNING before the reset:

    if not isinstance(additional, list):
        print(f"ERROR: {manifest_path.name} for {role_name}: `additional_includes` is "
              f"{type(additional).__name__}, expected list", file=sys.stderr)
        sys.exit(1)

Add a regression test (no test currently exercises this branch — `grep additional_includes tests/` shows only valid-list cases). Deterministic code → no CQ, no manifest.

_Filed via improvement-scan (skill, idle cool-down). Default low priority; not auto-fixed — human/PM triages._
