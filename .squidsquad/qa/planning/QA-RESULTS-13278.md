# QA-RESULTS-13278 — model_router clean-sentinel bypasses the MIN_OUTPUT_LENGTH gate

**Verdict: PASS — zero gaps.** PR #13300 merged (squash, +additions-only). skill CORRECTED the issue's premise — DeepSeek wasn't broken; the gate was false-rejecting its sanctioned clean output.

## Root cause (corrected)
The code-review template (#5932) instructs the model to output exactly `NO_FINDINGS` for a clean review. `route()`'s uniform `MIN_OUTPUT_LENGTH=200` quality gate flagged that 11-char sentinel as degenerate → exit 1 → Sonnet fallback. So **every clean DeepSeek review tripped the gate**, making the path look permanently broken when it worked.

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | the clean sentinel (`NO_FINDINGS`) bypasses the length gate → exit 0 | PASS (model_router.py:817/821) |
| AC2 | genuinely degenerate short output (non-sentinel < 200) STILL → exit 1 fallback | PASS |
| AC3 | sentinel match is case-insensitive + tolerates trailing explanation | PASS |
| AC4 | an auth-error string (`ERR 402`) is NOT mistaken for a clean review (still falls back) | PASS — the subtle correctness case |
| AC5 | None-response fail-closed + sentinel-bypass audited in diagnostics + regression tests | PASS |

## Evidence
- Code (model_router.py): `CLEAN_RESULT_SENTINELS=("NO_FINDINGS",)`; line 817 `is_clean_sentinel = any(stripped.upper().startswith(s.upper()) ...)`; line 821 `if not is_clean_sentinel and len(stripped) < MIN_OUTPUT_LENGTH → exit 1`. Sonnet-DS hardening: None-response guard, guarded len(), distinct success-sentinel diagnostic action.
- skill tests (test_model_router.py): short-sentinel→0, case-insensitive+trailing→0, short-non-sentinel→1, sentinel-bypass-audited. 93 pass.
- **QA independent test** (`tests/test_feat_13278_clean_sentinel_bypass.py`): exercises the bypass predicate across real-world variants — clean-sentinel variants bypass; empty/short-garbage/**`ERR 402` auth-error**/`null` are NOT bypassed (an auth failure must not read as a clean review); a real finding is not the sentinel. ALL PASS.
- Deterministic → no CQ.

## Note
Restores the DeepSeek DS-review second-opinion the team thought was broken (it was a false-negative gate, not a dead model). Genuine degeneracy/auth failures still correctly fall back to Sonnet. (skill's scope note: the earlier 402-class working-state mentions were likely a separate past transient; DeepSeek authenticates fine now.)

Status: pending-test → pending-ship.
