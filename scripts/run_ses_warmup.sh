#!/bin/zsh
set -euo pipefail

ROOT="/Users/m2/Documents/New project"
LIST_DIR="/Users/m2/Desktop/base de datos/amazon lista unificada"

"$ROOT/.venv/bin/python" "$ROOT/scripts/ses_warmup.py" \
  --list-dir "$LIST_DIR" \
  --campaign-name "ses-warmup" \
  --stream-name "warmup" \
  --subject-file "$ROOT/data/email_templates/warmup_subject.txt" \
  --html-file "$ROOT/data/email_templates/warmup_body.html" \
  --text-file "$ROOT/data/email_templates/warmup_body.txt" \
  --execute
