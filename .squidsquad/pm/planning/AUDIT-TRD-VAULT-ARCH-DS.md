Now I have all the evidence needed. Let me compile the comprehensive audit.

---

# VAULT-ARCH.md Audit — Findings Report

## Summary Table

| Verdict | Count |
|---|---|
| CONFIRMED | 12 |
| DRIFT | 6 |
| STALE | 6 |
| GAP | 4 |
| IN PROGRESS | 0 |
| HELD | 0 |

---

## CONFIRMED Findings

### Finding 1

- **TRD section**: §4.4 — Confidence Decay, "Configuration drift" paragraph
- **Verdict**: CONFIRMED
- **Evidence**: `references/scripts/vault_optimize.py:42` hardcodes `STALE_DAYS = 60`. No code reads `Confidence Decay Days` from `.squidsquad/config.md`. The `_is_config_enabled()` function (`vault_optimize.py:96-107`) only reads the enabled flag, not the decay days field.
- **Severity**: low (doc already acknowledges this, tracked in #10099)

### Finding 2

- **TRD section**: §7.1 — vault-protocol source-vs-spec drift (links field, source:code, auto-maintain behavior)
- **Verdict**: CONFIRMED
- **Evidence**: `references/sub-skills/common/vault-protocol.md:33` lists `links` as a required frontmatter field. `vault-protocol.md:35` lists `source: code` as valid. `vault-protocol.md:88` describes auto-maintain `links` behavior ("Parse all `[[note-name]]` from the note's body. Update the `links` field in frontmatter to match"). None of these three behaviors are implemented in `vault_check.py` — it checks for `links` as a required field but the doc says it was dropped.
- **Severity**: medium (sync tracked in #10098)

### Finding 3

- **TRD section**: §7.1 — `source: code` value dropped per §4.3 spec
- **Verdict**: CONFIRMED (with nuance)
- **Evidence**: §4.3 spec lists `source: conversation | review | observation | research` (no `code`). But `vault-protocol.md:35` lists `source`: `conversation`, `code`, `review`, `observation`, `research` and `vault_check.py:27` has `VALID_SOURCES = {"conversation", "code", "review", "observation", "research"}`. The spec dropped `code` but both implementation files still include it.
- **Severity**: medium

### Finding 4

- **TRD section**: §8.1 — `dedup-check` subcommand exists in vault_check.py
- **Verdict**: CONFIRMED
- **Evidence**: `references/scripts/vault_check.py:270` defines `dedup_check()`, line 363 dispatches `cmd == "dedup-check"`, line 377 shows `--title` + `--tags` usage. Matches doc exactly.
- **Severity**: N/A

### Finding 5

- **TRD section**: §8.2 — vault_entity.py subcommands (extract, extract --file)
- **Verdict**: CONFIRMED
- **Evidence**: `references/scripts/vault_entity.py:9-10` shows usage matches doc: `extract "<text>"` and `extract --file <path>`.
- **Severity**: N/A

### Finding 6

- **TRD section**: §8.4 — vault_remember.py subcommands (is-quiet, write-budget, inc-writes, reset-writes, briefing-budget)
- **Verdict**: CONFIRMED
- **Evidence**: `references/scripts/vault_remember.py:8-12` shows all five subcommands exist as documented.
- **Severity**: N/A

### Finding 7

- **TRD section**: §10.3 — Owner label drift (`<role>` vs `<role>-lead`)
- **Verdict**: CONFIRMED
- **Evidence**: 6 notes use `skill-lead`, 2 use `pm-lead`. Spec in §4.3 says `owner: pm | worker | verifier | dm | shared` (no `-lead` suffix). Affected notes: `decision-clone-isolation-architecture.md`, `decision-comprehension-test-pipeline.md`, `decision-cycle-runner-architecture.md`, `decision-local-config-priority.md`, `learning-commit-code-state-exclusion.md`, `learning-create-test-environments.md`, `learning-l4-only-fix-skips-pr-flow.md`, `learning-migration-6274-cutover.md`.
- **Severity**: low (doc already self-reports this in §10.3)

### Finding 8

- **TRD section**: §7.4 — vault-synthesis path, behavior, cycle counter, activation gates
- **Verdict**: CONFIRMED
- **Evidence**: `references/sub-skills/roles/pm/vault-synthesis.md:1-60` matches doc: 5-consecutive-quiet-cycle counter, 10+ galaxy note gate, 5-step process, max 1 posture per cycle, `pattern-posture-*` naming, `confidence: medium`, requires human approval. Composed only for PM (line 3: `roles: [pm]`).
- **Severity**: N/A

### Finding 9

- **TRD section**: §9.4 — Post-cycle Step 4b vault-remember integration
- **Verdict**: CONFIRMED
- **Evidence**: `references/sub-skills/common/vault-remember.md:6` (`### Step 4b — Vault Remember (End-of-Cycle Reflection)`), staleness check at lines 16-23 (always runs, doesn't consume budget), quiet-cycle gate at lines 25-29, write budget at lines 31-34, 4-gate filter at lines 47-65.
- **Severity**: N/A

### Finding 10

- **TRD section**: §11.5 — vault-remember and vault-synthesis run inline (not as background subagents)
- **Verdict**: CONFIRMED
- **Evidence**: Both `references/sub-skills/common/vault-remember.md` and `references/sub-skills/roles/pm/vault-synthesis.md` have `slot: instructions` and are composed directly into the consuming agent's CLAUDE.md. No subagent spawn logic exists in either file. Doc's self-reported gap in §11.5 is accurate — filed as #10180.
- **Severity**: N/A (self-reported gap)

### Finding 11

- **TRD section**: §3.3 — `_rewrite_wikilinks_after_archive` function exists
- **Verdict**: CONFIRMED
- **Evidence**: `references/scripts/vault_optimize.py:165` defines `_rewrite_wikilinks_after_archive(note_name, notes)`. Called at line 273 after prune operations. Matches doc's description.
- **Severity**: N/A

### Finding 12

- **TRD section**: §6 — Vault templates exist on disk
- **Verdict**: CONFIRMED
- **Evidence**: All 7 templates at `references/vault-templates/` match doc's table: `BRIEFING.md`, `archives-template.md`, `areas-template.md`, `galaxy-template.md`, `human-profile-seed.md`, `projects-template.md`, `resources-template.md`.
- **Severity**: N/A

---

## DRIFT Findings

### Finding 13

- **TRD section**: §7.2 — "five galaxy categories: DECISIONS, PATTERNS, LEARNINGS, STYLES, plus PROJECT CONTEXT"
- **Verdict**: DRIFT
- **Evidence**: `references/sub-skills/common/vault-remember.md:38-45` lists only 4 categories: DECISIONS, PATTERNS, LEARNINGS, PROJECT CONTEXT. STYLES is missing. The doc claims 5 categories including STYLES, but the actual sub-skill only evaluates 4.
- **Severity**: medium — agents will never create `style-*` notes from vault-remember reflection (consistent with §10.2 showing 0 `style-*` notes)
- **Suggested action**: Either add STYLES category to `vault-remember.md` or update §7.2 to match the actual 4-category implementation.

### Finding 14

- **TRD section**: §7.2 — "always-on, no feature toggle" / "the legacy `config.py get vault-remember` enabled-flag read has been retired"
- **Verdict**: DRIFT
- **Evidence**: `references/sub-skills/common/vault-remember.md:10-14` still contains the config gate: "Check vault-remember setting: `python references/scripts/config.py get vault-remember`. If `no`, skip this step entirely." The doc claims this was retired, but the source still has it.
- **Severity**: high — the doc makes a definitive claim about a feature toggle being removed that still exists in the sub-skill that agents execute every cycle
- **Suggested action**: Remove the config gate from `vault-remember.md` lines 10-14, or update §7.2 to reflect the actual state.

### Finding 15

- **TRD section**: §7.3 — "always-on, no feature toggle (the quiet-cycle + note-count gates already provide sufficient activation control)"
- **Verdict**: DRIFT
- **Evidence**: `references/sub-skills/common/vault-optimize.md:10` still has: "**Config gate**: Check `Vault Optimize > Enabled` in `config.md`. If `no`, skip entirely." The doc claims no feature toggle, but the sub-skill has one.
- **Severity**: medium
- **Suggested action**: Remove the config gate from `vault-optimize.md` line 10, or update §7.3 to match.

### Finding 16

- **TRD section**: §7.3 / §8.3 — "Invokes `vault_optimize.py run`" convenience subcommand
- **Verdict**: DRIFT
- **Evidence**: `references/sub-skills/common/vault-optimize.md:17` says `python references/scripts/vault_optimize.py run`. VAULT-ARCH.md §8.3 table lists `run` as a subcommand. But `references/scripts/vault_optimize.py:565-644` shows the actual CLI dispatch: the command is `full-sweep`, not `run`. There is no `"run"` branch in the CLI dispatch. The Python function is called `run_optimize()` (line 531), but the CLI surface is `full-sweep`. Both the doc AND the sub-skill reference a command that doesn't exist.
- **Severity**: high — if an agent pastes the sub-skill's `vault_optimize.py run` command, it will get "Unknown command: run" and exit code 1
- **Suggested action**: Either add a `"run"` CLI alias in `vault_optimize.py` that maps to `run_optimize()`, or update both `vault-optimize.md:17` and VAULT-ARCH.md §7.3/§8.3 to say `full-sweep`.

### Finding 17

- **TRD section**: §5 — BRIEFING.md table: "no explicit Blockers section"
- **Verdict**: DRIFT
- **Evidence**: `.squidsquad/vault/BRIEFING.md:64` has `## Constraints & Blockers` heading with 3 bullet points (harness unreachable, pending backlog, event-driven architecture). The doc claims no explicit Blockers section, but one exists.
- **Severity**: low
- **Suggested action**: Update §5 table to reflect that BRIEFING.md now has a Constraints & Blockers section.

### Finding 18

- **TRD section**: §4.3 — `source:` enum: `conversation | review | observation | research` (no `code`)
- **Verdict**: DRIFT
- **Evidence**: §4.3 spec excludes `code`. But `references/scripts/vault_check.py:27` has `VALID_SOURCES = {"conversation", "code", "review", "observation", "research"}` and `references/sub-skills/common/vault-protocol.md:35` lists `source: code` as valid. The spec and implementation disagree on whether `code` is valid.
- **Severity**: medium — notes with `source: code` would pass validation but violate the §4.3 spec
- **Suggested action**: Align spec and code — either remove `code` from `vault_check.py` and `vault-protocol.md`, or add it back to §4.3.

---

## STALE Findings

### Finding 19

- **TRD section**: §10.1 — archives/ count: "0 | Empty"
- **Verdict**: STALE
- **Evidence**: `.squidsquad/vault/archives/shipped-pre-2026-05-19.md` exists (created 2026-05-25, `status: archived`). The doc's snapshot date is 2026-05-24, so this was accurate at snapshot time but is now stale.
- **Severity**: medium
- **Suggested action**: Update §10.1 to reflect actual archive count of 1.

### Finding 20

- **TRD section**: §10.2 — Galaxy note breakdown: decision=16, learning=9, pattern=3 (total 28)
- **Verdict**: STALE
- **Evidence**: Actual counts from `.squidsquad/vault/galaxy/`: decision=18, learning=10, pattern=3 (total 31). Three new notes added since the 2026-05-24 snapshot.
- **Severity**: medium
- **Suggested action**: Update §10.2 counts.

### Finding 21

- **TRD section**: §10.3 — Ownership distribution counts
- **Verdict**: STALE
- **Evidence**: Doc claims galaxy-only: pm=9, skill=11, skill-lead=6, pm-lead=2. Actual counts from grep: pm=11, skill=12, skill-lead=6, pm-lead=2. pm and skill counts shifted by +2 and +1 respectively.
- **Severity**: low
- **Suggested action**: Update §10.3 counts.

### Finding 22

- **TRD section**: §10.4 — Confidence distribution: high=24, medium=4, low=0
- **Verdict**: STALE
- **Evidence**: Actual counts from `.squidsquad/vault/galaxy/` frontmatter: high=26, medium=5, low=0. Shifted by +2 high, +1 medium.
- **Severity**: low
- **Suggested action**: Update §10.4 counts.

### Finding 23

- **TRD section**: §10.5 — Status distribution: "whole vault, 33 notes" / "All... active"
- **Verdict**: STALE
- **Evidence**: Non-BRIEFING vault notes now total 37 (2 projects + 2 areas + 1 resources + 1 archives + 31 galaxy). 36 active + 1 archived (`shipped-pre-2026-05-19.md`). BRIEFING.md has no YAML frontmatter so isn't in the status distribution count.
- **Severity**: medium
- **Suggested action**: Update §10.5 with actual counts (37 notes, 36 active, 1 archived).

### Finding 24

- **TRD section**: §5 — BRIEFING.md: "80+ lines (today's snapshot)"
- **Verdict**: STALE
- **Evidence**: `.squidsquad/vault/BRIEFING.md` is 73 lines. The doc claims 80+ but the file has been trimmed (entries graduated to `archives/shipped-pre-2026-05-19.md` as noted on line 29).
- **Severity**: low
- **Suggested action**: Update §5 to reflect actual 73 lines.

---

## GAP Findings

### Finding 25

- **TRD section**: §8.1 — vault_check.py subcommands table
- **Verdict**: GAP
- **Evidence**: Doc lists 4 subcommands: `validate`, `check-frontmatter`, `check-wikilinks`, `dedup-check`. Three implemented subcommands are undocumented: `check-structure` (`vault_check.py:66-88`), `list-orphans` (`vault_check.py:159-183`), `suggest-connections` (`vault_check.py:186-250`).
- **Severity**: low — agents can still discover these via `--help`
- **Suggested action**: Add the missing subcommands to §8.1 table.

### Finding 26

- **TRD section**: §8.3 — vault_optimize.py subcommands table
- **Verdict**: GAP
- **Evidence**: Doc lists: `full-sweep`, `prune-scan`, `consolidate-scan`, `decay-apply`, `add-question`, `run`. Missing from doc: `reindex` (`vault_optimize.py:420-448`), `relevance-report` (`vault_optimize.py:451-498`), `pending-count` (`vault_optimize.py:501-529`). Additionally, `run` is documented but doesn't exist as a CLI command (see Finding 16).
- **Severity**: low
- **Suggested action**: Add `reindex`, `relevance-report`, `pending-count` to §8.3 table. Replace `run` with `full-sweep`.

### Finding 27

- **TRD section**: §8.4 — vault_remember.py subcommands table
- **Verdict**: GAP
- **Evidence**: Doc lists: `is-quiet`, `write-budget`, `inc-writes`, `reset-writes`, `briefing-budget`. Missing from doc: `effective-confidence` (`vault_remember.py:13,402-407`), `note-count` (`vault_remember.py:14,408-410`), `decay-scan` (`vault_remember.py:15,411+`).
- **Severity**: low
- **Suggested action**: Add missing subcommands to §8.4 table.

### Finding 28

- **TRD section**: §4.2a — "checked manually today; planned to be enforced by a future `vault_check.py check-consistency` subcommand (tracked in #10098)"
- **Verdict**: GAP
- **Evidence**: `references/scripts/vault_check.py` has no `check-consistency` subcommand — grep confirms zero matches. The consistency rules (folder↔type, galaxy prefix↔type) are documented in §4.2a but have no automated enforcement.
- **Severity**: medium — folder/type/prefix agreement has no validation at all today
- **Suggested action**: Implement `check-consistency` subcommand per #10098, or mark as explicitly deferred with a timeline.

---

## Items NOT Flagged (IN PROGRESS / HELD per manifest)

None of the gaps or drifts above are covered by the in-flight or held items in the audit manifest:

- **E6 V2 CUTOVER (#10685)**: Compose/skill cutover — unrelated to vault
- **PRD-D Sub-skills as Claude Skills (#10781)**: Sub-skill format change — could incidentally affect vault sub-skills, but doesn't address any gap listed above
- **E7 (#10686)**: V2 migration smoke — unrelated to vault
- **D6 (#10677)**: Config field removal — unrelated to vault
- **#10690**: Wiki-link cross-reference rework — related to wikilinks but doesn't address vault-remember categories, config gates, or script subcommand gaps

---

## Summary of Actual Issues Requiring Action

| Priority | Finding | Issue |
|---|---|---|
| **HIGH** | #16 | `vault_optimize.py run` doesn't exist — both VAULT-ARCH.md §7.3/§8.3 and `vault-optimize.md:17` reference a non-existent CLI command |
| **HIGH** | #14 | Doc claims vault-remember config gate is retired, but `vault-remember.md:10-14` still has it |
| **MEDIUM** | #13 | Doc claims 5 categories (includes STYLES); actual sub-skill has 4 — STYLES notes will never be created by vault-remember |
| **MEDIUM** | #15 | Doc claims vault-optimize is always-on; `vault-optimize.md:10` has a config gate |
| **MEDIUM** | #18 | `source: code` dropped from §4.3 spec but still valid in vault-protocol.md and vault_check.py |
| **MEDIUM** | #19-#24 | Six stale inventory claims (§10.1-10.5, §5) — counts shifted since 2026-05-24 snapshot |
| **MEDIUM** | #28 | `check-consistency` subcommand planned but not implemented |
| **LOW** | #25-#27 | Three script subcommand tables missing implemented commands |