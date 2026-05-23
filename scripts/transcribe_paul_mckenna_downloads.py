from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from transcribe_translate_audio import normalize_for_upload, transcribe_audio, translate_text


APP_CONTAINER = Path(
    "/Users/m2/Library/Containers/5F400AEE-E013-43FC-A64A-08E3EC0CB557"
)
DEFAULT_DOCUMENTS_DIR = APP_CONTAINER / "Data" / "Documents"
DEFAULT_CACHE_DIR = (
    APP_CONTAINER / "Data" / "Library" / "Caches" / "com.paulmckenna.pmk3" / "fsCachedData"
)
DEFAULT_OUTPUT_ROOT = Path("/Users/m2/Desktop/Transcripciones Audios")


@dataclass
class TrackRecord:
    program_id: str
    program_name: str
    chapter_id: str
    chapter_name: str
    order: int
    source_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Busca los audios descargados de la app de Paul McKenna y los transcribe "
            "agrupando la salida por programa."
        )
    )
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=DEFAULT_DOCUMENTS_DIR,
        help=f"Carpeta local donde la app guarda MP3 descargados. Default: {DEFAULT_DOCUMENTS_DIR}",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"Carpeta con el índice cacheado de la app. Default: {DEFAULT_CACHE_DIR}",
    )
    parser.add_argument(
        "--cache-json",
        type=Path,
        default=None,
        help="Ruta directa al JSON del catálogo. Si se omite, se detecta automáticamente.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Raíz de salida. Se creará una subcarpeta por programa. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--backend",
        default="local-whisper",
        choices=["local-whisper", "openai"],
        help="Motor de transcripción. Default: local-whisper",
    )
    parser.add_argument(
        "--openai-model",
        default="whisper-1",
        choices=["whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe"],
        help="Modelo de OpenAI cuando backend=openai.",
    )
    parser.add_argument(
        "--whisper-model",
        default="tiny",
        help="Modelo local de Whisper, por ejemplo tiny, base, small, medium, large.",
    )
    parser.add_argument(
        "--whisper-command",
        default="whisper",
        help="Ruta al binario de Whisper local si no está en el PATH.",
    )
    parser.add_argument(
        "--whisper-device",
        default="cpu",
        help="Dispositivo para Whisper local. Default: cpu",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Código ISO-639-1 del idioma origen. Default: en",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Contexto adicional para mejorar la transcripción.",
    )
    parser.add_argument(
        "--target-language",
        default="es",
        help="Idioma de salida para la traducción. Default: es",
    )
    parser.add_argument(
        "--translator",
        default="google",
        choices=["google", "none"],
        help="Backend de traducción. Usa none para solo transcribir.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Omite pistas que ya tengan salida generada.",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Solo copia el respaldo de los audios originales a cada carpeta de programa.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Solo muestra los programas y pistas encontradas, sin transcribir.",
    )
    parser.add_argument(
        "--program-filter",
        default=None,
        help="Filtra programas cuyo nombre contenga este texto.",
    )
    return parser.parse_args()


def sanitize_path_component(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\\\|?*]+', " ", value).strip()
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized or "Sin nombre"


def detect_catalog_json(cache_dir: Path) -> Path:
    candidates = sorted(cache_dir.glob("*"))
    json_candidates: list[Path] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("result"), list):
            json_candidates.append(candidate)

    if not json_candidates:
        raise SystemExit(f"No encontré un JSON de catálogo en {cache_dir}")

    return max(json_candidates, key=lambda path: path.stat().st_size)


def load_catalog(cache_json: Path) -> list[dict]:
    payload = json.loads(cache_json.read_text(encoding="utf-8"))
    result = payload.get("result")
    if not isinstance(result, list):
        raise SystemExit(f"El archivo {cache_json} no tiene la estructura esperada.")
    return result


def collect_downloaded_tracks(
    items: list[dict],
    documents_dir: Path,
    program_filter: str | None = None,
) -> list[TrackRecord]:
    products = {
        item["_id"]: item
        for item in items
        if item.get("_type") == "product" and item.get("name")
    }
    chapters = {
        item["_id"]: item
        for item in items
        if item.get("_type") == "chapter" and item.get("name")
    }

    downloaded_tracks: list[TrackRecord] = []
    name_filter = program_filter.lower() if program_filter else None

    for product_id, product in products.items():
        program_name = str(product["name"]).strip()
        if name_filter and name_filter not in program_name.lower():
            continue

        chapter_refs = product.get("chapters") or []
        if not isinstance(chapter_refs, list):
            continue

        order_map = {
            chapter_ref.get("_ref"): index
            for index, chapter_ref in enumerate(chapter_refs, start=1)
            if isinstance(chapter_ref, dict) and chapter_ref.get("_ref")
        }

        for chapter_id, order in order_map.items():
            chapter = chapters.get(chapter_id)
            if not chapter:
                continue

            source_path = documents_dir / f"{chapter_id}.mp3"
            if not source_path.exists():
                continue

            downloaded_tracks.append(
                TrackRecord(
                    program_id=product_id,
                    program_name=program_name,
                    chapter_id=chapter_id,
                    chapter_name=str(chapter["name"]).strip(),
                    order=order,
                    source_path=source_path,
                )
            )

    return sorted(downloaded_tracks, key=lambda item: (item.program_name.lower(), item.order, item.chapter_name.lower()))


def ensure_output_dirs(program_dir: Path) -> dict[str, Path]:
    paths = {
        "root": program_dir,
        "audio_backup": program_dir / "audios",
        "original": program_dir / "original",
        "translation": program_dir / "es",
        "metadata": program_dir / "metadata",
        "scratch": program_dir / "_normalized_audio",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def build_track_stem(track: TrackRecord) -> str:
    return f"{track.order:02d} - {sanitize_path_component(track.chapter_name)}"


def backup_audio_file(track: TrackRecord, output_dirs: dict[str, Path]) -> Path:
    audio_backup_path = output_dirs["audio_backup"] / f"{build_track_stem(track)}{track.source_path.suffix.lower()}"
    shutil.copy2(track.source_path, audio_backup_path)
    return audio_backup_path


def process_track(
    client: OpenAI | None,
    args: argparse.Namespace,
    track: TrackRecord,
    program_dir: Path,
) -> dict:
    output_dirs = ensure_output_dirs(program_dir)
    stem = build_track_stem(track)
    audio_backup_path = output_dirs["audio_backup"] / f"{stem}{track.source_path.suffix.lower()}"
    transcript_path = output_dirs["original"] / f"{stem}.txt"
    translation_path = output_dirs["translation"] / f"{stem}.es.txt"
    metadata_path = output_dirs["metadata"] / f"{stem}.json"
    audio_backup_exists = audio_backup_path.exists()

    if not (args.resume and audio_backup_exists):
        backup_audio_file(track, output_dirs)

    if args.audio_only:
        return {
            "program": track.program_name,
            "track": track.chapter_name,
            "source_path": str(track.source_path),
            "audio_backup_path": str(audio_backup_path),
            "transcript_path": None,
            "translation_path": None,
            "status": "skipped" if args.resume and audio_backup_exists else "ok",
        }

    if args.resume:
        transcript_ready = transcript_path.exists()
        translation_ready = args.translator == "none" or translation_path.exists()
        if transcript_ready and translation_ready:
            return {
                "program": track.program_name,
                "track": track.chapter_name,
                "source_path": str(track.source_path),
                "audio_backup_path": str(audio_backup_path),
                "transcript_path": str(transcript_path),
                "translation_path": str(translation_path) if args.translator != "none" else None,
                "status": "skipped",
            }

    upload_path = normalize_for_upload(track.source_path, output_dirs["scratch"])
    transcript_text = transcribe_audio(client, upload_path, args)
    transcript_path.write_text(transcript_text, encoding="utf-8")

    translation_text = None
    if args.translator != "none":
        translation_text = translate_text(transcript_text, args.target_language)
        translation_path.write_text(translation_text, encoding="utf-8")

    metadata = {
        "program_id": track.program_id,
        "program_name": track.program_name,
        "chapter_id": track.chapter_id,
        "chapter_name": track.chapter_name,
        "order": track.order,
        "source_path": str(track.source_path),
        "upload_path": str(upload_path),
        "backend": args.backend,
        "model": args.whisper_model if args.backend == "local-whisper" else args.openai_model,
        "source_language": args.language or "auto",
        "target_language": args.target_language if args.translator != "none" else None,
        "translator": args.translator,
        "transcript_path": str(transcript_path),
        "translation_path": str(translation_path) if args.translator != "none" else None,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "program": track.program_name,
        "track": track.chapter_name,
        "source_path": str(track.source_path),
        "audio_backup_path": str(audio_backup_path),
        "transcript_path": str(transcript_path),
        "translation_path": str(translation_path) if args.translator != "none" else None,
        "status": "ok",
    }


def print_discovery_summary(tracks: list[TrackRecord], output_root: Path) -> None:
    grouped: dict[str, list[TrackRecord]] = {}
    for track in tracks:
        grouped.setdefault(track.program_name, []).append(track)

    print(f"Programas encontrados: {len(grouped)}")
    print(f"Pistas encontradas: {len(tracks)}")
    print(f"Salida base: {output_root}")
    for program_name in sorted(grouped):
        program_dir = output_root / sanitize_path_component(program_name)
        print(f"\n- {program_name} ({len(grouped[program_name])} pistas)")
        print(f"  Carpeta: {program_dir}")


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not args.documents_dir.exists():
        raise SystemExit(f"No existe la carpeta de documentos de la app: {args.documents_dir}")

    cache_json = args.cache_json or detect_catalog_json(args.cache_dir)
    items = load_catalog(cache_json)
    tracks = collect_downloaded_tracks(items, args.documents_dir, args.program_filter)

    if not tracks:
        raise SystemExit("No encontré pistas descargadas que coincidan con el catálogo.")

    print(f"Catálogo usado: {cache_json}")
    print_discovery_summary(tracks, args.output_root)

    if args.list_only:
        return

    client = OpenAI() if args.backend == "openai" else None
    run_manifest_path = args.output_root / "all_programs_run_manifest.jsonl"
    summary: list[dict] = []

    for index, track in enumerate(tracks, start=1):
        program_dir = args.output_root / sanitize_path_component(track.program_name)
        print(f"\n[{index}/{len(tracks)}] {track.program_name} -> {track.chapter_name}")
        try:
            result = process_track(client, args, track, program_dir)
            print(f"  {result['status'].upper()} -> {result['transcript_path']}")
        except Exception as exc:
            result = {
                "program": track.program_name,
                "track": track.chapter_name,
                "source_path": str(track.source_path),
                "audio_backup_path": None,
                "transcript_path": "",
                "translation_path": None,
                "status": "error",
                "error": str(exc),
            }
            print(f"  ERROR -> {exc}")

        summary.append(result)
        run_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with run_manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    ok_count = sum(1 for item in summary if item["status"] == "ok")
    skipped_count = sum(1 for item in summary if item["status"] == "skipped")
    error_count = sum(1 for item in summary if item["status"] == "error")

    print("\nResumen")
    print(f"  OK: {ok_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Error: {error_count}")
    print(f"  Resultados: {run_manifest_path}")


if __name__ == "__main__":
    main()
