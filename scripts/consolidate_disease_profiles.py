#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


SYSTEM_RULES = [
    ("respiratorio", ["asma", "bronqu", "laring", "amigdal", "sinus", "respir", "pulmon"]),
    ("digestivo", ["colitis", "gastr", "reflujo", "ulcera", "úlcera", "intestin", "pancrea", "hep", "biliar", "digest"]),
    ("endocrino_metabolico", ["diabetes", "hipogluc", "hipertiroid", "ovario poliqu", "metabol"]),
    ("neurosensorial", ["migra", "vertigo", "vértigo", "sordera", "glaucoma", "catarata", "tdah", "toc", "paralisis facial", "parálisis facial"]),
    ("osteomuscular", ["artritis", "escoliosis", "osteoporosis", "fibromialgia", "columna", "gota", "torticolis", "tortícolis"]),
    ("dermatologico", ["dermat", "eczema", "urticaria", "psoriasis", "piel"]),
    ("emocional_mental", ["ansiedad", "depresion", "depresión", "bipolar", "insomnio", "fatiga crónica", "fatiga cronica", "bulimia"]),
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_value = re.sub(r"\s+", " ", ascii_value).strip()
    return ascii_value


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_text(value)).strip("-")


def split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", text)]
    return [part for part in parts if part]


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result


def infer_system(name: str, blob: str) -> str:
    haystack = normalize_text(f"{name} {blob}")
    for system_name, needles in SYSTEM_RULES:
        if any(needle in haystack for needle in needles):
            return system_name
    return "indeterminado"


def extract_possible_origins(entries: list[dict]) -> list[str]:
    candidates: list[str] = []
    for entry in entries:
        paragraphs = split_paragraphs(entry.get("biodescodificacion", ""))
        candidates.extend(paragraphs[:4])
    return dedupe_keep_order(candidates)[:6]


def extract_support_methods(entries: list[dict]) -> list[str]:
    methods: list[str] = []
    for entry in entries:
        text = entry.get("treatment", "")
        paragraphs = split_paragraphs(text)
        methods.extend(paragraphs[:6])
    return dedupe_keep_order(methods)[:8]


def extract_symptom_notes(entries: list[dict]) -> list[str]:
    chunks: list[str] = []
    for entry in entries:
        symptoms = entry.get("symptoms", "")
        if symptoms:
            chunks.append(symptoms.strip())
    return dedupe_keep_order(chunks)[:4]


def build_summary(entries: list[dict]) -> str:
    for entry in entries:
        summary = entry.get("summary", "").strip()
        if summary:
            return summary
    origins = extract_possible_origins(entries)
    return origins[0] if origins else ""


def consolidate(entries: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        grouped[normalize_text(entry["canonical_name"])].append(entry)

    profiles = []
    for key, group in sorted(grouped.items()):
        canonical_name = group[0]["canonical_name"].strip()
        source_titles = dedupe_keep_order([item["source_title"] for item in group])
        summary = build_summary(group)
        possible_origins = extract_possible_origins(group)
        support_methods = extract_support_methods(group)
        symptom_notes = extract_symptom_notes(group)
        blob = " ".join(
            [
                summary,
                " ".join(possible_origins),
                " ".join(symptom_notes),
            ]
        )

        profiles.append(
            {
                "canonical_name": canonical_name,
                "slug": slugify(canonical_name),
                "aliases": dedupe_keep_order([item["canonical_name"] for item in group]),
                "system_name": infer_system(canonical_name, blob),
                "summary": summary,
                "possible_origins": possible_origins,
                "symptom_notes": symptom_notes,
                "support_methods": support_methods,
                "source_titles": source_titles,
                "source_count": len(source_titles),
                "entries_count": len(group),
                "review_status": "auto_compiled",
            }
        )

    return {
        "profiles_count": len(profiles),
        "profiles": profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolida entradas de enfermedades en perfiles canónicos.")
    parser.add_argument("entries_path", type=Path, help="Archivo disease_entries_raw.json")
    parser.add_argument("output_path", type=Path, help="Archivo de salida disease_profiles.json")
    args = parser.parse_args()

    payload = load_json(args.entries_path)
    consolidated = consolidate(payload["entries"])

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(consolidated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"profiles_count": consolidated["profiles_count"], "output_path": str(args.output_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
