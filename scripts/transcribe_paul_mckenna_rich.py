from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from transcribe_translate_audio import normalize_for_upload, transcribe_audio, translate_text


BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "data" / "audio_manifests" / "paul_mckenna_i_can_make_you_rich.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "audio_transcripts" / "paul_mckenna_i_can_make_you_rich"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only.lower()).strip("-")
    return cleaned or "track"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe los audios de Paul McKenna - I Can Make You Rich con nombres legibles."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help=f"Manifest con el mapeo de pistas. Default: {MANIFEST_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directorio de salida. Default: {DEFAULT_OUTPUT_DIR}",
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
        default="medium",
        help="Modelo local de Whisper, por ejemplo tiny, base, small, medium, large.",
    )
    parser.add_argument(
        "--whisper-command",
        default="whisper",
        help="Ruta al binario de Whisper local si no está en el PATH.",
    )
    parser.add_argument(
        "--whisper-device",
        default=None,
        help="Dispositivo para Whisper local, por ejemplo cpu o cuda.",
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
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        raise SystemExit(f"No existe el manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def ensure_output_dirs(output_dir: Path) -> dict[str, Path]:
    paths = {
        "original": output_dir / "original",
        "translation": output_dir / "es",
        "metadata": output_dir / "metadata",
        "scratch": output_dir / "_normalized_audio",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def build_output_stem(track: dict) -> str:
    return f"{int(track['order']):02d}-{slugify(track['name'])}"


def main() -> None:
    load_dotenv()
    args = parse_args()
    tracks = load_manifest(args.manifest)
    output_dirs = ensure_output_dirs(args.output_dir)
    client = OpenAI() if args.backend == "openai" else None

    manifest_results_path = args.output_dir / "run_manifest.jsonl"
    summary: list[dict] = []

    for track in tracks:
        source_path = Path(track["source_path"])
        stem = build_output_stem(track)
        transcript_path = output_dirs["original"] / f"{stem}.txt"
        translation_path = output_dirs["translation"] / f"{stem}.es.txt"
        metadata_path = output_dirs["metadata"] / f"{stem}.json"

        if args.resume:
            transcript_ready = transcript_path.exists()
            translation_ready = args.translator == "none" or translation_path.exists()
            if transcript_ready and translation_ready:
                result = {
                    "track": track["name"],
                    "source_path": str(source_path),
                    "transcript_path": str(transcript_path),
                    "translation_path": str(translation_path) if args.translator != "none" else None,
                    "status": "skipped",
                }
                summary.append(result)
                with manifest_results_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(f"[skip] {track['name']}")
                continue

        if not source_path.exists():
            result = {
                "track": track["name"],
                "source_path": str(source_path),
                "transcript_path": "",
                "translation_path": None,
                "status": "missing",
            }
            summary.append(result)
            with manifest_results_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"[missing] {track['name']} -> {source_path}")
            continue

        print(f"[run] {track['order']:02d} {track['name']}")
        try:
            upload_path = normalize_for_upload(source_path, output_dirs["scratch"])
            transcript_text = transcribe_audio(client, upload_path, args)
            transcript_path.write_text(transcript_text, encoding="utf-8")

            translation_text = None
            if args.translator != "none":
                translation_text = translate_text(transcript_text, args.target_language)
                translation_path.write_text(translation_text, encoding="utf-8")

            metadata = {
                "track": track,
                "backend": args.backend,
                "model": args.whisper_model if args.backend == "local-whisper" else args.openai_model,
                "source_language": args.language or "auto",
                "target_language": args.target_language if args.translator != "none" else None,
                "translator": args.translator,
                "upload_path": str(upload_path),
                "transcript_path": str(transcript_path),
                "translation_path": str(translation_path) if args.translator != "none" else None,
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

            result = {
                "track": track["name"],
                "source_path": str(source_path),
                "transcript_path": str(transcript_path),
                "translation_path": str(translation_path) if args.translator != "none" else None,
                "status": "ok",
            }
            print(f"  OK -> {transcript_path.name}")
        except Exception as exc:  # pragma: no cover - runtime path
            result = {
                "track": track["name"],
                "source_path": str(source_path),
                "transcript_path": "",
                "translation_path": None,
                "status": "error",
                "error": str(exc),
            }
            print(f"  ERROR -> {exc}")

        summary.append(result)
        with manifest_results_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")

    ok_count = sum(1 for item in summary if item["status"] == "ok")
    skipped_count = sum(1 for item in summary if item["status"] == "skipped")
    missing_count = sum(1 for item in summary if item["status"] == "missing")
    error_count = sum(1 for item in summary if item["status"] == "error")

    print("\nResumen")
    print(f"  OK: {ok_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Missing: {missing_count}")
    print(f"  Error: {error_count}")
    print(f"  Resultados: {manifest_results_path}")


if __name__ == "__main__":
    main()
