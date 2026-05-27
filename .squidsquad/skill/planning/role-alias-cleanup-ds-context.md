# Code review request: role/alias vocabulary cleanup in arch docs

## What this commit does

Three architecture docs (`HARNESS-ARCH.md`, `AGENT-RUNTIME.md`, `INSTALLER-ARCH.md`) were updated to fix a vocabulary mismatch. The codebase uses the identifier `role` everywhere (FastAPI routes `{role}`, `AgentState.role`, `SQUIDSQUAD_ROLE` env var, `--role` CLI flag, dict keys) but the **value** passed in is always the alias (e.g. `skill`, `verifier`, `human`), not the L2 categorical role (`pm` / `qa` / `worker` / `dm`).

This commit fixes the vocabulary in docs **only** — leaving HTTP API path templates `{role}` and CLI flag references like `--role` alone because they faithfully match real FastAPI routes (`harness.py:1406, 1420, 1460...`) and argparse argument names. The underlying code-level rename is tracked separately in #10358.

## Specific edit categories

| Category | What was changed | Why |
|---|---|---|
| On-disk path placeholders | `.squidsquad/<role>/.claude-pid` → `<alias>/.claude-pid`; similarly for `working-state.md`, `.subloop-last-run`, agent directories, clone registry | These directories are literally alias-keyed on disk per `harness.py` `AgentState` keying behavior; calling them `<role>` was misleading |
| Internal data structure descriptions | `dict[role, event_id]` → `dict[alias, event_id]`; "Per-role cursor" → "Per-alias cursor" | The dict keys are alias values |
| State-file JSON shape | `.harness-state.json` outer key `"<role>"` → `"<alias>"`; added inner `"role"` field carrying the categorical role | Outer key is the install-time agent name (alias); the categorical role goes inside |
| Event ID hash input | `sha256(timestamp + role + ...)` → `sha256(timestamp + alias + ...)` prose | The hash incorporates the agent identifier (alias-typed) |
| Vocabulary footnote in §9 | Sharpened to explicitly call out the code-vs-doc mismatch and reference #10358 | Helps readers understand why `{role}` still appears in §4 API table |

## Deliberately NOT changed

- §4 HTTP API path templates `/agents/{role}`, `/events/for/{role}`, etc. — match `@app.get("/agents/{role}")` in `harness.py:1406`
- Response shapes containing `{role, alias, ...}` — match what `AgentState.to_dict()` returns
- CLI references like `event_poll.py --wait --role <role>` — `--role` is the actual argparse flag name in `event_poll.py:354`
- Genuine categorical-role usage like "the L2 role determines responsibilities"

## What I want you to look for

1. **Consistency:** did I miss any `<role>` placeholders in on-disk paths or internal data-structure descriptions across the three docs? (See diff to verify the doc-only scope.)
2. **Correctness:** in HARNESS-ARCH.md §7.5, I rewrote the `.harness-state.json` JSON shape — outer key became `<alias>`, and I added an inner `role` field for the categorical role. Is the resulting shape coherent? Does it match what `harness.py` actually persists?
3. **Doc-vs-code accuracy:** I claim the API path templates `{role}` and the env var name `SQUIDSQUAD_ROLE` are kept because they match real code. Spot-check whether the docs' API table in §4 actually matches `harness.py`'s FastAPI routes.
4. **Voice/clarity:** the vocabulary footnote in §9 is dense. Is it understandable to a reader who hasn't read this audit?
5. **Anything else off:** if you spot bugs, typos, broken cross-references, conflicting prose between the three docs — flag them.

## What's in the diff file

`.squidsquad/skill/planning/role-alias-cleanup-diff.patch` is the full diff for commit 13a958e8 on branch `docs/harness-direct-spawn-draft` (PR #10357). It touches:

- `docs/HARNESS-ARCH.md` (20 lines changed)
- `docs/AGENT-RUNTIME.md` (18 lines changed)
- `docs/INSTALLER-ARCH.md` (10 lines changed)
- `.squidsquad/skill/planning/REVIEW-ROLE-ALIAS-AUDIT.md` (audit record, 105 lines added)

Total: 4 files, 153 insertions, 24 deletions.

## Format of your response

Standard code-review format: list findings categorized by severity (BLOCK / FLAG / NIT), each with file + line reference and a concrete suggested fix. If everything looks good, say so explicitly so I don't second-guess.
