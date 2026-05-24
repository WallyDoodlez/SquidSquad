I've verified the three R7-applied changes (§8.1, §8.4, §7.6 diagram). All three are correctly applied. However, I found two pre-existing documentation calculation errors in the cadence summary lines.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 402
- **Severity**: LOW
- **Issue**: Wrong time approximation in EAD cadence summary. Three empty polls at 10s = 30s elapsed, then three at 30s = 90s elapsed. Total to reach 60s ceiling: 120s = 2 minutes exactly, not ≈3 minutes.
- **Evidence**: The cadence pseudocode (lines 391–399) specifies 3 consecutive empty polls at 10s then step to 30s, then 3 more at 30s then step to 60s. Poll times: t=10, 20, 30 (step to 30s), 60, 90, 120 (step to 60s). Elapsed = 120s = 2 minutes. "≈3 minutes" is off by ~50%.
- **Suggested fix**: Change `(≈3 minutes of inactivity)` to `(≈2 minutes of inactivity)`.

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 598
- **Severity**: LOW
- **Issue**: Wrong time approximation in event_poll cadence summary. Three empty polls at 5s = 15s elapsed, then three at 30s = 90s elapsed. Total to reach 60s ceiling: 105s ≈ 1.75 minutes, not ≈2.5 minutes.
- **Evidence**: The cadence pseudocode (lines 587–595) specifies 3 consecutive empty polls at 5s then step to 30s, then 3 more at 30s then step to 60s. Poll times: t=5, 10, 15 (step to 30s), 45, 75, 105 (step to 60s). Elapsed = 105s ≈ 1.75 min. "≈2.5 minutes" is off by ~40%.
- **Suggested fix**: Change `(≈2.5 minutes idle)` to `(≈1.75 minutes idle)`.

---

The R7-applied changes are all correct: §8.1 clearly separates configurable mode from transient fallback mixed mode; §8.4 distinguishes "configured no" from "yes+probe-fail" fallback; and §7.6 diagram nodes all use properly quoted Mermaid label syntax. No issues remain with the R7 fixes themselves. The two LOW findings above are pre-existing math errors unrelated to R7.