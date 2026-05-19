#!/usr/bin/env bash
# Pre-flip audit for event-driven mode per CONTEXT.md §6.4
# Run from repo root: bash .squidsquad/pm/planning/pre-flip-audit.sh <role>
# Exits 0 if all checks pass for the given role, non-zero otherwise.

set -uo pipefail

ROLE="${1:-}"
if [ -z "$ROLE" ]; then
  echo "Usage: $0 <role>   (one of: skill, pm, qa, dm)" >&2
  exit 2
fi

PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  if [ "$result" = "PASS" ]; then
    echo "  [PASS] $label"
    PASS=$((PASS+1))
  else
    echo "  [FAIL] $label"
    FAIL=$((FAIL+1))
  fi
}

echo "=== Pre-flip audit for role=$ROLE ==="
echo ""

# Item 1 — #8692 singleton enforcement shipped
echo "Item 1 — #8692 singleton enforcement shipped"
S=$(gh issue view 8692 --json state --jq .state 2>/dev/null)
[ "$S" = "CLOSED" ] && check "#8692 closed" PASS || check "#8692 closed (got: $S)" FAIL

# Item 2 — #4792 harness sole-authority lifecycle shipped (via #8979)
echo "Item 2 — #4792 harness sole-authority lifecycle shipped (#8979 remediation)"
S=$(gh issue view 8979 --json state --jq .state 2>/dev/null)
[ "$S" = "CLOSED" ] && check "#8979 closed" PASS || check "#8979 closed (got: $S)" FAIL
# Sentinel-absence cross-check across the 7 scripts
SENTINEL_HITS=$(grep -rE '\.stop|\.restart|\.health' references/scripts/harness.py references/scripts/boot_remote.py references/scripts/health_check.py references/scripts/cycle_pre.py references/scripts/cycle_post.py references/scripts/start_team.py references/scripts/reboot_agent.py 2>/dev/null | grep -v '^.*:#' | grep -v 'legacy' | wc -l)
[ "$SENTINEL_HITS" -eq 0 ] && check "no functional sentinel-file refs in 7 scripts" PASS || check "sentinel-file refs found ($SENTINEL_HITS lines — review)" FAIL

# Item 3 — #8697 compose dual-mode shipped
echo "Item 3 — #8697 compose dual-mode shipped"
S=$(gh issue view 8697 --json state --jq .state 2>/dev/null)
[ "$S" = "CLOSED" ] && check "#8697 closed" PASS || check "#8697 closed (got: $S)" FAIL
# Events-mode tree exists for this role
if [ -d "references/sub-skills/common-events" ]; then
  check "common-events/ tree exists" PASS
else
  check "common-events/ tree missing" FAIL
fi

# Item 4 — L4 audit for /loop residue
echo "Item 4 — L4 audit for /loop residue applicable to role=$ROLE"
LOOP_HITS=$(grep -lE '/loop|cycle_pre|cycle_post|30.minute' .squidsquad/project/shared-*.md .squidsquad/project/${ROLE}-*.md 2>/dev/null | wc -l)
[ "$LOOP_HITS" -eq 0 ] && check "no /loop language in role-applicable L4" PASS || check "/loop language present in L4 ($LOOP_HITS files — review manually)" FAIL

# Item 5 — Post-incident re-verification (4 grep checks)
echo "Item 5 — Post-incident re-verification"

# 5a — TrackerHandoffDispatcher gone from harness.py (code-level, ignore comments)
HIT_5A=$(grep -nE 'TrackerHandoffDispatcher' references/scripts/harness.py 2>/dev/null | grep -vE '^[0-9]+:\s*#|^[0-9]+:\s*"""' | wc -l | tr -d ' ')
HIT_5A=${HIT_5A:-0}
[ "$HIT_5A" -eq 0 ] && check "5a: no TrackerHandoffDispatcher code refs in harness.py" PASS || check "5a: TrackerHandoffDispatcher code refs found ($HIT_5A — comments OK, only code excluded)" FAIL

# 5b — GET /events/for/<role> bootup-incomplete gate gone
HIT_5B=$(grep -cE "gated.*bootup.incomplete|bootup.*incomplete.*gate" references/scripts/harness.py 2>/dev/null | head -1 | tr -d ' ')
HIT_5B=${HIT_5B:-0}
[ "$HIT_5B" -eq 0 ] && check "5b: no bootup-incomplete gating branch in harness.py" PASS || check "5b: bootup-incomplete gating found ($HIT_5B)" FAIL

# 5c — cycle_post.py REQUIRED_FIELDS mode-gated; _advance_event_cursor + _do_restart_sentinel deleted (code-level, ignore comments)
HIT_5C_CURSOR=$(grep -nE '_advance_event_cursor|_do_restart_sentinel' references/scripts/cycle_post.py 2>/dev/null | grep -vE '^[0-9]+:\s*#|^[0-9]+:\s*"""' | wc -l | tr -d ' ')
HIT_5C_CURSOR=${HIT_5C_CURSOR:-0}
HIT_5C_MODE=$(grep -cE "EVENT_REQUIRED_FIELDS|mode.gated|mode_gated" references/scripts/cycle_post.py 2>/dev/null | head -1 | tr -d ' ')
HIT_5C_MODE=${HIT_5C_MODE:-0}
[ "$HIT_5C_CURSOR" -eq 0 ] && check "5c: _advance_event_cursor / _do_restart_sentinel code refs deleted" PASS || check "5c: dead code refs found ($HIT_5C_CURSOR)" FAIL
[ "$HIT_5C_MODE" -gt 0 ] && check "5c: REQUIRED_FIELDS mode-gated" PASS || check "5c: REQUIRED_FIELDS not mode-gated" FAIL

# 5d — event_poll.py exists
[ -f "references/scripts/event_poll.py" ] && check "5d: event_poll.py exists" PASS || check "5d: event_poll.py missing" FAIL

# Item 6 — event-mode L1 base + boot sequence in events compose for this role
echo "Item 6 — event-mode L1 base in role=$ROLE compose"
EVENT_INC="references/roles/${ROLE}/includes-events.yml"
if [ -f "$EVENT_INC" ]; then
  HIT_L1=$(grep -cE "l1-base|cursor-management|forge-read-pattern|idle-cooldown-loop|comment-handling" "$EVENT_INC" 2>/dev/null || echo 0)
  if [ "$HIT_L1" -ge 4 ]; then
    check "6: event-mode L1 base fragments referenced in $EVENT_INC" PASS
  else
    check "6: event-mode L1 base fragments missing in $EVENT_INC ($HIT_L1 of 5 expected — #8998 may not have shipped)" FAIL
  fi
else
  check "6: $EVENT_INC missing" FAIL
fi

# Item 7 — bootup_complete informational flag in AgentState
HIT_BC=$(grep -c "bootup_complete" references/scripts/harness.py 2>/dev/null || echo 0)
[ "$HIT_BC" -gt 0 ] && check "7: bootup_complete present in AgentState" PASS || check "7: bootup_complete missing" FAIL

# Item 8 — compose.py deploy <role> produces events-mode CLAUDE.md with no /loop language
echo "Item 8 — compose.py deploy $ROLE for events-mode output check"
# Stash any pending changes and snapshot current CLAUDE.md, then run deploy and diff
SNAPSHOT="/tmp/claude-${ROLE}-snapshot.md"
[ -f ".squidsquad/${ROLE}/CLAUDE.md" ] && cp ".squidsquad/${ROLE}/CLAUDE.md" "$SNAPSHOT"
# (Deploy and diff to be run explicitly by operator — automated detection of "events mode" requires config flip first)
echo "  [INFO]  Item 8 requires manual: temporarily flip role=$ROLE to event-driven: yes, run compose.py deploy $ROLE, grep for /loop|cycle_pre|cycle_post in the output."

# Additional Phase 5 deliverables sanity check
echo ""
echo "=== Phase 5 deliverable sanity check (informational) ==="
for n in 8694 8695 8697 8700 8701 8704 4792 8979 8998 8999; do
  S=$(gh issue view "$n" --json state --jq .state 2>/dev/null)
  echo "  #$n  state=$S"
done

echo ""
echo "=== Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Pre-flip checklist NOT satisfied for role=$ROLE."
  exit 1
fi

echo ""
echo "Pre-flip checklist satisfied for role=$ROLE."
echo "REMINDER: Item 8 still requires manual confirmation after flipping events: yes for this role."
exit 0
