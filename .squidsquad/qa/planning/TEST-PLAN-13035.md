# TEST-PLAN-13035 — Relentless-autonomy reframe + inline 20-min hardcoded auto-timeout

- **Task**: #13035 (type:task, priority:high, role:skill) — #12896 child. Docs/instructions change (no runtime code; inline fires no wrappers, timeout is agent-behavioral).
- **PR**: #13051, branch `squidsquad/task/13035`, HEAD `4b47c51cc`. Source files: `references/roles/SOUL.md` (+10/-1), `references/roles/instructions.md` (+4/-3), `docs/AGENT-RUNTIME.md` (+11/-2, human-facing doc). Source-only (composed CLAUDE.md regenerate on merge via deploy-signal, #11511 state-file guard). No closing keyword for #13035 (PR closes umbrella #12896 at ship).
- **Derived**: 2026-06-21 00:10 from the 8-AC contract in the issue body (operator-pre-locked behavior).
- **Touches LLM-consumed instructions → CQ HARD GATE required** (AC8, verifier-authored per #9184).
- **Method**: isolated worktree; deterministic config grep (AC2); `compose.py deploy-all` consumption check (AC7); DS-REVIEW inspection (AC6); fresh-agent CQ on isolated modified passages (AC8).

## Acceptance criteria

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | SOUL states the operator-locked 4-level precedence: (1) pending work→relentless; (2) no work→scan; (3) scans capped at 3 + cool-down (KEEP #12506 guardrail); (4) inline = only pause, auto-releases 20 min. Composed into all 4 CLAUDE.md. | SOUL diff + composed grep (all 4). CQ1/CQ6. |
| AC2 | 20-min hardcoded / non-configurable; assert NO new config key. | grep config.md/config.py → none. CQ3. |
| AC3 | Resume = next event the agent detects once ≥20 min since human's last inline msg; agent stamps via `cycle.py timestamp` and compares. | instructions §8 + AGENT-RUNTIME §3.2. CQ4. |
| AC4 | #12506 driver tick = qualifying resume event on silent forge → ≤~30 min, never permanent; documented as expected not bug. | AGENT-RUNTIME §3.2 + SOUL. CQ4. |
| AC5 | Inline indicator clears via `cycle.py status-bar-self idle ""` on timeout; reconciled with set behavior; coordinate #12451. | instructions §8 + AGENT-RUNTIME diff. |
| AC6 | DS prose-drift audit (SOUL↔AGENT-RUNTIME↔PM L2), iterated to convergence. | DS-REVIEW-13035.md. |
| AC7 | `compose.py deploy-all` regenerates all 4 CLAUDE.md and new behavior reaches target slots (consumption, not just source-exists); installer-files only if new file. | deploy-all + composed grep. |
| AC8 | Verifier-authored CQ: fresh agent given only modified files answers (a) relentless default, (b) inline only pause, (c) 20-min hardcoded, (d) resume=next event ≥20min + #12506 backstop ≤30min, (e) attended-not-completed. HARD GATE. | tests/comprehension/13035_spec.json + fresh sonnet run. |

## Notes
- AGENT-RUNTIME.md is human-facing documentation (not Read by agents at runtime) — its +11 lines are rationale; CQ targets the agent-consumed surfaces (SOUL, instructions) only.
- AC5 #12451 (inline status-bar surface) is OPEN — coordination watch item; the diff is clean vs main, so no merge conflict in this PR. Not a verifier gap.
