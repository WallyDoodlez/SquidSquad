# DS-fallback review — Iter 40 (G10 close)

## Verdict: PASS-WITH-WARNINGS

## Findings

### F1 — `get_alias` has no FIELD_MAP entry for `worker` or `verifier` class names [INFO]

**File**: `references/scripts/config.py:545-556` (`get_alias`), `references/scripts/config.py:69-74` (FIELD_MAP alias entries)

`get_alias(role)` builds the lookup key as `alias-{role}` and consults `FIELD_MAP`. The registered alias keys are `alias-skill`, `alias-pm`, `alias-dm`, `alias-designer`, `alias-qa` — no `alias-worker` or `alias-verifier`. If `$ROLE` is passed as the canonical role-class name `worker` or `verifier`, `get_alias` falls through to `return role` and emits the bare class name. The shell logic then evaluates `ALIAS == $ROLE`, so `ROLE_LABEL="$ROLE"` — the raw class name. This is functionally correct (the label shows `worker` or `verifier`, which is accurate), but the asymmetry in the FIELD_MAP means the alias lookup silently degrades for these two classes. If an install ever declares a separate alias for the verifier role class (e.g. `alias-verifier: qe`), that key would need to be added to FIELD_MAP before the new logic could resolve it. Pre-existing limitation, not introduced by this commit; no behavioral regression here.

No fix required for G10 scope. Worth a follow-up note to track the FIELD_MAP gap for `worker`/`verifier` class aliases.

---

### F2 — `config.py alias` error path: stdout contamination risk [WARNING]

**File**: `references/statusline.sh:169`

```sh
ALIAS=$(python references/scripts/config.py alias "$ROLE" 2>/dev/null) || true
```

`2>/dev/null` suppresses stderr from `config.py`, which is correct. However, `get_alias` currently never prints error text to stdout — it always either returns the alias string or the bare role name. But the `|| true` guard only protects against non-zero exit codes crashing the shell via `set -e`; it does NOT prevent `ALIAS` from capturing unexpected stdout content if `config.py` were changed in the future to emit a warning prefix on stdout (e.g. a deprecation notice).

The consequence would be: `ALIAS` picks up the warning text, `[ "$ALIAS" != "$ROLE" ]` is true, and `ROLE_LABEL` becomes the warning string rather than the role label. This is a fragility in the interface contract, not a current defect. Low probability given Python's convention of using stderr for warnings, but worth noting.

**Recommended fix** (low-urgency): add a caller-side validation that `ALIAS` looks like a plausible alias (e.g., no whitespace, length < 32) before trusting it, or pin `config.py alias` to stdout-clean output in its docstring.

---

### F3 — Empty `$ROLE` guard is upstream; shell block has no local guard [INFO]

**File**: `references/statusline.sh:25` (upstream guard), `references/statusline.sh:169-174` (new block)

The empty-`$ROLE` case is fully handled by `[ -z "$ROLE" ] && exit 0` at line 25, which fires before the alias-resolution block at line 169. There is no gap. Documented here only to confirm the guard was verified rather than assumed.

---

### F4 — `[ROLE]` substitution confirmed correct: alias is the substitution value [INFO]

**File**: `references/scripts/compose.py:1230`, `references/scripts/compose.py:648`

`compose.py deploy <alias>` calls `_substitute_placeholders(body, alias, role)` where `alias` is the install's configured alias string (e.g. `dm`, `pm`, `qa`, `skill`). Inside `_substitute_placeholders`, `content.replace("[ROLE]", role_name)` substitutes the alias literal. The four L2 source files (`references/roles/{dm,pm,verifier,worker}/instructions.md`) now carry `` `[ROLE]` role label ``; compose correctly resolves these to `` `dm` role label ``, `` `pm` role label ``, `` `qa` role label ``, `` `skill` role label `` respectively. Verified against the current composed outputs in `.squidsquad/{dm,pm,qa,skill}/CLAUDE.md` — no `[ROLE]` leaks.

---

### F5 — Backward compat: uppercase `DM`/`PM`/`QA` → lowercase `dm`/`pm`/`qa` is intentional but visible [WARNING]

**Scope**: UX change for all existing installs where the role alias matches the role-class name

On installs that ran before this commit, the statusline showed `DM`, `PM`, `QA` in uppercase because the old tier-2 fallback (`elif [ "$ROLE" = "pm" ]; then ROLE_LABEL="PM"`) fired. After this commit, installs where alias == role-class name (the common case) will show lowercase `dm`, `pm`, `qa`. The commit message explicitly documents this as intentional and notes the portability win.

This is not a defect but it is a visible change for every operator who reads the statusline. The old behavior was a hardcoded lie on non-standard installs (e.g. verifier aliased to `qe` still saw `QA`); the new behavior is consistent but lowercase. Any external scripts, screenshots, or user expectations tied to the uppercase labels will be mismatched post-upgrade.

No regression in correctness; potential friction in UX documentation or onboarding materials that show the old uppercase form. If operator-facing docs show `QA role label` screenshots, they should be updated.

---

### F6 — `worker` L2 source: `[ROLE]` replaces "Your role label" rather than a hardcoded uppercase label [INFO]

**File**: `references/roles/worker/instructions.md:105` (post-commit), diff hunk lines 196-201

The diff shows the worker line changed from `- Your role label and current iteration number` to `` - `[ROLE]` role label and current iteration number ``. The pre-commit wording was prose without backtick-wrapping; the post-commit wording adds backtick formatting around the alias, consistent with the dm/pm/verifier treatment. Minor formatting improvement, no behavioral gap. Composed output for the `skill` alias: `` `skill` role label `` — correct.

---

## Summary

The refactor is mechanically sound. Shell error-handling is correct given the upstream `[ -z "$ROLE" ]` guard and `2>/dev/null` stderr suppression. The `[ROLE]` placeholder substitution is confirmed to use the alias (not the role-class) as its resolved value, which is the right source of truth. Composed CLAUDE.md files show no placeholder leaks. The only items flagging above WARNING are: (F2) a latent stdout-contamination fragility in the `config.py alias` interface contract, and (F5) a visible UX change (uppercase → lowercase labels) that is intentional but may require doc/screenshot updates.
