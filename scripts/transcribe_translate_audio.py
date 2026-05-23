from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from openai import OpenAI

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - optional at runtime
    GoogleTranslator = None


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "audio_cache"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "audio_transcripts"
SUPPORTED_UPLOAD_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
DISCOVERY_EXTENSIONS = SUPPORTED_UPLOAD_EXTENSIONS | {".aac"}


@dataclass
class ProcessingResult:
    source_path: str
    upload_path: str
    transcript_path: str
    translation_path: str | None
    status: str
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe archivos de audio locales con Whisper u OpenAI y tradúcelos al español."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directorio con audios MP3/AAC/M4A. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directorio de salida para transcripciones y traducciones. Default: {DEFAULT_OUTPUT_DIR}",
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
        help="Modelo de OpenAI para transcripción cuando backend=openai.",
    )
    parser.add_argument(
        "--whisper-model",
        default="medium",
        help="Modelo local de Whisper, por ejemplo tiny, base, small, medium, large.",
    )
    parser.add_argument(
        "--whisper-command",
        default=os.getenv("WHISPER_COMMAND", "whisper"),
        help="Ruta al binario de Whisper local. También puedes usar la variable WHISPER_COMMAND.",
    )
    parser.add_argument(
        "--whisper-device",
        default=None,
        help="Dispositivo para Whisper local, por ejemplo cpu o cuda.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Código ISO-639-1 del idioma origen si ya lo conoces, por ejemplo en o es.",
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
        help="Backend de traducción. Usa none para transcribir sin traducir.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Busca audios de manera recursiva dentro del input-dir.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Omite archivos que ya tienen salida generada.",
    )
    return parser.parse_args()


def discover_audio_files(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files = [
        path
        for path in input_dir.glob(pattern)
        if path.is_file() and path.suffix.lower() in DISCOVERY_EXTENSIONS
    ]
    return sorted(files)


def ensure_ffmpeg_available() -> str:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "Se encontró un archivo .aac, pero ffmpeg no está disponible para convertirlo a .m4a."
        )
    return ffmpeg_bin


def normalize_for_upload(audio_path: Path, scratch_dir: Path) -> Path:
    if audio_path.suffix.lower() != ".aac":
        return audio_path

    ffmpeg_bin = ensure_ffmpeg_available()
    unique_suffix = hashlib.md5(str(audio_path).encode("utf-8")).hexdigest()[:10]
    converted_path = scratch_dir / f"{audio_path.stem}-{unique_suffix}.m4a"
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(audio_path),
        "-c:a",
        "aac",
        str(converted_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "ffmpeg no pudo convertir el archivo AAC.")
    return converted_path


def build_transcription_kwargs(args: argparse.Namespace, audio_file) -> dict:
    kwargs = {
        "model": args.openai_model,
        "file": audio_file,
    }
    if args.language:
        kwargs["language"] = args.language
    if args.prompt:
        kwargs["prompt"] = args.prompt
    return kwargs


def transcribe_with_openai(client: OpenAI, upload_path: Path, args: argparse.Namespace) -> str:
    with upload_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(**build_transcription_kwargs(args, audio_file))
    return getattr(response, "text", str(response)).strip()


def ensure_whisper_command_available(command_name: str) -> str:
    if Path(command_name).exists():
        return command_name

    resolved = shutil.which(command_name)
    if resolved:
        return resolved

    raise RuntimeError(
        "No encontré Whisper en este entorno. Pasa --whisper-command con la ruta completa, "
        "por ejemplo /ruta/a/tu/venv/bin/whisper."
    )


def transcribe_with_local_whisper(upload_path: Path, args: argparse.Namespace) -> str:
    whisper_command = ensure_whisper_command_available(args.whisper_command)
    with tempfile.TemporaryDirectory(prefix="whisper_out_") as temp_dir:
        command = [
            whisper_command,
            str(upload_path),
            "--task",
            "transcribe",
            "--model",
            args.whisper_model,
            "--output_dir",
            temp_dir,
            "--output_format",
            "txt",
            "--verbose",
            "False",
            "--fp16",
            "False",
        ]
        if args.language:
            command.extend(["--language", args.language])
        if args.prompt:
            command.extend(["--initial_prompt", args.prompt])
        if args.whisper_device:
            command.extend(["--device", args.whisper_device])

        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Whisper falló.")

        transcript_path = Path(temp_dir) / f"{upload_path.stem}.txt"
        if not transcript_path.exists():
            raise RuntimeError(
                f"Whisper terminó, pero no generó el archivo esperado: {transcript_path}"
            )
        return transcript_path.read_text(encoding="utf-8").strip()


def transcribe_audio(client: OpenAI | None, upload_path: Path, args: argparse.Namespace) -> str:
    if args.backend == "local-whisper":
        return transcribe_with_local_whisper(upload_path, args)
    if client is None:
        raise RuntimeError("No se pudo inicializar el cliente OpenAI.")
    return transcribe_with_openai(client, upload_path, args)


def split_text_for_translation(text: str, max_chars: int = 3500) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if paragraph_len > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            for start in range(0, paragraph_len, max_chars):
                chunks.append(paragraph[start : start + max_chars])
            continue

        projected = current_len + paragraph_len + (2 if current else 0)
        if projected > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len = projected

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def translate_text(text: str, target_language: str) -> str:
    if not text.strip():
        return ""
    if GoogleTranslator is None:
        raise RuntimeError(
            "Falta la dependencia deep-translator. Instálala con pip install -r requirements.txt."
        )

    translator = GoogleTranslator(source="auto", target=target_language)
    translated_chunks = [translator.translate(chunk) for chunk in split_text_for_translation(text)]
    return "\n\n".join(chunk.strip() for chunk in translated_chunks if chunk and chunk.strip())


def build_output_paths(output_dir: Path, input_dir: Path, source_path: Path) -> tuple[Path, Path, Path]:
    relative_parent = source_path.relative_to(input_dir).parent
    base_name = source_path.stem

    transcript_path = output_dir / "original" / relative_parent / f"{base_name}.txt"
    translation_path = output_dir / "es" / relative_parent / f"{base_name}.es.txt"
    metadata_path = output_dir / "metadata" / relative_parent / f"{base_name}.json"
    return transcript_path, translation_path, metadata_path


def ensure_parent_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def should_skip_existing(args: argparse.Namespace, transcript_path: Path, translation_path: Path) -> bool:
    if not args.resume:
        return False
    if args.translator == "none":
        return transcript_path.exists()
    return transcript_path.exists() and translation_path.exists()


def process_file(
    client: OpenAI | None,
    args: argparse.Namespace,
    source_path: Path,
    scratch_dir: Path,
) -> ProcessingResult:
    transcript_path, translation_path, metadata_path = build_output_paths(
        args.output_dir, args.input_dir, source_path
    )
    ensure_parent_dirs([transcript_path, translation_path, metadata_path])

    if should_skip_existing(args, transcript_path, translation_path):
        return ProcessingResult(
            source_path=str(source_path),
            upload_path=str(source_path),
            transcript_path=str(transcript_path),
            translation_path=str(translation_path) if args.translator != "none" else None,
            status="skipped",
        )

    upload_path = normalize_for_upload(source_path, scratch_dir)
    transcript_text = transcribe_audio(client, upload_path, args)
    translation_text = None

    transcript_path.write_text(transcript_text, encoding="utf-8")

    if args.translator != "none":
        translation_text = translate_text(transcript_text, args.target_language)
        translation_path.write_text(translation_text, encoding="utf-8")

    metadata = {
        "source_path": str(source_path),
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

    return ProcessingResult(
        source_path=str(source_path),
        upload_path=str(upload_path),
        transcript_path=str(transcript_path),
        translation_path=str(translation_path) if args.translator != "none" else None,
        status="ok",
    )


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not args.input_dir.exists():
        raise SystemExit(f"No existe el directorio de entrada: {args.input_dir}")

    audio_files = discover_audio_files(args.input_dir, recursive=args.recursive)
    if not audio_files:
        raise SystemExit(f"No se encontraron audios compatibles en: {args.input_dir}")

    client = OpenAI() if args.backend == "openai" else None
    scratch_dir = args.output_dir / "_normalized_audio"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.output_dir / "manifest.jsonl"
    results: list[ProcessingResult] = []

    for index, audio_path in enumerate(audio_files, start=1):
        print(f"[{index}/{len(audio_files)}] Procesando {audio_path}")
        try:
            result = process_file(client, args, audio_path, scratch_dir)
        except Exception as exc:  # pragma: no cover - runtime/network path
            result = ProcessingResult(
                source_path=str(audio_path),
                upload_path=str(audio_path),
                transcript_path="",
                translation_path=None,
                status="error",
                error=str(exc),
            )
            print(f"  ERROR: {exc}")
        else:
            print(f"  OK -> {result.transcript_path}")
            if result.translation_path:
                print(f"  ES -> {result.translation_path}")

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("a", encoding="utf-8") as manifest_file:
            manifest_file.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
        results.append(result)

    ok_count = sum(1 for item in results if item.status == "ok")
    skipped_count = sum(1 for item in results if item.status == "skipped")
    error_count = sum(1 for item in results if item.status == "error")

    print("\nResumen")
    print(f"  OK: {ok_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Error: {error_count}")
    print(f"  Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
