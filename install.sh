#!/usr/bin/env bash
# Rehoboam installer — copies the skill into Claude Code's personal skills dir.
set -euo pipefail

TARGET="${1:-$HOME/.claude/skills/rehoboam}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v python3 >/dev/null 2>&1 || {
  echo "⚠ python3 not found — the intro animation needs it (the orchestrator itself does not)."
}

mkdir -p "$TARGET"
cp -R "$SRC/SKILL.md" "$SRC/scripts" "$SRC/references" "$SRC/assets" "$TARGET/"

echo "◉ Rehoboam installed at $TARGET"
echo "  Try it in Claude Code:  /rehoboam <task to build>"
python3 "$TARGET/scripts/rehoboam_intro.py" 2>/dev/null || true
