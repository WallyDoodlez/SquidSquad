Now I have all the evidence needed. Here are my findings:

---

### Finding 1

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 123 (new §2.3, "Resuming autonomous mode after an inline session" paragraph)
- **Severity**: error
- **Issue**: The claim "re-arm the Monitor tool (event mode) per the boot-bootstrap recovery directive" is factually wrong on two levels.

  1. **There is no "re-arm" procedure for the Monitor tool.** The Monitor invocation is `persistent: true` (`references/sub-skills/common-events/event-mode-contract.md`, line 46). It stays running across turns — after an inline interaction, Monitor is still active and delivers the next nudge automatically. No explicit "re-arm" step exists.

  2. **The event-mode contract explicitly forbids re-invoking Monitor.** `event-mode-contract.md` line 51: *"If the Monitor tool exits for ANY reason — end your session right away. Do NOT attempt to re-invoke Monitor."* Telling an agent (or operator) to "re-arm" Monitor directly contradicts the event-mode contract's unconditional rule.

  3. **The boot-bootstrap has no event-mode recovery directive.** `references/sub-skills/common/boot-bootstrap.md` (lines 68-78) defines a single recovery instruction — re-invoke `/loop` — and it is scoped exclusively to the POLLING mode block. The EVENT mode block (lines 46-66) loads sub-skills but has no equivalent recovery directive. The phrase "boot-bootstrap recovery directive" (used by `ralph-loop-overview.md` files) refers only to the loop-mode re-invoke.

- **Evidence**:
  - `references/sub-skills/common-events/event-mode-contract.md:46` — `persistent: true` on Monitor invocation
  - `references/sub-skills/common-events/event-mode-contract.md:51` — "Do NOT attempt to re-invoke Monitor"
  - `references/sub-skills/common/boot-bootstrap.md:68-78` — POLLING mode recovery: "re-invoke the same literal command"
  - `references/sub-skills/common/boot-bootstrap.md:46-66` — EVENT mode block has no recovery directive
  - `references/sub-skills/roles/worker/ralph-loop-overview.md:13` — only covers resuming `/loop` mode, not event mode
  - `grep` for "re-arm" across `references/` returns zero matches

- **Suggested fix**: Replace the sentence with two mode-specific statements that match the actual contracts:

  > **Resuming autonomous mode after an inline session.** In loop mode, re-invoke `/loop` per the recovery directive in the boot bootstrap (`common/boot-bootstrap.md`). In event mode, the Monitor tool is persistent — it continues delivering nudges after the inline interaction ends; the agent returns to idle and processes the next nudge when it arrives. The session's wake mode itself does NOT change — it stays whichever was selected at boot (§8.3).

---

### Finding 2

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 123 (new §2.3, "Resuming autonomous mode after an inline session" paragraph)
- **Severity**: warning
- **Issue**: The phrase "per the boot-bootstrap recovery directive" is used as a catch-all covering both loop and event mode, but the boot-bootstrap only contains a recovery directive for loop (POLLING) mode. An agent or operator reading this arch doc and then consulting the boot-bootstrap for event-mode inline-recovery guidance will find nothing — the event-mode block in `boot-bootstrap.md` loads sub-skills (`event-driven-workflow`, `event-mode-contract`, `cursor-management`, etc.) but has no labeled recovery directive.

- **Evidence**:
  - `references/sub-skills/common/boot-bootstrap.md:68-78` — labeled "POLLING mode" block contains "re-invoke the same literal command"
  - `references/sub-skills/common/boot-bootstrap.md:46-66` — labeled "EVENT mode" block has `→ run sub-skill:` chains but no recovery instruction
  - `references/sub-skills/roles/*/ralph-loop-overview.md` — each says "To resume `/loop` mode after an inline session, re-run the recovery directive from the boot bootstrap" (loop-mode-only)

- **Suggested fix**: Covered by the suggested fix for Finding 1 — making the two mode paths explicit removes the false implication that the boot-bootstrap has a unified recovery directive covering both modes.

---

### Finding 3

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 123 (new §2.3)
- **Severity**: warning
- **Issue**: The cross-reference to §8.3 ("Boot decision tree") is technically correct (§8.3 does document sticky-mode-per-session at line 1129), but it's a confusing choice for a reader trying to understand *inline recovery*. §8.3's primary subject is the boot-time harness probe and wake-mode binding — not what to do after an inline session. A more helpful cross-reference would be to the boot-bootstrap source file (`common/boot-bootstrap.md`) or to §8.2/§8.4 which discuss session lifecycle. As written, a reader clicking through to §8.3 expecting inline-recovery guidance will find a Mermaid flowchart about harness probing.

- **Evidence**:
  - `docs/AGENT-RUNTIME.md:1129` — §8.3 says "The probe runs **once per session** at boot, not per cycle. Once the wake mechanism binds, it stays for the lifetime of the session." This supports the "mode does NOT change" claim but doesn't address inline recovery at all.
  - `docs/AGENT-RUNTIME.md:1107-1128` — the §8.3 Mermaid diagram is about boot probing, not inline mode

- **Suggested fix**: Keep the §8.3 cross-ref for the "mode does not change" claim (it is correct there), but don't lean on it for recovery procedure. The recovery guidance should be self-contained in §2.3 or cross-reference the source files directly.

---

### Finding 4

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 111 (new §2.3 lead sentence)
- **Severity**: warning
- **Issue**: The section is numbered §2.3 under the parent heading "## 2. Two triggering modes" (line 55), but the lead sentence explicitly states: "Inline mode is not a third triggering mode in the §2 sense." This creates a structural contradiction between the heading ("Two triggering modes") and the existence of a third numbered subsection. An agent scanning the table of contents will see §2.3 as a peer of loop mode and event mode, potentially misclassifying inline mode as a third wake mechanism.

- **Evidence**: Line 55: heading "## 2. Two triggering modes" — line 109: subsection "### 2.3 Inline mode (human override)" — line 111: "Inline mode is not a third triggering mode in the §2 sense."

- **Suggested fix**: Either (a) promote inline mode to its own top-level section (§2.5 or a new §3) with a title like "Human interaction (inline mode)", or (b) if keeping it under §2, change the heading to something like "## 2. Triggering modes and human interaction" to avoid the numbering contradiction. The ralph-loop-overview files and `instructions.md` treat inline mode as a separate concept ("#### 8. Human interruption (inline mode)") rather than a sub-bullet of triggering modes — the arch doc should follow the same pattern.

---

NO_FINDINGS (for the remaining claims: cycle_pre/cycle_post not running, working-state.md not mechanically updated, status-bar untouched, tracker.py durability, override discipline, monitoring impact, §8.3 cross-ref for mode-stickiness — all these are correct and consistent with the agent-facing sub-skills and instructions).