# TEST-PLAN-10388 — PRD-A / Story A4: compose.py deploy-all --check mode

**Source**: issue #10388 ACs.
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `--check` flag added to `deploy-all` (and `deploy <alias>` if cheap).
- **AC-2**: In-memory composition compared against on-disk `.squidsquad/<alias>/CLAUDE.md`; exit 0 if all match, 1 if any differ.
- **AC-3**: Stderr emits structured per-alias diff (alias + slot(s) differing).
- **AC-4**: No writes to disk in `--check` mode.
- **AC-5**: Distinct exit codes — 0 clean / 1 drift / 2 error (e.g. malformed source).
- **AC-6**: Tests cover clean install (0), edited L4 without recompose (1), missing source (2).

## Test Cases

### TC-1 (AC-1, --check accepted on both commands):
- `compose.py deploy <alias> --check` and `compose.py deploy-all --check` both run end-to-end.

### TC-2 (AC-2 clean): in-memory compose == disk → status clean.

### TC-3 (AC-2 drift): on-disk file differs → status drift.

### TC-4 (AC-3 diff content): drift reports which H2 sections changed.

### TC-5 (AC-4 no-write): running --check leaves disk files unchanged.

### TC-6 (AC-5 exit codes): exit ∈ {0, 1, 2} and the V2-combination case returns the error code path.

### TC-7 (AC-6 missing source): when on-disk file is absent → "missing" status path.

## Non-goals
- Harness boot invocation (PRD E).
- Auto-fix (`--check` is read-only).
