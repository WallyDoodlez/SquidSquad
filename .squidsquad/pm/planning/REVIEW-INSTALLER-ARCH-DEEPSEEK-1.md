Now I have all the evidence needed. Here are my findings:

---

### Finding 1

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 55, 104 (mermaid), 149
- **Severity**: error
- **Issue**: Broken cross-reference — three locations refer to the "upgrade flow (§7)" but the upgrade flow lives at §10. §7 is "The installer agent (Q-new21)."
- **Evidence**: 
  - Line 55: `routes to the upgrade flow (§7)`
  - Line 104 (mermaid node label): `Upgrade["Upgrade flow §7"]`
  - Line 149: `routes to the upgrade flow (§7)`
  The upgrade flow is defined at §10 (lines 353–390). Section 7 (lines 286–296) is about the installer agent's key contracts — it has nothing about upgrades.
- **Suggested fix**: Replace all three `§7` references with `§10`.

---

### Finding 2

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 186
- **Severity**: error
- **Issue**: The Phase 3 review screen example text contains capability concepts that §8 explicitly declares are removed from the install model.
- **Evidence**: Line 186 reads: `"I'm about to set up SquidSquad with: [be, fe] roles + pm + qa + dm; GitHub Issues tracker; 30-min loop; Figma design; local delivery; …"`. "Figma design" and "local delivery" are capability concepts from the removed `references/sub-skills/capabilities/` directory. §8.3 (lines 327–332) states there is "No `capabilities/` sub-skill set in the install scaffold" and that the capabilities directory "are slated for removal." The revision log (line 449) claims "All references in §3 (inputs), §4 (Phase 1 conversation, Phase 5 atomic write), and §5 (file layout) updated to drop capability mentions." This one was missed.
- **Suggested fix**: Replace the review screen example with capability-free text, e.g.: `"I'm about to set up SquidSquad with: [be, fe] roles + pm + qa + dm; GitHub Issues tracker; 30-min loop. …"`.

---

### Finding 3

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 400
- **Severity**: error
- **Issue**: §11.1 claims "Phases 0–6 make no changes the user can see" but Phase 5 writes `.squidsquad/` to the local filesystem (per §4.7), which is a user-visible change detectable by `git status`.
- **Evidence**: Line 400: `Phases 0–6 make no changes the user can see (Phase 0a shared_fs.py init is idempotent — creates dirs only if absent).` Line 194–198 (§4.7 Phase 5): `Scaffolds .squidsquad/ — creates the role dirs, vault skeleton, project-local L4 directory, config.md, and per-role SOUL.md files.` and `Writes are local but not yet committed.` A `git status` after Phase 5 will show untracked `.squidsquad/` files — these are user-visible. The parenthetical exemption only covers Phase 0a, not Phase 5. This also contradicts §11.2 (line 407) which acknowledges "interrupted mid-Phase-5 (filesystem partially scaffolded)" — if Phase 5 truly made no changes, there could be no partial scaffold.
- **Suggested fix**: Rewrite to `Phases 0–4 make no changes the user can see. Phase 5 writes locally (uncommitted); Phase 6 regenerates CLAUDE.md outputs. The user can abort through Phase 6 with a git checkout of the working tree.` — or restructure to honestly describe the local-write boundary.

---

### Finding 4

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 51–55 (§2 commitments #1, #2), 44 (mermaid)
- **Severity**: error
- **Issue**: The document mixes two different numbering schemes — WIZARD.md's "Step" numbering and its own "Phase" numbering — without clarifying the distinction, creating direct contradictions.
- **Evidence**:
  - §2 commitment #2 (line 54): `Step 7 commits everything atomically (scaffold + L4 enrichment + labels + push)` — this uses WIZARD.md's Step 7 (which bundles scaffold, compose, commit, push). But INSTALLER-ARCH's own §4 phase flow puts commit at **Phase 8**, with Phase 7 being "Tracker setup."
  - §2 mermaid (line 44): `Installer -->|"Step 7 commit"| Repo` — again WIZARD numbering.
  - §4 flowchart Phase 7 label: `Tracker setup (labels + initial issues)` vs. the "Step 7" commit in §2.
  - §2 commitment #2 (line 54): `Steps 0–6 are pure conversation` — WIZARD numbering (WIZARD Step 6 = review screen). But in §4, Phase 5 already writes to disk.
  - The §4 flowchart mermaid line 108: `P4 -->|"yes"| P5 --> P6 --> P7 --> P8 --> P9` — Phase 8 is commit.
  An implementer reading §2 sees "Step 7 commits" and "Phases 0–6 are conversation." Then §4's own phase flow puts commit at Phase 8 and Phase 5 writes to disk. These are irreconcilable unless the reader already knows WIZARD.md's step numbering.
- **Suggested fix**: Either (a) use only Phase numbering throughout and remove all "Step N" references, mapping WIZARD Step 7 → Phases 5–9; or (b) add an explicit note at the top of §2 mapping WIZARD steps to architecture phases: e.g., "In this doc, 'Step N' refers to the WIZARD.md runbook step; the architecture breaks Step 7 into distinct Phases 5–9."

---

### Finding 5

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 347
- **Severity**: warning
- **Issue**: §9 references "Phase 5c" for Forgejo setup, but no "Phase 5c" is defined in the §4 phase flow. The phases are 0, 0a, 0b, 1–9.
- **Evidence**: Line 347: `The installer offers this at Phase 5c if the human explicitly requests it.` The §4 phase flow (lines 89–121) defines Phases 0–9 with sub-phases 0a and 0b only. There is no Phase 5a, 5b, or 5c. The WIZARD.md runbook has a "Step 5c — Forge backend" (line 457 of WIZARD.md), so "Phase 5c" appears to be a WIZARD step number mistakenly called a "Phase."
- **Suggested fix**: Either define Phase 5 sub-phases in §4 or rephrase to reference the WIZARD step explicitly: `The installer offers this during the forge backend conversation step (WIZARD.md Step 5c) if the human explicitly requests it.`

---

### Finding 6

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 353–390 (§10)
- **Severity**: warning
- **Issue**: The upgrade flow lacks user interaction gates and harness interaction specification. The fresh-install path has extensive conversation (Phase 1), review (Phase 3), and explicit approval (Phase 4), but the upgrade flow has none — no confirmation before pulling, no review of what changes, no abort option. Additionally, step 3 says "Restart affected agents via the harness" but does not specify how the ephemeral installer agent restarts harness-managed agents.
- **Evidence**: Lines 371–375 list only three mechanical steps (pull, recompose, restart). Compare with fresh-install Phases 1–4 (conversation → synthesis → review → approval). There is no step like "present user with what will change and ask for confirmation." For the harness restart: the installer is defined as an ephemeral Claude Code session (§7, line 296: "exits after Phase 9"). How it restarts agents via the harness is unspecified — does it call a CLI command? `start.sh`? An HTTP endpoint? This is a missing implementation detail.
- **Suggested fix**: Add a user-facing step between "Pull" and "Recompose" showing diff/change summary and asking for confirmation. Specify the harness restart mechanism explicitly (e.g., `POST /agents/{role}/restart` or `start.sh --restart`).

---

### Finding 7

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 184–198 (§4.6–4.7)
- **Severity**: warning
- **Issue**: Phase 4 (user approval gate) has no dedicated section or prose description. §4.6 describes Phase 3 (review screen), then §4.7 is titled "Phase 4–5 — Atomic write" and describes only Phase 5 actions. The approval decision — how the installer asks, what constitutes a "yes" vs "no," format of the prompt — is not specified.
- **Evidence**: The flowchart (line 98–99) shows P4 as a diamond decision node `{"Phase 4<br/>User approves?"}` with edges to Phase 5 (`"yes"`) and Abort (`"no"`). But §4.6 ends with "The human approves, edits, or aborts" (line 186), and §4.7 immediately jumps to the five atomic-write steps without addressing the approval interaction itself. An implementer would need to invent the approval prompt and response parsing.
- **Suggested fix**: Either add a brief "Phase 4 — Approval" section describing the prompt format and accepted responses, or expand §4.6's last sentence to specify the approval mechanism concretely (e.g., "The installer presents a `[P] Proceed / [E] Edit / [A] Abort` prompt and waits for the user's choice").

---

### Finding 8

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 78–79 (§3.2 outputs)
- **Severity**: low
- **Issue**: The outputs table lists only `.harness-port` among runtime harness files, but the §5 file layout (line 257) and AGENT-RUNTIME.md §5 list `.harness-state.json` and `.event-state.json` as harness-owned runtime files written to `.squidsquad/`. The installer does not write these (the harness does), but neither does it write `.harness-port` — so the output table is inconsistent about which runtime files it surfaces.
- **Evidence**: §3.2 line 79: `.squidsquad/.harness-port (at runtime)` listed as output. §5 line 257: `(runtime) .harness-port, .harness-state.json, .event-state.json — created when the harness boots`. AGENT-RUNTIME.md §5 (lines 499–509) lists both `.harness-state.json` and `.event-state.json` as harness-owned state files at the `.squidsquad/` root.
- **Suggested fix**: Either add `.harness-state.json` and `.event-state.json` to the §3.2 outputs table for completeness, or add a note that only `.harness-port` is listed and the others are documented in AGENT-RUNTIME.md.