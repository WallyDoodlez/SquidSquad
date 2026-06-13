# Gap Audit — L1 Composed CLAUDE.md vs `docs/AGENT-RUNTIME.md`

**Issue**: #11144 polish session — overnight gap audit
**Branch**: `squidsquad/skill/compose-polish-session` @ HEAD `827d4d2c5`
**Author**: skill (cycle ~late 2026-06-07)
**Audience**: discussion with operator tomorrow

## Scope

Comparison of the agent-facing operating manual (L1 `references/roles/instructions.md` → composed `.squidsquad/<role>/CLAUDE.md`) against the architecture reference (`docs/AGENT-RUNTIME.md`) for **mutual coverage gaps**: concepts in arch that should be in L1 (because the agent needs to know), and concepts in L1 that should be in arch (because the arch model is incomplete without them).

Did not survey: HARNESS-ARCH.md (separate audit if needed), per-role L2/L3 content (role-specific layers), per-sub-skill content (runtime-loaded mechanics).

## Findings — by severity

### LARGE gap — discuss tomorrow

**G-1. `§7.5 Nudge handling while busy` is not in L1.** Arch doc says: if a new nudge arrives while the agent is mid-cycle, the agent notes it in conversation context (no file write, no queue, no flag), continues current event uninterrupted, emits `ack-cursor`, then enters the §7.1 walk to GET fresh events. L1 §3 only covers what happens WITHIN one nudge — it does not address the new-nudge-during-cycle case. Agents could plausibly do the wrong thing (pivot to new nudge immediately, queue it to a file, etc.). Worth a short addition to L1 §3 or a new sub-section under "Your cycle (event mode)".
- Arch: `docs/AGENT-RUNTIME.md:1035-1057`
- L1: no equivalent
- Recommended fix: 1–2 sentence addition under L1 §3 or as a §3 caveat. Reference §7.5.

**G-2. `§2.3 Inline mode` structural placement (DS Finding 4).** DS audit flagged that §2.3 sits under the H2 "## 2. Two triggering modes" parent heading but explicitly states "Inline mode is not a third triggering mode in the §2 sense". A reader scanning the TOC sees §2.3 as a peer of loop and event modes. Two options:
  - **(a)** Promote inline mode to its own top-level H2 section (e.g. "## 3. Human interaction" with current §3 onwards renumbered)
  - **(b)** Rename "## 2. Two triggering modes" → "## 2. Triggering modes and human interaction"
  - L1 puts inline mode in §8 under "Your cycle (event mode)" — peer to lifetime overview / session boot / per-nudge cycle. Arguably the same structural confusion but less prominent.
  - Recommendation: discuss whether (a) or (b) better matches the architectural intent. (a) is more disruptive (section renumber); (b) is cosmetic.

### MEDIUM gap — minor

**G-3. Improvement-subloop throttle mechanism not in L1.** Arch §7.6 spells out the per-agent throttle: at most one subloop per agent per N minutes (default 30), via the `.squidsquad/<alias>/.subloop-last-run` file. L1 §4 only says "the cool-down timer reaches its threshold" without explaining HOW the timer works. The `idle-cooldown-loop` sub-skill (Read at boot) likely covers this — should verify. If the sub-skill carries it, L1's deferral is fine; if not, the throttle is a hidden mechanic.
- Arch: `docs/AGENT-RUNTIME.md:1081`
- L1: §4 mentions "cool-down timer" without mechanism
- Recommended fix: verify `idle-cooldown-loop.md` describes the `.subloop-last-run` file; if not, add it to that sub-skill (not L1 — too operational for the orientation slot).

**G-4. Signal catalog (§4.2) not enumerated in L1.** Arch lists 4 canonical signals: `assigned-to`, `booted`, `ack-cursor`, `ack-stop`. L1 mentions each in context (booted in §2, ack-cursor in §3 + Step 7, ack-stop in Step 7 stop handling) but never lists them together. Agents may not have a holistic view of the wire vocabulary. Not blocking — most agents will never directly construct these signals (they're behind `tracker.py`, `cycle_post.py`, the harness).
- Arch: `docs/AGENT-RUNTIME.md:258-272`
- L1: in-context mentions, no enumeration
- Recommended fix: probably none. The current in-context coverage matches the agent's actual interaction surface.

**G-5. `§7.3 Work handoff / /work/assign` not in L1.** Arch describes the wire mechanism of how `tracker.py transition` POSTs `/work/assign` to the harness, which rewrites the `role:<target>` label and emits `assigned-to`. L1 Tracker Protocol section says "Never construct `gh issue edit` label commands manually" — pointing to `tracker.py`. The agent does the right thing without knowing the internal mechanism. Not a real gap; just a layer abstraction.
- Arch: `docs/AGENT-RUNTIME.md:895-1029`
- L1: tracker.py abstraction
- Recommended fix: none.

### NO gap — already covered (sanity checks)

- **Care filter (§7.4)** ↔ L1 §3 care filter caption ✓
- **Boot sequence (§7.2 / §8.3)** ↔ L1 §2 + Step 1 boot block ✓
- **Mode selection (§8.1, §8.2, §8.4)** ↔ L1 Step 1 boot block + "Loaded mode is sticky" ✓
- **Inline mode (§2.3)** ↔ L1 §8 ✓ (after today's add)
- **Cursor model (§4.3)** ↔ L1 §3 caption + Step 7 + `cursor-management.md` (runtime-loaded) ✓
- **Improvement subloop concept (§7.6)** ↔ L1 §4 ✓ (mechanism in `idle-cooldown-loop.md`)
- **Event store / cascade protection (§4.6) / port discovery (§4.7)** — harness-internal, not agent-facing ✓
- **EAD (§4.4)** — harness-internal ✓
- **Process tree (§3)** — agent doesn't need full tree picture ✓

## DS audit summary on §2.3 (today's add)

- 4 findings; 1 error + 3 warnings.
- **Finding 1 (error)** + **Finding 2 (warning)** — "re-arm Monitor" misinformation fixed at commit `827d4d2c5`.
- **Finding 3 (warning)** — §8.3 cross-ref narrowed in same commit.
- **Finding 4 (warning)** — structural §2.3 vs "Two triggering modes" heading — deferred (G-2 above).

## What I'm NOT recommending tonight

I am not touching:
- L1 §3 (the new-nudge-during-cycle addition is best discussed first — it could be a sentence or a sub-section, and the right size depends on operator preference)
- AGENT-RUNTIME §2 heading rename or §2.3 promotion (the DS structural question)
- `idle-cooldown-loop.md` (need to verify what it says before adding the throttle mechanic)
- L1 §8 (the inline-mode L1 section is correctly silent on "how to resume" because Monitor is persistent + autonomous wake handles it)

## Suggested decision order tomorrow

1. **G-1 + G-2 first** (the two questions that require operator judgment on scope and structure)
2. **G-3** if you want — quick verification of `idle-cooldown-loop.md`
3. Skip G-4 / G-5 unless you disagree with the "no gap" call
