#!/usr/bin/env bash
# Ingesta de subtítulos de cursos al Sinodal: limpia con IA -> agrega al corpus -> embeddings.
# Requiere OPENAI_API_KEY en el .env del repo. Uso: bash scripts/ingesta_sinodal.sh [N]
#   N = cuántas lecciones (0 o vacío = todas; útil poner 10 para una prueba chica).
set -e
cd "$(dirname "$0")/.."
N="${1:-0}"

echo "== 1/3 Limpiando subtítulos con IA (lecciones: $N; 0 = todas) =="
python3 scripts/clean_subtitle_lessons.py "$N"

if [ ! -s data/chunks/subtitle_chunks_clean.jsonl ]; then
  echo "No se generaron chunks limpios. Reviso el .env / la salida de arriba."; exit 1
fi

echo "== 2/3 Agregando al corpus del Sinodal =="
cat data/chunks/subtitle_chunks_clean.jsonl >> data/chunks/library_chunks.jsonl

echo "== 3/3 Regenerando embeddings =="
python3 scripts/build_embeddings_index.py

echo ""
echo "LISTO. El Sinodal ya tiene el contenido de los cursos (local)."
echo "Para que entre en vivo: commit + deploy a Render."
