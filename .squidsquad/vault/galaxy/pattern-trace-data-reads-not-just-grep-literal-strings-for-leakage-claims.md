---
type: pattern
tags: [verifier, foreign-repo-safety, greenfield, config-leakage, verification-technique]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: []
---

## Context

Verifying #12527 (greenfield installer smoke test), skill's own load-bearing positive claim was: composed output for a foreign target contains "zero self-references" to the installing (self-hosted) clone, checked by grepping composed `CLAUDE.md` output for literal strings (`SquidSquad-2`, `D:/Dev/Dev`, sibling clone names, etc.). That check passed and was reported as proof the compose engine is "foreign-repo-safe."

## Content

A literal-string self-reference search only catches leakage that is *visible as text* — hardcoded paths, repo names, clone identifiers baked into templates. It does NOT catch **data leakage through a shared code path that reads a value from the wrong source and writes it, verbatim, into output that happens to look plausible**. In this case: `compose.py`'s `_substitute_placeholders` reads config values via `_read_config_value()` → `config.get_field()`, which resolves against `config.CONFIG_PATH` — a path fixed at `config.py` import time to the *installing* script's own repo root, never parameterized by the `target_root` the compose call was explicitly given. Every placeholder substitution sourced this way (`workers`, `alias-pm/qa/dm`, `project-name`, test commands, etc.) silently reads the installing clone's config, not the target's.

This class of bug is invisible to a literal-string diff whenever the leaked value *coincidentally* matches what the target's own correct value would have been — which is exactly what happened here (the leaked `workers` value "skill" matched the target spec's own hardcoded worker id, a SEPARATE bug in the same task). A "zero self-references" result is therefore **necessary but not sufficient** evidence for a foreign-repo-safety claim.

**The stronger technique**: trace the actual *data-read paths* a compose/scaffold engine exercises, not just the rendered text. Concretely: monkeypatch the suspect read function (here, `config.get_field`) to print a stack trace on every call while running the real flow end-to-end. This surfaces every call site touching the config/identity system in one pass, cheaply, and turns "does this look self-hosted-free" into "here is every place this run actually read shared state, and from where."

## Rationale

Verifying a "no leakage" claim by searching for known-bad strings only tests the leaks you already imagined. Tracing what the code actually *reads* during the run tests every leak the code *can produce*, including ones whose current value happens to be innocuous. This generalizes beyond installers: any "isolated from X" / "doesn't touch Y" claim about a code path that reads shared/global state should be checked by tracing the actual reads, not by grepping the output for expected bad values.

## Related

(none yet)

---

### Changelog

- 2026-07-18 — Created by verifier after catching #13595 (source-clone config leak) underneath a passed literal-string self-reference check during #12527's verification.
