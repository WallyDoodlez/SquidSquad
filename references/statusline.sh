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

# Time since last iteration → countdown timer
ITER_DIR="$SQDIR/$ROLE/iterations"
LATEST=""
if [ -d "$ITER_DIR" ]; then
  LATEST=$(ls "$ITER_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
fi

TIMER_STR="🔄 ${INTERVAL}m"
NOW=$(date +%s)
if [ -n "$LATEST" ]; then
  if stat --version >/dev/null 2>&1; then
    LAST_MOD=$(stat -c %Y "$LATEST" 2>/dev/null)
  else
    LAST_MOD=$(stat -f %m "$LATEST" 2>/dev/null)
  fi
  if [ -n "$LAST_MOD" ]; then
    ELAPSED=$(( (NOW - LAST_MOD) / 60 ))
    REMAINING=$(( INTERVAL - ELAPSED ))
    if [ "$REMAINING" -le 0 ]; then
      TIMER_STR="🔜 <1m"
    elif [ "$REMAINING" -le 1 ]; then
      TIMER_STR="🔜 <1m"
    else
      TIMER_STR="🔄 ${REMAINING}m"
    fi
  fi
fi

# Git sync: ↑N unpushed / ↓N behind remote
GIT_SYNC=""
AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null)
BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null)
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
    FEATS_FILE="$SQDIR/$AGENT/features.md"
    if [ -f "$FEATS_FILE" ]; then
      PLANNING_FEAT=$(grep -B5 'Status\*\*: Planning' "$FEATS_FILE" 2>/dev/null | grep -oE 'FEAT-[A-Z]+-[0-9]+' | head -1)
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

  # Build PM line 1
  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${SHIP_STR}"
  [ -n "$PLANNING_STR" ] && LINE1="${LINE1} │ ${PLANNING_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  # Agent health icons for line 2: 🦑 healthy, 👻 stalled, 🥚 never started
  HEALTH=""
  THRESHOLD_SECS=$(( INTERVAL * 2 * 60 ))
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    RECENT=$(git log --oneline --since="${INTERVAL}2 minutes ago" --grep="^${AGENT}:" 2>/dev/null | head -1)
    if [ -n "$RECENT" ]; then
      HEALTH="${HEALTH}🦑"
    else
      EVER=$(git log --oneline --grep="^${AGENT}:" -1 2>/dev/null)
      if [ -n "$EVER" ]; then
        HEALTH="${HEALTH}👻"
      else
        HEALTH="${HEALTH}🥚"
      fi
    fi
  done

  # Rest nudge (right-aligned on line 2)
  HOUR=$(date +%H)
  REST=""
  if [ "$HOUR" -ge 22 ]; then
    REST="🌙 late"
  elif [ "$HOUR" -ge 0 ] && [ "$HOUR" -lt 2 ]; then
    REST="😴 rest?"
  elif [ "$HOUR" -ge 2 ] && [ "$HOUR" -lt 6 ]; then
    REST="🛏️ sleep!"
  fi

  LINE2="  ${HEALTH}"
  [ -n "$REST" ] && LINE2="${LINE2}                                    ${REST}"

  echo -e "${LINE1}"
  echo -e "${LINE2}"

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
    BUGS_FILE="$SQDIR/$ROLE/bugs.md"
    FEATS_FILE="$SQDIR/$ROLE/features.md"
    BUG_COUNT=0
    FEAT_COUNT=0
    [ -f "$BUGS_FILE" ] && BUG_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Open|Investigating)' "$BUGS_FILE" 2>/dev/null) || true
    [ -f "$FEATS_FILE" ] && FEAT_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Approved|In Progress)' "$FEATS_FILE" 2>/dev/null) || true
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

  echo -e "${LINE1}"
fi
