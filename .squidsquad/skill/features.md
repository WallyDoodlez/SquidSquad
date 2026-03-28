# Feature Tracker

_Features start as Pending (awaiting human approval) and move through Approved → In Progress → Pending Test → Shipped._

---

## FEAT-SKILL-001 — Use structured prompts during setup

- **Priority**: High
- **Status**: Approved
- **Owner**: skill-lead
- **Description**: The current setup flow asks freeform questions. Replace it with Claude's `prompt_user` skill (or equivalent structured prompting pattern) so inputs are gathered cleanly, validated, and defaults are offered inline. This makes setup more reliable and easier to script.
- **Acceptance Criteria**:
  - [ ] Each setup question uses a structured prompt with a clear label, description, and default value shown
  - [ ] Invalid inputs (e.g. interval < 1, empty project name) are caught and re-prompted rather than silently accepted
  - [ ] Setup can be completed from a single natural-language sentence if all info is provided upfront (e.g. "Set up SquidSquad for kubex, BE only, 5 min interval")
  - [ ] SKILL.md Step 1 updated to reflect the new prompting approach

### Discussion

> [2026-03-27 20:00] **pm/qa**: Seeded at initialization. Approved by human at setup time.

---

## FEAT-SKILL-002 — Import existing bugs and features from external sources during setup

- **Priority**: High
- **Status**: Approved
- **Owner**: skill-lead
- **Description**: During setup Step 1, after gathering project details, offer to import existing bugs or features from an external source. Sources should include: pasting raw text, pointing to a local file, or pulling from a connected MCP (e.g. GitHub Issues, Jira, Linear, Notion) if one is available in the session. Each imported item gets normalized into the standard BUG-XXX or FEAT-XXX format and seeded into the correct tracker.
- **Acceptance Criteria**:
  - [ ] Setup offers an import prompt after project details are gathered: "Do you have existing bugs or features to import? (paste text, file path, or MCP source — or skip)"
  - [ ] Pasted text is parsed and normalized into tracker entries with reasonable field inference (title, severity/priority, description)
  - [ ] File path input reads the file and parses it the same way
  - [ ] If an MCP tool is available in the session (e.g. GitHub Issues, Jira), it is offered as an import option and items are fetched and mapped to the tracker format
  - [ ] Imported items are filed to the correct tracker (fe/, be/, skill/, etc.) based on inferred or stated owner
  - [ ] Each imported entry gets a Discussion note: `> **pm/qa**: Imported from [source] at setup.`
  - [ ] SKILL.md Step 1 and Step 6 updated to document the import flow

### Discussion

> [2026-03-27 20:00] **pm/qa**: Seeded at initialization. Approved by human at setup time.
