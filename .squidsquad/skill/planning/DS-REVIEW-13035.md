Now I have all the data I need. Here is my systematic audit across all four audit items.

---

## Summary

The three changed files are **strongly aligned** on the core mechanism. They agree on the 20-min hardcoded window, the resume trigger (next event ≥20 min), the ≤~30-min driver-tick backstop bound, and the indicator-clear command (`status-bar-self idle ""`). No conflict with PM L2 advertise-duty. One genuine prose inconsistency found.

---

### Finding 1

- **File**: `references/roles/SOUL.md`
- **Line**: 58
- **Severity**: warning
- **Issue**: SOUL.md's blanket "All timestamps come from `cycle.py timestamp-short`" rule contradicts the inline auto-timeout's need for `cycle.py timestamp` (full date+time, not HH:MM:SS), which is correctly specified in `instructions.md` line 154 and `AGENT-RUNTIME.md` line 135.

- **Evidence**:
  - `SOUL.md` line 58: "All timestamps come from `python references/scripts/cycle.py timestamp-short` — never guess or fabricate times."
  - `instructions.md` line 154: "stamp it with `python references/scripts/cycle.py timestamp`"
  - `AGENT-RUNTIME.md` line 135: "stamps the human's last-inline-message time itself — via `cycle.py timestamp`"
  - `references/scripts/cycle.py` lines 46-57: `timestamp` returns `YYYY-MM-DD HH:MM`; `timestamp-short` returns `HH:MM:SS`. Only `timestamp` carries the date prefix needed for comparison across day boundaries — `timestamp-short` is insufficient for the ≥20-min elapsed check.
  - SOUL.md line 54 itself delegates the inline timeout mechanics to "your Agent Functions" (instructions.md §8), creating a self-contradiction within the same file: the general rule on line 58 is inconsistent with the specific mechanism delegated on line 54.

- **Suggested fix**: Add a parenthetical exception at SOUL.md line 58: "All timestamps come from `python references/scripts/cycle.py timestamp-short` (except the inline auto-timeout, which uses `cycle.py timestamp` per instructions.md §8) — never guess or fabricate times." Or, alternatively, broaden the rule to match `identity.md` line 27 which already correctly allows both: "from `cycle.py timestamp-short` or `timestamp`."

---

**Cross-check results on the four explicit audit items:**

| Audit item | SOUL.md | instructions.md §8 | AGENT-RUNTIME.md §3/§3.2 | Verdict |
|---|---|---|---|---|
| 20-min hardcoded + no config key | line 54: "hardcoded and non-configurable (explicit operator directive — there is no config key for it)" | line 154: "hardcoded / non-configurable (operator directive — there is no config key for it; do not add one)" | line 134: "fixed 20 minutes by explicit operator directive — no config key is added" | ✅ Consistent |
| Resume trigger = next event after ≥20 min | line 54: "resume on the next event you detect once ≥20 minutes have elapsed" | line 154: "the next event you detect after the 20 minutes — a forge nudge in event mode, or ... #12506 self-wake driver tick" | line 136: "next event it detects once ≥20 minutes have elapsed since the human's last inline message: a forge nudge in event mode (or a `/loop` tick in loop mode)" | ✅ Consistent (different levels of mode-specificity) |
| ≤~30-min driver-tick backstop | line 54: "≤~30 min — bounded by the driver cool-down, never permanent" | line 154: "≤~30 min, bounded by the driver's cool-down cadence — never permanent; the ≤30-min lag versus the nominal 20 is expected, not a bug" | line 137: "≤~30 minutes, not exactly 20 — bounded, never permanent. This ≤30-min lag is the accepted tradeoff" | ✅ Consistent |
| Indicator-clear to idle | line 54: "clear the inline indicator on release" (delegates exact command) | lines 151, 154: `status-bar-self idle ""` | lines 121, 136: `status-bar-self idle ""` | ✅ Consistent |
| Conflict with PM L2 advertise-duty | line 45: PM role in return path is "records the answer and re-assigns" — this is about re-assignment, orthogonal to advertising | No mention of PM advertising (correct — this is L1/L2, not PM-specific) | §3.1 return path matches SOUL.md — PM role is about ticket re-assignment, not advertising | ✅ No conflict. PM's advertising duty (`responsibility.md` line 13) is complementary: it handles surfacing `pending-human-*` tickets to the operator, which is a different concern from the auto-timeout mechanism preventing inline strand. |