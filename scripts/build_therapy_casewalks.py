from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_LIBRARY_DIR = BASE_DIR / "data" / "processed_library"
OUTPUT_JSON = BASE_DIR / "data" / "therapy_casewalks.json"
OUTPUT_CSV = BASE_DIR / "data" / "therapy_casewalks.csv"
OUTPUT_MD = BASE_DIR / "data" / "therapy_casewalks.md"

TARGET_TRACKS = ("Salud", "Diplomados")


STAGE_RULES = {
    "setup": (
        "version acelerada de como yo doy las consultas",
        "yo en mis consultas",
        "esta es una terapia presencial",
        "vamos a pasar gente al frente",
        "mecanica como hago yo las sesiones",
        "papelitos",
    ),
    "intake": (
        "motivo de consulta",
        "caracteristicas del sintoma",
        "fecha aproximada de origen",
        "parejas significativas",
        "cuentame de tu",
        "que paso",
        "te hace sentido",
    ),
    "systemic_analysis": (
        "analisis sistemico",
        "simplemente con ver fechas",
        "fechas que mas se repiten",
        "cuentame de tu mama",
        "cuentame de tu papa",
        "proyecto sentido",
        "talon de aquiles",
    ),
    "conflict_synthesis": (
        "masa conflictual",
        "drama de tu vida",
        "reducirse a una o dos frases",
        "tu verdadero motivo de consulta",
        "lo que tu vienes a trabajar",
        "el drama de tu vida es",
    ),
    "intervention": (
        "eft pro",
        "toma tres respiraciones",
        "cierra tus ojos",
        "aunque sientes",
        "golpecitos",
        "liberar la emocion",
        "procedimiento",
        "digitopuntura",
        "puentes energeticos",
    ),
    "tasks_and_closure": (
        "las tareas",
        "descansas dos o tres dias",
        "sepelio simbolico",
        "acto psicomagico",
        "romper el pacto",
        "un aplauso para",
        "te lo voy a mandar a tu correo",
    ),
}

STAGE_ORDER = [
    "setup",
    "intake",
    "systemic_analysis",
    "conflict_synthesis",
    "intervention",
    "tasks_and_closure",
]

STAGE_LABELS = {
    "setup": "Apertura del espacio terapéutico",
    "intake": "Entrevista y toma de datos",
    "systemic_analysis": "Análisis sistémico",
    "conflict_synthesis": "Síntesis del conflicto",
    "intervention": "Intervención o liberación",
    "tasks_and_closure": "Tareas y cierre",
}

REAL_CASE_MARKERS = (
    "te hace sentido",
    "que recuerdas",
    "qué recuerdas",
    "cuentame",
    "cuéntame",
    "cuando empezo",
    "cuándo empezó",
    "cuando comenzo",
    "qué paso",
    "que paso",
    "tu mama",
    "tu papa",
    "tu hijo",
    "tu pareja",
    "tu paciente",
    "las tareas",
    "descansas dos o tres dias",
    "te lo voy a mandar",
)

THEORY_MARKERS = (
    "voy a comenzar con teoria",
    "ahorita termino de teoria",
    "curso pasado",
    "a lo largo de los ultimos cuatro cursos",
    "chakras",
    "meridianos",
    "teoria astrologica",
    "nodo norte",
    "nodo sur",
    "esto se lo decimos por telefono",
    "esta es una terapia presencial",
    "version acelerada de como yo doy las consultas",
)

METADATA_LINE_PATTERNS = (
    re.compile(r"^=+$"),
    re.compile(r"^(bloque|linea|línea|curso|modulo|m[oó]dulo|fecha de proceso)\s*:\s*", re.IGNORECASE),
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def compact_text(value: str, limit: int = 1100) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def first_sentence(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return parts[0].strip()


def load_manifest_name(manifest_path: Path) -> str:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return manifest_path.parent.name
    return str(payload.get("course_name") or manifest_path.parent.name).strip()


def iter_transcripts() -> list[tuple[str, str, Path]]:
    entries: list[tuple[str, str, Path]] = []
    for track in TARGET_TRACKS:
        for manifest_path in sorted((PROCESSED_LIBRARY_DIR / track).glob("*/course_manifest.json")):
            course_id = manifest_path.parent.name
            course_name = load_manifest_name(manifest_path)
            transcript_path = manifest_path.parent / "sources" / "transcripcion_completa.txt"
            if transcript_path.exists():
                entries.append((course_id, course_name, transcript_path))
    return entries


def parse_transcript_paragraphs(transcript_path: Path) -> list[dict[str, str | int]]:
    lines = transcript_path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").splitlines()
    paragraphs: list[dict[str, str | int]] = []
    current_block = ""
    buffer: list[str] = []
    index = 0

    def flush() -> None:
        nonlocal buffer, index
        text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
        if text:
            index += 1
            paragraphs.append({"block": current_block, "text": text, "index": index})
        buffer = []

    for raw_line in lines:
        line = raw_line.strip()
        if raw_line.startswith("BLOQUE:"):
            flush()
            current_block = raw_line.split(":", 1)[1].strip()
            continue
        if any(pattern.match(line) for pattern in METADATA_LINE_PATTERNS):
            flush()
            continue
        if not line:
            flush()
            continue
        buffer.append(line)
    flush()
    return paragraphs


def detect_stage_hits(text: str) -> dict[str, int]:
    normalized = normalize_text(text)
    hits: dict[str, int] = {}
    for stage, phrases in STAGE_RULES.items():
        count = sum(1 for phrase in phrases if phrase in normalized)
        if count:
            hits[stage] = count
    return hits


def merge_segments(paragraphs: list[dict[str, str | int]]) -> list[list[dict[str, str | int]]]:
    candidates = []
    for paragraph in paragraphs:
        hits = detect_stage_hits(str(paragraph["text"]))
        if not hits:
            continue
        candidates.append({**paragraph, "stage_hits": hits, "score": sum(hits.values())})

    if not candidates:
        return []

    segments: list[list[dict[str, str | int]]] = []
    current = [candidates[0]]
    for paragraph in candidates[1:]:
        previous = current[-1]
        same_block = paragraph.get("block") == previous.get("block")
        close_enough = int(paragraph["index"]) - int(previous["index"]) <= 3
        if same_block and close_enough:
            current.append(paragraph)
            continue
        segments.append(current)
        current = [paragraph]
    segments.append(current)
    return segments


def _real_case_bonus(text: str) -> int:
    normalized = normalize_text(text)
    bonus = sum(2 for marker in REAL_CASE_MARKERS if marker in normalized)
    question_bonus = min(text.count("?"), 4)
    if any(token in normalized for token in ("tu ", "tus ", "te ", "recuerdas", "sentias", "sentías")):
        bonus += 2
    return bonus + question_bonus


def _theory_penalty(text: str) -> int:
    normalized = normalize_text(text)
    penalty = sum(3 for marker in THEORY_MARKERS if marker in normalized)
    if "setup" in normalized and len(normalized) > 1000:
        penalty += 2
    return penalty


def _stage_snippets(segment: list[dict[str, str | int]]) -> list[dict[str, str]]:
    stage_parts: dict[str, list[str]] = defaultdict(list)
    for item in segment:
        for stage in dict(item["stage_hits"]).keys():
            stage_parts[stage].append(str(item["text"]))

    snippets: list[dict[str, str]] = []
    for stage in STAGE_ORDER:
        parts = stage_parts.get(stage) or []
        if not parts:
            continue
        unique_parts: list[str] = []
        seen: set[str] = set()
        for part in parts:
            key = normalize_text(part)
            if not key or key in seen:
                continue
            seen.add(key)
            unique_parts.append(part)
        text = " ".join(unique_parts)
        snippets.append(
            {
                "stage_id": stage,
                "label": STAGE_LABELS[stage],
                "snippet": compact_text(text, 680),
            }
        )
    return snippets


def classify_segment(segment: list[dict[str, str | int]]) -> dict[str, object]:
    stage_counts: dict[str, int] = defaultdict(int)
    score = 0
    text_parts: list[str] = []
    for item in segment:
        text_parts.append(str(item["text"]))
        score += int(item["score"])
        for stage, count in dict(item["stage_hits"]).items():
            stage_counts[stage] += int(count)

    ordered_stages = [stage for stage in STAGE_ORDER if stage in stage_counts]
    joined_text = " ".join(text_parts)
    score += _real_case_bonus(joined_text)
    score -= _theory_penalty(joined_text)
    if "intake" in stage_counts and "conflict_synthesis" in stage_counts:
        score += 4
    if "intervention" in stage_counts and "tasks_and_closure" in stage_counts:
        score += 4
    return {
        "score": score,
        "stages": ordered_stages,
        "stage_counts": dict(stage_counts),
        "text": joined_text,
        "stage_snippets": _stage_snippets(segment),
    }


def _looks_like_casewalk(classified: dict[str, object]) -> bool:
    score = int(classified["score"])
    stages = list(classified["stages"])
    text = str(classified["text"])
    normalized = normalize_text(text)

    if score < 12:
        return False
    if "intake" not in stages:
        return False
    if not any(stage in stages for stage in ("conflict_synthesis", "intervention", "tasks_and_closure")):
        return False
    if len(stages) < 3:
        return False
    if _theory_penalty(text) >= _real_case_bonus(text) + 4:
        return False
    if "setup" in stages and stages[:2] == ["setup", "intake"] and len(stages) == 3 and "intervention" not in stages:
        return False
    if len(normalized) < 500:
        return False
    return True


def _learning_value(classified: dict[str, object]) -> str:
    stages = list(classified["stages"])
    if "intervention" in stages and "tasks_and_closure" in stages:
        return "Muestra el recorrido casi completo: entrevista, hipótesis, intervención y cierre."
    if "conflict_synthesis" in stages and "intervention" in stages:
        return "Ayuda a ver cómo el terapeuta pasa de pistas a conflicto dominante y luego a intervención."
    if "systemic_analysis" in stages and "conflict_synthesis" in stages:
        return "Sirve para aprender cómo se cruzan fechas, vínculos y relato para delimitar el conflicto."
    return "Aporta un tramo útil del método clínico paso a paso."


def build_casewalks() -> dict:
    casewalks: list[dict[str, object]] = []
    flat_rows: list[dict[str, object]] = []

    for course_id, course_name, transcript_path in iter_transcripts():
        paragraphs = parse_transcript_paragraphs(transcript_path)
        for segment_index, segment in enumerate(merge_segments(paragraphs), start=1):
            classified = classify_segment(segment)
            if not _looks_like_casewalk(classified):
                continue
            casewalk = {
                "casewalk_id": f"{course_id}::{segment_index:03d}",
                "course_id": course_id,
                "course_name": course_name,
                "track": transcript_path.parts[-4],
                "source_file": str(transcript_path),
                "block": str(segment[0].get("block", "")),
                "paragraph_start": int(segment[0]["index"]),
                "paragraph_end": int(segment[-1]["index"]),
                "score": int(classified["score"]),
                "stages": list(classified["stages"]),
                "stage_counts": dict(classified["stage_counts"]),
                "learning_value": _learning_value(classified),
                "stage_snippets": list(classified["stage_snippets"]),
                "snippet": compact_text(str(classified["text"]), 2200),
            }
            casewalks.append(casewalk)

            for stage in casewalk["stages"]:
                flat_rows.append(
                    {
                        "casewalk_id": casewalk["casewalk_id"],
                        "course_id": course_id,
                        "course_name": course_name,
                        "track": transcript_path.parts[-4],
                        "block": casewalk["block"],
                        "score": casewalk["score"],
                        "stage": stage,
                        "paragraph_start": casewalk["paragraph_start"],
                        "paragraph_end": casewalk["paragraph_end"],
                        "source_file": str(transcript_path),
                        "snippet": casewalk["snippet"],
                    }
                )

    casewalks.sort(key=lambda item: (-int(item["score"]), str(item["course_name"]), int(item["paragraph_start"])))

    grouped_by_course: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in casewalks:
        grouped_by_course[str(item["course_id"])].append(item)

    courses = []
    for course_id, items in sorted(grouped_by_course.items()):
        first = items[0]
        courses.append(
            {
                "course_id": course_id,
                "course_name": first["course_name"],
                "track": first["track"],
                "casewalk_count": len(items),
                "top_casewalks": items[:6],
            }
        )

    return {
        "casewalk_count": len(casewalks),
        "courses": courses,
        "casewalks": casewalks,
        "flat_rows": flat_rows,
    }


def write_outputs(payload: dict) -> None:
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = sorted(
        payload["flat_rows"],
        key=lambda item: (
            str(item["course_name"]),
            -int(item["score"]),
            str(item["stage"]),
            int(item["paragraph_start"]),
        ),
    )
    fieldnames = [
        "casewalk_id",
        "course_id",
        "course_name",
        "track",
        "block",
        "score",
        "stage",
        "paragraph_start",
        "paragraph_end",
        "source_file",
        "snippet",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    markdown_lines = ["# Casos guía del método terapéutico", ""]
    for course in payload["courses"]:
        markdown_lines.append(f"## {course['course_name']}")
        markdown_lines.append("")
        for item in course["top_casewalks"]:
            markdown_lines.append(
                f"- `score {item['score']}` | etapas `{', '.join(item['stages'])}` | bloque `{item['block'] or 'sin_bloque'}`"
            )
            markdown_lines.append(f"  {item['learning_value']}")
            for stage in item.get("stage_snippets", []):
                markdown_lines.append(f"  - **{stage['label']}**: {stage['snippet']}")
            markdown_lines.append(f"  - **Vista compacta**: {item['snippet']}")
        markdown_lines.append("")
    OUTPUT_MD.write_text("\n".join(markdown_lines), encoding="utf-8")


def main() -> None:
    payload = build_casewalks()
    write_outputs(payload)
    print(f"Casos guía generados en {OUTPUT_JSON}")
    print(f"CSV generado en {OUTPUT_CSV}")
    print(f"Markdown generado en {OUTPUT_MD}")
    print(f"Casewalks detectados: {payload['casewalk_count']}")


if __name__ == "__main__":
    main()
