#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADING_PATTERN = re.compile(
    r"^\s*(m[oó]dulo|modulo|lecci[oó]n|leccion|tema|unidad|clase|cap[ií]tulo|capitulo)\b[:\s-]*",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_whitespace(text: str) -> str:
    text = text.replace("\f", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for part in re.split(r"\n\s*\n", text):
        cleaned = normalize_whitespace(part)
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def paragraph_is_heading(paragraph: str) -> bool:
    first_line = paragraph.split("\n", 1)[0].strip()
    if len(first_line) > 120:
        return False
    return bool(HEADING_PATTERN.match(first_line))


def chunk_paragraphs(paragraphs: list[str], chunk_size: int, overlap: int) -> list[dict]:
    chunks = []
    current_paragraphs: list[str] = []
    current_heading = ""
    current_length = 0

    def flush():
        nonlocal current_paragraphs, current_length
        if not current_paragraphs:
            return
        chunks.append(
            {
                "heading": current_heading,
                "text": "\n\n".join(current_paragraphs).strip(),
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
            current_heading = paragraph.split("\n", 1)[0].strip()

        paragraph_length = len(paragraph) + 2
        if current_paragraphs and current_length + paragraph_length > chunk_size:
            flush()

        current_paragraphs.append(paragraph)
        current_length += paragraph_length

    flush()
    return merge_small_chunks(chunks)


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
    parser.add_argument("--chunk-size", type=int, default=1800, help="Tamaño máximo por chunk")
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
                normalized = normalize_whitespace(text)
                if not normalized:
                    continue

                paragraphs = split_paragraphs(normalized)
                if not paragraphs:
                    continue

                chunks = chunk_paragraphs(paragraphs, args.chunk_size, args.overlap)
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
