# TEST-PLAN-10442 — PRD-B / Story B3: length floor + code-block parity verifier

**Source**: issue #10442 ACs (parent PRD compose-assemble-stage §4.6).
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `check_length_floor(linked: str, assembled: str, floor: float = 0.8) -> bool` returns False when assembled is too short relative to linked at the configured floor.
- **AC-2**: `check_code_block_parity(linked: str, assembled: str, tolerance: float = 0.1) -> bool` returns False when fenced-code-block count OR inline-backtick count drifts by more than ±tolerance vs linked.
- **AC-3**: Both functions live in `references/scripts/assemble_verifier.py` alongside B2's `verify_preservation`.
- **AC-4**: Unit tests cover the 5 named boundary cases:
  1. empty assembled with non-empty linked → length floor fails
  2. assembled at exactly `0.8 * len(linked)` → length floor passes (inclusive boundary)
  3. assembled at `0.79 * len(linked)` → length floor fails
  4. fenced code block count drops >10% → code parity fails
  5. inline backtick span count changes >10% → code parity fails

## Test Cases

### TC-1 (AC-1, AC-3 module placement): live import + signature check
- Probe: `import assemble_verifier; assemble_verifier.check_length_floor` exists with signature `(linked, assembled, floor=0.8)`.

### TC-2 (AC-2, AC-3): live import + signature check
- Probe: `assemble_verifier.check_code_block_parity` exists with signature `(linked, assembled, tolerance=0.1)`.

### TC-3 (AC-4 boundary 1): empty assembled fails
- `check_length_floor("hello", "")` → False.

### TC-4 (AC-4 boundary 2): exact 0.8x passes
- linked = 100 chars; assembled = 80 chars → True.

### TC-5 (AC-4 boundary 3): 0.79x fails
- linked = 100 chars; assembled = 79 chars → False.

### TC-6 (AC-4 boundary 4): fenced-block drop >10% fails
- linked has 10 fenced blocks; assembled has 8 → drop = 20% → False.

### TC-7 (AC-4 boundary 5): inline backtick change >10% fails
- linked has 10 inline backticks; assembled has 8 → drop = 20% → False.

### TC-8 (cross-counting prevention): inline counter doesn't double-count fenced backticks
- Fenced block ``` ``` should not contribute to inline count after fencing is stripped.

### TC-9 (no LLM dep, pure Python): module has no anthropic/openai/requests imports.

### TC-10 (combined dimension): either AC-1 OR AC-2 failing is reportable independently.

## Non-goals (not tested here)

- B2's verify_preservation (covered by TEST-PLAN-10441 verification, prior PASS)
- Calling the LLM (B1 owns)
- Abort-on-failure plumbing (B7 owns)
