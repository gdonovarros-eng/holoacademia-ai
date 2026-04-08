from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "therapy_manual_index.json"
THERAPY_DIPLOMA_IDS = {
    "diplomado-ancestros-y-raices",
    "diplomado-sanacion-energetica-integral",
    "diplomado-terapia-holistica-1",
}


SYSTEM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "digestivo": ("digest", "estomag", "gastr", "intestin", "colon", "reflujo", "ulcera", "helicobacter"),
    "neurosensorial": ("vertigo", "mareo", "tinnitus", "oido", "audit", "neuro", "sensorial", "vestib"),
    "emocional_mental": ("emocion", "miedo", "ansiedad", "creencia", "shock", "bioshock", "trauma", "mental"),
    "respiratorio": ("respir", "bronqu", "pulmon", "asma", "faring", "laringe", "alerg"),
    "dermatologico": ("piel", "dermat", "eczema", "cabello", "alopecia"),
    "osteomuscular": ("hues", "musc", "articul", "desvaloriz", "columna", "rodilla", "dolor"),
    "endocrino_metabolico": ("endocr", "tiroid", "diabetes", "metabol", "pancre", "hipofis"),
    "reproductor": ("reproduct", "sexual", "uter", "prostat", "ovari", "embarazo", "fertil"),
    "renal_excretor": ("renal", "rinon", "riñon", "vejiga", "orina", "urin"),
    "cardiovascular": ("corazon", "corazón", "vascular", "sangre", "circul", "presion"),
}

TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "transgeneracional": ("transgener", "ancestro", "linaje", "arbol", "árbol", "genograma", "doble", "yacente"),
    "sentimental": ("sentimental", "pareja", "vinculo", "vínculo", "rechazo", "abandono", "separacion"),
    "patogenos": ("bacteria", "virus", "hongo", "parasito", "parásito", "helicobacter", "microb"),
    "rastreo": ("rastreo", "rastrear", "localizar", "inventario", "conflictologico", "conflictológico"),
    "eft": ("eft", "tapping", "gamma", "linea de tiempo", "línea de tiempo", "pnl"),
    "bioenergetico": ("chakra", "meridiano", "qi", "yin", "yang", "bioener", "campo", "radionica", "radiónica"),
    "pares": ("par ", "pares ", "biomagnet", "holobiomagnet", "gauss"),
    "liberacion": ("liberacion", "liberación", "descarga", "desactivar", "reprogramar", "desarticular"),
    "sistemico": ("sistemic", "madre", "padre", "familiar", "ordenes del amor", "órdenes del amor"),
}

COURSE_BOOSTS: dict[str, dict[str, list[str]]] = {
    "curso-holobiomagnetismo-parte-1": {
        "systems": ["digestivo", "neurosensorial", "bioenergetico"],
        "tags": ["pares", "rastreo", "liberacion", "patogenos"],
    },
    "curso-holobiomagnetismo-parte-2": {
        "systems": ["emocional_mental", "neurosensorial", "bioenergetico"],
        "tags": ["pares", "rastreo", "eft", "liberacion", "transgeneracional"],
    },
    "diplomado-terapia-holistica-1": {
        "systems": ["digestivo", "respiratorio", "bioenergetico"],
        "tags": ["rastreo", "pares", "patogenos", "liberacion", "sistemico"],
    },
    "diplomado-sanacion-energetica-integral": {
        "systems": ["emocional_mental", "bioenergetico"],
        "tags": ["eft", "liberacion", "sistemico", "transgeneracional", "sentimental"],
    },
    "diplomado-ancestros-y-raices": {
        "systems": ["emocional_mental"],
        "tags": ["transgeneracional", "sistemico", "sentimental"],
    },
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    cleaned = no_accents.lower().replace("–", "-")
    return re.sub(r"\s+", " ", cleaned).strip()


def compact_text(text: str, limit: int = 420) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def split_label_and_body(item: str) -> tuple[str, str]:
    cleaned = " ".join((item or "").split()).strip("• ")
    if not cleaned or re.match(r"^\d+\)", cleaned):
        return "", ""
    for separator in (": ", " — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            if 2 <= len(left) <= 160:
                return left.strip(), right.strip()
    return cleaned.strip(), ""


def is_manual(source: dict) -> bool:
    title = normalize_text(source.get("source_title", ""))
    source_file = normalize_text(source.get("source_file", ""))
    course_id = source.get("course_id", "")
    if not (
        "/salud/" in source_file
        or course_id in THERAPY_DIPLOMA_IDS
        or "/diplomados/" in source_file
    ):
        return False
    return "manual" in title or "manual" in source_file


def detect_systems(blob: str, course_id: str) -> list[str]:
    found: list[str] = []
    for system_name, keywords in SYSTEM_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            found.append(system_name)
    found.extend(COURSE_BOOSTS.get(course_id, {}).get("systems", []))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def detect_tags(blob: str, course_id: str) -> list[str]:
    found: list[str] = []
    for tag_name, keywords in TAG_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            found.append(tag_name)
    found.extend(COURSE_BOOSTS.get(course_id, {}).get("tags", []))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def build_index() -> dict:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    manual_sources = [source for source in payload.get("source_studies", []) if is_manual(source)]

    manuals: list[dict] = []
    course_index: dict[str, list[str]] = defaultdict(list)
    system_index: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)

    for source in manual_sources:
        course_id = source["course_id"]
        source_file = source["source_file"]
        manual_id = f"{course_id}::{Path(source_file).stem}"
        blob_parts = [
            source.get("course_name", ""),
            source.get("source_title", ""),
            source.get("summary", ""),
            *source.get("key_points", []),
            *source.get("key_concepts", []),
            *source.get("protocols", []),
            *source.get("glossary", []),
        ]
        blob = normalize_text(" ".join(blob_parts))
        systems = detect_systems(blob, course_id)
        tags = detect_tags(blob, course_id)

        protocol_routes = []
        for item in source.get("protocols", []):
            title, body = split_label_and_body(item)
            if not title:
                continue
            protocol_routes.append(
                {
                    "title": title,
                    "body": compact_text(body, 520) if body else "",
                }
            )

        manual_entry = {
            "manual_id": manual_id,
            "course_id": course_id,
            "course_name": source["course_name"],
            "source_title": source["source_title"],
            "source_file": source_file,
            "summary": compact_text(source.get("summary", ""), 520),
            "key_points": source.get("key_points", [])[:6],
            "key_concepts": source.get("key_concepts", [])[:10],
            "glossary": source.get("glossary", [])[:10],
            "protocol_routes": protocol_routes[:8],
            "systems": systems,
            "tags": tags,
            "search_blob": blob,
        }
        manuals.append(manual_entry)
        course_index[course_id].append(manual_id)
        for system_name in systems:
            system_index[system_name].append(manual_id)
        for tag_name in tags:
            tag_index[tag_name].append(manual_id)

    return {
        "manual_count": len(manuals),
        "manuals": manuals,
        "course_index": course_index,
        "system_index": system_index,
        "tag_index": tag_index,
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado terapéutico por manual en {OUTPUT_PATH}")
    print(f"Manuales: {index['manual_count']}")
    print(f"Sistemas indexados: {len(index['system_index'])} | Tags indexados: {len(index['tag_index'])}")


if __name__ == "__main__":
    main()
