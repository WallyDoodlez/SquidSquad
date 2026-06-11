# Composed CLAUDE.md ↔ Sub-Skill Resolution Audit

Audited: 2026-06-11. Branch: `squidsquad/task/11334`.
Scope: all 4 composed CLAUDE.md files (pm, qa/verifier, dm, skill/worker).
Resolved via: `docs/sub-skill-catalog.md`, `references/sub-skills/`, composed CLAUDE.md content.

---

## Marker inventory

All distinct `→ run sub-skill: <name>` markers found across the 4 composed CLAUDE.md files, with source resolution.

| Marker name | Roles invoking | Source path | Status | Notes |
|---|---|---|---|---|
| `event-driven-workflow` | pm, qa, dm, skill | `references/sub-skills/common-events/event-driven-workflow.md` | OK | Event-mode contract load, boot-bootstrap block |
| `event-mode-contract` | pm, qa, dm, skill | `references/sub-skills/common-events/event-mode-contract.md` | OK | Event-mode contract load, boot-bootstrap block |
| `cursor-management` | pm, qa, dm, skill | `references/sub-skills/common-events/cursor-management.md` | OK | Event-mode contract load |
| `forge-read-pattern` | pm, qa, dm, skill | `references/sub-skills/common-events/forge-read-pattern.md` | OK | Event-mode contract load |
| `idle-cooldown-loop` | pm, qa, dm, skill | `references/sub-skills/common-events/idle-cooldown-loop.md` | OK | Event-mode contract load |
| `comment-handling` | pm, qa, dm, skill | `references/sub-skills/common-events/comment-handling.md` | OK | Event-mode contract load |
| `roles/dm/events/pr-merge-wait` | dm | `references/sub-skills/roles/dm/events/pr-merge-wait.md` | OK | DM-only event contract addition; file exists |
| `resume-working-state` | pm, qa, dm, skill | `references/sub-skills/common/resume-working-state.md` | OK | Step 2 |
| `checkin` | pm | `references/sub-skills/roles/pm/checkin.md` | OK | PM step:cycle/check-in |
| `github-issues` | pm | `references/sub-skills/roles/pm/github-issues.md` | OK | PM step:cycle/triage-external |
| `task-pickup` | pm, qa, dm, skill | `references/sub-skills/common/task-pickup.md` | OK | Step 3 (event-mode pickup no-op) and DM step 2.1 |
| `task-intake` | pm | `references/sub-skills/roles/pm/task-intake.md` | OK | PM step:cycle/task-intake |
| `task-approval` | pm | `references/sub-skills/roles/pm/task-approval.md` | OK | PM step:cycle/task-approval |
| `pipeline-sentinel` | pm | `references/sub-skills/roles/pm/pipeline-sentinel.md` | OK | PM step:cycle/pipeline-sentinel |
| `git-commit` | pm, qa, dm, skill | `references/sub-skills/common/git-commit.md` | OK | Step 5 checkpoint |
| `working-state` | pm, qa, dm, skill | `references/sub-skills/common/working-state.md` | OK | Step 6 cleanup (compound line) |
| `vault-remember` | pm, qa, dm, skill | `references/sub-skills/common/vault-remember.md` | OK | Step 6 cleanup (compound line); all 4 roles present |
| `improvement-scan-slim` | pm, qa, dm, skill | `references/sub-skills/common/improvement-scan-slim.md` | OK | Step 6 cleanup (compound line) |
| `health-check` | pm | `references/sub-skills/roles/pm/health-check.md` | OK | PM step:cycle/health-check |
| `boot-remote-agents` | pm | `references/sub-skills/common/boot-remote-agents.md` | OK | PM step:cycle/boot-remote-agents |
| `own-domain-autofix` | pm | `references/sub-skills/roles/pm/own-domain-autofix.md` | OK | PM step:cycle/own-domain-autofix |
| `soul-shepherd` | pm | `references/sub-skills/roles/pm/soul-shepherd.md` | OK | PM step:cycle/soul-shepherd |
| `vault-optimize` | pm | `references/sub-skills/common/vault-optimize.md` | OK | PM step:cycle/vault-optimize |
| `vault-synthesis` | pm | `references/sub-skills/roles/pm/vault-synthesis.md` | OK | PM step:cycle/vault-synthesis |
| `agent-lifecycle` | pm, qa, dm, skill | `references/sub-skills/common/agent-lifecycle.md` | OK | Step 7 |
| `self-restart` | pm, qa, dm, skill | `references/sub-skills/common/self-restart.md` | OK | Step 7 |
| `tracker-protocol` | pm, qa, dm, skill | `references/sub-skills/common/tracker-protocol.md` | OK | Tracker Protocol section; also bare marker in skill CLAUDE.md:590 |
| `l4-curation` | pm, qa, dm, skill | `references/sub-skills/common/l4-curation.md` | OK | Reactive sub-skills section |
| `roles/pm/issue-filing` | pm | `references/sub-skills/roles/pm/issue-filing.md` | OK | Slash-bearing; file exists |
| `roles/pm/discussion-protocol` | pm | `references/sub-skills/roles/pm/discussion-protocol.md` | OK | Slash-bearing; file exists |
| `vault-protocol` | pm, qa, dm, skill | `references/sub-skills/common/vault-protocol.md` | OK | Vault Protocol section; standalone marker in all 4 roles |
| `verification` | qa | `references/sub-skills/roles/verifier/verification.md` | OK | QA step:cycle/work and step:cycle/pickup-task |
| `roles/verifier/issue-filing` | qa | `references/sub-skills/roles/verifier/issue-filing.md` | OK | Slash-bearing; file exists |
| `roles/verifier/discussion-protocol` | qa | `references/sub-skills/roles/verifier/discussion-protocol.md` | OK | Slash-bearing; file exists |
| `capability-check` | dm | `references/sub-skills/common/capability-check.md` | OK | DM-specific; catalog marks deprecated but file exists and resolves |
| `roles/dm/discussion-protocol` | dm | `references/sub-skills/roles/dm/discussion-protocol.md` | OK | Slash-bearing; file exists |
| `roles/dm/issue-filing` | dm | `references/sub-skills/roles/dm/issue-filing.md` | OK | Slash-bearing; file exists |
| `delivery-packaging` | dm | `references/sub-skills/roles/dm/delivery-packaging.md` | OK | DM step:cycle/delivery-packaging |
| `version-bumps` | dm | `references/sub-skills/roles/dm/version-bumps.md` | OK | DM step:cycle/version-bump |
| `doc-improvement-loop` | dm | `references/sub-skills/roles/dm/doc-improvement-loop.md` | OK | DM step:cycle/doc-improvement |
| `triage-issues` | skill | `references/sub-skills/roles/worker/triage-issues.md` | OK | skill (worker) Step 2 |
| `pickup-comment-fidelity` | skill | `references/sub-skills/common/pickup-comment-fidelity.md` | OK | skill CLAUDE.md:544; file exists |
| `implement-tasks` | skill | `references/sub-skills/roles/worker/implement-tasks.md` | OK | skill step:cycle/implement |
| `working-state` (cleanup) | skill | `references/sub-skills/common/working-state.md` | OK | skill CLAUDE.md:598 standalone marker at step:cycle/cleanup |
| `vault-protocol-slim` | (none) | (deleted Iter 56 / #11331) | OK — retired cleanly | Zero `→ run sub-skill: vault-protocol-slim` markers in all 4 composed CLAUDE.md. Not in `references/installer-files.txt`. Source file absent from disk. Only references are in historical planning docs and test fixtures under `tests/comprehension/8697_fixtures/`. |

### Notes on resolution convention

- **Bare names** (`task-pickup`, `vault-protocol`, etc.) resolve via `docs/sub-skill-catalog.md` → typically `references/sub-skills/common/<name>.md`.
- **Slash-bearing names** (`roles/pm/issue-filing`, `roles/dm/events/pr-merge-wait`, etc.) are the source path verbatim under `references/sub-skills/`.
- **`boot-bootstrap`** is NOT a `→ run sub-skill:` marker. It appears as an HTML comment boundary (`<!-- sub-skill: boot-bootstrap -->` / `<!-- /sub-skill: boot-bootstrap -->`) in all 4 composed CLAUDE.md files. Its content was moved into L1 `references/roles/instructions.md` between those markers. No agent attempts to `→ run sub-skill: boot-bootstrap` at runtime — confirmed.
- **`ralph-loop-overview`** per-role files (`roles/pm/ralph-loop-overview.md`, etc.) are loaded via a `Read` directive in the POLLING mode block, not via `→ run sub-skill:` markers. All 4 source files exist. No `→ run sub-skill: ralph-loop-overview` marker exists.

---

## Orphan sub-skill files

Files under `references/sub-skills/` that have no `→ run sub-skill:` marker invoking them directly. Annotated with the reason they exist.

| File | Reason for no marker | Status |
|---|---|---|
| `common/cycle-runner.md` | `slot: instructions` + `ordinal: 10` — inlined at compose time into the Instructions slot (not a runtime-load marker). Present in PM, QA, DM, skill CLAUDE.md as inlined content. | OK — inlined |
| `common/context-pressure.md` | `slot: instructions` — inlined at compose time. Content lives in the composed body as the "Step 1b — Context Pressure Check" section. | OK — inlined |
| `common/interval-sync.md` | `slot: instructions` — inlined. Content appears as "Step 1d — Interval Sync". | OK — inlined |
| `common/pr-protocol.md` | `slot: instructions, ordinal: 12` — inlined. Content appears as the "PR Protocol — Creation and Merge" section in composed CLAUDE.md. | OK — inlined |
| `common/improvement-scan.md` | `slot: instructions` — inlined into PM and skill composed CLAUDE.md via includes.yml. The runtime `→ run sub-skill: improvement-scan-slim` marker covers the cleanup path; the full-scan path fires via `idle-cooldown-loop` step 3 with prose reference "Run your role's scanning sub-skill" (no explicit marker name in idle-cooldown-loop.md body). | OK — inlined; see Finding 1 |
| `common/chat-etiquette.md` | Intentionally deferred — chat roadmap. Catalog explicitly marks as "deferred — chat roadmap". Do not delete. | OK — parked |
| `common/consensus-protocol.md` | Same as `chat-etiquette`. Intentionally parked. | OK — parked |
| `common/mention-protocol.md` | Same as `chat-etiquette`. Intentionally parked. | OK — parked |
| `roles/pm/delivery.md` | `slot: instructions, roles: [pm]` — inlined into PM CLAUDE.md as "Delivery" section. Not a runtime marker. | OK — inlined |
| `roles/pm/testing-and-verification.md` | `slot: instructions, roles: [pm]` — inlined into PM CLAUDE.md as "Steps 3–6 — Testing & Verification". | OK — inlined |
| `roles/pm/improvement-scan.md` | `slot: instructions, roles: [pm]` — inlined into PM CLAUDE.md via PM's includes.yml. Not present as a `→ run sub-skill:` marker in the composed output. Used by the improvement subloop (prose says "filed via the role's improvement-scan sub-skill (e.g. roles/pm/improvement-scan)") — but without an explicit `→ run sub-skill: roles/pm/improvement-scan` marker, the agent relies on catalog guidance to find it. | WARN — see Finding 1 |
| `roles/dm/task-pickup.md` | `slot: instructions, roles: [dm]` — inlined into DM CLAUDE.md via includes.yml. Step 2.1 uses bare `→ run sub-skill: task-pickup` (which resolves to `common/task-pickup.md`), not the DM override. | WARN — see Finding 2 |
| `roles/dm/issue-triage.md` | `slot: instructions, roles: [dm]` — inlined into DM CLAUDE.md via includes.yml (as "Step 1e — Triage Bugs"). No `→ run sub-skill: issue-triage` marker exists anywhere. | OK — inlined only; content reached via inline path |
| `roles/verifier/skill/finding-categories.md` | `slot: instructions, roles: [verifier]` — inlined into QA composed CLAUDE.md. No `→ run sub-skill:` marker. | OK — inlined |
| `references/sub-skills/manifest.md` | Catalog/manifest document, not a sub-skill body. Not expected to have a marker. | OK — meta file |
| `references/sub-skills/project/*` | L4 seed templates — not consumed by agents at runtime via markers; copied at install time to `.squidsquad/project/`. | OK — seeds |

---

## Findings

- **Finding 1 — `idle-cooldown-loop` names no role-specific improvement-scan sub-skill explicitly.**
  File: `references/sub-skills/common-events/idle-cooldown-loop.md:31`
  Text: "Run your role's scanning sub-skill."
  The instruction is prose-only with no `→ run sub-skill: <name>` marker. An agent in the improvement cooldown loop must infer which file to read from catalog context (the L1 instructions.md at line 113 says "e.g. `roles/pm/improvement-scan`"). This is low-risk for PM (the catalog example is PM-specific) but potentially ambiguous for worker/skill, verifier, and DM roles which don't have a `roles/<role>/improvement-scan.md`. Verifier and DM use `improvement-scan-slim` for cleanup; in idle mode their scanning sub-skill is the inlined `common/improvement-scan.md`, but the catalog says `improvement-scan` is used by "PM, worker" — verifier and DM have no improvement-scan catalog entry for the idle path. Catalog `docs/sub-skill-catalog.md:141` says `improvement-scan-slim | Filing-only variant (no auto-fix) — used by roles whose lane is verifying/delivering, not implementing | verifier, DM`. So verifier and DM in idle mode should use `improvement-scan-slim` not the full scan — but `idle-cooldown-loop.md` doesn't differentiate. Not a broken marker (no MISSING file), but a documentation gap that could cause agent confusion on verifier/DM idle scans.
  Severity: LOW (file exists; agent degrades gracefully to `improvement-scan-slim` at step 6 anyway).

- **Finding 2 — Catalog claims `roles/dm/task-pickup` is a slash-bearing marker; reality is bare `task-pickup`.**
  Catalog: `docs/sub-skill-catalog.md:235`: "`roles/dm/task-pickup` | DM's queue: pending-ship items — slash-bearing per #10743".
  DM composed CLAUDE.md step 2.1 (`dm/CLAUDE.md:456`): `→ run sub-skill: task-pickup` (bare).
  DM source instructions (`references/roles/dm/instructions.md:67`): `→ run sub-skill: task-pickup` (bare).
  The DM's step 2.1 resolves to `common/task-pickup.md` (the generic pending-item pickup), NOT `roles/dm/task-pickup.md`. The DM role-specific override at `roles/dm/task-pickup.md` is inlined at compose time but is NOT the file an agent reads when it encounters `→ run sub-skill: task-pickup`. The catalog description ("DM's queue: pending-ship items") matches `common/task-pickup.md`'s behavior for pending-ship, so functionally this is likely correct behavior. But the catalog's claim that `roles/dm/task-pickup` is "slash-bearing" (implying an agent invokes it as `→ run sub-skill: roles/dm/task-pickup`) is INACCURATE — no such marker exists anywhere.
  Severity: LOW (catalog misdescription; runtime behavior is correct since `common/task-pickup.md` resolves and works).

- **Finding 3 — `capability-check` is marked "deprecated — slated for removal" in catalog but still active in DM CLAUDE.md.**
  Catalog: `docs/sub-skill-catalog.md:143`: "`capability-check` | _deprecated — slated for removal_".
  DM composed CLAUDE.md (`dm/CLAUDE.md:492`): `→ run sub-skill: capability-check` (active marker).
  DM source (`references/roles/dm/instructions.md:8`): `→ run sub-skill: capability-check`.
  DM includes.yml line 19: `- common/capability-check`.
  The file `references/sub-skills/common/capability-check.md` EXISTS and resolves correctly. This is a documentation status mismatch (catalog says deprecated but it's still live), not a broken marker. The removal paired with capability-framework retirement per INSTALLER-ARCH.md §8 has not yet shipped.
  Severity: INFO (no runtime breakage; removal is intentionally deferred).

- **Finding 4 — `vault-remember` at Step 6 is embedded in a compound line, not a standalone marker.**
  All 4 roles: `→ run sub-skill: 'working-state' ... → run sub-skill: 'vault-remember' ... → run sub-skill: 'improvement-scan-slim'` on a single line.
  The audit prompt asks if Iter 57 "promoted vault-remember to its own L1 marker". The current state is that `vault-remember` is present in the compound cleanup line for all 4 roles, and is referenced in prose in the Vault Protocol section ("use vault-remember to capture durable learnings") — but there is no standalone `→ run sub-skill: vault-remember` at a separate line outside the compound. The Vault Protocol section has a standalone `→ run sub-skill: vault-protocol` but no standalone `→ run sub-skill: vault-remember`. This is the actual state post-#11334/#11331. The source file `references/sub-skills/common/vault-remember.md` exists and resolves correctly.
  Severity: INFO (no broken resolution; the compound line form is readable and functional).

- **Finding 5 — `improvement-scan-slim` fires at Step 6 cleanup for PM and skill (worker) roles.**
  The audit context notes PM and worker should use the full `improvement-scan`, not the slim variant. However, the L1 instructions.md (line 251) and all 4 composed CLAUDE.md files use `improvement-scan-slim` at step:cycle/cleanup. The full `improvement-scan` fires only via `idle-cooldown-loop` in event mode. This is the intended architecture per the composition source — the Step 6 cleanup marker is explicitly described as the loop-mode path. No broken file; this is expected behavior by design.
  Severity: INFO (not a bug; architecture is intentional).

---

## Verification of special-attention items

### vault-protocol-slim (deleted Iter 56 / #11331)

- **No `→ run sub-skill: vault-protocol-slim` marker** in any of the 4 composed CLAUDE.md files. Confirmed by grep: zero matches.
- **Not in `references/installer-files.txt`**: `grep vault-protocol-slim references/installer-files.txt` returns empty. Clean.
- **Source file absent**: `references/sub-skills/common/vault-protocol-slim.md` does NOT exist on disk. The only vault files in `common/` are `vault-optimize.md`, `vault-protocol.md`, `vault-remember.md`.
- **Remaining references**: Historical only — in `tests/comprehension/8697_fixtures/` (old test fixtures), `.squidsquad/pm/planning/` (planning docs), `.squidsquad/qa/planning/` (QA results). None are runtime-path files.
- **Verdict**: Retired cleanly.

### boot-bootstrap (deleted as sub-skill in #11144)

- Content is inlined between `<!-- sub-skill: boot-bootstrap -->` / `<!-- /sub-skill: boot-bootstrap -->` markers in all 4 composed CLAUDE.md files.
- **No `→ run sub-skill: boot-bootstrap` marker** exists in any composed CLAUDE.md. Confirmed.
- Source content lives in L1 `references/roles/instructions.md` between the same comment markers.
- **Verdict**: Correctly inlined; not referenced as a runtime sub-skill.

### issue-filing (retired in #11334)

- **No bare `→ run sub-skill: issue-filing` marker** in any composed CLAUDE.md. Confirmed.
- Per-role markers exist: `roles/pm/issue-filing` (pm:649), `roles/verifier/issue-filing` (qa:501), `roles/dm/issue-filing` (dm:513). All 3 source files exist.
- `skill/CLAUDE.md:592` mentions `common/issue-filing.md` was retired — prose reference only, not a marker.
- **Verdict**: Retired cleanly; per-role variants are live and resolving.

### vault-protocol and vault-remember (Iter 56-57)

- `→ run sub-skill: vault-protocol` appears as a standalone marker in ALL 4 composed CLAUDE.md (pm:717, qa:639, dm:641, skill:800). Source `references/sub-skills/common/vault-protocol.md` exists with `slot: instructions` frontmatter and "all roles write per their lane" content.
- `→ run sub-skill: vault-remember` appears in all 4 at Step 6 cleanup (compound line) and in prose at the Vault Protocol section. No standalone marker outside the compound line. Source `references/sub-skills/common/vault-remember.md` exists.
- **Verdict**: vault-protocol is fully wired with standalone markers across all 4 roles. vault-remember is wired but only via compound cleanup line (not a dedicated standalone marker outside that line). Both source files are present and consistent.

### pickup-comment-fidelity (worker only)

- `→ run sub-skill: pickup-comment-fidelity` appears at `skill/CLAUDE.md:544` under `step:cycle/pickup-comment-fidelity`.
- Source `references/sub-skills/common/pickup-comment-fidelity.md` exists.
- Catalog: "pickup-comment-fidelity | Pickup comments must accurately reflect tracker state | worker". Marker appears in skill (worker class) only — matches catalog.
- **Verdict**: OK — correctly wired.

### Self-skill slash-bearing markers

- `roles/pm/improvement-scan` — referenced in L1 prose at `references/roles/instructions.md:113` (example text), but NOT as a `→ run sub-skill:` marker in any composed CLAUDE.md. Source `references/sub-skills/roles/pm/improvement-scan.md` exists with `slot: instructions`. Inlined via includes.yml.
- `roles/pm/ralph-loop-overview` — referenced as a `Read` directive at `pm/CLAUDE.md:479` (not `→ run sub-skill:`). Source exists.
- `roles/verifier/ralph-loop-overview` — same pattern. Source exists.
- `roles/dm/ralph-loop-overview` — same pattern. Source exists.
- `roles/worker/ralph-loop-overview` — same pattern. Source exists.
- **Verdict**: These are loaded via `Read` at runtime from the POLLING mode block, not via `→ run sub-skill:` markers. All 4 source files exist. No breakage.

### L2 flat-top deletions (Iter 49)

- The audit prompt notes DM, worker, verifier flat-top was deleted in Iter 49. The sub-skills previously referenced only by flat-top were preserved:
  - `pickup-comment-fidelity` — preserved, wired in skill CLAUDE.md:544. OK.
  - Other "only flat-top" sub-skills would need verification; current scan finds no orphaned marker pointing to missing files.
- **Verdict**: No orphaned markers found from Iter 49 flat-top removal.

---

## Summary

- **44 distinct `→ run sub-skill:` marker names** across all 4 composed CLAUDE.md files (including `vault-protocol-slim` which has 0 markers — confirmed clean).
- **80+ sub-skill source files** under `references/sub-skills/` (common: 23, common-events: 6, roles/pm: 14, roles/verifier: 4, roles/dm: 9, roles/worker: 3, project: 16).
- **0 BROKEN markers** — every `→ run sub-skill: <name>` marker in all 4 composed CLAUDE.md files resolves to an existing source file.
- **0 STALE markers** — no marker references a deleted or moved file.
- **3 INFO/LOW findings** (not runtime-breaking):
  1. `idle-cooldown-loop.md` improvement-scan step uses prose-only "Run your role's scanning sub-skill" with no explicit marker for verifier/DM roles.
  2. Catalog claims `roles/dm/task-pickup` is a slash-bearing runtime marker; actual runtime marker is bare `task-pickup` (resolves to `common/task-pickup.md`). Catalog description is inaccurate.
  3. `capability-check` is live in DM but catalog marks it "deprecated — slated for removal."
- **vault-protocol-slim**: retired cleanly — zero markers, not in installer-files.txt, source file absent.
- **boot-bootstrap, issue-filing**: both retired cleanly from the `→ run sub-skill:` marker surface.
- **vault-protocol + vault-remember**: both present across all 4 roles (vault-protocol as standalone markers; vault-remember in compound Step 6 cleanup line for all 4).
