# Token Efficiency — Analysis & Reduction Plan

- **Date:** 2026-07-12
- **Operator concern (2026-07-12):** "the models are pretty token intensive — analyze to find a way to decrease."
- **Method:** structural audit of everything that enters agent context (measured live: composed CLAUDE.md sizes, per-cycle file embeds, sub-skill Read sizes, session-restart cadence, model/effort config), plus prior token-audit docs (FEAT-SKILL-195, FEAT-PM-475, FEAT-PM-2070, FEAT-PM-3465).

---

## 1. Where the tokens actually go (ranked, measured)

| # | Cost center | Measured | Frequency | Est. cost |
|---|---|---|---|---|
| 1 | **`working-state.md` embedded verbatim in `cycle-input.json`** (`cycle_pre.py:447-515`, `raw_content` — no truncation, no gate) | **dm: 188KB** (24.6K words), pm: 35KB; spec says it should be a ~10-line Task/Status block, and skill/qa (2-4KB) prove the spec works | **every cycle** (per cared event) | dm ~32-48K tok/cycle; pm ~6-9K |
| 2 | Composed `CLAUDE.md` | pm 76KB / skill 86KB / qa 68KB / dm 77KB (~17-22K tok) — regrown past the 2026-04 diet baseline (FEAT-SKILL-195 measured pm at 72KB *before* that diet shipped) | every session boot | ~20K tok/boot |
| 3 | **Session restarts are frequent** — recompose deploy-halt fires on any `references/`-touching merge: **12 commits in the last 24h, 28 in 7 days**, each a candidate full-fleet restart; plus context-70% restarts | cold cache + full re-read of #2, BRIEFING, ~56KB boot sub-skills | per restart | ~35-40K tok × 4 agents × up to ~daily-or-worse |
| 4 | **BRIEFING.md** | 40KB / ~6.7K tok — **3.3× over its own 2,000-token budget** (`vault_remember.py briefing-budget` measures it; the gate only limits *additions*, never shrinks the file) | boot + re-read each stale cycle | ~6.7K tok |
| 5 | PM `cycle-input.json` | 29KB/581 lines — dominated by full GitHub label objects (id/description/color per label per issue) and inline-comment payloads | every PM cycle | ~7K tok |
| 6 | Every-cycle sub-skill Reads | `task-intake` 26KB, `verification` 27KB, `tracker-protocol` 12KB, `pipeline-sentinel` 15KB — re-Read on every marker hit, so each cycle in a long session appends another full copy to context | per cycle | 10-20K tok/cycle |
| 7 | `scan-history.md` fallback | skill: **137KB**, unbounded append-only; the documented fallback read when `scan_index.py` fails | latent | 30K+ tok on trigger |
| 8 | Effort/model config | all four roles run `--effort high`; primary model not pinned (no `--model` flag); subagents already sonnet; deepseek already routes research + code-review | continuous | multiplier on everything above |

Not problems (checked): compose output has no timestamps (cache-stable prefix ✓); event nudges are edge-triggered, not polled ✓; vault search is capped at 10 files-with-matches ✓; iteration logs pruned to 20 ✓.

---

## 2. Fixes

### T1 — working-state hygiene (highest leverage, small change)

1. **Enforce the existing spec**: `working-state.md` is Task/Status/Started/Decisions — cleared on completion. dm and pm have drifted into append-only session journals (14 boot-narrative blocks in pm, journals back to 2026-06-14 in dm).
2. **Mechanical gate** (don't rely on discipline — the drift proves it): `cycle_pre._read_working_state` truncation guard — embed at most N KB (proposal: 8KB) of `raw_content`, newest-first, with an explicit `[TRUNCATED — file is X KB, spec is ~10 lines; clean me]` marker; `cycle_post._do_working_state_update` warns when writing >8KB.
3. One-time cleanup: archive dm/pm journal blocks to their iteration logs (which are pruned and not re-read); reset both files to spec shape.
4. **Savings: ~32-48K tokens per DM cycle, ~6-9K per PM cycle** — the single biggest win available, and it's a bugfix, not a redesign.

### T2 — BRIEFING diet + hard budget

1. One-time trim back to the documented ~50-line shape (graduate history to `archives/` — the mechanism already exists and was used pre-2026-05-19).
2. Make the budget *corrective*, not just additive: the existing every-cycle BRIEFING staleness check (vault-remember step, not quiet-gated) also flags `briefing-budget` overage as a must-fix, so PM trims on contact instead of only being blocked from adding.
3. Savings: ~4-5K tokens per boot/re-read, every role. (Also queued in the vault plan §9.2.3 — same fix, one implementation.)

### T3 — Restart hygiene (REVISED 2026-07-12 — automated batching rejected by operator)

Operator decision: **no automated deploy batching.** Reboots are at human discretion, and the operator already batches naturally ("reboot when something important lands, along with the smaller stuff that accumulated"). Harness telemetry confirms it: one spawn per agent for the current harness session — the 12-merges/day figure was a theoretical worst case, not observed behavior. What remains of T3:

1. ~~Deploy batching~~ — dropped. Manual discretion is the batching policy.
2. **Raise `Context Threshold` 70 → 75-80 *after* T1 lands** (T1 slows context growth dramatically, so sessions naturally live longer) — folded into T1's follow-up, not a separate ticket.
3. (Optional, unticketed) checksum-gated per-role restart on the post-merge path would make each *manual* reboot cheaper — revisit only if autonomous 24/7 operation later makes restart cadence a real cost.

### T4 — cycle-input diet

1. Strip GitHub label objects to bare names in `_gh_fetch` post-processing; drop `color`/`description`/`id` (pure ballast in agent context).
2. Cap embedded comment bodies (first ~500 chars + "read the issue for more" — the forge-read pattern already tells agents to read the issue when acting).
3. Savings: ~10-15KB per PM cycle; smaller for others.

### T5 — Composed-prompt re-diet + sub-skill re-read discipline

1. Re-run the FEAT-SKILL-195-style audit on today's 67-90KB composed files (they've regrown past the post-diet baseline); same targets: duplicated common content, prose that belongs in scripts, dead branches. Target 15-20%.
2. **Skip redundant re-Reads within a session:** rule in the cycle contract — a sub-skill already Read this session may be skipped *unless* a deploy/recompose happened since (deploy already restarts the session, so "since last restart" ≈ "this session"). Biggest effect on `tracker-protocol`/`task-intake`/`verification` which currently re-enter context every cycle. Needs CQ specs (instruction change) and careful wording so agents don't skip after compaction — tie the rule to "visible in current context" not memory.
3. Split the two giant per-cycle sub-skills (`task-intake` 26KB, `verification` 27KB) into a lean hot-path core + cold-path reference sections read only when the relevant branch triggers.

### T6 — Effort/model tiering (multiplier)

1. **Effort:** all roles run `high`. Proposal: dm `medium` (delivery packaging is mechanical), qa `medium` (test execution follows a written plan; judgment concentrated in plan authoring which PM/skill own), keep pm/skill `high`. Measure for a week before/after (see T8).
2. **Primary model pinning:** add `model-<role>` config + `--model` in `thin_launcher.py` (already scoped as web-plan W4; tier aliases only, per house rule). Enables e.g. dm on Sonnet.
3. **Router:** `improvement-scan` and `discussion-prep` are candidates for `deepseek-v4-pro` routing (config-only change; `comprehension`/`qa-execution` stay Claude-locked by design).

### T7 — scan-history pruning

Add pruning to `scan_index.py` rebuild (keep last N entries, archive rest) and a size guard on the documented fallback path (read tail, not whole file).

### T8 — Measure it (prerequisite for tuning, not for T1-T4)

Today there is zero token telemetry. #13561 P3's statusline POST delivers per-turn `context_window` + `cost` per agent to the harness — add a tiny daily aggregate (`tokens by role by day`, harness-local) and put the number on the TUI/web. Every T-item above then gets a before/after instead of a guess.

---

## 3. Sequencing

| Item | Size | Savings | Depends on |
|---|---|---|---|
| T1 working-state gate + cleanup | S | **~32-48K/cycle (dm)** — do first | — |
| T2 BRIEFING diet | S | ~5-7K/boot/role | — |
| T4 cycle-input diet | S | ~3-4K/PM-cycle | — |
| T3 restart hygiene (revised) | XS | threshold bump only, post-T1 | T1 |
| T5 prompt re-diet + re-read rule | M | 15-20% of boot + 10-20K/cycle | CQ |
| T6 effort/model tiering | S-M | multiplier | T8 to verify; web W4 for UI |
| T7 scan-history | XS | latent-risk removal | — |
| T8 telemetry | S | measurement | #13561 P3 |

T1+T2+T4 are a week-one bundle with no architectural risk and the majority of the win.
