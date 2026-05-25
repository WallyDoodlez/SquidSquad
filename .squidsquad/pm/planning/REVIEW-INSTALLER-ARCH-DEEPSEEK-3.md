Now I have all the evidence needed. Let me compile the findings.

---

## Review Results

### R2 Fixes — All Clean ✓

- **Dead (MEMORY) links**: No `(MEMORY)` link targets remain in the doc body. The only hit is in the revision log describing the fix. Lines 96 and 379 use inline descriptions as specified. ✓
- **Phase 7 diagram** (line 116): Node text is `"(initial issues)"` — correct, not the old `"(labels + initial issues)"`. ✓
- **G4 reference** (line 475): Reads `"§11.2"` — correct, not the old `"Phase 5.1"`. ✓

### Categorical-Role Rewrite — 3 Inconsistencies Found

---

### Finding 1

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 209
- **Severity**: MEDIUM
- **Issue**: "team shape" used where "team preset" is the canonical term per the categorical-role rewrite.
- **Evidence**: The revision log (line 501) explicitly states that §3.1 was updated from "team shape (which dev roles)" to "team preset (which workers and verifiers)". §1.1 defines "team preset" as the canonical term. Line 209 in §4.7 (Phase 4 — Approval gate) was missed: `"the user names which detail to change — team shape, loop interval, tracker, etc."`. This is the only remaining prose use of the old term outside the revision log.
- **Suggested fix**: Change `"team shape"` to `"team preset"` on line 209.

---

### Finding 2

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 242
- **Severity**: LOW
- **Issue**: Placeholder `<team_shape>` in the commit message convention uses the old term; should be `<team_preset>`.
- **Evidence**: §4.11 Phase 8: `Commit message follows the convention wizard: SquidSquad install — <team_shape>.` The install spec in §4.5 uses `team_preset:` as its key (line 187). The commit message placeholder should match the canonical terminology from §1.1.
- **Suggested fix**: Change `<team_shape>` to `<team_preset>` on line 242.

---

### Finding 3

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 367 (and echoed in revision log line 498)
- **Severity**: MEDIUM
- **Issue**: `"follow-up issue against worker (skill)"` uses `worker` as if it were a concrete role name assignable in the tracker, but `worker` is now a categorical class, not a concrete role in any shipped preset.
- **Evidence**: §1.1 (line 21) states: "The default preset has one worker named `dev`". No shipped preset has a concrete role literally named `worker`. SquidSquad's tracker requires concrete role assignees — you can't file an issue against a class. The phrase `follow-up issue against worker (skill)` is ambiguous: which concrete worker role (`dev`? `fe`? `be`?) should own this follow-up? It reads as a leftover from the pre-categorical model where `worker` was a concrete role name. The revision log (line 501) says prose was changed from "concrete role names (`be`, `fe`, `skill`, `qa`, `dev`, etc.)" — confirming `worker` was not among the canonical concrete names from before either, making this usage genuinely unclear.
- **Suggested fix**: Either (a) use the categorical class clearly: `"follow-up issue against the worker class (skill)"` or (b) specify the default-preset concrete role: `"follow-up issue against dev (skill)"`. The same fix applies to the echo at line 498.

---

**Summary**: R2 fixes are clean. The categorical-role rewrite has 3 residual inconsistencies (2 MEDIUM, 1 LOW) where old "team shape" / `<team_shape>` terminology and an ambiguous `worker` reference survived the rewrite.