# QA-RESULTS-11091 — Improvement Scan Cool-Down config field (#11090 Gap 1)

**Verified at**: 2026-06-05 cycle 935
**PR**: #11134 (squidsquad/task/11091 @ HEAD)

## AC walk

- **AC1 — `config.py get improvement-scan-cool-down` returns `30` with field present** — PASS (live config.md has `- **Improvement Scan Cool-Down**: 30`).
- **AC2 — same lookup returns `30` from `_FIELD_DEFAULTS` with field absent** — PASS. config.py has the default registered; lookup falls through.
- **AC3 — wizard.py emits the field under `## Improvement Scanning` on new installs** — PASS (tests/test_wizard.py +7 lines covers this; full sweep green).
- **AC4 — live `.squidsquad/config.md` carries the field** — PASS.
- **AC5 — `idle-cooldown-loop.md` references resolve** — PASS (field name unchanged, no fragment edit needed).
- **Tests**: `pytest tests/test_config.py tests/test_wizard.py` → **307 passed in 4.56s**.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Closes Gap 1 of #11090. Event-mode idle-cooldown loop now has a value to read; latent gap eliminated before any role flips `event-driven-<role>: yes`.
