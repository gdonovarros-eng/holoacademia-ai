#!/bin/zsh

set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat <<'EOF'
Uso:
  ./scripts/download_youtube_videos.sh "<URL_DEL_CANAL_O_PLAYLIST_O_ARCHIVO>" "<CARPETA_DESTINO>" [all|streams|list]

Ejemplos:
  ./scripts/download_youtube_videos.sh "https://www.youtube.com/@MiCanal" "$HOME/Movies/MisVideosYT" streams
  ./scripts/download_youtube_videos.sh "https://www.youtube.com/@MiCanal" "icloud:Videos/MisVideosYT" streams
  ./scripts/download_youtube_videos.sh "https://www.youtube.com/@MiCanal/streams" "icloud:Videos/MisVideosYT"
  ./scripts/download_youtube_videos.sh "/ruta/live_urls.txt" "icloud:Videos/MisVideosYT" list
  YTDLP_BROWSER=safari ./scripts/download_youtube_videos.sh "https://www.youtube.com/playlist?list=TU_PLAYLIST" "$HOME/Desktop/YT"

Notas:
  - Requiere tener instalado yt-dlp.
  - Usa las cookies del navegador para acceder a videos privados o no listados
    siempre que tu sesion ya este iniciada en ese navegador.
  - Cambia el navegador con la variable YTDLP_BROWSER. Por defecto usa chrome.
  - Si el destino empieza con "icloud:", se guarda dentro de iCloud Drive.
EOF
  exit 1
fi

SOURCE_URL="$1"
DEST_DIR="$2"
BROWSER="${YTDLP_BROWSER:-chrome}"
MODE="${3:-all}"
ICLOUD_ROOT="${HOME}/Library/Mobile Documents/com~apple~CloudDocs"
ARCHIVE_FILE="${DEST_DIR}/.yt_download_archive.txt"

if [[ "$MODE" != "all" && "$MODE" != "streams" && "$MODE" != "list" ]]; then
  echo "Modo invalido: $MODE"
  echo "Usa 'all', 'streams' o 'list'"
  exit 1
fi

if [[ "$MODE" == "streams" && "$SOURCE_URL" != *"/streams"* && "$SOURCE_URL" != *"/live"* && "$SOURCE_URL" != *"playlist?list="* ]]; then
  SOURCE_URL="${SOURCE_URL%/}/streams"
fi

if [[ "$DEST_DIR" == icloud:* ]]; then
  if [[ ! -d "$ICLOUD_ROOT" ]]; then
    echo "No encontre la carpeta local de iCloud Drive en esta Mac."
    exit 1
  fi

  DEST_DIR="${ICLOUD_ROOT}/${DEST_DIR#icloud:}"
fi

ARCHIVE_FILE="${DEST_DIR}/.yt_download_archive.txt"

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "No encontre yt-dlp en tu sistema."
  echo "Instalalo en Mac con: brew install yt-dlp"
  exit 1
fi

mkdir -p "$DEST_DIR"

echo "Descargando desde: $SOURCE_URL"
echo "Guardando en: $DEST_DIR"
echo "Usando cookies del navegador: $BROWSER"
echo "Modo: $MODE"

COMMON_ARGS=(
  --ignore-errors
  --continue
  --no-overwrites
  --retries 10
  --fragment-retries 10
  --sleep-requests 2
  --sleep-interval 5
  --max-sleep-interval 10
  --download-archive "$ARCHIVE_FILE"
  --cookies-from-browser "$BROWSER"
  --format "bv*+ba/b"
  --merge-output-format mp4
  --output "${DEST_DIR}/%(upload_date>%Y-%m-%d)s - %(title).180B [%(id)s].%(ext)s"
)

if [[ "$MODE" == "list" ]]; then
  if [[ ! -f "$SOURCE_URL" ]]; then
    echo "No encontre el archivo de URLs: $SOURCE_URL"
    exit 1
  fi

  yt-dlp "${COMMON_ARGS[@]}" --batch-file "$SOURCE_URL"
else
  yt-dlp "${COMMON_ARGS[@]}" --yes-playlist "$SOURCE_URL"
fi

echo "Listo. Tus videos quedaron en: $DEST_DIR"
