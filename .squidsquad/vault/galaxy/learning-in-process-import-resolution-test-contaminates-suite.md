---
type: learning
tags: [skill, testing, pytest, sys-modules, import-isolation, collection-order, regression-test]
created: 2026-06-17
owner: skill
status: active
confidence: high
source: observation
links: [learning-tests-must-not-mutate-shared-live-state, decision-deterministic-testing, learning-gate-collection-abort-masks-reds]
---

## Context

#12509 fixed a basename shadow (`tests/integration/harness.py` shadowed
`references/scripts/harness.py`, breaking bare `pytest tests/` collection). The
*fix* (rename) was correct and uncontested. The **regression test** took THREE
QA rejections (cy251 / cy270 / cy273), all on one function that tried to assert
`import harness` resolves to the real supervisor module *at runtime, in-process*:

- cy251: `sys.modules.pop("harness")` + live `import harness`, `finally` restored
  only `sys.path` — left a re-imported, divergent module bound.
- cy270: snapshot+restore the `sys.modules` key, then `importlib.util.find_spec`
  (no execute, no `sys.modules` mutation). Helped (7→5 failures) but did NOT clear it.
- cy273: even find_spec + `sys.path.insert(0, SCRIPTS_DIR)` still diverged module
  identity in a full-suite run. Pinned by deselect: dropping the fn → 13 passed clean.

The residual was a **collection-order interaction**: running that fn in-suite
diverged the `harness` module object that a *sibling* test
(`test_feat_10681`'s `patch("harness.HARNESS_STATE_FILE")`) had bound at
collection time — so the patch redirected a different object than the assertion
checked. Order-dependent, invisible when the file runs alone.

## Lesson

**A test that asserts module-resolution by touching import state contaminates
the whole suite.** `sys.modules` pop/restore is the obvious vector, but even the
"clean" forms (`find_spec`, `sys.path.insert`) perturb global resolution enough
to break sibling `patch("mod.attr")` assertions through collection order. Two
in-process attempts to tame it both failed; the third QA round correctly said
*drop it*. "Passes when run alone" ≠ "safe in `pytest tests/`".

The regression you actually need is usually **structural, not behavioral**: a
filesystem check (the colliding basename is absent / a general "no test-dir
module shadows a `references/scripts/` module" scan) locks the exact bug class
with ZERO import machinery and cannot contaminate anything. A reintroduced
collision fails it.

## How to apply

- Locking an import/shadow/resolution bug? Prefer a **filesystem-level** guard
  (presence/absence, basename-collision scan) over asserting runtime resolution.
- If runtime resolution genuinely must be asserted, run it in a **subprocess**
  (`subprocess.run([sys.executable, "-c", ...])`) so all import-state side
  effects die with the child — never in-process.
- When a sibling's `patch("mod.attr")` starts failing only in a full run, suspect
  another test mutated `sys.modules`/`sys.path` for `mod`. See
  [[learning-tests-must-not-mutate-shared-live-state]] (the live-state analogue).
- Example of the structural form: `tests/test_12509_no_harness_basename_shadow.py`
  (the surviving two guards + a NOTE block recording why the third was dropped).
