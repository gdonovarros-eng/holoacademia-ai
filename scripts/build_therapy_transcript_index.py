from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "therapy_transcript_index.json"
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
    "bioenergetico": ("chakra", "meridiano", "qi", "yin", "yang", "bioener", "campo"),
    "pares": ("par ", "pares ", "biomagnet", "holobiomagnet", "gauss"),
    "liberacion": ("liberacion", "liberación", "descarga", "desactivar", "reprogramar", "desarticular"),
    "sistemico": ("sistemic", "madre", "padre", "familiar", "ordenes del amor", "órdenes del amor"),
}

COURSE_BOOSTS: dict[str, dict[str, list[str]]] = {
    "curso-holobiomagnetismo-parte-1": {
        "systems": ["digestivo", "neurosensorial", "bioenergetico"],
        "tags": ["pares", "rastreo", "liberacion"],
    },
    "curso-holobiomagnetismo-parte-2": {
        "systems": ["emocional_mental", "neurosensorial", "bioenergetico"],
        "tags": ["pares", "rastreo", "eft", "liberacion", "transgeneracional"],
    },
    "curso-holobiomagnetismo-2021": {
        "systems": ["digestivo", "respiratorio", "bioenergetico"],
        "tags": ["pares", "rastreo", "patogenos", "liberacion"],
    },
    "curso-psicosomatica-y-biodescodificacion-1": {
        "systems": ["emocional_mental", "digestivo", "respiratorio"],
        "tags": ["rastreo", "sistemico", "liberacion"],
    },
    "curso-psicosomatica-y-biodescodificacion-2": {
        "systems": ["emocional_mental", "digestivo", "neurosensorial", "respiratorio"],
        "tags": ["rastreo", "eft", "liberacion", "sistemico"],
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
    "psicosomatrix": {
        "systems": ["emocional_mental"],
        "tags": ["rastreo", "liberacion", "sistemico"],
    },
    "medicina-energetica": {
        "systems": ["bioenergetico", "emocional_mental"],
        "tags": ["bioenergetico", "eft", "liberacion"],
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
    if not cleaned:
        return "", ""
    for separator in (": ", " — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            if 2 <= len(left) <= 160:
                return left.strip(), right.strip()
    return cleaned.strip(), ""


def is_transcript(source: dict) -> bool:
    title = source.get("source_title", "")
    source_file = source.get("source_file", "")
    course_id = source.get("course_id", "")
    title_norm = normalize_text(title)
    file_norm = normalize_text(source_file)
    if not (
        "/salud/" in file_norm
        or course_id in THERAPY_DIPLOMA_IDS
        or "/diplomados/" in file_norm
    ):
        return False
    return "transcrip" in title_norm or "transcrip" in file_norm or "memoria parcial de fragmentos" in title_norm


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
    transcript_sources = [source for source in payload.get("source_studies", []) if is_transcript(source)]

    transcripts: list[dict] = []
    course_index: dict[str, list[str]] = defaultdict(list)
    system_index: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)

    for source in transcript_sources:
        course_id = source["course_id"]
        source_file = source["source_file"]
        transcript_id = f"{course_id}::{Path(source_file).stem}"
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

        transcript_entry = {
            "transcript_id": transcript_id,
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
        transcripts.append(transcript_entry)
        course_index[course_id].append(transcript_id)
        for system_name in systems:
            system_index[system_name].append(transcript_id)
        for tag_name in tags:
            tag_index[tag_name].append(transcript_id)

    return {
        "transcript_count": len(transcripts),
        "transcripts": transcripts,
        "course_index": course_index,
        "system_index": system_index,
        "tag_index": tag_index,
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado terapéutico por transcripción en {OUTPUT_PATH}")
    print(f"Transcripciones: {index['transcript_count']}")
    print(f"Sistemas indexados: {len(index['system_index'])} | Tags indexados: {len(index['tag_index'])}")


if __name__ == "__main__":
    main()
