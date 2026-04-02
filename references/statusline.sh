#!/bin/bash
# SquidSquad Status Line — Emoji Rich design
# Receives JSON session data on stdin; prints status to stdout

INPUT=$(cat)

SQDIR=".squidsquad"
[ ! -d "$SQDIR" ] && exit 0

# Chain user's original status bar (if saved during setup)
USER_STATUSLINE="$SQDIR/.user-statusline"
if [ -f "$USER_STATUSLINE" ] && [ -s "$USER_STATUSLINE" ]; then
  USER_CMD=$(cat "$USER_STATUSLINE")
  USER_OUTPUT=$(echo "$INPUT" | timeout 1 bash -c "$USER_CMD" 2>/dev/null) || true
  [ -n "$USER_OUTPUT" ] && echo "$USER_OUTPUT"
fi

# Read role
ROLE_FILE="$SQDIR/.active-role"
[ ! -f "$ROLE_FILE" ] && exit 0
ROLE=$(cat "$ROLE_FILE" | tr -d '[:space:]')
[ -z "$ROLE" ] && exit 0

# ANSI colors
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

# Read version from config
VERSION=$(grep 'SquidSquad Version' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+[.0-9]*')
VERSION=${VERSION:-'?'}

# Parse context window usage from JSON stdin
CTX_PCT=$(echo "$INPUT" | grep -oE '"used_percentage"[[:space:]]*:[[:space:]]*[0-9.]+' | head -1 | grep -oE '[0-9.]+$')
CTX_PCT=${CTX_PCT%%.*}
CTX_PCT=${CTX_PCT:-0}

# Context emoji + colored percentage text
if [ "$CTX_PCT" -ge 75 ]; then
  CTX_STR="🧠💀 ${RED}${CTX_PCT}%${RESET}"
elif [ "$CTX_PCT" -ge 50 ]; then
  CTX_STR="🧠🔥 ${YELLOW}${CTX_PCT}%${RESET}"
else
  CTX_STR="🧠 ${GREEN}${CTX_PCT}%${RESET}"
fi

# Get interval from config
INTERVAL=$(grep 'Minutes' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
INTERVAL=${INTERVAL:-10}

# Time since last cycle → countdown timer
# Uses current-state file mtime (written every cycle, including quiet ones)
# Fallback to latest iter file if current-state doesn't exist
CYCLE_TIMESTAMP_FILE="$SQDIR/$ROLE/current-state"
if [ ! -f "$CYCLE_TIMESTAMP_FILE" ]; then
  ITER_DIR="$SQDIR/$ROLE/iterations"
  if [ -d "$ITER_DIR" ]; then
    CYCLE_TIMESTAMP_FILE=$(ls "$ITER_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
  fi
fi

TIMER_STR="🔄 ${INTERVAL}m"
NOW=$(date +%s)
if [ -n "$CYCLE_TIMESTAMP_FILE" ] && [ -f "$CYCLE_TIMESTAMP_FILE" ]; then
  if stat --version >/dev/null 2>&1; then
    LAST_MOD=$(stat -c %Y "$CYCLE_TIMESTAMP_FILE" 2>/dev/null)
  else
    LAST_MOD=$(stat -f %m "$CYCLE_TIMESTAMP_FILE" 2>/dev/null)
  fi
  if [ -n "$LAST_MOD" ]; then
    ELAPSED=$(( (NOW - LAST_MOD) / 60 ))
    REMAINING=$(( INTERVAL - ELAPSED ))
    if [ "$REMAINING" -le 0 ]; then
      OVERDUE=$(( ELAPSED - INTERVAL ))
      TIMER_STR="⏰ +${OVERDUE}m"
    elif [ "$REMAINING" -le 1 ]; then
      TIMER_STR="🔜 <1m"
    else
      TIMER_STR="🔄 ${REMAINING}m"
    fi
  fi
fi

# Git sync: ↑N unpushed / ↓N behind remote
GIT_SYNC=""
AHEAD=$(timeout 2 git rev-list --count @{u}..HEAD 2>/dev/null) || true
BEHIND=$(timeout 2 git rev-list --count HEAD..@{u} 2>/dev/null) || true
[ -n "$AHEAD" ] && [ "$AHEAD" -gt 0 ] && GIT_SYNC="↑${AHEAD}"
if [ -n "$BEHIND" ] && [ "$BEHIND" -gt 0 ]; then
  [ -n "$GIT_SYNC" ] && GIT_SYNC="${GIT_SYNC} "
  GIT_SYNC="${GIT_SYNC}↓${BEHIND}"
fi

# Role label
if [ "$ROLE" = "pm" ]; then
  ROLE_LABEL="PM/QA"
else
  ROLE_LABEL="$ROLE"
fi

# --- Read current-state file for line 2 ---
STATE_FILE="$SQDIR/$ROLE/current-state"
CURRENT_PHASE=""
CURRENT_DESC=""
if [ -f "$STATE_FILE" ]; then
  STATE_LINE=$(head -1 "$STATE_FILE" 2>/dev/null)
  CURRENT_PHASE=$(echo "$STATE_LINE" | cut -d'|' -f1)
  CURRENT_DESC=$(echo "$STATE_LINE" | cut -d'|' -f2-)
fi

# --- Resolve line 2: current step or rotating hint ---
get_line2() {
  local role_type="$1"  # "dev" or "pm"

  # If there's an active step description, show it (🚧 prefix)
  if [ -n "$CURRENT_DESC" ]; then
    # Truncate at 58 chars (60 minus 🚧 emoji width)
    if [ "${#CURRENT_DESC}" -gt 58 ]; then
      CURRENT_DESC="${CURRENT_DESC:0:55}..."
    fi
    echo "  🚧 $CURRENT_DESC"
    return
  fi

  # Otherwise show rotating hint based on phase
  local hint_file="$SQDIR/hints-${role_type}.txt"
  [ ! -f "$hint_file" ] && return

  local phase="${CURRENT_PHASE:-idle}"

  # Collect matching hints for this phase
  local hints=()
  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^# ]] && continue
    [ -z "$line" ] && continue
    local h_phase=$(echo "$line" | cut -d'|' -f1)
    local h_text=$(echo "$line" | cut -d'|' -f2-)
    if [ "$h_phase" = "$phase" ] && [ -n "$h_text" ]; then
      hints+=("$h_text")
    fi
  done < "$hint_file"

  # Fallback to idle hints if no phase match
  if [ ${#hints[@]} -eq 0 ] && [ "$phase" != "idle" ]; then
    while IFS= read -r line; do
      [[ "$line" =~ ^# ]] && continue
      [ -z "$line" ] && continue
      local h_phase=$(echo "$line" | cut -d'|' -f1)
      local h_text=$(echo "$line" | cut -d'|' -f2-)
      if [ "$h_phase" = "idle" ] && [ -n "$h_text" ]; then
        hints+=("$h_text")
      fi
    done < "$hint_file"
  fi

  [ ${#hints[@]} -eq 0 ] && return

  # Rotate every 60 seconds
  local idx=$(( (NOW / 60) % ${#hints[@]} ))
  local hint="${hints[$idx]}"

  # Truncate at 58 chars (60 minus 💡 emoji width)
  if [ "${#hint}" -gt 58 ]; then
    hint="${hint:0:55}..."
  fi

  echo "  💡 $hint"
}

# === PM-specific segments ===
if [ "$ROLE" = "pm" ]; then
  # Ship counter: 📦 N/threshold, 🚀 if near bump
  SHIPPED=$(grep 'Shipped Since Last Bump' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
  SHIP_THRESHOLD=$(grep 'Ship Threshold' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
  SHIPPED=${SHIPPED:-0}
  SHIP_THRESHOLD=${SHIP_THRESHOLD:-10}
  SHIP_STR="📦 ${SHIPPED}/${SHIP_THRESHOLD}"
  NEAR_BUMP=$(( SHIP_THRESHOLD - 1 ))
  [ "$SHIPPED" -ge "$NEAR_BUMP" ] && SHIP_STR="${SHIP_STR} 🚀"

  # Planning phase: 📋 FEAT-XXX PN — check all dev agent features for Planning status
  PLANNING_STR=""
  AGENTS=$(grep 'Dev Agents' "$SQDIR/config.md" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    FEATS_FILE="$SQDIR/$AGENT/features/INDEX.md"
    if [ -f "$FEATS_FILE" ]; then
      PLANNING_FEAT=$(grep -E '\| Planning \|' "$FEATS_FILE" 2>/dev/null | grep -oE 'FEAT-[A-Z]+-[0-9]+' | head -1)
      if [ -n "$PLANNING_FEAT" ]; then
        # Detect which phase by checking for existing artifacts
        PLAN_DIR="$SQDIR/$AGENT/planning"
        PHASE="P1"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-RESEARCH.md" ] && PHASE="P2"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-CONTEXT.md" ] && PHASE="P3"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-TEST-PLAN.md" ] && PHASE="P3✓"
        PLANNING_STR="📋 ${PLANNING_FEAT} ${PHASE}"
        break
      fi
    fi
  done

  # Agent health icons: 🦑 healthy, 👻 stalled, ❓ unknown
  # Reads cross-clone current-state files via .local-config paths
  # Include DM in health check if it exists
  DM_AGENT=""
  [ -d "$SQDIR/dm" ] && DM_AGENT="dm"
  ALL_AGENTS="pm $AGENTS $DM_AGENT"
  HEALTH=""
  STALE_THRESHOLD=$(( INTERVAL * 2 ))  # 2x iteration interval in minutes
  LOCAL_CONFIG="$SQDIR/.local-config"
  for AGENT in $ALL_AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    # Read agent's clone path from .local-config
    AGENT_PATH=""
    if [ -f "$LOCAL_CONFIG" ]; then
      AGENT_PATH=$(grep "\\*\\*${AGENT}\\*\\*:" "$LOCAL_CONFIG" 2>/dev/null | sed 's/.*\*\*: *//' | tr -d '[:space:]')
    fi
    # If this is our own role, use local path
    if [ "$AGENT" = "$ROLE" ]; then
      AGENT_STATE="$SQDIR/$AGENT/current-state"
    elif [ -n "$AGENT_PATH" ] && [ -d "$AGENT_PATH" ]; then
      AGENT_STATE="${AGENT_PATH}/.squidsquad/${AGENT}/current-state"
    else
      HEALTH="${HEALTH}❓"
      continue
    fi
    if [ -f "$AGENT_STATE" ]; then
      if stat --version >/dev/null 2>&1; then
        AGENT_MOD=$(stat -c %Y "$AGENT_STATE" 2>/dev/null)
      else
        AGENT_MOD=$(stat -f %m "$AGENT_STATE" 2>/dev/null)
      fi
      if [ -n "$AGENT_MOD" ]; then
        AGENT_AGE=$(( (NOW - AGENT_MOD) / 60 ))
        if [ "$AGENT_AGE" -le "$STALE_THRESHOLD" ]; then
          HEALTH="${HEALTH}🦑"
        else
          HEALTH="${HEALTH}👻"
        fi
      else
        HEALTH="${HEALTH}❓"
      fi
    else
      HEALTH="${HEALTH}❓"
    fi
  done

  # Rest nudge
  HOUR=$(date +%H)
  REST=""
  if [ "$HOUR" -ge 22 ]; then
    REST="🌙"
  elif [ "$HOUR" -ge 0 ] && [ "$HOUR" -lt 2 ]; then
    REST="😴"
  elif [ "$HOUR" -ge 2 ] && [ "$HOUR" -lt 6 ]; then
    REST="🛏️"
  fi

  # Build PM line 1 — health icons right-aligned
  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${SHIP_STR}"
  [ -n "$PLANNING_STR" ] && LINE1="${LINE1} │ ${PLANNING_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR} │ ${HEALTH}"
  [ -n "$REST" ] && LINE1="${LINE1} ${REST}"

  # Line 2: current step or rotating hint
  LINE2=$(get_line2 "pm")

  echo -e "${LINE1}"
  [ -n "$LINE2" ] && echo -e "${LINE2}"

# === DM segments ===
elif [ "$ROLE" = "dm" ]; then
  ROLE_LABEL="DM"

  # Check working state for active task
  WS_FILE="$SQDIR/$ROLE/working-state.md"
  ACTIVE_TASK=""
  if [ -f "$WS_FILE" ]; then
    WS_STATUS=$(grep '^\- \*\*Status\*\*:' "$WS_FILE" 2>/dev/null | head -1)
    if echo "$WS_STATUS" | grep -q 'in-progress'; then
      ACTIVE_TASK=$(grep '^\- \*\*Task\*\*:' "$WS_FILE" 2>/dev/null | sed 's/.*: //' | tr -d '[:space:]')
    fi
  fi

  if [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "none" ]; then
    WORK_STR="📦 ${ACTIVE_TASK}"
  else
    # Count Pending Ship items across all dev agent trackers
    AGENTS=$(grep 'Dev Agents' "$SQDIR/config.md" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
    PSHIP_COUNT=0
    for AGENT in $AGENTS; do
      AGENT=$(echo "$AGENT" | tr -d '[:space:]')
      [ -z "$AGENT" ] && continue
      FEATS_FILE="$SQDIR/$AGENT/features/INDEX.md"
      if [ -f "$FEATS_FILE" ]; then
        C=$(grep -cE '\| Pending Ship \|' "$FEATS_FILE" 2>/dev/null) || true
        PSHIP_COUNT=$(( PSHIP_COUNT + ${C:-0} ))
      fi
    done

    if [ "$PSHIP_COUNT" -eq 0 ]; then
      WORK_STR="✅ clear"
    else
      WORK_STR="📦${PSHIP_COUNT} pending"
    fi
  fi

  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${WORK_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  # Line 2: current step or rotating hint
  LINE2=$(get_line2 "dm")

  echo -e "${LINE1}"
  [ -n "$LINE2" ] && echo -e "${LINE2}"

# === Dev agent segments ===
else
  # Check working state for active task
  WS_FILE="$SQDIR/$ROLE/working-state.md"
  ACTIVE_TASK=""
  if [ -f "$WS_FILE" ]; then
    WS_STATUS=$(grep '^\- \*\*Status\*\*:' "$WS_FILE" 2>/dev/null | head -1)
    if echo "$WS_STATUS" | grep -q 'in-progress'; then
      ACTIVE_TASK=$(grep '^\- \*\*Task\*\*:' "$WS_FILE" 2>/dev/null | sed 's/.*: //' | tr -d '[:space:]')
    fi
  fi

  if [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "none" ]; then
    WORK_STR="🔨 ${ACTIVE_TASK}"
  else
    # Backlog counts
    BUGS_FILE="$SQDIR/$ROLE/bugs/INDEX.md"
    FEATS_FILE="$SQDIR/$ROLE/features/INDEX.md"
    BUG_COUNT=0
    FEAT_COUNT=0
    [ -f "$BUGS_FILE" ] && BUG_COUNT=$(grep -cE '\| (Open|Investigating) \|' "$BUGS_FILE" 2>/dev/null) || true
    [ -f "$FEATS_FILE" ] && FEAT_COUNT=$(grep -cE '\| (Approved|In Progress) \|' "$FEATS_FILE" 2>/dev/null) || true
    BUG_COUNT=${BUG_COUNT:-0}
    FEAT_COUNT=${FEAT_COUNT:-0}

    if [ "$BUG_COUNT" -eq 0 ] && [ "$FEAT_COUNT" -eq 0 ]; then
      WORK_STR="✅ clear"
    else
      WORK_STR=""
      [ "$BUG_COUNT" -gt 0 ] && WORK_STR="🐛${BUG_COUNT}"
      if [ "$FEAT_COUNT" -gt 0 ]; then
        [ -n "$WORK_STR" ] && WORK_STR="${WORK_STR} "
        WORK_STR="${WORK_STR}⭐${FEAT_COUNT}"
      fi
    fi
  fi

  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${WORK_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  # Line 2: current step or rotating hint
  LINE2=$(get_line2 "dev")

  echo -e "${LINE1}"
  [ -n "$LINE2" ] && echo -e "${LINE2}"
fi
