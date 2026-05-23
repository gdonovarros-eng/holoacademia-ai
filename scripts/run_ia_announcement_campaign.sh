#!/bin/zsh
set -euo pipefail

ROOT="/Users/m2/Documents/New project"
LIST_DIR="${1:-$ROOT/data/ia_launch_audience}"
CURRENT_HOUR="$(date +%H)"
LOCK_DIR="$ROOT/tmp/ia_announcement.lock"
STATE_FILE="$ROOT/data/ia_announcement_state.json"
PLAN_FILE="$ROOT/data/ia_announcement_plan.json"

announcement_is_complete() {
  "$ROOT/.venv/bin/python" - <<'PY'
import json
from pathlib import Path

state_path = Path("/Users/m2/Documents/New project/data/ia_announcement_state.json")
plan_path = Path("/Users/m2/Documents/New project/data/ia_announcement_plan.json")

if not state_path.exists() or not plan_path.exists():
    raise SystemExit(1)

state = json.loads(state_path.read_text(encoding="utf-8"))
plan = json.loads(plan_path.read_text(encoding="utf-8"))
run_count = int(state.get("run_count", 0))
plan_days = len(plan.get("daily_limits") or [])
pending = state.get("pending_run")

if isinstance(pending, dict):
    target_limit = int(pending.get("target_limit", 0))
    processed = int(pending.get("processed", 0))
    if target_limit > 0 and processed < target_limit:
        raise SystemExit(1)

raise SystemExit(0 if plan_days > 0 and run_count >= plan_days else 1)
PY
}

if [ "$CURRENT_HOUR" -lt 8 ]; then
  echo "Aun no son las 08:00 locales. La campana espera hasta despues de esa hora."
  exit 0
fi

mkdir -p "$ROOT/tmp"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Ya hay una corrida activa de la campana de anuncio. No se inicia otra."
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

announcement_status=0
"$ROOT/.venv/bin/python" "$ROOT/scripts/ses_warmup.py" \
  --list-dir "$LIST_DIR" \
  --plan-file "$PLAN_FILE" \
  --state-file "$STATE_FILE" \
  --log-file "$ROOT/data/ia_announcement_runs.jsonl" \
  --failure-file "$ROOT/data/ia_announcement_failures.csv" \
  --campaign-name "ia-announcement" \
  --stream-name "announcement" \
  --subject-file "$ROOT/data/email_templates/ia_launch_subject.txt" \
  --html-file "$ROOT/data/email_templates/ia_launch_body.html" \
  --text-file "$ROOT/data/email_templates/ia_launch_body.txt" \
  --execute || announcement_status=$?

if announcement_is_complete; then
  echo "La campana IA announcement ya termino. Se inicia ia-launch-full."
  zsh "$ROOT/scripts/run_ia_launch_campaign.sh" "$LIST_DIR"
  exit 0
fi

exit "$announcement_status"
