#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


SECTION_LABELS = [
    "Síntomas",
    "Las principales causas médicas incluyen",
    "Causas médicas",
    "Chakra relacionado",
    "Biodescodificación",
    "Tratamiento",
    "Mantras",
]

ENTRY_HEADING_RE = re.compile(r"^\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñüÜ0-9 ,()/\-]{2,90}):\s*$")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\f", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_disease_dictionary_texts(catalog_path: Path):
    catalog = load_json(catalog_path)
    for item in catalog:
        if item.get("category") == "disease_dictionary":
            yield item


def looks_like_entry_heading(lines: list[str], idx: int) -> str | None:
    line = lines[idx].strip()
    if not line or len(line) < 4:
        return None
    match = ENTRY_HEADING_RE.match(line)
    if not match:
        return None

    heading = match.group(1).strip()
    lowered = heading.lower()
    if lowered in {"índice", "introducción", "mantras"}:
        return None
    if lowered.startswith("las principales causas"):
        return None
    if lowered.startswith("causas médicas"):
        return None
    if lowered.startswith("chakra relacionado"):
        return None
    if lowered.startswith("biodescodificación"):
        return None
    if lowered.startswith("tratamiento"):
        return None

    lookahead = "\n".join(lines[idx + 1 : idx + 8])
    if any(label in lookahead for label in ("Síntomas:", "Biodescodificación:", "Tratamiento:", "Chakra relacionado:")):
        return heading
    return None


def find_entry_ranges(text: str) -> list[tuple[str, int, int]]:
    lines = text.splitlines()
    headings: list[tuple[str, int]] = []

    for idx in range(len(lines)):
        heading = looks_like_entry_heading(lines, idx)
        if heading:
            headings.append((heading, idx))

    ranges: list[tuple[str, int, int]] = []
    for i, (heading, start_idx) in enumerate(headings):
        end_idx = headings[i + 1][1] if i + 1 < len(headings) else len(lines)
        ranges.append((heading, start_idx, end_idx))
    return ranges


def extract_section(entry_text: str, label: str, next_labels: list[str]) -> str:
    pattern = re.escape(label) + r":?\s*"
    match = re.search(pattern, entry_text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = match.end()
    tail = entry_text[start:]
    next_positions = []
    for next_label in next_labels:
        nxt = re.search(r"\n\s*" + re.escape(next_label) + r":?\s*", tail, flags=re.IGNORECASE)
        if nxt:
            next_positions.append(nxt.start())
    end = min(next_positions) if next_positions else len(tail)
    return normalize_whitespace(tail[:end])


def extract_entry_sections(entry_text: str) -> dict:
    sections = {}
    labels = SECTION_LABELS
    for idx, label in enumerate(labels):
        next_labels = labels[idx + 1 :]
        sections[label] = extract_section(entry_text, label, next_labels)
    return sections


def compact_summary(sections: dict[str, str]) -> str:
    for key in ("Biodescodificación", "Síntomas", "Tratamiento"):
        value = sections.get(key, "")
        if value:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", value) if p.strip()]
            if paragraphs:
                return paragraphs[0][:1200]
    return ""


def build_entry(source_item: dict, heading: str, entry_text: str) -> dict:
    sections = extract_entry_sections(entry_text)
    canonical_name = heading.strip()
    return {
        "canonical_name": canonical_name,
        "slug": slugify(canonical_name),
        "source_title": source_item["title"],
        "source_id": source_item["reference_id"],
        "source_text_path": source_item["text_path"],
        "raw_heading": heading,
        "summary": compact_summary(sections),
        "symptoms": sections.get("Síntomas", ""),
        "medical_causes": sections.get("Las principales causas médicas incluyen", "") or sections.get("Causas médicas", ""),
        "chakra_related": sections.get("Chakra relacionado", ""),
        "biodescodificacion": sections.get("Biodescodificación", ""),
        "treatment": sections.get("Tratamiento", ""),
        "mantras": sections.get("Mantras", ""),
        "raw_text": normalize_whitespace(entry_text),
    }


def extract_entries_from_source(source_item: dict) -> list[dict]:
    text_path = Path(source_item["text_path"])
    text = normalize_whitespace(text_path.read_text(encoding="utf-8", errors="ignore"))
    entries: list[dict] = []
    for heading, start_idx, end_idx in find_entry_ranges(text):
        lines = text.splitlines()
        entry_text = "\n".join(lines[start_idx:end_idx]).strip()
        entries.append(build_entry(source_item, heading, entry_text))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae entradas estructuradas de enfermedades desde la biblioteca de referencia.")
    parser.add_argument("catalog_path", type=Path, help="Ruta a catalog.json de reference_processed")
    parser.add_argument("output_path", type=Path, help="Archivo JSON de salida")
    args = parser.parse_args()

    entries: list[dict] = []
    for source_item in iter_disease_dictionary_texts(args.catalog_path):
        entries.extend(extract_entries_from_source(source_item))

    output = {
        "entries_count": len(entries),
        "entries": entries,
    }

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entries_count": len(entries), "output_path": str(args.output_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
