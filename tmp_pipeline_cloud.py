import csv
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# =========================
# CONFIGURACIÓN
# =========================
BASE = Path.home() / "Desktop" / "holo_pipeline"
INBOX = BASE / "01_inbox_video"
BIBLIOTECA = BASE / "02_biblioteca"
DONE_LOGS = BASE / "03_done_logs"
CSV_PATH = BASE / "videos.csv"
LOG_PATH = DONE_LOGS / "procesados.log"
MODELOS_DIR = BASE / "00_modelos_whisper"

CHUNK_SECONDS = 600   # 10 minutos
MP3_BITRATE = "32k"
WHISPER_BACKEND = os.getenv("HOLO_WHISPER_BACKEND", "auto").strip().lower()
WHISPER_MODEL = os.getenv("HOLO_WHISPER_MODEL", "small").strip()
WHISPER_DEVICE = os.getenv("HOLO_WHISPER_DEVICE", "cpu").strip()
WHISPER_COMPUTE_TYPE = os.getenv("HOLO_WHISPER_COMPUTE_TYPE", "int8").strip()
YTDLP_BIN = os.getenv("HOLO_YTDLP_BIN", "yt-dlp").strip() or "yt-dlp"
YTDLP_COOKIES_FROM_BROWSER = [
    valor.strip()
    for valor in os.getenv("HOLO_YTDLP_COOKIES_FROM_BROWSER", "chrome").split(",")
    if valor.strip()
]

INBOX.mkdir(parents=True, exist_ok=True)
BIBLIOTECA.mkdir(parents=True, exist_ok=True)
DONE_LOGS.mkdir(parents=True, exist_ok=True)
MODELOS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.touch(exist_ok=True)

LINEAS_VALIDAS = {
    "salud": "Salud",
    "mística": "Mística",
    "mistica": "Mística",
    "desarrollo personal": "Desarrollo Personal",
    "wellnes": "Wellnes",
    "wellness": "Wellnes",
    "diplomados": "Diplomados",
}

_WHISPER_BACKEND_REAL = None
_WHISPER_RUNNER = None

# =========================
# UTILIDADES
# =========================
def log(mensaje: str):
    print(mensaje)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")

def slug(texto: str) -> str:
    texto = str(texto).strip().lower()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"\s+", "_", texto)
    return texto

def nombre_seguro(texto: str) -> str:
    texto = str(texto).strip()
    texto = re.sub(r'[\\/:"*?<>|]+', "", texto)
    texto = re.sub(r"\s+", "_", texto)
    return texto

def normalizar_linea(linea_raw: str) -> str:
    clave = str(linea_raw).strip().lower()
    return LINEAS_VALIDAS.get(clave, str(linea_raw).strip())

def detectar_delimitador(csv_path: Path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        primera_linea = f.readline()
    return ";" if ";" in primera_linea else ","

def cargar_filas(csv_path: Path):
    delimitador = detectar_delimitador(csv_path)
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimitador)
        return list(reader)

def es_url_youtube(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(
        dominio in host for dominio in (
            "youtube.com",
            "youtu.be",
            "youtube-nocookie.com",
        )
    )

def descargar_archivo(url: str, destino: Path):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=120) as respuesta:
        with open(destino, "wb") as f:
            while True:
                chunk = respuesta.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

def borrar_si_existe(path_obj: Path):
    if path_obj.exists():
        path_obj.unlink()

def limpiar_archivos_temporales(prefijo_base: str):
    for f in INBOX.glob(f"{prefijo_base}*"):
        try:
            f.unlink()
        except Exception:
            pass

def descargar_audio_youtube(url: str, audio_path: Path):
    if shutil.which(YTDLP_BIN) is None:
        raise RuntimeError(
            f"No encontré yt-dlp en PATH. Instálalo o define HOLO_YTDLP_BIN. Valor actual: {YTDLP_BIN}"
        )

    salida_template = str(audio_path.with_suffix(".%(ext)s"))
    comando_base = [
        YTDLP_BIN,
        "--no-playlist",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--output", salida_template,
        url,
    ]
    intentos = []
    for browser in YTDLP_COOKIES_FROM_BROWSER:
        intentos.append((["--cookies-from-browser", browser], f"cookies:{browser}"))
    intentos.append(([], "sin_cookies"))

    errores = []
    for argumentos_extra, etiqueta in intentos:
        comando = [comando_base[0], *argumentos_extra, *comando_base[1:]]
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
        )
        if resultado.returncode == 0:
            break

        detalle = (
            resultado.stderr.strip().splitlines()[-1]
            if resultado.stderr and resultado.stderr.strip()
            else resultado.stdout.strip().splitlines()[-1]
            if resultado.stdout and resultado.stdout.strip()
            else f"código {resultado.returncode}"
        )
        errores.append(f"{etiqueta} -> {detalle}")
    else:
        raise RuntimeError(f"yt-dlp falló para YouTube: {' | '.join(errores)}")

    candidatos = [audio_path]
    candidatos.extend(sorted(audio_path.parent.glob(f"{audio_path.stem}.*")))
    for candidato in candidatos:
        if candidato.exists() and candidato.is_file():
            if candidato != audio_path:
                borrar_si_existe(audio_path)
                candidato.replace(audio_path)
            return

    raise FileNotFoundError(f"yt-dlp terminó pero no encontré el audio esperado: {audio_path.name}")

# =========================
# AUDIO
# =========================
def extraer_audio_mp3(video_path: Path, audio_path: Path):
    comando = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", MP3_BITRATE,
        str(audio_path)
    ]
    subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def obtener_duracion_segundos(audio_path: Path) -> float:
    comando = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
    return float(resultado.stdout.strip())

def partir_audio_en_chunks(audio_path: Path, output_prefix: str, chunk_seconds: int = 600):
    duracion_total = obtener_duracion_segundos(audio_path)
    total_chunks = math.ceil(duracion_total / chunk_seconds)
    chunks = []

    for i in range(total_chunks):
        inicio = i * chunk_seconds
        salida = INBOX / f"{output_prefix}__chunk_{i+1:03d}.mp3"

        comando = [
            "ffmpeg",
            "-y",
            "-i", str(audio_path),
            "-ss", str(inicio),
            "-t", str(chunk_seconds),
            "-acodec", "copy",
            str(salida)
        ]
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        chunks.append(salida)

    return chunks

# =========================
# TRANSCRIPCIÓN
# =========================
def _cargar_backend_whisper():
    global _WHISPER_BACKEND_REAL, _WHISPER_RUNNER

    if _WHISPER_RUNNER is not None:
        return _WHISPER_BACKEND_REAL, _WHISPER_RUNNER

    errores = []
    backends_preferidos = (
        ["faster-whisper", "openai-whisper"]
        if WHISPER_BACKEND == "auto"
        else [WHISPER_BACKEND]
    )

    for backend in backends_preferidos:
        if backend == "faster-whisper":
            try:
                from faster_whisper import WhisperModel
            except ModuleNotFoundError:
                errores.append("faster-whisper")
                continue

            model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                download_root=str(MODELOS_DIR)
            )

            def runner(chunk_path: Path) -> str:
                segmentos, _info = model.transcribe(
                    str(chunk_path),
                    language="es",
                    task="transcribe",
                    beam_size=5,
                    vad_filter=True
                )
                partes = []
                for segmento in segmentos:
                    texto = segmento.text.strip()
                    if texto:
                        partes.append(texto)
                return " ".join(partes).strip()

            _WHISPER_BACKEND_REAL = "faster-whisper"
            _WHISPER_RUNNER = runner
            return _WHISPER_BACKEND_REAL, _WHISPER_RUNNER

        if backend == "openai-whisper":
            try:
                import whisper
            except ModuleNotFoundError:
                errores.append("openai-whisper")
                continue

            model = whisper.load_model(WHISPER_MODEL, download_root=str(MODELOS_DIR))

            def runner(chunk_path: Path) -> str:
                resultado = model.transcribe(
                    str(chunk_path),
                    language="es",
                    task="transcribe",
                    fp16=False,
                    verbose=False
                )
                return str(resultado.get("text") or "").strip()

            _WHISPER_BACKEND_REAL = "openai-whisper"
            _WHISPER_RUNNER = runner
            return _WHISPER_BACKEND_REAL, _WHISPER_RUNNER

        raise ValueError(
            f"Backend no soportado: {backend}. Usa HOLO_WHISPER_BACKEND=auto, faster-whisper u openai-whisper."
        )

    raise RuntimeError(
        "No encontré Whisper local instalado. Instala una de estas opciones:\n"
        "1. pip install faster-whisper\n"
        "2. pip install openai-whisper torch\n"
        f"Modelo configurado: {WHISPER_MODEL}"
    )

def transcribir_chunk(chunk_path: Path) -> str:
    _backend, runner = _cargar_backend_whisper()
    return runner(chunk_path)

def transcribir_chunks(chunks):
    textos = []
    for idx, chunk in enumerate(chunks, start=1):
        size_mb = chunk.stat().st_size / (1024 * 1024)
        log(f"Transcribiendo chunk {idx}/{len(chunks)} - {chunk.name} ({size_mb:.2f} MB)")

        if size_mb > 24:
            raise ValueError(f"Chunk demasiado grande ({size_mb:.2f} MB): {chunk.name}")

        texto = transcribir_chunk(chunk)
        textos.append(texto.strip())

    return "\n\n".join(textos)

# =========================
# BIBLIOTECA / ÍNDICE
# =========================
def obtener_rutas_curso(linea: str, curso: str):
    carpeta_linea = BIBLIOTECA / normalizar_linea(linea)
    carpeta_curso = carpeta_linea / nombre_seguro(curso)
    carpeta_curso.mkdir(parents=True, exist_ok=True)

    transcript_master = carpeta_curso / "transcripcion_completa.txt"
    index_csv = carpeta_curso / "index_modulos.csv"

    if not index_csv.exists():
        with open(index_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "fecha_proceso",
                "linea",
                "curso",
                "modulo",
                "url",
                "estado",
                "nombre_bloque"
            ])

    return carpeta_curso, transcript_master, index_csv

def modulo_ya_procesado(index_csv: Path, modulo: str, url: str) -> bool:
    if not index_csv.exists():
        return False

    with open(index_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["modulo"] == str(modulo) and row["url"] == str(url) and row["estado"] == "listo":
                return True
    return False

def registrar_modulo(index_csv: Path, linea: str, curso: str, modulo: str, url: str, estado: str, nombre_bloque: str):
    with open(index_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            linea,
            curso,
            modulo,
            url,
            estado,
            nombre_bloque
        ])

def modulo_ya_anexado_en_master(transcript_master: Path, nombre_bloque: str) -> bool:
    if not transcript_master.exists():
        return False

    marcador = f"BLOQUE: {nombre_bloque}"
    with open(transcript_master, "r", encoding="utf-8") as f:
        return marcador in f.read()

def append_transcripcion_master(transcript_master: Path, linea: str, curso: str, modulo: str, texto: str, nombre_bloque: str):
    encabezado = f"""
============================================================
BLOQUE: {nombre_bloque}
LÍNEA: {linea}
CURSO: {curso}
MÓDULO: {modulo}
FECHA DE PROCESO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
============================================================

"""
    with open(transcript_master, "a", encoding="utf-8") as f:
        f.write(encabezado)
        f.write(texto.strip())
        f.write("\n\n\n")

# =========================
# PROCESO PRINCIPAL
# =========================
def main():
    if not CSV_PATH.exists():
        log(f"ERROR: No existe el CSV en {CSV_PATH}")
        return

    filas = cargar_filas(CSV_PATH)

    if not filas:
        log("ERROR: El CSV está vacío.")
        return

    log(f"Columnas detectadas: {list(filas[0].keys())}")

    requeridas = ["CURSO", "MODULO", "URL", "LINEA"]
    faltantes = [c for c in requeridas if c not in filas[0]]
    if faltantes:
        log(f"ERROR: Faltan columnas requeridas: {faltantes}")
        return

    try:
        backend_real, _runner = _cargar_backend_whisper()
    except Exception as e:
        log(f"ERROR AL CARGAR WHISPER LOCAL: {e}")
        return

    log(
        f"Backend de transcripción local: {backend_real} | "
        f"modelo={WHISPER_MODEL} | device={WHISPER_DEVICE}"
    )

    for numero_fila, fila in enumerate(filas, start=2):
        curso = ""
        modulo = ""
        url = ""
        linea = ""
        nombre_base = f"fila_{numero_fila:04d}"
        transcript_master = None
        index_csv = None
        video_path = INBOX / f"{nombre_base}.mp4"
        audio_path = INBOX / f"{nombre_base}.mp3"

        try:
            curso = str(fila.get("CURSO") or "").strip()
            modulo = str(fila.get("MODULO") or "").strip()
            url = str(fila.get("URL") or "").strip()
            linea = str(fila.get("LINEA") or "").strip()

            faltantes_fila = [
                campo for campo, valor in {
                    "CURSO": curso,
                    "MODULO": modulo,
                    "URL": url,
                    "LINEA": linea,
                }.items() if not valor
            ]
            if faltantes_fila:
                raise ValueError(f"Fila {numero_fila} incompleta. Faltan: {faltantes_fila}")

            nombre_base = f"{slug(linea)}__{slug(curso)}__modulo_{slug(modulo)}"
            video_path = INBOX / f"{nombre_base}.mp4"
            audio_path = INBOX / f"{nombre_base}.mp3"

            carpeta_curso, transcript_master, index_csv = obtener_rutas_curso(linea, curso)

            if modulo_ya_procesado(index_csv, modulo, url):
                log(f"YA PROCESADO, SE SALTA: {curso} / módulo {modulo}")
                continue

            log(f"\nProcesando: {nombre_base}")
            if es_url_youtube(url):
                log("Descargando audio desde YouTube...")
                descargar_audio_youtube(url, audio_path)
                origen_audio = "youtube"
            else:
                log("Descargando video...")
                log("Extrayendo audio MP3 ligero...")
                descargar_archivo(url, video_path)
                extraer_audio_mp3(video_path, audio_path)
                borrar_si_existe(video_path)
                origen_audio = "directo"

            size_audio_mb = audio_path.stat().st_size / (1024 * 1024)
            log(
                f"Audio base generado ({origen_audio}): "
                f"{audio_path.name} ({size_audio_mb:.2f} MB)"
            )

            log("Partiendo audio en chunks...")
            chunks = partir_audio_en_chunks(audio_path, nombre_base, CHUNK_SECONDS)

            # borra el mp3 base apenas ya existen los chunks
            borrar_si_existe(audio_path)

            texto_modulo = transcribir_chunks(chunks)

            if modulo_ya_anexado_en_master(transcript_master, nombre_base):
                log("La transcripción ya estaba anexada en el archivo maestro, se evita duplicado.")
            else:
                log("Pegando transcripción al archivo maestro del curso...")
                append_transcripcion_master(
                    transcript_master,
                    normalizar_linea(linea),
                    curso,
                    modulo,
                    texto_modulo,
                    nombre_base
                )

            registrar_modulo(
                index_csv=index_csv,
                linea=normalizar_linea(linea),
                curso=curso,
                modulo=modulo,
                url=url,
                estado="listo",
                nombre_bloque=nombre_base
            )

            log("Borrando chunks temporales...")
            for c in chunks:
                borrar_si_existe(c)

            log(f"LISTO: {curso} / módulo {modulo}")

        except Exception as e:
            contexto_curso = curso or "(sin curso)"
            contexto_modulo = modulo or "(sin módulo)"
            log(f"ERROR EN {contexto_curso} / módulo {contexto_modulo} / fila {numero_fila}: {e}")
            if index_csv is not None:
                registrar_modulo(
                    index_csv=index_csv,
                    linea=normalizar_linea(linea),
                    curso=curso,
                    modulo=modulo,
                    url=url,
                    estado=f"error: {e}",
                    nombre_bloque=nombre_base
                )
            limpiar_archivos_temporales(nombre_base)
            borrar_si_existe(video_path)
            borrar_si_existe(audio_path)

if __name__ == "__main__":
    main()
