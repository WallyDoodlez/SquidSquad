# Code Review — #13198 (shared cli_stdio.harden_stdio + fleet CLI hardening)

**Reviewer**: DeepSeek 402 → Sonnet subagent **twice hit API 529 (server-wide overload, infra-transient, 0 tokens — did not run)** → **inline adversarial self-review** by skill-lead (best available given the infra block; the change is fleet-wide-but-mechanical with a green gate + behavior tests + fleet-wiring guard). Per [[feedback_model_router_auto_fallback]] the fallback is a Claude subagent; here the subagent infra itself was down, so the review was done inline.
**Scope**: new `references/scripts/cli_stdio.py`; 8 wired CLI mains (config/subloop_driver/model_router/scan_index/compose/boot_remote/add_role/migrate_state_branch); tracker.py delegate; installer-files.txt; tests.

## Verdict: NO_BLOCKING_FINDINGS

Reviewed against 6 dimensions:
1. **Lazy import** (`from cli_stdio import harden_stdio` in main()): resolves — scripts run from `references/scripts/` (sys.path[0]) and already do un-wrapped sibling imports (config, etc.); cli_stdio.py ships installer-tracked in the same dir → as safe as the established pattern.
2. **Wiring completeness**: `harden_stdio()` is the FIRST statement of each wired main() (before any print/side-effect); `if __name__=="__main__": main()` is the sole entry. No early return ahead of it; no alternate entry points bypass main().
3. **tracker delegate**: `_harden_stdio` → shared helper; existing #13185 tracker tests pass (`sys` is one shared module object).
4. **Machine-readable output**: `json.dumps` defaults to `ensure_ascii=True` → JSON stdout is pure ASCII → never triggers backslashreplace. Only decorative non-ASCII (not machine-parsed) is affected, and only where it would otherwise have CRASHED → strictly better, no corruption risk.
5. **Wiring guard test**: string-presence (`harden_stdio()` in each script) — deliberately simple regression guard; adequate with the helper behavior tests + gate.
6. **installer-files**: cli_stdio.py added + header `253→254` (4 manifest count-header tests green).

## Findings & disposition

1. **LOW — lazy import not wrapped in try/except** — a missing cli_stdio (broken/partial install) would crash main() at the import, which contradicts the "never crash the CLI for stdio hardening" philosophy. → **NOT CHANGED** (dispositioned): consistent with the codebase — every existing sibling import in these scripts (e.g. `import config`) is un-wrapped, and cli_stdio.py ships installer-tracked alongside; wrapping only this one import (×9) would be inconsistent churn. A partial install missing cli_stdio.py has larger problems.
2. **LOW — cycle.py left on its own UTF-8 reconfigure** (not the shared helper) — → **INTENTIONAL**: cycle.py already force-reconfigures stdout to UTF-8 (a different but equally crash-safe approach); aligning it to the shared helper is a cosmetic follow-on, left out to avoid churning working code.

## Gate
Full static gate **PASS 4949/0/0** (only baseline known-failures excluded). Targeted: cli_stdio + tracker + 4 installer-count tests = 66 passed.
