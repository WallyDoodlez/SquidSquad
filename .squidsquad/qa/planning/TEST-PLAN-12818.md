# TEST-PLAN-12818 — L2 PM: brief summary on no-action wakes (suppress per-agent detail)

type:task (operator-pre-approved). PR #12953, branch `squidsquad/task/12818`, role:skill.
Explicit 5-AC list in the issue. Touches LLM-consumed instruction
(`references/roles/pm/`) → **CQ HARD GATE** (AC5, verifier-owned).
Verified in isolated worktree `D:\Dev\Dev\sq-12818-verify`.

Hygiene note (→PM, non-blocking): #12818 carries BOTH status:approved AND
status:pending-test (double status-label; canonical for QA = pending-test).

## AC verification plan (from issue body)
- **AC1 (source):** directive in L2 PM source under `references/roles/pm/`, authored at
  source (NOT edited in composed `.squidsquad/pm/CLAUDE.md`). Evidence: diff adds it to
  `references/roles/pm/SOUL.md` (Communication Style section).
- **AC2 (compose consumption):** after `compose.py deploy pm`, composed
  `.squidsquad/pm/CLAUDE.md` contains the directive in the User-Facing / Communication-Style
  region. Evidence: ran deploy pm in worktree → directive at composed line 205.
- **AC3 (no contradiction / prose-drift):** directive refines, not contradicts, L1 Soul
  User-Facing Communication (default one-liner + jargon-free intact). Evidence: composed L1
  rule at line 131-137 intact; L2 directive says "refines (does not replace)" + preserves
  default one-liner + jargon-free; §4 no-action-wake line (365) consistent.
- **AC4 (manifest):** no new `references/` file → installer-files.txt unchanged. Evidence:
  diff = only `references/roles/pm/SOUL.md` (existing) + `tests/comprehension/12818_spec.json`
  (under tests/, not references/). installer-files.txt NOT in diff. Correct.
- **AC5 (comprehension):** fresh PM reading composed CLAUDE.md, on no-action wake → brief
  generic summary, no per-agent enumeration. Verifier-authored independent CQ.

## Method / evidence
- **AC5 CQ (verifier-owned):** authored 5 independent questions; fresh sonnet given ONLY
  the L1 User-Facing Communication rule + the new L2 directive → 5/5 correct, zero
  anti-patterns (brief-generic; no enumerate; real-action unrestricted; internal-logs
  unrestricted; default one-liner OK + reword short/generic/jargon-free). Skill also
  authored 12818_spec.json (CQ is verifier's lane #9184) → flagged PM, non-blocking; ran my own.
- **No-reg:** full `run_tests.py static` (pending — see QA-RESULTS).
- Pre-existing config.md `Dev Agents:`→`Workers:` deprecation WARNING on compose (not #12818) → flag PM, non-blocking.
