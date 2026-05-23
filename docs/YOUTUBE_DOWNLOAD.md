# Descargar tus videos de YouTube en Mac

Este flujo esta pensado para bajar tus propios videos sin poner tu contrasena en un script.

## Opcion recomendada

1. Inicia sesion en YouTube en tu navegador.
2. Instala `yt-dlp`:

```bash
brew install yt-dlp
```

3. Ejecuta el script:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal/videos" "$HOME/Movies/MisVideosYT"
```

## Solo la pestaña "En directo"

Si quieres descargar solo los videos de la biblioteca que aparecen en `En directo`, usa el modo `streams`:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal" "icloud:Videos/MisDirectosYT" streams
```

Tambien puedes pasar directamente la URL de esa pestaña:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal/streams" "icloud:Videos/MisDirectosYT"
```

Eso evita bajar los videos normales del canal.

## Si quieres exactamente lo que ves en YouTube Studio

La pagina de `studio.youtube.com/.../videos/live` es una vista interna de YouTube Studio. A veces coincide con la pestaña publica `@TuCanal/streams`, pero si tienes emisiones privadas, no listadas o con filtros especiales, puede no ser identica.

En ese caso, el camino mas preciso es descargar desde una lista exacta de URLs:

```bash
./scripts/download_youtube_videos.sh "/ruta/live_urls.txt" "icloud:Videos/MisDirectosYT" list
```

El archivo `live_urls.txt` debe tener una URL por linea.

## Guardar dentro de iCloud Drive

Si quieres que los videos caigan en una carpeta especifica de iCloud, usa el prefijo `icloud:`:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal/videos" "icloud:Videos/MisVideosYT"
```

Si ademas quieres solo `En directo`:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal" "icloud:Videos/MisDirectosYT" streams
```

Ese ejemplo guarda en:

```bash
$HOME/Library/Mobile Documents/com~apple~CloudDocs/Videos/MisVideosYT
```

Tambien puedes cambiar `Videos/MisVideosYT` por la carpeta que quieras dentro de iCloud Drive.

## Si tus videos son privados o no listados

El script usa las cookies del navegador con `--cookies-from-browser`, asi que puede acceder a contenido que tu cuenta si puede ver.

Si usas Safari en vez de Chrome:

```bash
YTDLP_BROWSER=safari ./scripts/download_youtube_videos.sh "https://www.youtube.com/@TuCanal/videos" "$HOME/Movies/MisVideosYT"
```

## Si quieres bajar videos concretos

Tambien puedes pasar una playlist o una URL especifica:

```bash
./scripts/download_youtube_videos.sh "https://www.youtube.com/playlist?list=TU_PLAYLIST" "$HOME/Desktop/YT"
```

## Recomendacion importante

Si necesitas absolutamente todos tus archivos originales, incluyendo material no visible desde la pagina publica del canal, Google Takeout suele ser la opcion mas completa para exportar el contenido de tu cuenta.
