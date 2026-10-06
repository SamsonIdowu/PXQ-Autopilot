#!/usr/bin/env bash
# Builds the pxq-agents Claude Code plugin from the repo's .claude/ folder.
# The repo stays the source of truth. The plugin is a packaged copy for people
# who run agents outside this repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/plugin"
VERSION="$(cat "$ROOT/VERSION")"
rm -rf "$OUT" && mkdir -p "$OUT/.claude-plugin" "$OUT/agents" "$OUT/skills" "$OUT/hooks" "$OUT/config" "$OUT/schemas" "$OUT/learning"
cp "$ROOT"/.claude/agents/*.md "$OUT/agents/"
cp -r "$ROOT"/.claude/skills/. "$OUT/skills/"
cp "$ROOT"/.claude/hooks/guard_bash.py "$OUT/hooks/"
cp "$ROOT"/config/*.yaml "$OUT/config/"
cp "$ROOT"/schemas/*.json "$OUT/schemas/"
cp -r "$ROOT"/learning/lessons "$OUT/learning/"
cp "$ROOT"/.mcp.json "$OUT/.mcp.json"
mkdir -p "$OUT/scripts/owner" && cp "$ROOT"/scripts/owner/pxq.sh "$OUT/scripts/owner/"
mkdir -p "$OUT/scripts/automation" && cp "$ROOT"/scripts/automation/open_plan.py "$OUT/scripts/automation/"
cat > "$OUT/.claude-plugin/plugin.json" <<JSON
{
  "name": "pxq-agents",
  "version": "$VERSION",
  "description": "Wazuh PXQ Planner, Tester and Reviewer agents with their skills, lessons and safety hooks.",
  "author": { "name": "Wazuh Product Experience and Quality" }
}
JSON
cat > "$OUT/hooks/hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "CLAUDE_PROJECT_DIR=\"${CLAUDE_PLUGIN_ROOT}\" python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/guard_bash.py\"" } ] }
    ]
  }
}
JSON
echo "Built pxq-agents $VERSION in $OUT"
