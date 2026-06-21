Now I have all the information I need. Let me do the detailed comparison between the SOUL.md text and the AGENT-RUNTIME §3.1 spec.

---

### Finding 1

- **File**: `references/roles/SOUL.md`
- **Line**: 43
- **Severity**: error
- **Issue**: The return-path description misattributes the re-assignment action. SOUL.md says "the human (through inline mode), or PM on their behalf, records the answer and re-assigns the ticket back to your alias." This tells the agent that either the human or PM will do the re-assignment. The spec (§3.1, line 140) says that when the human answers the *originating agent* via inline mode, **the agent re-assigns the ticket back to itself** (`/work/assign` to its own alias via a transition) — the human never performs forge transitions. The human provides the answer; the agent (or PM) handles the re-assignment.
- **Evidence**: 
  - Spec §3.1 line 140: "**Human → originating agent (inline):** the agent records the human's answer into the ticket and **re-assigns the ticket back to itself** (`/work/assign` to its own alias via a transition), which resumes the work."
  - Spec's own summary at line 1329: "Return path is human-mediated (originator self-reassigns, or PM reassigns on its behalf; wrong-agent → 'not my territory')."
  - SOUL.md line 43 collapses this to "the human... re-assigns" — making the human the grammatical subject of the re-assignment verb, which contradicts both spec statements. The human is never the actor for forge transitions.
- **Suggested fix**: Rewrite the return-path sentence to correctly attribute the re-assignment. For example:

  ```
  The human answers asynchronously and the work resumes later via the return path:
  if the human reaches you directly (inline), record the answer and re-assign the ticket
  back to yourself; if the human reaches PM instead, PM records the answer and re-assigns
  it to you on their behalf. If a human reaches you about work that was never yours,
  reply "this isn't my territory — wrong agent" and point them to the right alias or to PM.
  ```

  This distinguishes the two valid return paths (agent self-reassigns vs. PM reassigns) and makes clear the agent is the actor in the first case.

---

Now addressing the other three review criteria:

**(2) Conflict with "Professionalism: when uncertain ask"** — No conflict. Line 41 explicitly bridges the two sections: `"Ask, don't guess" above means *ask asynchronously*, never sit and wait.` This resolves the potential tension by redefining "ask" to mean "ask asynchronously" in autonomous modes, while preserving inline mode as the synchronous channel. The bridge is clear and intentional.

**(3) Ambiguity causing pause or bare-comment usage** — The directive is explicit on both points:
- "**never pause and wait for a human**" (line 41) — reinforced with "Do not wait" (line 43)
- "**via a transition** (never a bare comment; bare comments wake no one and leave no ownership)" (line 43) — double-negative and explicit rationale

No ambiguity that would cause an agent to pause or use a bare comment.

**(4) Token economy** — The new section is 5 lines (39–43), including the heading. The rationale is compressed into the opening sentence. No verbosity concern. The L1 is paid every boot; this addition is proportionate.

**No behavioral regression** — The change adds a constraint on *how* to ask (async, via transition), but does not remove the agent's ability or obligation to ask. The bridge line preserves the "ask, don't guess" principle while redirecting it to the async channel. Existing behavior in inline mode is explicitly preserved as the sole synchronous channel.
---

## Resolution (skill, 2026-06-18)

**Finding 1 (error) — RESOLVED.** Rewrote the return-path sentence to correctly attribute the re-assignment per §3.1: added explicit "**a human never makes the forge transition; you or PM do**", and split the two valid paths — (a) human reaches the originator inline → the *agent* records + re-assigns to itself; (b) human reaches PM inline → *PM* records + re-assigns on the agent's behalf. Verified the corrected text composes into all four roles' soul (`_assemble_soul`). Findings 2-4 + no-regression: PASS as reviewed (no change needed).
