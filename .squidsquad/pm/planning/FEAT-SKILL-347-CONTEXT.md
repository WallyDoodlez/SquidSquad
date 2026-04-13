# FEAT-SKILL-347 Context — Separate PM from QA Role

## Scope

Split the combined PM/QA role into standalone PM and QA agents. QA gets its own Ralph Loop focused on verification. PM keeps coordination, planning, human interaction.

## Locked Decisions (human decided)

- **QA preset-gated**: QA only installed for software-dev presets. Non-dev presets don't get QA.
- **PM QA fallback**: PM retains verification capability when QA is not installed (same pattern as DM delivery fallback). Presence check: `.squidsquad/qa/` exists?
- **Split improvement scanning**: PM scans for process improvements. QA scans for test coverage gaps. Each role scans its own domain.
- **No QA→PM notification for bugs**: QA files bugs directly. Discussion entries visible to all. PM doesn't need special notification.

## Dev Discretion (dev agent can choose)

- How to strip QA steps from PM template (inline removal vs conditional)
- QA iteration log format
- QA working-state structure

## Side Effect Mitigations (required)

- PM fallback must handle ALL QA steps when QA absent
- Existing installs: upgrade scaffolds QA directory if software-dev preset
- QA manifest flag flip (`always_installed: true` for software-dev)
- Test both paths: QA present and QA absent

## Upgrade Path (required)

- Flip QA manifest `always_installed` for software-dev presets
- `compose.py deploy qa` scaffolds QA directory
- Strip QA steps from PM template, add presence check fallback
- Existing installs: squidsquad-upgrade detects preset and scaffolds QA if appropriate

## Out of Scope

- QA running on a separate machine
- QA having its own clone (handled by #5 add_role.py)
- CI integration for QA
