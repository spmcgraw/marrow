#!/usr/bin/env bash
set -euo pipefail

VENV="${CLAUDE_PROJECT_DIR}/api/.venv"
PY="${VENV}/bin/python"

[[ -x "$PY" ]] || exit 0

VERSION="$("$PY" --version 2>&1)"

CONTEXT="Project Python venv: ${VENV}
Interpreter: ${PY} (${VERSION})
Note: Bash tool shell state does not persist between calls. Invoke ${PY} directly, or re-source ${VENV}/bin/activate in each Bash command that needs it."

ESCAPED=$(printf '%s' "$CONTEXT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

cat <<EOF
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ${ESCAPED}}}
EOF
