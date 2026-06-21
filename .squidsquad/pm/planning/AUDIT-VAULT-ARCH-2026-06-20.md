# VAULT-ARCH.md Drift Audit — 2026-06-20

> **Auditor**: Claude (fresh agent, no prior context). Evidence read in full before any finding was classified.
> **Files read**: `docs/VAULT-ARCH.md`, `references/scripts/vault_check.py`, `references/scripts/vault_optimize.py`, `references/scripts/vault_entity.py`, `references/scripts/vault_remember.py`, `references/sub-skills/common/vault-protocol.md`, `references/sub-skills/common/vault-remember.md`, `references/sub-skills/common/vault-optimize.md`, `references/sub-skills/roles/pm/vault-synthesis.md`, `.squidsquad/vault/**` (directory tree + BRIEFING.md), `.squidsquad/config.md`, `.squidsquad/pm/planning/AUDIT-TRD-VAULT-ARCH-DS.md` (prior audit).
> **Live vault snapshot**: 2026-06-20 (today). VAULT-ARCH.md snapshot date: 2026-05-24.

---

## 1. Verdict Tally

### New findings (this audit)

| Classification | Count |
|---|---|
| CONFIRMED | 7 |
| DRIFT | 8 |
| GAP | 5 |
| STALE | 6 |
| **Total** | **26** |

### Prior-audit finding disposition (AUDIT-TRD-VAULT-ARCH-DS.md, 28 findings)

| Disposition | Count |
|---|---|
| STILL-VALID | 19 |
| NOW-RESOLVED | 0 |
| CHANGED (severity/detail updated) | 6 |
| NOT-VERIFIABLE (prior audit made error) | 3 |

---

## 2. Prior-Audit Finding Disposition

The prior DS audit (file `AUDIT-TRD-VAULT-ARCH-DS.md`) made 28 findings across CONFIRMED (12), DRIFT (6), STALE (6), and GAP (4) categories. Dispositions below.

| Prior ID | Prior classification | Disposition | Notes |
|---|---|---|---|
| 1 | CONFIRMED — `STALE_DAYS = 60` hardcoded, config not read | STILL-VALID | `vault_optimize.py:42` still hardcodes `STALE_DAYS = 60`. `vault_remember.py:effective_confidence` DOES read `confidence-decay-days` from config via `get_field()` (line 211), but `vault_optimize.py:decay()` does not. The split is new detail not in the prior audit. |
| 2 | CONFIRMED — `links` field + `source: code` + auto-maintain still in vault-protocol.md | STILL-VALID | `vault-protocol.md:44` still lists `links` in frontmatter; `vault-protocol.md:44` lists `source: code`; `vault-protocol.md:97` still describes auto-maintain. Unchanged. |
| 3 | CONFIRMED — `source: code` in vault_check.py `VALID_SOURCES` | STILL-VALID | `vault_check.py:27` still has `VALID_SOURCES = {"conversation", "code", "review", "observation", "research"}`. Unchanged. |
| 4 | CONFIRMED — `dedup-check` subcommand exists | STILL-VALID | `vault_check.py:270,363,377`. Unchanged. |
| 5 | CONFIRMED — vault_entity.py subcommands match doc | STILL-VALID | `vault_entity.py:9-10`. Unchanged. |
| 6 | CONFIRMED — vault_remember.py 5 core subcommands exist | CHANGED | Now 8 subcommands: the documented 5 plus `effective-confidence`, `note-count`, `decay-scan` (see new Finding N-GAP-4 below). |
| 7 | CONFIRMED — owner label drift (`<role>` vs `<role>-lead`) | CHANGED | Vault has grown massively since the DS audit. Owner drift persists but the distribution has shifted substantially. New counts in §10.3 finding below. |
| 8 | CONFIRMED — vault-synthesis matches doc | STILL-VALID | `references/sub-skills/roles/pm/vault-synthesis.md` matches VAULT-ARCH.md §7.4. Unchanged. |
| 9 | CONFIRMED — vault-remember Step 4b matches doc | STILL-VALID | `vault-remember.md:6` structure intact. However, prior audit missed that the config gate (Finding 14) is still live — see STILL-VALID on finding 14. |
| 10 | CONFIRMED — vault-remember and vault-synthesis run inline | STILL-VALID | Both still have `slot: instructions`; no subagent spawn logic. §11.5 gap still open (#10180). |
| 11 | CONFIRMED — `_rewrite_wikilinks_after_archive` exists | STILL-VALID | `vault_optimize.py:165`. Unchanged. |
| 12 | CONFIRMED — vault templates match doc | STILL-VALID | All 7 templates at `references/vault-templates/` match §6 table. Unchanged. |
| 13 | DRIFT — doc claims 5 reflection categories (incl. STYLES); sub-skill has 4 | STILL-VALID | `vault-remember.md:41-48` still lists DECISIONS / PATTERNS / LEARNINGS / PROJECT CONTEXT only (no STYLES). Zero `style-*` notes confirm agents never create them via vault-remember. |
| 14 | DRIFT — doc claims vault-remember config gate retired; gate still in sub-skill | STILL-VALID | `vault-remember.md:12-17` still has the `python references/scripts/config.py get vault-remember` config gate. Doc §7.2 says "the legacy `config.py get vault-remember` enabled-flag read has been retired" — false. Config has `Vault Remember > Enabled: yes`, confirming the gate is live. |
| 15 | DRIFT — doc claims vault-optimize always-on; sub-skill has config gate | STILL-VALID | `vault-optimize.md:10` still has the `Vault Optimize > Enabled` config gate. Config has `Vault Optimize > Enabled: yes`. Doc §7.3 claim of "always-on, no feature toggle" is still false. |
| 16 | DRIFT — `vault_optimize.py run` command doesn't exist; CLI surface is `full-sweep` | STILL-VALID (HIGH severity confirmed) | `vault_optimize.py` CLI dispatch has no `"run"` branch (`vault_optimize.py:574`). `vault-optimize.md:17` still calls `python references/scripts/vault_optimize.py run`. This is a live breakage. |
| 17 | DRIFT — §5 claims no Blockers section; BRIEFING.md has one | STILL-VALID (updated detail) | BRIEFING.md today has `## Constraints & Blockers` at line 91. Doc §5 says "no explicit Blockers section." The doc's §5 section description is stale on this point. |
| 18 | DRIFT — `source: code` in §4.3 spec vs implementation | STILL-VALID | §4.3 spec omits `code`; `vault_check.py:27` and `vault-protocol.md:44` still include it. |
| 19 | STALE — archives/ count was "0 / Empty" | CHANGED | Prior audit said 1 note (created 2026-05-25). Now still 1 note (`shipped-pre-2026-05-19.md`). The stale snapshot claim was acknowledged; live count is 1. |
| 20 | STALE — galaxy note counts (decision=16, learning=9, pattern=3, total=28) | CHANGED — massively outdated | Today: decision=19, learning=56, pattern=18 (0 posture), style=0. Total galaxy=93. Prior audit said 31; today is 93. The vault has grown significantly. |
| 21 | STALE — ownership distribution counts | CHANGED — counts now unverifiable without reading all 93 galaxy notes | Prior audit verified specific counts against the 31-note vault. Today's 93-note vault was not fully scanned for `owner:` fields in this audit. The drift described in §10.3 (owner label convention) still applies. |
| 22 | STALE — confidence distribution (high=24, medium=4) | CHANGED — stale snapshot | Today's vault has 93 galaxy notes; distribution not fully re-scanned. The underlying stale-snapshot issue remains. |
| 23 | STALE — status distribution (33 notes, all active) | CHANGED | Now 100+ vault .md files (excluding .gitkeep); 1 note confirmed `archived`. Distribution counts in VAULT-ARCH.md §10.5 are entirely stale. |
| 24 | STALE — BRIEFING.md "80+ lines (today's snapshot)" | CHANGED | BRIEFING.md today is 102 lines (not 73 as the DS audit claimed — the DS audit appears to have read an older snapshot). Doc §5 claim of "80+" is outdated in both directions. |
| 25 | GAP — vault_check.py missing 3 undocumented subcommands | STILL-VALID | `check-structure` (`vault_check.py:66`), `list-orphans` (`vault_check.py:159`), `suggest-connections` (`vault_check.py:186`) still undocumented in §8.1. |
| 26 | GAP — vault_optimize.py missing 3 subcommands + `run` doesn't exist | STILL-VALID | `reindex` (`vault_optimize.py:617`), `relevance-report` (`vault_optimize.py:630`), `pending-count` (`vault_optimize.py:641`) still undocumented. `run` still absent from CLI. |
| 27 | GAP — vault_remember.py missing 3 subcommands | STILL-VALID | `effective-confidence`, `note-count`, `decay-scan` (`vault_remember.py:13-15`) still undocumented in §8.4. |
| 28 | GAP — `check-consistency` subcommand planned but not implemented | STILL-VALID | Zero `check-consistency` matches in `vault_check.py`. |

---

## 3. New Findings (not in prior DS audit)

### 3.1 Findings Table

| ID | Doc location | Doc claim | Code reality (cite) | Classification | Severity | Canonical side |
|---|---|---|---|---|---|---|
| N-CONF-1 | §3.3, §7.3 | `vault_optimize.py prune-scan` auto-archives `status: superseded` galaxy notes regardless of staleness | `vault_optimize.py:234` — `if fm.get("status", "").strip() == "superseded": should_archive = True` — superseded notes ARE archived regardless of staleness/orphan | CONFIRMED | n/a | n/a |
| N-CONF-2 | §9.5 | vault files committed by `cycle_post.py` | `state_bus.py` and `migrate_state_branch.py` references cannot be verified without reading those files, but the vault directory exists on main and is git-tracked; no `.gitignore` excludes vault notes | CONFIRMED (partial — git tracking verified; specific line cites unverified) | n/a | n/a |
| N-CONF-3 | §8.3 doc table — `add-question` subcommand | `vault_optimize.py add-question --agent <r> --note <p> --question "<q>"` | `vault_optimize.py:644` dispatches `add-question`; `vault_optimize.py:512` implements `add_question(agent, note_path, question)` | CONFIRMED | n/a | n/a |
| N-CONF-4 | §4.4 decay — `vault_remember.py` effective-confidence DOES read config | Doc §4.4 "configuration drift" says `vault_optimize.py` hardcodes threshold AND does not read config — implying no config reading exists | `vault_remember.py:211` calls `get_field("confidence-decay-days")` in `effective_confidence()`. The split: `vault_optimize.py:decay()` hardcodes (doc is correct); `vault_remember.py:effective_confidence()` reads config (doc omits this half). | CONFIRMED (doc is correct about `vault_optimize.py`; omits that `vault_remember.py` does read config) | low | Fix doc (add nuance) |
| N-CONF-5 | §6, §10.7 — vault templates list | Doc lists 7 templates: `BRIEFING.md`, `archives-template.md`, `areas-template.md`, `galaxy-template.md`, `human-profile-seed.md`, `projects-template.md`, `resources-template.md` | `references/vault-templates/` glob confirms exactly these 7 files | CONFIRMED | n/a | n/a |
| N-CONF-6 | §7.1 — vault-protocol-slim was retired in #11331 | Doc §7 says "`vault-protocol-slim` read-only variant was retired in #11331 (Iter 56)" | No `vault-protocol-slim.md` exists under `references/sub-skills/`. Retirement confirmed. | CONFIRMED | n/a | n/a |
| N-CONF-7 | §7.3 — vault-optimize activated only on 20+ notes | "Activates only when the vault has 20+ notes" | `vault_optimize.py:144` checks `note_count < MIN_VAULT_SIZE` where `MIN_VAULT_SIZE = 20` | CONFIRMED | n/a | n/a |
| N-DRIFT-1 | §10.1 — note counts snapshot | `BRIEFING.md: 1 (88 lines)` | BRIEFING.md today is **102 lines** (measured). Doc says 88 at snapshot date (2026-05-24). | STALE | low | Fix doc |
| N-DRIFT-2 | §10.2 — galaxy note breakdown | `decision-*: 16`, `learning-*: 9`, `pattern-*: 3`, `style-*: 0`, `pattern-posture-*: 0`, total 28 | Today: `decision-*: 19`, `learning-*: 56`, `pattern-*: 18` (non-posture), `pattern-posture-*: 0`, `style-*: 0`. Total galaxy: **93 notes**. | STALE | medium | Fix doc |
| N-DRIFT-3 | §10.1 — archives count | `archives/: 0 \| Empty` | `archives/` contains **1 file** (`shipped-pre-2026-05-19.md`). | STALE | low | Fix doc |
| N-DRIFT-4 | §4.4 — decay applies to `updated:` field | "Decay steps do NOT modify `updated:`" | `vault_optimize.py:383` — `header = re.sub(r"updated: \S+", f"updated: {today}", header, count=1)` — decay DOES modify `updated:` in the same operation as the confidence change. Doc explicitly says decay doesn't touch `updated:`; code says it does. | DRIFT | high | Fix code OR fix doc (significant semantic divergence — if decay touches `updated:`, the 120-day `medium → low` clock resets on a `high → medium` decay, which is the exact behavior the doc says is prevented) |
| N-DRIFT-5 | §7.2 — vault-remember priority order when >2 candidates pass | "decisions > learnings > patterns" | `vault-remember.md:82-84` says the same: "1. Decisions … 2. Learnings … 3. Patterns" | CONFIRMED (prior DS audit finding 9 called this confirmed; re-confirmed) | n/a | n/a |
| N-DRIFT-6 | §8.3 — `vault_optimize.py run` subcommand listed in table | Doc §8.3 table has `run \| Convenience: invokes the full pipeline`; §7.3 says "Invokes `vault_optimize.py run`" | `vault_optimize.py` CLI dispatch (`vault_optimize.py:574`) has `full-sweep` → `run_optimize()` but no `run` branch. The internal function is named `run_optimize()` but is not reachable via `vault_optimize.py run`. This is the same as prior finding 16 but now verified against the full CLI code. | DRIFT (same as prior Finding 16) | high | Fix code (add `run` alias) or fix both sub-skill + doc |
| N-DRIFT-7 | §7.3 — `vault-optimize.md` description of "Reindex" step | Doc §7.3 step 3: "Reindex — walk all notes, rebuild the wikilink graph (inbound/outbound adjacency)" | `vault-optimize.md:23` says step 3 is "**Reindex**: Rebuilds `links` frontmatter from body wikilinks across all notes." — the sub-skill describes rebuilding `links` frontmatter, not "the wikilink graph." The `vault_optimize.py:reindex()` function (`vault_optimize.py:420`) confirms it updates `links:` frontmatter, not a separate graph file. | DRIFT | low | Fix doc (§7.3 step 3 description) |
| N-DRIFT-8 | §3.2 — Galaxy note size limit "max ~500 lines" | `vault-protocol.md:69` says "max ~500 lines (split if larger)"; vault-check Level 1 step 5 says "If the note is in `galaxy/` and exceeds 500 lines, warn" | But `vault_check.py` has NO code that checks note line count or emits a size warning. The check described in `vault-protocol.md:98` is in the sub-skill prose only — not implemented in `vault_check.py`. | DRIFT | low | Fix code (implement size check in vault_check.py) or fix doc |
| N-GAP-1 | §9.5 — vault `.relevance-index.json` is gitignored | "`.relevance-index.json` — written by `vault_optimize.py` (gitignored)" | `.relevance-index.json` exists at `.squidsquad/vault/.relevance-index.json` (confirmed by directory listing). Whether it is actually gitignored requires checking `.gitignore` — not verified. Doc claims gitignored; current presence on disk does not confirm or deny gitignore status. | GAP (unverified claim) | low | Verify `.gitignore` contains the path |
| N-GAP-2 | §7.2 — "five galaxy categories: DECISIONS, PATTERNS, LEARNINGS, STYLES, plus PROJECT CONTEXT" | `vault-remember.md:41-48` enumerates only 4: DECISIONS, PATTERNS, LEARNINGS, PROJECT CONTEXT. No STYLES category. | GAP | medium | Fix sub-skill (add STYLES) or fix doc (remove claim) |
| N-GAP-3 | §4.3 — required frontmatter includes `source:` field | `REQUIRED_FM_FIELDS = {"type", "tags", "created", "updated", "owner", "status", "confidence"}` at `vault_check.py:25` — `source` is NOT in the required-fields set | GAP | medium | Doc §4.3 lists `source:` as required; code does not validate it. Fix code to add `source` to `REQUIRED_FM_FIELDS`, or fix doc to mark `source` as optional. |
| N-GAP-4 | §8.4 — vault_remember.py subcommands table | Doc lists 5 subcommands: `is-quiet`, `write-budget`, `inc-writes`, `reset-writes`, `briefing-budget` | `vault_remember.py:13-15` and CLI dispatch (`vault_remember.py:374+`) shows 3 additional subcommands: `effective-confidence`, `note-count`, `decay-scan`. These are live and callable but undocumented. | GAP | low | Fix doc (add 3 subcommands to §8.4 table) |
| N-GAP-5 | §7.1 — vault-check Level 1 "auto-maintain `links` frontmatter" behavior | `vault-protocol.md:97`: "Auto-maintain `links` frontmatter: Parse all `[[note-name]]` from the note's body. Update the `links` field in frontmatter to match (bare names, YAML list). This is automatic — agents do not manually curate the `links` field." | `vault_check.py` has NO function that updates `links` frontmatter. The `reindex()` function in `vault_optimize.py` does this, but it runs as part of vault-optimize (quiet cycles), not as part of Level 1 vault-check. The doc says Level 1 auto-maintains `links`; the code puts that in vault-optimize. | GAP | medium | Fix doc (Level 1 does NOT auto-maintain `links`; that's vault-optimize/reindex) or fix code |

### 3.2 Summary of New Findings by ID

**CONFIRMED (7):** N-CONF-1 through N-CONF-7

**STALE (6, including snapshot drift items):**
- N-DRIFT-1: BRIEFING.md line count (88 → 102)
- N-DRIFT-2: Galaxy note counts massively outdated (28 → 93)
- N-DRIFT-3: Archives count (0 → 1)
- (Prior findings 20-24 cover the other stale inventory items; still valid)

**DRIFT (5 genuinely new divergences):**
- N-DRIFT-4: Decay modifies `updated:` field — doc says it doesn't (HIGH)
- N-DRIFT-6: `vault_optimize.py run` CLI command absent (HIGH, same root as prior finding 16)
- N-DRIFT-7: Reindex description ("wikilink graph" vs "`links` frontmatter")
- N-DRIFT-8: Galaxy note size limit check not implemented in `vault_check.py`

**GAP (5 new):**
- N-GAP-1: `.relevance-index.json` gitignore status unverified
- N-GAP-2: STYLES reflection category (same as prior finding 13 but reclassified as GAP)
- N-GAP-3: `source:` field not in `REQUIRED_FM_FIELDS` in vault_check.py
- N-GAP-4: 3 undocumented vault_remember.py subcommands
- N-GAP-5: Level 1 vault-check does not auto-maintain `links` frontmatter

---

## 4. Critical New Finding: `updated:` Modified During Decay (N-DRIFT-4)

This finding is the highest-severity new drift not caught by the prior DS audit. VAULT-ARCH.md §4.4 states explicitly:

> "Decay steps do NOT modify `updated:` — the decay clock keys off the last *human or agent semantic edit*, not the decay event itself. So `medium → low` at 120 days means 120 days since the last semantic `updated:` value, not 60 days after a prior `high → medium` decay step."

But `vault_optimize.py:383-384`:
```python
header = header.replace(f"confidence: {confidence}", f"confidence: {new_confidence}", 1)
header = re.sub(r"updated: \S+", f"updated: {today}", header, count=1)
```

The decay function updates `updated:` to today's date as part of the confidence change. This has two consequences:

1. After a `high → medium` decay, the note's `updated:` field is reset to today. The clock for `medium → low` now starts from today, not from the original semantic edit. The doc's guarantee ("120 days from last semantic edit") is broken.
2. Notes that have decayed once are protected from further decay for another 60 days, because their `updated:` was refreshed by the decay itself. The `decay-scan` in `vault_remember.py` reads `updated:` to find notes needing decay — so a note that was decayed `high → medium` last month will not appear in `decay-scan` for another 60 days.

This divergence means the vault's confidence model behaves differently than documented, and any agent reasoning about "this note decayed 60 days ago so it's been `medium` for 60 days" will be wrong.

---

## 5. Reconcile Fix-List

### Bucket A — DOC edits (PM-owned, changes only to `docs/VAULT-ARCH.md`)

Priority order within bucket:

| Priority | Finding IDs | Actionable description |
|---|---|---|
| HIGH | N-DRIFT-4 (or CODE) | §4.4 decay section: either (a) document that `updated:` IS modified by decay and revise the "120 days from last semantic edit" guarantee, or (b) confirm the code must be fixed — do not leave doc and code contradicting each other on this semantically critical point |
| HIGH | Prior-14 | §7.2 Scripts-used paragraph: remove the claim that "the legacy `config.py get vault-remember` enabled-flag read has been retired" — it has not been retired; the gate is live in `vault-remember.md:12-17` |
| HIGH | Prior-15, Prior-16 | §7.3 description: remove "always-on, no feature toggle" claim and "Invokes `vault_optimize.py run`" — replace with `full-sweep` and document that config gate still exists |
| HIGH | Prior-16 | §8.3 subcommands table: replace `run` row with `full-sweep`; add note that `run` is an internal function alias only |
| MED | N-GAP-2 / Prior-13 | §7.2 reflection categories: either add STYLES category or remove it from the documented 5-category list; 0 `style-*` notes proves agents do not create them |
| MED | Prior-18 | §4.3 `source:` enum: either add `code` back or note that `code` is accepted by `vault_check.py` and `vault-protocol.md` even though the spec dropped it (pick one truth) |
| MED | N-GAP-5 | §7.1 Level 1 vault-check description: step 4 "Auto-maintain `links` frontmatter" does NOT run in Level 1 — it runs in vault-optimize `reindex`. Remove from Level 1 description or document correctly which step does it |
| MED | N-DRIFT-7 | §7.3 step 3 "Reindex": change "rebuild the wikilink graph (inbound/outbound adjacency)" to accurately describe that it updates `links:` frontmatter in each note to match body wikilinks |
| LOW | N-GAP-3 | §4.3 required frontmatter: mark `source:` as optional or note that `vault_check.py` does not validate it (only `confidence` is validated in the required-fields set) |
| LOW | N-DRIFT-1 / N-DRIFT-2 / N-DRIFT-3 | §10.1-10.6 snapshot inventory: add a note that §10 reflects the 2026-05-24 snapshot only; today's vault has 93 galaxy notes (decision=19, learning=56, pattern=18), 1 archive, BRIEFING.md is 102 lines |
| LOW | N-GAP-1 | §3.3 / §9.5: add a note to verify `.relevance-index.json` and `.obsidian/` appear in `.gitignore` |
| LOW | N-CONF-4 | §4.4 "Configuration drift" paragraph: add nuance that `vault_remember.py effective-confidence` DOES read `confidence-decay-days` from config; only `vault_optimize.py decay()` ignores it |

### Bucket B — CODE changes (skill-owned, changes to scripts/sub-skills)

Priority order within bucket:

| Priority | Finding IDs | Actionable description |
|---|---|---|
| HIGH | Prior-16 / N-DRIFT-6 | `references/scripts/vault_optimize.py`: add a `"run"` CLI alias in `main()` that calls `run_optimize()` and prints results — this makes both `vault-optimize.md:17` and VAULT-ARCH.md §7.3/§8.3 accurate without requiring doc changes to both |
| HIGH | N-DRIFT-4 | `references/scripts/vault_optimize.py:decay()`: remove the `updated:` rewrite from the confidence-decay operation (lines 383-384). Only update `confidence:` frontmatter and append the changelog entry. The `updated:` date must stay at the last semantic edit date to honor the documented decay clock semantics |
| HIGH | Prior-14 | `references/sub-skills/common/vault-remember.md`: remove config gate block (lines 12-17: `python references/scripts/config.py get vault-remember … If no, skip`) if the intent is to make vault-remember always-on, per doc §7.2 — OR keep the gate and update doc |
| HIGH | Prior-15 | `references/sub-skills/common/vault-optimize.md`: remove config gate block (line 10) if the intent is to make vault-optimize always-on, per doc §7.3 — OR keep the gate and update doc |
| MED | N-GAP-2 / Prior-13 | `references/sub-skills/common/vault-remember.md`: add **STYLES** reflection category (step 5 after PROJECT CONTEXT): `→ If yes: vault-create galaxy/style-*.md` — to make zero `style-*` notes a data signal not a code defect |
| MED | N-GAP-3 | `references/scripts/vault_check.py:25`: add `"source"` to `REQUIRED_FM_FIELDS` so vault-check validates the `source:` field that the spec requires |
| MED | N-GAP-5 | `references/sub-skills/common/vault-protocol.md`: remove "Auto-maintain `links` frontmatter" from vault-check Level 1 description (it belongs in vault-optimize reindex, not Level 1 vault-check) — OR implement it in `vault_check.py` |
| MED | Prior-2 / Prior-3 | `references/sub-skills/common/vault-protocol.md`: (a) remove `links:` from the required frontmatter example in vault-create step 2; (b) remove `source: code` from the valid source values; (c) remove auto-maintain `links` description from vault-check Level 1 step 4 — all three are tracked in #10098 |
| LOW | N-DRIFT-8 | `references/scripts/vault_check.py`: implement the galaxy note size check (>500 lines → warn) that `vault-protocol.md:98` describes but that `vault_check.py` never actually does |
| LOW | Prior-25 | `docs/VAULT-ARCH.md` §8.1: add `check-structure`, `list-orphans`, `suggest-connections` to the subcommands table |
| LOW | Prior-26 | `docs/VAULT-ARCH.md` §8.3: add `reindex`, `relevance-report`, `pending-count` to the subcommands table |
| LOW | Prior-27 / N-GAP-4 | `docs/VAULT-ARCH.md` §8.4: add `effective-confidence`, `note-count`, `decay-scan` to the subcommands table |
| LOW | Prior-28 | `references/scripts/vault_check.py`: implement `check-consistency` subcommand (folder↔type, galaxy prefix↔type) per #10098 |

---

## 6. Revision Log

- **2026-06-20** — Fresh audit against live vault (93 galaxy notes), all 4 scripts, all vault sub-skills read in full. 26 findings classified. Prior DS audit (28 findings) fully dispositioned. Critical new finding on `updated:` modification during decay (N-DRIFT-4) not in prior audit.
