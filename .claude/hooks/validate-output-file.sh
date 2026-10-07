#!/bin/bash
# PostToolUse / Write: warn if a docs/ or output/ file was written empty. Never blocks.
FILE_PATH=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")
# Normalise Windows backslashes, then make the path relative to the project dir
FILE_PATH="${FILE_PATH//\\//}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_DIR="${PROJECT_DIR//\\//}"
FILE_PATH="${FILE_PATH#$PROJECT_DIR/}"
# PWD may be /c/... while the tool path is C:/...; fall back to matching the docs/ or output/ segment
case "$FILE_PATH" in
  docs/*|output/*) ;;
  *)
    case "$FILE_PATH" in
      */docs/*) FILE_PATH="docs/${FILE_PATH##*/docs/}" ;;
      */output/*) FILE_PATH="output/${FILE_PATH##*/output/}" ;;
    esac
    ;;
esac

if [[ "$FILE_PATH" == docs/* ]] || [[ "$FILE_PATH" == output/* ]]; then
  if [ ! -s "$FILE_PATH" ]; then
    echo "WARNING: $FILE_PATH was written but is empty. The agent may have failed to produce output." >&2
  else
    LINES=$(wc -l < "$FILE_PATH")
    echo "OK: $FILE_PATH written ($LINES lines)" >&2
  fi
fi
exit 0
