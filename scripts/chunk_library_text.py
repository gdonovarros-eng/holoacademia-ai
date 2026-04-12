#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADING_PATTERN = re.compile(
    r"^\s*("
    r"m[oó]dulo|modulo|lecci[oó]n|leccion|tema|unidad|clase|"
    r"cap[ií]tulo|capitulo|sistema|protocolo|bloque|sesi[oó]n|"
    r"sesion|pr[aá]ctica|practica|parte|nivel"
    r")\b[:\s-]*",
    re.IGNORECASE,
)

TRANSCRIPT_METADATA_LINE = re.compile(
    r"^\s*("
    r"l[ií]nea|linea|curso|m[oó]dulo|modulo|bloque|fecha de proceso|"
    r"impartido por|ponente|docente|facilitador|duraci[oó]n|duracion"
    r")\s*:\s*.+$",
    re.IGNORECASE,
)

MANUAL_FRONTMATTER_PATTERNS = [
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^[A-ZÁÉÍÓÚÜÑ .,'/-]{3,}\s+\d{1,4}\s*$"),
    re.compile(r"si vas a reproducir este material", re.IGNORECASE),
    re.compile(r"1era edici[oó]n|primera edici[oó]n|actualizado", re.IGNORECASE),
    re.compile(r"copyright|todos los derechos reservados", re.IGNORECASE),
    re.compile(r"lista de reproducci[oó]n|canal de youtube|youtube", re.IGNORECASE),
    re.compile(r"por un mundo sano|s[eé] profesional", re.IGNORECASE),
]

MANUAL_ADMIN_PATTERNS = [
    re.compile(r"\bcurr[ií]culum\b|\bcurriculum\b", re.IGNORECASE),
    re.compile(r"\bsemblanza\b", re.IGNORECASE),
    re.compile(r"\bcalendario\b", re.IGNORECASE),
    re.compile(r"\bhorario\b", re.IGNORECASE),
    re.compile(r"\binscripci[oó]n\b", re.IGNORECASE),
]

INDEX_LINE_SPLIT = re.compile(r"[\r\n]+")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_whitespace(text: str) -> str:
    text = text.replace("\f", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_line(text: str) -> str:
    return normalize_whitespace(text).replace("\n", " ").strip()


def split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for part in re.split(r"\n\s*\n", text):
        cleaned = normalize_whitespace(part)
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def first_line(paragraph: str) -> str:
    return clean_line(paragraph.split("\n", 1)[0])


def is_page_marker(paragraph: str) -> bool:
    line = first_line(paragraph)
    if not line:
        return True
    if re.fullmatch(r"\d{1,4}", line):
        return True
    if re.fullmatch(r"[A-ZÁÉÍÓÚÜÑ .,'/-]{3,}\s+\d{1,4}", line):
        return True
    return False


def looks_like_metadata_block(paragraph: str) -> bool:
    lines = [clean_line(line) for line in paragraph.splitlines() if clean_line(line)]
    if len(lines) < 2:
        return False
    matches = sum(1 for line in lines if TRANSCRIPT_METADATA_LINE.match(line))
    return matches >= max(2, len(lines) // 2)


def looks_like_heading_line(line: str) -> bool:
    line = clean_line(line)
    if not line or len(line) > 140:
        return False

    if HEADING_PATTERN.match(line):
        return True

    if re.match(r"^\d+(?:\.\d+)*\s+[A-ZÁÉÍÓÚÜÑ]", line):
        return True

    if line.isupper() and 2 <= len(line.split()) <= 12:
        return True

    return False


def paragraph_is_heading(paragraph: str) -> bool:
    return looks_like_heading_line(first_line(paragraph))


def strip_leading_noise(paragraphs: list[str], source_type: str) -> list[str]:
    if not paragraphs:
        return paragraphs

    cleaned = list(paragraphs)
    idx = 0
    max_probe = min(len(cleaned), 16)

    while idx < max_probe:
        paragraph = cleaned[idx]
        line = first_line(paragraph)

        if is_page_marker(paragraph):
            idx += 1
            continue

        if source_type == "transcripcion":
            if looks_like_metadata_block(paragraph):
                idx += 1
                continue
            if idx < 4 and TRANSCRIPT_METADATA_LINE.match(line):
                idx += 1
                continue
            break

        if source_type == "manual":
            matched_front = any(pattern.search(paragraph) for pattern in MANUAL_FRONTMATTER_PATTERNS)
            matched_admin = idx < 6 and any(pattern.search(paragraph) for pattern in MANUAL_ADMIN_PATTERNS)
            very_short_upper = line.isupper() and len(line.split()) <= 10 and len(line) <= 80
            if matched_front or matched_admin or very_short_upper:
                idx += 1
                continue
            if idx < 6 and not re.search(r"[.!?]", paragraph) and len(paragraph) < 180:
                idx += 1
                continue
            break

        if source_type == "indice":
            if not line or looks_like_metadata_block(paragraph):
                idx += 1
                continue
            break

        break

    trimmed = cleaned[idx:]
    return trimmed or cleaned


def extract_source_heading(paragraphs: list[str], source_type: str, source_file: str) -> str:
    probe = paragraphs[:10]

    if source_type == "transcripcion":
        for paragraph in probe:
            lines = [clean_line(line) for line in paragraph.splitlines() if clean_line(line)]
            for line in lines:
                if re.match(r"^\s*(m[oó]dulo|modulo|bloque|clase|sesi[oó]n|sesion)\s*:\s*.+$", line, re.IGNORECASE):
                    return line

    for paragraph in probe:
        line = first_line(paragraph)
        if looks_like_heading_line(line):
            return line

    stem = Path(source_file).stem.replace("_", " ").replace("-", " ").strip()
    return stem[:120] if stem else ""


def merge_small_chunks(chunks: list[dict], minimum_size: int = 350) -> list[dict]:
    if not chunks:
        return chunks

    merged = []
    idx = 0
    while idx < len(chunks):
        current = chunks[idx]
        if len(current["text"]) >= minimum_size or idx == len(chunks) - 1:
            merged.append(current)
            idx += 1
            continue

        nxt = chunks[idx + 1]
        merged.append(
            {
                "heading": current["heading"] or nxt["heading"],
                "text": f"{current['text']}\n\n{nxt['text']}".strip(),
            }
        )
        idx += 2

    return merged


def chunk_paragraphs(
    paragraphs: list[str],
    *,
    chunk_size: int,
    overlap: int,
    default_heading: str = "",
) -> list[dict]:
    chunks = []
    current_paragraphs: list[str] = []
    current_heading = default_heading
    current_length = 0

    def flush():
        nonlocal current_paragraphs, current_length
        if not current_paragraphs:
            return

        text = "\n\n".join(current_paragraphs).strip()
        if text:
            chunks.append(
                {
                    "heading": current_heading,
                    "text": text,
                }
            )

        if overlap <= 0:
            current_paragraphs = []
            current_length = 0
            return

        overlap_paragraphs = []
        overlap_length = 0
        for paragraph in reversed(current_paragraphs):
            overlap_paragraphs.insert(0, paragraph)
            overlap_length += len(paragraph) + 2
            if overlap_length >= overlap:
                break

        current_paragraphs = overlap_paragraphs
        current_length = sum(len(p) + 2 for p in current_paragraphs)

    for paragraph in paragraphs:
        if paragraph_is_heading(paragraph):
            current_heading = first_line(paragraph) or current_heading or default_heading

        paragraph_length = len(paragraph) + 2
        if current_paragraphs and current_length + paragraph_length > chunk_size:
            flush()

        current_paragraphs.append(paragraph)
        current_length += paragraph_length

    flush()
    return merge_small_chunks(chunks)


def chunk_index_text(text: str, source_file: str) -> list[dict]:
    lines = [clean_line(line) for line in INDEX_LINE_SPLIT.split(text) if clean_line(line)]
    if not lines:
        return []

    groups: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    target_size = 900

    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > target_size:
            groups.append(current)
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        groups.append(current)

    heading = f"Índice - {Path(source_file).stem}".strip(" -")
    return [{"heading": heading, "text": "\n".join(group)} for group in groups]


def source_chunk_params(source_type: str, default_chunk_size: int, default_overlap: int) -> tuple[int, int]:
    if source_type == "transcripcion":
        return max(1000, default_chunk_size - 350), max(100, default_overlap - 80)
    if source_type == "manual":
        return default_chunk_size, default_overlap
    if source_type == "indice":
        return 900, 0
    return default_chunk_size, default_overlap


def build_chunks_for_source(
    *,
    text: str,
    source_type: str,
    source_file: str,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    if source_type == "indice":
        return chunk_index_text(normalized, source_file)

    paragraphs = split_paragraphs(normalized)
    if not paragraphs:
        return []

    paragraphs = strip_leading_noise(paragraphs, source_type)
    if not paragraphs:
        return []

    default_heading = extract_source_heading(paragraphs, source_type, source_file)
    return chunk_paragraphs(
        paragraphs,
        chunk_size=chunk_size,
        overlap=overlap,
        default_heading=default_heading,
    )


def iter_manifests(processed_root: Path):
    for path in sorted(processed_root.rglob("course_manifest.json")):
        if path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera chunks JSONL a partir de textos procesados de la biblioteca."
    )
    parser.add_argument("processed_root", type=Path, help="Ruta raíz procesada")
    parser.add_argument("output_jsonl", type=Path, help="Archivo JSONL de salida")
    parser.add_argument("--chunk-size", type=int, default=1800, help="Tamaño máximo base por chunk")
    parser.add_argument("--overlap", type=int, default=250, help="Solapamiento aproximado entre chunks")
    args = parser.parse_args()

    processed_root = args.processed_root.expanduser().resolve()
    output_jsonl = args.output_jsonl.expanduser().resolve()
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for manifest_path in iter_manifests(processed_root):
            manifest = load_json(manifest_path)

            for source in manifest.get("sources", []):
                if source.get("status") != "ok":
                    continue

                text_path = Path(source["text_path"])
                text = text_path.read_text(encoding="utf-8", errors="ignore")
                source_type = str(source.get("tipo", "")).strip().lower()
                source_file = str(source.get("archivo_original", "")).strip()

                chunk_size, overlap = source_chunk_params(
                    source_type,
                    args.chunk_size,
                    args.overlap,
                )

                chunks = build_chunks_for_source(
                    text=text,
                    source_type=source_type,
                    source_file=source_file,
                    chunk_size=chunk_size,
                    overlap=overlap,
                )

                for idx, chunk in enumerate(chunks, start=1):
                    total_chunks += 1
                    record = {
                        "chunk_id": f"{manifest['course_id']}::{source['source_id']}::{idx:04d}",
                        "course_id": manifest["course_id"],
                        "course_name": manifest["course_name"],
                        "linea": manifest["linea"],
                        "tipo": manifest["tipo"],
                        "audiencia": manifest.get("audiencia", "Alumnos"),
                        "idioma": manifest.get("idioma", "es"),
                        "source_id": source["source_id"],
                        "source_type": source["tipo"],
                        "source_file": source["archivo_original"],
                        "source_text_path": source["text_path"],
                        "heading": chunk["heading"],
                        "text": chunk["text"],
                        "char_count": len(chunk["text"]),
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {"output_jsonl": str(output_jsonl), "total_chunks": total_chunks},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
