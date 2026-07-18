Now I have a thorough understanding of the document. Let me compile my findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 60 (step 3) vs. 35 (invariant)
- **Severity**: error
- **Issue**: §4 step 3 instructs the installer to discover the user's workflow in terms that contradict the invariant work lifecycle stated in §3. The invariant (§3 line 35) is `create → build → verify → deliver`. But §4 step 3 (line 60) tells the installer to ask about how tasks are "**created**, **delivered**, **verified**, and **technically done**" — omitting "build" entirely, replacing it with "technically done," and reversing the deliver/verify order (delivered before verified instead of verify→deliver).
- **Evidence**: The invariant defines the canonical lifecycle. The installer's discovery questions use a different decomposition. This means the installer would learn about the user's workflow in the wrong shape, then have to silently re-map to the invariant lifecycle — a gap that would cause confusion or missed phases. Notably, the empty-project adaptation (§4 "Adapting to an empty project," line 79) correctly uses `create → build → verify → deliver`, confirming the normal-path wording is the outlier.
- **Suggested fix**: Rewrite §4 step 3 to use the invariant lifecycle terms: "how tasks are **created**, **built**, **verified**, and **delivered**" — preserving the canonical order and including "build."

---

### Finding 2

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 56
- **Severity**: error
- **Issue**: §4 step 1 instructs the installer to confirm "the seeded references are good," but the term "seeded references" is never defined anywhere in this document or its listed cross-references (§9).
- **Evidence**: A grep of the entire `.squidsquad/` tree confirms "seeded references" appears only on this one line and nowhere else. An LLM installer agent encountering this directive would have no way to determine what "seeded references" are, where to find them, or what "good" means as a criterion.
- **Suggested fix**: Either define "seeded references" explicitly (what they are, where they live, what validity check to perform) or remove the directive. If it refers to files that `wizard.py`'s prerequisite check validates, say so explicitly.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 70
- **Severity**: error
- **Issue**: §4 step 8 tells the installer to "spawn a separate sub-agent" for independent verification, but provides zero mechanism for doing so. The installer is an LLM agent — it needs to know *how* to spawn a sub-agent (what tool to call, what API, what context to pass). None of this is specified.
- **Evidence**: The document says "A fresh, independent agent — not you, who made the choices — performs this so the check is objective." This is a hard requirement — verification must happen with a separate agent. But without any actionable instruction on how to spawn one, the installer cannot fulfill this step. The cross-referenced tools (§9: wizard.py, manifest.py, compose.py) don't obviously expose a sub-agent-spawning capability.
- **Suggested fix**: Specify the concrete mechanism: either name a tool/command to spawn the verification sub-agent and describe what inputs it needs (the proposed customizations, the project context), or explain the sub-agent-spawning primitive the installer is expected to use (e.g., a specific Claude tool call, a Python helper, etc.).

---

### Finding 4

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 72
- **Severity**: warning
- **Issue**: §4 step 9 says "Configure the tracker" with no specifics about what configuration is required, what form it takes, or how to apply it. The forge (GitHub Issues) is a hard invariant (§3 line 32), so this is a critical step — but the installer has no actionable guidance.
- **Evidence**: "Configure the tracker" could mean creating labels, setting up a GitHub Project board, installing a GitHub App, configuring webhooks, initializing issue templates, or any combination. The installer would not know what constitutes a correctly configured tracker. The companion tool `wizard.py` is described as handling "prerequisite checks, scaffolder, config writer" (§1 line 9) — "tracker configuration" is not listed among its responsibilities.
- **Suggested fix**: Either enumerate what tracker configuration means (e.g., "create these labels: …", "enable Issues if disabled", "verify the repo has no conflicting issue templates") or explicitly delegate it to a named tool with a specific invocation. If tracker configuration is handled by `wizard.py`, say so here.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 54
- **Severity**: warning
- **Issue**: §4 step 0 tells the installer "Use `deny` rules, never `ask`" and explains the semantic difference — but never specifies *where or how* to write these rules. The installer knows what to achieve but not the mechanism.
- **Evidence**: The instruction mentions "shared settings for all agents" (line 50) as the destination for the user's deny paths, and says the default deny-list covers "recursive force-deletes of the filesystem root and home directory" (line 50). But the file format, config key, or tool invocation to persist deny rules is never given. An LLM installer would have to guess the config schema.
- **Suggested fix**: State the concrete destination for deny rules — e.g., "write them to `.squidsquad/config/deny.yaml` under the key `paths`" (or whatever the actual mechanism is), or name the wizard.py sub-command that applies them.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 68
- **Severity**: warning
- **Issue**: §4 step 7 says "scaffold `.squidsquad/`, compose the agents, and apply the customizations" with no sequencing guidance. Three helper tools are listed (§1 line 9 and §9 line 145): `wizard.py` (scaffolder, config writer), `manifest.py` (roles and presets), `compose.py` (composing agent instructions). The installer needs to know the correct order and dependencies between these tools.
- **Evidence**: The tools have clear dependencies — you likely need to scaffold before composing, and manifest data likely feeds into compose. But the doc never states: "first call wizard.py to scaffold, then manifest.py to resolve roles, then compose.py with the manifest output." The installer could call them in the wrong order or skip one.
- **Suggested fix**: Add a brief tool-calling sequence for step 7 — even a one-liner like "Call `wizard.py scaffold`, then `manifest.py`, then `compose.py` with the customizations" — so the installer knows the dependency chain.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 106
- **Severity**: warning
- **Issue**: §5 says "A fallback interval may be written to config with a sensible default — never a headline setting." The installer is expected to write a concrete value to config, but no default value is provided.
- **Evidence**: The doc correctly frames the loop as a fallback, not a user choice. But if the installer is to write a fallback interval to config, it needs to know what number to write. "Sensible default" is a judgment call with no anchoring — is it 30 seconds? 5 minutes? 30 minutes? Different choices have very different system behavior (too fast = noise; too slow = long stalls when harness is down).
- **Suggested fix**: Provide the concrete default value (e.g., "30 minutes") that the installer should write. The installer can still adapt it based on project characteristics if the variables allow it, but there must be a baseline.

---

### Finding 8

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 58
- **Severity**: warning
- **Issue**: §4 step 2 says "you only see the folder you're installed in" — but the scope is ambiguous. The installer is running to *perform* an installation; it's not yet installed. What folder does this constraint refer to? The repo root? The `.squidsquad/` directory that will be scaffolded? The current working directory?
- **Evidence**: This constraint on the installer's filesystem visibility is immediately followed by "and external references the user points to" — which may be URLs or sibling repos outside the working directory. The tension between "you only see the folder you're installed in" and "ask for external references" is unresolved. Can the installer fetch URLs? Read sibling repos? The boundary is unclear.
- **Suggested fix**: Clarify: "you can read anything in the repo root (the working directory) and follow URLs the user provides, but you cannot traverse outside the repo's directory tree on the local filesystem."

---

### Finding 9

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 56
- **Severity**: warning
- **Issue**: §4 step 1 tells the installer to "Confirm there's a GitHub repo, `gh` is authenticated" — but provides no guidance for the failure case. GitHub Issues as the forge is a hard invariant (§3 line 32). If `gh` is not authenticated or there is no GitHub repo, what should the installer do? Abort? Help the user set it up? This is a critical fork with no resolution path.
- **Evidence**: The invariants make GitHub Issues mandatory. Step 1 is the gate. But unlike step 0 (which has explicit Yes/No branches with clear outcomes), step 1 has no failure branch. The installer would not know whether to walk the user through `gh auth login`, suggest they create a repo, or abort with a message.
- **Suggested fix**: Add a failure branch: "If there's no GitHub repo or `gh` isn't authenticated, explain that GitHub Issues is required for the team's shared workspace and help the user get set up (or stop if they prefer)."

---

### Finding 10

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 117-119
- **Severity**: warning
- **Issue**: §7 describes a runtime customization affordance — "they simply tell the PM how they want the team to behave … and it's saved as a durable project customization behind the scenes" — but the installer is never told to set up any mechanism that would enable this. The PM agent receiving a natural-language request and persisting it as a customization implies some infrastructure (a customization store, a PM capability to interpret and save requests). The installer should configure this during setup.
- **Evidence**: §4 step 7 applies customizations confirmed during the install conversation, but §7 describes an ongoing, post-install customization path that the user is told they can use "any time, not just by re-running setup." If the installer doesn't set up the mechanism for the PM to receive and persist these runtime customizations, the promise in §7 is hollow.
- **Suggested fix**: Either add to §4 step 7 or §4 step 9 a note that the installer must ensure the PM's instructions include the customization-update capability, or (if the mechanism is inherent in the compose output) state that explicitly so the installer knows this is already handled.

---

### Finding 11

- **File**: `.squidsquad/pm/planning/_installer-runtime-input.md`
- **Line**: 46-48 (§4 header) vs. 50-54 (§4 step 0)
- **Severity**: warning
- **Issue**: §4's preamble says "The understanding stages (2–4) shift with the project; the later stages (5–9) are the same either way." But step 0 (Consent & guardrails) is not in either group — it precedes step 1. The numbering implies steps 0–9, but the "understanding stages (2–4)" and "later stages (5–9)" grouping silently excludes steps 0 and 1 from both categories. An installer reading this may wonder: is step 0 part of "understanding" or "later"? Does it shift with the project or stay the same? The text resolves this implicitly (step 0 is "first, before anything"), but the categorical statement is inaccurate.
- **Evidence**: The statement "The understanding stages (2–4) shift with the project; the later stages (5–9) are the same either way" is a false partition of the 10 steps (0–9). Steps 0 and 1 are unclassified, creating ambiguity about whether they adapt to project state.
- **Suggested fix**: Rewrite to: "The understanding stages (2–4) shift with the project; stages 0–1 and 5–9 are the same either way." This accurately covers all 10 steps.