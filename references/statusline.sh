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

# Read role — prefer env var (session-scoped), fall back to file (clone-based setups)
ROLE="${SQUIDSQUAD_ROLE:-}"
if [ -z "$ROLE" ]; then
  ROLE_FILE="$SQDIR/.active-role"
  [ ! -f "$ROLE_FILE" ] && exit 0
  ROLE=$(cat "$ROLE_FILE" | tr -d '[:space:]')
fi
[ -z "$ROLE" ] && exit 0

# ANSI colors
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

# Read version from config
VERSION=$(grep 'SquidSquad Version' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+[.0-9]*')
VERSION=${VERSION:-'?'}

# --- Resolve agent list once, schema-aware (#328 Phase I) ---
#
# The legacy `grep 'Dev Agents'` worked only for the v1 config.md schema.
# After #328 the wizard writes v2 configs with per-agent entries. We
# call `config.py list-agents` once at the top and stash the results in
# shell variables — that way every segment downstream (backlog cache,
# PM health check, DM work counter) sees the same canonical list
# regardless of which schema the config.md was written in.
#
# DEV_AGENTS_LIST — space-separated ids of every dev-role agent
# ALL_AGENT_IDS   — space-separated ids of EVERY installed agent (pm, dm, dev, qa, designer)
DEV_AGENTS_LIST=""
ALL_AGENT_IDS=""
if [ -f "$SQDIR/config.md" ]; then
  _AGENTS_RAW=$(python references/scripts/config.py list-agents 2>/dev/null) || _AGENTS_RAW=""
  if [ -n "$_AGENTS_RAW" ]; then
    while IFS=$'\t' read -r _AID _AROLE _AALIAS; do
      [ -z "$_AID" ] && continue
      ALL_AGENT_IDS="${ALL_AGENT_IDS}${_AID} "
      if [ "$_AROLE" = "dev" ]; then
        DEV_AGENTS_LIST="${DEV_AGENTS_LIST}${_AID} "
      fi
    done <<EOF
$_AGENTS_RAW
EOF
  fi
fi

# Parse context window usage from JSON stdin
CTX_PCT=$(echo "$INPUT" | grep -oE '"used_percentage"[[:space:]]*:[[:space:]]*[0-9.]+' | head -1 | grep -oE '[0-9.]+$')
CTX_PCT=${CTX_PCT%%.*}
CTX_PCT=${CTX_PCT:-0}

# Write real context pressure to disk for agents to read
if [ -n "$ROLE" ] && [ -d "$SQDIR/$ROLE" ]; then
  echo "$CTX_PCT" > "$SQDIR/$ROLE/context-pressure.tmp" && mv -f "$SQDIR/$ROLE/context-pressure.tmp" "$SQDIR/$ROLE/context-pressure"
fi

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

# #8700: in event-driven mode there are no /loop ticks, so the cycle
# countdown is meaningless. Show 📡 events instead of a misleading overdue
# counter. WAKE_MODE comes from statusline_data.py which reads config.md.
WAKE_MODE=$(timeout 1 python references/scripts/statusline_data.py mode "$ROLE" 2>/dev/null) || WAKE_MODE="polling"
NOW=$(date +%s)

if [ "$WAKE_MODE" = "event-driven" ]; then
  TIMER_STR="📡 events"
else
  TIMER_STR="🔄 ${INTERVAL}m"
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
fi

# Vault pending questions: 🗄️ N (escalating 🔥 at 3+)
VAULT_Q=""
VAULT_Q_COUNT=$(python references/scripts/vault_optimize.py pending-count 2>/dev/null) || true
VAULT_Q_COUNT=${VAULT_Q_COUNT:-0}
if [ "$VAULT_Q_COUNT" -gt 0 ]; then
  FIRES=""
  if [ "$VAULT_Q_COUNT" -ge 3 ]; then
    # 2^(count-3) fires, capped at 8
    FIRE_COUNT=1
    EXP=$(( VAULT_Q_COUNT - 3 ))
    i=0
    while [ "$i" -lt "$EXP" ]; do
      FIRE_COUNT=$(( FIRE_COUNT * 2 ))
      i=$(( i + 1 ))
    done
    [ "$FIRE_COUNT" -gt 8 ] && FIRE_COUNT=8
    j=0
    while [ "$j" -lt "$FIRE_COUNT" ]; do
      FIRES="${FIRES}🔥"
      j=$(( j + 1 ))
    done
  fi
  VAULT_Q="🗄️${VAULT_Q_COUNT}${FIRES}"
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

# Role label — alias is sole truth (#11144 G10).
# Look up the alias from config; if it differs from $ROLE (which means
# the caller passed a role-class name), use the alias. Otherwise $ROLE
# is already the alias — use it raw. No hardcoded uppercase fallback.
#
# Defensive parse: `config.py alias` is contracted to print a single
# kebab-case token to stdout (e.g. `qa`, `skill`, `frontend-1`). The
# guard below rejects ALIAS if it isn't a single line matching that
# shape — protects against future-stdout pollution (#11144 Iter 40 DS
# F2). On reject, fall through to raw $ROLE.
ALIAS=$(python references/scripts/config.py alias "$ROLE" 2>/dev/null) || true
if echo "$ALIAS" | grep -Eq '^[a-z][a-z0-9-]*$' && [ "$ALIAS" != "$ROLE" ]; then
  ROLE_LABEL="$ALIAS"
else
  ROLE_LABEL="$ROLE"
fi

# --- Read role state for line 2 (#8700) ---
# Source: statusline_data.py phase <role>
#   - event-driven mode: queries harness API (GET /agents/<role>/health)
#   - polling mode: reads .squidsquad/<role>/current-state
#   - either way, prints `phase|description` (or empty)
STATE_LINE=$(timeout 2 python references/scripts/statusline_data.py phase "$ROLE" 2>/dev/null) || STATE_LINE=""
CURRENT_PHASE=""
CURRENT_DESC=""
if [ -n "$STATE_LINE" ]; then
  CURRENT_PHASE=$(echo "$STATE_LINE" | cut -d'|' -f1)
  CURRENT_DESC=$(echo "$STATE_LINE" | cut -d'|' -f2-)
fi

# --- Resolve line 2: current step or rotating hint ---
get_line2() {
  local role_type="$1"  # "worker"/"verifier"/"pm" (6274.2 canonical; legacy "dev"/"qa" still accepted via internal fallback)

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
  # #6274 dual-aware: try the post-rename canonical name first, fall back to
  # the deprecated name for legacy installs that haven't re-composed yet.
  local hint_file="$SQDIR/hints-${role_type}.txt"
  if [ ! -f "$hint_file" ]; then
    case "$role_type" in
      worker)   hint_file="$SQDIR/hints-dev.txt" ;;
      verifier) hint_file="$SQDIR/hints-qa.txt" ;;
    esac
  fi
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

# --- Backlog counts via GitHub Issues (cached) ---
# Cache refreshes at most every 5 minutes to avoid API latency in statusline
BACKLOG_CACHE="$SQDIR/.backlog-cache"
CACHE_MAX_AGE=300  # seconds
CACHE_STALE=true
if [ -f "$BACKLOG_CACHE" ]; then
  if stat --version >/dev/null 2>&1; then
    CACHE_MOD=$(stat -c %Y "$BACKLOG_CACHE" 2>/dev/null)
  else
    CACHE_MOD=$(stat -f %m "$BACKLOG_CACHE" 2>/dev/null)
  fi
  if [ -n "$CACHE_MOD" ]; then
    CACHE_AGE=$(( NOW - CACHE_MOD ))
    [ "$CACHE_AGE" -lt "$CACHE_MAX_AGE" ] && CACHE_STALE=false
  fi
fi

if [ "$CACHE_STALE" = true ]; then
  # Refresh cache in background (don't block statusline rendering)
  (
    AGENTS_LIST="$DEV_AGENTS_LIST"
    CACHE_TMP="$BACKLOG_CACHE.tmp"
    : > "$CACHE_TMP"
    for A in $AGENTS_LIST; do
      A=$(echo "$A" | tr -d '[:space:]')
      [ -z "$A" ] && continue
      BUGS=$(timeout 5 gh issue list --label "type:issue,role:$A" --state open --json number --limit 100 2>/dev/null | grep -c '"number"') || true
      FEATS=$(timeout 5 gh issue list --label "type:task,role:$A,status:approved" --state open --json number --limit 100 2>/dev/null | grep -c '"number"') || true
      FEATS_IP=$(timeout 5 gh issue list --label "type:task,role:$A,status:in-progress" --state open --json number --limit 100 2>/dev/null | grep -c '"number"') || true
      PSHIP=$(timeout 5 gh issue list --label "type:task,role:$A,status:pending-ship" --state open --json number --limit 100 2>/dev/null | grep -c '"number"') || true
      echo "${A}:bugs=${BUGS:-0}:feats=$(( ${FEATS:-0} + ${FEATS_IP:-0} )):pship=${PSHIP:-0}" >> "$CACHE_TMP"
    done
    # PM planning: check for features in planning status
    PLANNING=$(timeout 5 gh issue list --label "type:task,status:planning" --state open --json number,title --limit 1 2>/dev/null | grep -oE '"number":[0-9]+' | head -1 | grep -oE '[0-9]+') || true
    echo "pm:planning=${PLANNING:-}" >> "$CACHE_TMP"
    mv -f "$CACHE_TMP" "$BACKLOG_CACHE" 2>/dev/null
  ) &
fi

# Read cache (may be from previous refresh)
read_backlog_cache() {
  local agent="$1" field="$2"
  [ ! -f "$BACKLOG_CACHE" ] && echo "0" && return
  local line=$(grep "^${agent}:" "$BACKLOG_CACHE" 2>/dev/null | head -1)
  [ -z "$line" ] && echo "0" && return
  local val=$(echo "$line" | grep -oE "${field}=[^:]*" | cut -d= -f2)
  echo "${val:-0}"
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

  # Planning phase: 📋 #NNN — check for features in Planning status via cached GH Issues
  PLANNING_STR=""
  PLANNING_NUM=$(read_backlog_cache "pm" "planning")
  if [ -n "$PLANNING_NUM" ] && [ "$PLANNING_NUM" != "0" ] && [ "$PLANNING_NUM" != "" ]; then
    PLANNING_STR="📋 #${PLANNING_NUM}"
  fi

  # Agent health icons: 🦑 healthy, 👻 stalled, ❓ unknown
  # Reads cross-clone current-state files via .local-config paths.
  # `ALL_AGENT_IDS` already contains every installed agent (pm + all
  # specialists + dm when present) — resolved once at the top of the
  # script, schema-aware.
  ALL_AGENTS="$ALL_AGENT_IDS"
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
      # Skip agents in registry but not installed (no directory anywhere)
      [ ! -d "$SQDIR/$AGENT" ] && continue
      AGENT_STATE="$SQDIR/$AGENT/current-state"
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
  [ -n "$VAULT_Q" ] && LINE1="${LINE1} │ ${VAULT_Q}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR} │ ${HEALTH}"
  [ -n "$REST" ] && LINE1="${LINE1} ${REST}"

  # Line 2: current step or rotating hint
  LINE2=$(get_line2 "pm")

  echo -e "${LINE1}"
  [ -n "$LINE2" ] && echo -e "${LINE2}"

# === DM segments ===
elif [ "$ROLE" = "dm" ]; then

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
    # Count Pending Ship items via cached GH Issues (schema-aware agent list)
    AGENTS="$DEV_AGENTS_LIST"
    PSHIP_COUNT=0
    for AGENT in $AGENTS; do
      AGENT=$(echo "$AGENT" | tr -d '[:space:]')
      [ -z "$AGENT" ] && continue
      C=$(read_backlog_cache "$AGENT" "pship")
      PSHIP_COUNT=$(( PSHIP_COUNT + ${C:-0} ))
    done

    if [ "$PSHIP_COUNT" -eq 0 ]; then
      WORK_STR="✅ clear"
    else
      WORK_STR="📦${PSHIP_COUNT} pending"
    fi
  fi

  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${WORK_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  [ -n "$VAULT_Q" ] && LINE1="${LINE1} │ ${VAULT_Q}"
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
    # Backlog counts via cached GH Issues
    BUG_COUNT=$(read_backlog_cache "$ROLE" "bugs")
    FEAT_COUNT=$(read_backlog_cache "$ROLE" "feats")
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
  [ -n "$VAULT_Q" ] && LINE1="${LINE1} │ ${VAULT_Q}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  # Line 2: current step or rotating hint (Verifier gets its own hints if available)
  # #6274 dual-aware: accept both new (verifier/worker) and legacy (qa/dev)
  # role names; get_line2 internally falls back from new→legacy hint file.
  if [ "$ROLE" = "verifier" ] || [ "$ROLE" = "qa" ]; then
    LINE2=$(get_line2 "verifier")
  else
    LINE2=$(get_line2 "worker")
  fi

  echo -e "${LINE1}"
  [ -n "$LINE2" ] && echo -e "${LINE2}"
fi
