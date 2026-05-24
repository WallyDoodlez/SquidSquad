All Round 1 fixes verified. I've found 3 **new** issues (not from Round 1):

---

### Finding 1

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 83, 356
- **Severity**: error
- **Issue**: Two markdown links use `(MEMORY)` as their target, but no file named `MEMORY` or `MEMORY.md` exists anywhere in the repository.
- **Evidence**: 
  - Line 83: `[feedback_clone_isolation](MEMORY)` — glob for `**/MEMORY*` and `**/memory*` returns zero results.
  - Line 356: `[project_tracker_abstraction](MEMORY)` — same dead target.
  - Both terms (`feedback_clone_isolation`, `project_tracker_abstraction`) appear nowhere else in the `docs/` directory, so neither is defined externally.
- **Suggested fix**: Either create a `MEMORY.md` reference doc defining these terms, or replace `(MEMORY)` with inline descriptions of what these concept references mean, or link to the actual file where these concepts are defined (e.g., if they live in `AGENT-RUNTIME.md` or `ARCHITECTURE.md`).

---

### Finding 2

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 103 (mermaid diagram node `P7`)
- **Severity**: warning
- **Issue**: The Phase 7 diagram node reads `"Phase 7<br/>Tracker setup<br/>(labels + initial issues)"`, attributing label creation to Phase 7, but the prose (§4.8 Phase 5 step 5 at line 208, and §4.10 at line 224) consistently says labels are created in Phase 5.
- **Evidence**: 
  - Line 101: `P5["Phase 5<br/>Atomic write<br/>(scaffold + L4 + labels)"]` — Phase 5 already claims labels.
  - Line 208: "Ensures GitHub labels — creates the status/role/type/priority/severity label taxonomy via `gh label create`" (in Phase 5).
  - Line 224: "Beyond the labels created in Phase 5, the installer may seed initial issues" (Phase 7 only does issues).
  - So labels appear in **both** P5 and P7 diagram nodes, but only P5 actually creates them.
- **Suggested fix**: Change line 103 from `"(labels + initial issues)"` to `"(initial issues)"`.

---

### Finding 3

- **File**: docs/INSTALLER-ARCH.md
- **Line**: 452
- **Severity**: warning
- **Issue**: The G4 open-question text references `"Phase 5.1"` as a cleanup path, but no section §5.1 or subsection "5.1" exists in this document. The notation `Phase 5.1` reads like a section number that doesn't exist (the doc has §5 at line 236, but it has no subsections).
- **Evidence**: 
  - Line 452: "The cleanup path in Phase 5.1 handles this, but the model isn't truly atomic."
  - The doc's section hierarchy: §5 is "File layout produced" (line 236) with no §5.1. Phase 5 is described in §4.8 (line 200) with numbered steps 1–5, where step 1 is "Cleans up any prior partial state."
  - The most likely intended reference is either "Phase 5 step 1" (the cleanup step at line 204) or "§11.2" (the interrupted-install recovery section at line 431). Neither is clearly what "Phase 5.1" means.
  - Contrast with the nearby §11.1 reference at line 426 which correctly uses `WIZARD's Step 7.1` — an explicit `Source.N` format.
- **Suggested fix**: Replace `"Phase 5.1"` with either `"Phase 5 step 1"` (if referring to the pre-scaffold cleanup at line 204) or `"§11.2"` (if referring to the interrupted-install recovery path at line 431). The latter matches the crash-between-5-and-8 scenario more precisely.