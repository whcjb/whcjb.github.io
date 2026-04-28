#!/bin/sh
# Called by Claude Code PostToolUse hook after Write tool.
# Reads JSON from stdin, checks if the written file is a calvin/*.md, then auto-commits.

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

case "$FILE" in
  */calvin/*.md) ;;
  *) exit 0 ;;
esac

cd /Users/yanpeifa/Documents/whcjb.github.io || exit 1

REL=$(python3 -c "import os; print(os.path.relpath('$FILE'))" 2>/dev/null)
BOOK=$(echo "$REL" | cut -d/ -f2)
CHAP=$(basename "$REL" .md)

git add "$REL"
git commit -m "feat: add $BOOK chapter $CHAP"
