# Audit Report

## Executive summary
- **8 findings**: 2 HIGH, 3 MED, 3 LOW.
- **Single biggest theme**: The `l4-curation.md` sub-skill defines a bucket called `soul-directives` that does not exist in the canonical architecture — the composed output has exactly five slots (`identity`, `soul`, `instructions`, `project-context`, `vault`), and `soul-directives` is not one of them. This creates a factual contradiction with `COMPOSE-ARCHITECTURE.md` and would block an implementer.

---

## HIGH findings

### H1 — `l4-curation.md` defines a non-existent L4 bucket `soul-directives`

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 2 table, step 5 table, and step 6 preamble
- **Quote**: `| `soul-directives` | who the role *is* — values, tone, professional identity, priorities |` and `| `.squidsquad/project/<role>-soul-directives.md` | per-role personality/values overlay |`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §5 defines exactly five top-level H2 sections: `identity`, `soul`, `instructions`, `project-context`, `vault`. The `soul` slot already covers "who the role is" — there is no `soul-directives` slot, no `soul-directives` op grammar, and no compose pipeline path that would process a file named `*-soul-directives.md`. An implementer following `l4-curation.md` would write L4 files that `compose.py` would either ignore or reject as invalid. This is a direct contradiction with the canonical slot model.
- **Fix**: Remove the `soul-directives` bucket entirely. All "who the role is" customizations flow through the existing `soul` slot using the standard op grammar (`replace`, `insert-after`, `append`). The `l4-curation.md` dialog should map "who the role is" requests to `slot: soul` with `op: append` (or `replace` for core trait overrides), not to a separate bucket.

### H2 — `l4-curation.md` defines a file-naming convention that contradicts `COMPOSE-ARCHITECTURE.md` §7.3

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 5 table
- **Quote**: `| `.squidsquad/project/<role>-instructions.md` | per-role instruction override |` and `| `.squidsquad/project/shared-instructions.md` | rule that applies to *every* role |`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §7.3 specifies the L4 file naming convention as `<slot>-<short-kebab-description>.md` (e.g., `instructions-pre-check-incidents.md`). The `l4-curation.md` convention uses `<role>-<bucket>.md` and `shared-<bucket>.md` — a completely different scheme. An implementer would not know which naming convention to follow, and `compose.py` would need to support both (which it doesn't — the spec only defines one). Furthermore, `l4-curation.md`'s scheme conflates role-scoping with the file name, while `COMPOSE-ARCHITECTURE.md` §7.3 has no role-scoping in the file name at all (role is implicit from the output directory).
- **Fix**: Align `l4-curation.md`'s file-naming guidance with `COMPOSE-ARCHITECTURE.md` §7.3: files are named `<slot>-<short-kebab-description>.md`. Role-scoping (if needed) should be handled via frontmatter `roles:` list (per `COMPOSE-ARCHITECTURE.md` §11.1 open question 3), not encoded in the filename. The "shared" concept is not defined in the architecture and should be removed.

---

## MED findings

### M1 — `l4-curation.md` step 6 references `insert` op, which does not exist in the canonical op grammar

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 6
- **Quote**: `| `insert` — new rule that should appear at a specific position within an L1–L3 section.`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §3.3 defines exactly four L4 ops: `append`, `insert-before`, `insert-after`, `replace`. There is no bare `insert` op. An implementer writing `op: insert` would get a validation failure from `compose.py` (per §4.2 step 4: "no orphan L4 file"). The `l4-curation.md` dialog should distinguish between `insert-before` and `insert-after`, not collapse them into a single ambiguous `insert`.
- **Fix**: Replace `insert` with `insert-before` or `insert-after` in the dialog guidance. The agent-internal decision should pick one based on whether the new rule should appear before or after the anchor step — the dialog with the human can ask "should this happen before or after [existing behaviour]?" without exposing the op names.

### M2 — `l4-curation.md` step 6 mentions `anchor` field, but `COMPOSE-ARCHITECTURE.md` uses `target`

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 6
- **Quote**: `The `anchor` points to the L1–L3 location.`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §3.3 defines the field as `target` (e.g., `target: step:cycle/file-bug`), not `anchor`. An implementer writing `anchor: step:cycle/file-bug` in L4 frontmatter would produce a file that `compose.py` cannot parse — the frontmatter schema expects `target`. This is a terminology mismatch that would cause silent failures (the file would be treated as having no target, and `insert-before`/`insert-after` ops without a target would fail validation).
- **Fix**: Replace all instances of `anchor` with `target` in `l4-curation.md`. The dialog should describe the concept functionally ("which existing behaviour this new rule relates to") without using either term in user-facing language.

### M3 — `l4-curation.md` step 8 says "compose pipeline runs the DeepSeek audit + mini-CQ gate", but `COMPOSE-ARCHITECTURE.md` §7.4 places those gates *before* compose runs

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 8
- **Quote**: `Persist via compose §7` (agent-internal). The compose pipeline runs the DeepSeek audit + mini-CQ gate.
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §7.4 specifies the safety gates in this order: (1) DeepSeek audit, (2) mini-CQ (human confirmation), (3) compose dry-run (`--check`). The gates run *before* the L4 file is written to disk — the compose dry-run validates the file would resolve cleanly, but the actual write+commit happens only after all three gates pass. `l4-curation.md` implies the gates are part of the compose pipeline itself, which would mean the file is already written before validation completes. This creates an ambiguity about when the file hits disk relative to the safety checks.
- **Fix**: Reword step 8 to match `COMPOSE-ARCHITECTURE.md` §7.4's sequence: "The agent then runs the DeepSeek audit on the proposed L4 entry, presents the draft to the human for mini-CQ confirmation, and runs `compose.py --check` as a dry-run. Only after all three gates pass does the agent write the file and commit." Remove the phrase "compose pipeline runs" — the gates are agent-side, not compose-side.

---

## LOW findings

### L1 — `l4-curation.md` step 2 bucket table says "Scope additions or restrictions flow through `instructions`", but `COMPOSE-ARCHITECTURE.md` §6.3 says "never-do prohibitions that are step-specific live in the sub-skill"

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 2
- **Quote**: `Scope additions or restrictions (what's in/out of a role's lane) flow through `instructions` — they're rules the role follows during its cycle`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §6.3 explicitly states that step-specific prohibitions (which are a form of scope restriction) live in the *sub-skill* source file, not in the composed orchestration. If a scope restriction is step-specific (e.g., "worker should not touch Dockerfile changes" — which would be a restriction on the `step:cycle/implement-task` step), it should be authored in the relevant sub-skill, not as an L4 instructions entry. The `l4-curation.md` guidance is too broad and would lead implementers to create L4 entries that duplicate or contradict sub-skill-level content.
- **Fix**: Add a qualification: "Scope additions or restrictions that apply broadly across a role's entire behaviour flow through `instructions`. Step-specific scope restrictions (e.g., 'don't do X during Y') should be authored in the relevant sub-skill's source file, not as an L4 entry — see COMPOSE-ARCHITECTURE §6.3."

### L2 — `l4-curation.md` step 5 table includes `shared-instructions.md` and `shared-soul-directives.md`, but `COMPOSE-ARCHITECTURE.md` has no concept of "shared" L4 files

- **Where**: `references/sub-skills/common/l4-curation.md` — "The elicitation dialog" step 5 table
- **Quote**: `| `.squidsquad/project/shared-instructions.md` | rule that applies to *every* role |`
- **Why it's a problem**: `COMPOSE-ARCHITECTURE.md` §7.3 defines L4 files as per-role: `compose.py deploy <role>` walks `.squidsquad/project/*.md` and applies them to the current role's composition. There is no mechanism for a single L4 file to apply to multiple roles — the `roles:` frontmatter list is listed as an open question in §11.1 (item 3), not a supported feature. An implementer writing `shared-instructions.md` would create a file that `compose.py` processes for every role, potentially causing unintended cross-role contamination or DRY violations.
- **Fix**: Remove the "shared" file concept from `l4-curation.md`. If a rule applies to every role, the agent should write one L4 file per role (or the feature should be implemented first — see `COMPOSE-ARCHITECTURE.md` §11.1 open question 3). Add a note that multi-role L4 files are deferred.

### L3 — `l4-curation.md` says "L4 curation is one-shot and durable" but `COMPOSE-ARCHITECTURE.md` §7.7 says the same — this is consistent but the cross-reference is missing

- **Where**: `references/sub-skills/common/l4-curation.md` — "Purpose" section, final paragraph
- **Quote**: `L4 curation is **one-shot and durable**: each customization is captured once via the dialog below, written to the right L4 file, and then persists across cycles without further intervention.`
- **Why it's a problem**: This is not a contradiction — both docs agree. However, the `l4-curation.md` statement lacks a cross-reference to `COMPOSE-ARCHITECTURE.md` §7.7, which contains the canonical definition of the one-shot+durable property. An implementer reading only `l4-curation.md` might miss the nuance in §7.7 about drift detection (caught at recompose time, not by a separate curation pass) and the conflict-resolution rules.
- **Fix**: Add a parenthetical cross-reference: "(see COMPOSE-ARCHITECTURE §7.7 for the drift-detection and conflict-resolution semantics that make this durable model safe)."

---

## What's working well

1. **The L1-L4 slot model is internally consistent across both architecture docs.** `COMPOSE-ARCHITECTURE.md` §5 defines five slots with clear ordering and content rules; `AGENT-RUNTIME.md` correctly references these slots without introducing new ones. The slot enum (`identity=0, soul=1, instructions=2, project-context=3, vault=4`) is unambiguous.

2. **The wake-mode handling (§6.5 in COMPOSE, §8.1 in AGENT-RUNTIME) is precisely specified.** The two parallel manifests, compose-time selection via `config.get_wake_mode()`, the prohibition on mode-conditional directives inside fragments, and the rule that mode flips require recompose+restart are all consistent across both docs. The worked examples in §5.6 showing exactly which sections diverge between modes is excellent.

3. **The step ID grammar (§6.1 in COMPOSE) is fully formalized** with BNF, character set restrictions, nesting depth limits, and global uniqueness rules. The step↔sub-skill mapping rules (1:1 default, N:1 allowed, 1:N forbidden) are explicit and would prevent a class of implementation bugs.

4. **The source-output sync mechanisms (§8 in COMPOSE) are well-structured** with three reinforcing layers (PR check, auto-recompose on merge, pre-ship gate) and clear failure modes. The defence-in-depth approach is appropriate for the "invisible bug" class of composed output drift.

5. **The cursor model and at-least-once delivery semantics in AGENT-RUNTIME are precisely specified** — harness-owned cursor, agent never writes it directly, `HTTP 410 Gone` for evicted cursors with a recovery path, and the sequence diagrams in §7.1 and §4.3 are unambiguous. The invariant that "agents do not write to harness-owned files; harness does not write to agent-owned files" is a clean architectural boundary.