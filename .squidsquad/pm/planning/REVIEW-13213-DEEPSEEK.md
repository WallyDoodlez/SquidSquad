Now I have all the evidence needed. Let me compile my findings.

---

## Findings

### Finding 1

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 689 vs 705
- **Severity**: MEDIUM
- **Issue**: §16.1 (line 689) labels `Stop` as a **"turn-complete heartbeat"**, but the new §16.3 transport description (line 705) explicitly groups `Stop` under **"pause-guard hooks" routed to `/hooks/pause`** — not as an activity-heartbeat hook routed to `/hooks/activity`. This creates an internal contradiction: the catalog calls it a heartbeat, but its transport classification puts it on the pause endpoint. The liveness model (§15.1 line 602) lists the cycle-completion heartbeat source as `cycle_post` (harness-side, not a Claude Code hook), not `Stop`. A reader sees `Stop` labeled a heartbeat in the catalog, then sees it routed to `/hooks/pause` and listed as a "pause-guard hook" in §16.3, which are incompatible framings.
- **Evidence**: 
  - §16.1 line 689: `| Stop (stop_hook_active) | agent finishes a turn | turn-complete heartbeat |`
  - §16.3 line 705: `Lower-frequency hooks — SessionEnd, and the pause-guard hooks (Notification / Stop / PreCompact etc. → /hooks/pause)`
  - §15.1 line 602 uses `cycle_post` (not `Stop`) as the cycle-completion heartbeat source.
  - §4.6 line 141: `/hooks/activity` receives activity heartbeats; `/hooks/pause` (line 142) receives pause-guard payloads. These are separate endpoints with separate semantics.
- **Suggested fix**: In §16.1 line 689, replace `turn-complete heartbeat` with `turn-complete signal (pause-aware: confirms agent completed a turn, routed to /hooks/pause)` — or if `Stop` really is meant as a heartbeat, fix §16.3 line 705 to remove `Stop` from the pause-guard group and add it to the activity-heartbeat group (routed via `activity_hook.py` → `/hooks/activity`).

### Finding 2

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 710
- **Severity**: LOW
- **Issue**: §16.4 consumer summary says heartbeat comes from `Pre/PostToolUse` without explicitly naming `PostToolUseFailure`, while every other section that enumerates heartbeat sources lists `PostToolUseFailure` separately: §4.6 line 141 (`UserPromptSubmit / PreToolUse / PostToolUse / PostToolUseFailure`), §15.1 line 602 (`PreToolUse / PostToolUse / PostToolUseFailure`), §16.1 line 687 (`PostToolUseFailure … heartbeat`), §16.3 line 705 (same four). The abbreviation `Pre/PostToolUse` in §16.4 is the only heartbeat-source enumeration in the doc that omits the failure variant — and it appears in the section that is the authoritative consumer summary for the liveness model.
- **Evidence**: 
  - §16.4 line 710: `heartbeat from UserPromptSubmit (prompt-receipt) + Pre/PostToolUse + cycle_post`
  - Contrast with §15.1 line 602: `every tool call (PreToolUse / PostToolUse / PostToolUseFailure)`
  - Contrast with §4.6 line 141: `UserPromptSubmit / PreToolUse / PostToolUse / PostToolUseFailure`
- **Suggested fix**: Change `Pre/PostToolUse` to `PreToolUse / PostToolUse / PostToolUseFailure` on §16.4 line 710 for consistency with the rest of the doc.

---

## Overall Verdict

**PASS with minor notes.** The core change — promoting `UserPromptSubmit` to an activity-heartbeat source — is internally consistent across all sections. The "two mechanisms" count in §15.1 remains correct (UserPromptSubmit is a new source within mechanism 1, not a new mechanism). §15.2's "this ONE signal serves three jobs" is still accurate (it describes the Pre/PostToolUse signal specifically, not all heartbeat sources). The cross-doc reference in AGENT-RUNTIME §8.2 matches HARNESS-ARCH. The doc-vs-code transport description (§16.3) correctly describes `activity_hook.py`'s async command-hook pattern, generic `hook_event_name` field, and `/hooks/activity` endpoint. The prompt-receipt heartbeat does not set in-flight — this is clear from the mermaid diagram annotations and the pause-aware guard description. §15.7 open questions remain accurate (window duration is still open). The two findings above are labeling/consistency polish, not correctness defects.