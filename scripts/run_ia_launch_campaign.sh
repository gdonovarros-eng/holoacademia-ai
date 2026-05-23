#!/bin/zsh
set -euo pipefail

ROOT="/Users/m2/Documents/New project"
LIST_DIR="${1:-$ROOT/data/ia_launch_audience}"
LOCK_DIR="$ROOT/tmp/ia_launch_full.lock"

mkdir -p "$ROOT/tmp"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Ya hay una corrida activa de la campana IA full. No se inicia otra."
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

"$ROOT/.venv/bin/python" "$ROOT/scripts/ses_warmup.py" \
  --list-dir "$LIST_DIR" \
  --state-file "$ROOT/data/ia_launch_state.json" \
  --log-file "$ROOT/data/ia_launch_runs.jsonl" \
  --failure-file "$ROOT/data/ia_launch_failures.csv" \
  --campaign-name "ia-launch-full" \
  --stream-name "announcement" \
  --subject-file "$ROOT/data/email_templates/ia_launch_subject.txt" \
  --html-file "$ROOT/data/email_templates/ia_launch_body.html" \
  --text-file "$ROOT/data/email_templates/ia_launch_body.txt" \
  --max-send 999999 \
  --execute
