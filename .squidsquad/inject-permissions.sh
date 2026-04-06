#!/bin/bash
# inject-permissions.sh — Merge .squidsquad/permissions.template.json into .claude/settings.json
# Called by startup scripts before launching Claude.
#
# Strategy: read the template (stripping comment lines), then use node
# to replace .permissions.allow in settings.json while preserving
# everything else (hooks, statusLine, etc.).

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE="$REPO_ROOT/.squidsquad/permissions.template.json"
SETTINGS="$REPO_ROOT/.claude/settings.json"

if [ ! -f "$TEMPLATE" ]; then
  echo "[inject-permissions] WARNING: $TEMPLATE not found — skipping permission injection."
  exit 0
fi

# Ensure settings.json exists with minimal structure
if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

# Use jq if available, otherwise fall back to node (Windows-compatible)
if command -v jq &>/dev/null; then
  # Strip comment lines then inject
  PERMS=$(grep -v '"// ' "$TEMPLATE")
  jq --argjson perms "$PERMS" '.permissions.allow = $perms' "$SETTINGS" > "$SETTINGS.tmp" && mv -f "$SETTINGS.tmp" "$SETTINGS"
elif command -v node &>/dev/null; then
  # Node reads both files directly — no stdin, works on Windows
  node -e "
    const fs = require('fs');
    const path = require('path');
    const templatePath = path.resolve('$TEMPLATE'.replace(/\\\\/g, '/'));
    const settingsPath = path.resolve('$SETTINGS'.replace(/\\\\/g, '/'));
    const stripBom = s => s.charCodeAt(0) === 0xFEFF ? s.slice(1) : s;
    const template = JSON.parse(stripBom(fs.readFileSync(templatePath, 'utf8')));
    const perms = template.filter(p => !p.startsWith('//'));
    const settings = JSON.parse(stripBom(fs.readFileSync(settingsPath, 'utf8')));
    if (!settings.permissions) settings.permissions = {};
    settings.permissions.allow = perms;
    fs.writeFileSync(settingsPath + '.tmp', JSON.stringify(settings, null, 2));
  " && mv -f "$SETTINGS.tmp" "$SETTINGS"
else
  echo "[inject-permissions] ERROR: Neither jq nor node found — cannot inject permissions."
  exit 1
fi

COUNT=$(grep -v '"// ' "$TEMPLATE" | grep -c '"')
echo "[inject-permissions] Injected $COUNT permission rules from template."
