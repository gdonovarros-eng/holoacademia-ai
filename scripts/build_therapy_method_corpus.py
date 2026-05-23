from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_LIBRARY_DIR = BASE_DIR / "data" / "processed_library"
OUTPUT_JSON = BASE_DIR / "data" / "therapy_method_corpus.json"
OUTPUT_CSV = BASE_DIR / "data" / "therapy_method_corpus.csv"
OUTPUT_MD = BASE_DIR / "data" / "therapy_method_corpus.md"


TARGET_TRACKS = ("Salud", "Diplomados")


@dataclass(frozen=True)
class CategoryRule:
    category_id: str
    label: str
    description: str
    keywords: tuple[str, ...]
    strong_phrases: tuple[str, ...] = ()
    min_score: int = 4


CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        category_id="espacio_terapeutico",
        label="Espacio terapeutico",
        description="Como abrir la sesion y construir la atmosfera terapeutica.",
        keywords=(
            "espacio terapeutico",
            "atmosfera terapeutica",
            "consultante a expresar",
            "expresar lo mas profundo",
            "tres discursos",
            "escuchar los tres discursos",
        ),
        strong_phrases=(
            "la terapia no es la aplicacion rutinaria de metodos",
            "edificar el espacio terapeutico",
        ),
        min_score=6,
    ),
    CategoryRule(
        category_id="preguntas_base_del_sintoma",
        label="Preguntas base del sintoma",
        description="Preguntas objetivas para abrir el caso desde el sintoma.",
        keywords=(
            "caracteristicas del sintoma",
            "frecuencia",
            "fecha aproximada del origen",
            "estimulan o lo inhiben",
            "estimulan o inhiben",
            "preguntas objetivas",
            "motivo de consulta",
        ),
        strong_phrases=(
            "las preguntas correctas",
            "preguntar detalles",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="pistas_e_investigacion",
        label="Pistas e investigacion",
        description="Trabajo de investigacion, pistas y formulacion inicial de hipotesis.",
        keywords=(
            "pistas",
            "hacer preguntas clave",
            "labor de investigacion",
            "escarbarle",
            "version correcta",
            "preguntas correctas",
            "que preguntar",
        ),
        strong_phrases=(
            "simples preguntas me dan grandes pistas",
            "preguntas que yo tengo que hacer",
            "todas estas pistas",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="analisis_sistemico",
        label="Analisis sistemico",
        description="Fechas, relaciones y lectura sistemica del caso.",
        keywords=(
            "analisis sistemico",
            "fechas de nacimiento",
            "parejas significativas",
            "padre o madre de los hijos",
            "proyecto sentido",
            "fecha de concepcion",
            "doble gestacion",
        ),
        strong_phrases=(
            "lo primero que debes de hacer es el analisis sistemico",
            "simplemente con ver fechas",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="masa_conflictual",
        label="Masa conflictual",
        description="Reduccion del drama del paciente a un eje conflictual breve.",
        keywords=(
            "masa conflictual",
            "drama de su vida",
            "reducirse a una o dos frases",
            "historia dramatica repetitiva",
            "historia dramatica",
            "campo de distorsion",
        ),
        strong_phrases=(
            "nuestra tarea para ayudar a que el paciente se sane es encontrar la masa conflictual",
            "debe de poder reducirse a una o dos frases",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="decision_fisico_vs_emocional",
        label="Decision fisico vs emocional",
        description="Como decidir si abrir por microbios, biomagnetismo emocional o entrevista profunda.",
        keywords=(
            "microb",
            "biomagnetismo emocional",
            "emociones atrapadas",
            "cinco elementos",
            "eft pro",
            "si el paciente viene por algo fisico",
            "tema exclusivamente emocional",
            "primer rastreo es microbiano",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="rastreo_y_pares",
        label="Rastreo y pares",
        description="Uso del rastreo y los pares como validacion del caso.",
        keywords=(
            "rastreo",
            "pares biomagneticos",
            "par biomagnetico",
            "supraconsciente",
            "validarlo",
            "holobiomagnet",
        ),
        strong_phrases=(
            "vamos a hacer un rastreo",
            "pares a validar",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="liberacion_emocional",
        label="Liberacion emocional",
        description="Expresar, tomar conciencia y liberar la congestion emocional.",
        keywords=(
            "expresar su drama",
            "tomar conciencia",
            "liberar la congestion emocional",
            "liberar la congestión emocional",
            "frecuencias cerebrales",
            "relajarlo",
            "conectarlo con ese momento",
            "contarsela",
            "tapping",
            "eft pro",
        ),
        strong_phrases=(
            "expresaron su drama",
            "liberaron la congestion emocional involucrada",
        ),
        min_score=4,
    ),
    CategoryRule(
        category_id="protocolos_y_liberaciones",
        label="Protocolos y liberaciones",
        description="Como decidir la intervencion, protocolos y actos de liberacion.",
        keywords=(
            "flores de bach",
            "ruptura de lazos",
            "eft pro",
            "puentes energeticos",
            "acto psicomagico",
            "sepelio simbolico",
            "chakras",
        ),
        strong_phrases=(
            "ahora si aplica tus metodos",
            "esos son los pasos de la terapia",
        ),
        min_score=4,
    ),
)


METADATA_LINE_PATTERNS = (
    re.compile(r"^=+$"),
    re.compile(r"^(bloque|linea|línea|curso|modulo|m[oó]dulo|fecha de proceso)\s*:\s*", re.IGNORECASE),
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def compact_text(value: str, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


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


def parse_transcript_paragraphs(transcript_path: Path) -> list[dict[str, str]]:
    lines = transcript_path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").splitlines()
    paragraphs: list[dict[str, str]] = []
    current_block = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = re.sub(r"\s+", " ", " ".join(buffer)).strip()
        if text:
            paragraphs.append({"block": current_block, "text": text})
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


def score_paragraph(paragraph_text: str, rule: CategoryRule) -> tuple[int, list[str]]:
    text_norm = normalize_text(paragraph_text)
    matched: list[str] = []
    score = 0
    for phrase in rule.strong_phrases:
        if phrase in text_norm:
            score += 6
            matched.append(phrase)
    for keyword in rule.keywords:
        if keyword in text_norm:
            score += 2
            matched.append(keyword)
    return score, matched


def build_corpus() -> dict:
    transcripts = iter_transcripts()
    categories_payload: dict[str, dict] = {}
    flat_rows: list[dict[str, str | int]] = []

    for rule in CATEGORY_RULES:
        categories_payload[rule.category_id] = {
            "label": rule.label,
            "description": rule.description,
            "snippets": [],
        }

    for course_id, course_name, transcript_path in transcripts:
        paragraphs = parse_transcript_paragraphs(transcript_path)
        for index, paragraph in enumerate(paragraphs, start=1):
            paragraph_text = paragraph["text"]
            for rule in CATEGORY_RULES:
                score, matched_terms = score_paragraph(paragraph_text, rule)
                if score < rule.min_score:
                    continue
                snippet = {
                    "course_id": course_id,
                    "course_name": course_name,
                    "track": transcript_path.parts[-4],
                    "source_file": str(transcript_path),
                    "block": paragraph.get("block", ""),
                    "paragraph_index": index,
                    "score": score,
                    "matched_terms": sorted(set(matched_terms)),
                    "snippet": compact_text(paragraph_text, 950),
                }
                categories_payload[rule.category_id]["snippets"].append(snippet)
                flat_rows.append(
                    {
                        "category_id": rule.category_id,
                        "category_label": rule.label,
                        "course_id": course_id,
                        "course_name": course_name,
                        "track": transcript_path.parts[-4],
                        "block": paragraph.get("block", ""),
                        "paragraph_index": index,
                        "score": score,
                        "matched_terms": " | ".join(sorted(set(matched_terms))),
                        "source_file": str(transcript_path),
                        "snippet": compact_text(paragraph_text, 950),
                    }
                )

    for payload in categories_payload.values():
        payload["snippets"].sort(
            key=lambda item: (
                item["course_name"],
                -int(item["score"]),
                int(item["paragraph_index"]),
            )
        )

    course_summary: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for category_id, payload in categories_payload.items():
        for snippet in payload["snippets"]:
            course_summary[snippet["course_id"]][category_id].append(snippet)

    course_entries = []
    for course_id, category_map in sorted(course_summary.items()):
        first = next(iter(category_map.values()))[0]
        course_entries.append(
            {
                "course_id": course_id,
                "course_name": first["course_name"],
                "track": first["track"],
                "categories": {
                    category_id: {
                        "count": len(items),
                        "top_snippets": items[:8],
                    }
                    for category_id, items in sorted(category_map.items())
                },
            }
        )

    return {
        "transcript_count": len(transcripts),
        "category_count": len(CATEGORY_RULES),
        "categories": categories_payload,
        "courses": course_entries,
        "flat_rows": flat_rows,
    }


def write_outputs(corpus: dict) -> None:
    OUTPUT_JSON.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = sorted(
        corpus.get("flat_rows", []),
        key=lambda row: (
            str(row["category_label"]),
            -int(row["score"]),
            str(row["course_name"]),
            int(row["paragraph_index"]),
        ),
    )
    fieldnames = [
        "category_id",
        "category_label",
        "course_id",
        "course_name",
        "track",
        "block",
        "paragraph_index",
        "score",
        "matched_terms",
        "source_file",
        "snippet",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    markdown_lines = ["# Corpus terapéutico", ""]
    for rule in CATEGORY_RULES:
        category_payload = corpus["categories"][rule.category_id]
        markdown_lines.append(f"## {rule.label}")
        markdown_lines.append("")
        markdown_lines.append(rule.description)
        markdown_lines.append("")
        for snippet in sorted(
            category_payload["snippets"],
            key=lambda item: (-int(item["score"]), item["course_name"], int(item["paragraph_index"])),
        )[:12]:
            markdown_lines.append(
                f"- `{snippet['course_name']}` | score `{snippet['score']}` | bloque `{snippet['block'] or 'sin_bloque'}`"
            )
            markdown_lines.append(f"  {snippet['snippet']}")
        markdown_lines.append("")
    OUTPUT_MD.write_text("\n".join(markdown_lines), encoding="utf-8")


def main() -> None:
    corpus = build_corpus()
    write_outputs(corpus)
    print(f"Corpus terapéutico generado en {OUTPUT_JSON}")
    print(f"CSV de revisión generado en {OUTPUT_CSV}")
    print(f"Resumen Markdown generado en {OUTPUT_MD}")
    print(f"Transcripciones procesadas: {corpus['transcript_count']}")
    print(f"Fragmentos detectados: {len(corpus['flat_rows'])}")
    for rule in CATEGORY_RULES:
        count = len(corpus["categories"][rule.category_id]["snippets"])
        print(f"- {rule.label}: {count}")


if __name__ == "__main__":
    main()
