#!/bin/bash
# SquidSquad Status Line — shown in Claude Code's status bar
# Receives JSON session data on stdin; prints ANSI-colored status to stdout

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
DIM='\033[2m'
RESET='\033[0m'

# Parse context window usage from JSON stdin (e.g. "used_percentage": 42.5)
CTX_PCT=$(echo "$INPUT" | grep -oE '"used_percentage"[[:space:]]*:[[:space:]]*[0-9.]+' | head -1 | grep -oE '[0-9.]+$')
CTX_PCT=${CTX_PCT%%.*}  # truncate to integer
CTX_PCT=${CTX_PCT:-0}

# Color context percentage
if [ "$CTX_PCT" -ge 90 ]; then
  CTX_STR="${RED}ctx:${CTX_PCT}%${RESET}"
elif [ "$CTX_PCT" -ge 70 ]; then
  CTX_STR="${YELLOW}ctx:${CTX_PCT}%${RESET}"
else
  CTX_STR="${DIM}ctx:${CTX_PCT}%${RESET}"
fi

# Get iteration number from latest iter-N.md
ITER_DIR="$SQDIR/$ROLE/iterations"
ITER_NUM=0
if [ -d "$ITER_DIR" ]; then
  LATEST=$(ls "$ITER_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
  if [ -n "$LATEST" ]; then
    ITER_NUM=$(echo "$LATEST" | grep -oE '[0-9]+\.md$' | grep -oE '[0-9]+')
  fi
fi

# Get interval from config
INTERVAL=$(grep 'Minutes' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
INTERVAL=${INTERVAL:-10}

# Time since last iteration (file modification time)
TIME_STR="-"
NOW=$(date +%s)
if [ -n "$LATEST" ]; then
  if stat --version >/dev/null 2>&1; then
    LAST_MOD=$(stat -c %Y "$LATEST" 2>/dev/null)
  else
    LAST_MOD=$(stat -f %m "$LATEST" 2>/dev/null)
  fi
  if [ -n "$LAST_MOD" ]; then
    ELAPSED=$(( (NOW - LAST_MOD) / 60 ))
    TIME_STR="${ELAPSED}m ago"
  fi
fi

# Count open bugs and actionable features
BUGS_FILE="$SQDIR/$ROLE/bugs.md"
FEATS_FILE="$SQDIR/$ROLE/features.md"
BUG_COUNT=0
FEAT_COUNT=0
[ -f "$BUGS_FILE" ] && BUG_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Open|Investigating)' "$BUGS_FILE" 2>/dev/null) || true
[ -f "$FEATS_FILE" ] && FEAT_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Approved|In Progress)' "$FEATS_FILE" 2>/dev/null) || true
BUG_COUNT=${BUG_COUNT:-0}
FEAT_COUNT=${FEAT_COUNT:-0}

# Build backlog string
BACKLOG=""
[ "$BUG_COUNT" -gt 0 ] && BACKLOG="${BUG_COUNT} bug$([ "$BUG_COUNT" -gt 1 ] && echo s)"
if [ "$FEAT_COUNT" -gt 0 ]; then
  [ -n "$BACKLOG" ] && BACKLOG="$BACKLOG "
  BACKLOG="${BACKLOG}${FEAT_COUNT} feat$([ "$FEAT_COUNT" -gt 1 ] && echo s)"
fi
[ -z "$BACKLOG" ] && BACKLOG="clear"

# Role label
if [ "$ROLE" = "pm" ]; then
  ROLE_LABEL="PM/QA"
else
  ROLE_LABEL="$ROLE"
fi

# PM: show other agents' health via git log commit prefixes
HEALTH=""
if [ "$ROLE" = "pm" ]; then
  AGENTS=$(grep 'Dev Agents' "$SQDIR/config.md" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
  THRESHOLD=$(( INTERVAL * 2 ))
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    # Check git log for recent commits with this agent's prefix
    RECENT=$(git log --oneline --since="${THRESHOLD} minutes ago" --grep="^${AGENT}:" 2>/dev/null | head -1)
    if [ -n "$RECENT" ]; then
      HEALTH="${HEALTH} ${GREEN}🦑${RESET}${AGENT}"
    else
      # Check if agent has ever committed
      EVER=$(git log --oneline --grep="^${AGENT}:" -1 2>/dev/null)
      if [ -n "$EVER" ]; then
        HEALTH="${HEALTH} ${RED}🦑✖${RESET}${AGENT}"
      else
        HEALTH="${HEALTH} ${DIM}🦑?${RESET}${AGENT}"
      fi
    fi
  done
fi

# Estimate time until next cycle
NEXT_STR=""
if [ -n "$LAST_MOD" ] && [ "$ELAPSED" -lt "$INTERVAL" ]; then
  REMAINING=$(( INTERVAL - ELAPSED ))
  NEXT_STR=" │ next in ~${REMAINING}m"
fi

# Output
if [ "$ROLE" = "pm" ]; then
  echo -e "${GREEN}🦑${RESET} ${ROLE_LABEL} │ iter ${ITER_NUM} │${HEALTH} │ ${CTX_STR} │ ${DIM}${TIME_STR}${NEXT_STR}${RESET}"
else
  echo -e "${GREEN}🦑${RESET} ${ROLE_LABEL} │ iter ${ITER_NUM} │ ${BACKLOG} │ ${CTX_STR} │ ${DIM}${TIME_STR}${NEXT_STR}${RESET}"
fi
