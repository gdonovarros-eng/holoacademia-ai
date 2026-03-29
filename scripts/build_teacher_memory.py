from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
LIBRARY_ROOT = BASE_DIR / "data" / "processed_library"
OUTPUT_PATH = BASE_DIR / "data" / "teacher_memory.json"
PARTIAL_PATH = BASE_DIR / "data" / "teacher_memory.partial.json"
MAX_SOURCE_CHARS = 12000
MAX_SUMMARY_CHARS = 520
MAX_ITEM_CHARS = 180
MAX_GLOSSARY_ITEM_CHARS = 120


SOURCE_SCHEMA = {
    "name": "teacher_source_digest",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "source_title": {"type": "string", "maxLength": 180},
            "summary": {"type": "string", "maxLength": MAX_SUMMARY_CHARS},
            "key_points": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 6,
            },
            "key_concepts": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 10,
            },
            "protocols": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 8,
            },
            "glossary": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_GLOSSARY_ITEM_CHARS},
                "maxItems": 8,
            },
        },
        "required": [
            "source_title",
            "summary",
            "key_points",
            "key_concepts",
            "protocols",
            "glossary",
        ],
        "additionalProperties": False,
    },
}


CHUNK_SCHEMA = {
    "name": "teacher_chunk_digest",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "maxLength": 360},
            "key_points": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 5,
            },
            "key_concepts": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 8,
            },
            "protocols": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 6,
            },
            "glossary": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_GLOSSARY_ITEM_CHARS},
                "maxItems": 6,
            },
        },
        "required": [
            "summary",
            "key_points",
            "key_concepts",
            "protocols",
            "glossary",
        ],
        "additionalProperties": False,
    },
}


COURSE_SCHEMA = {
    "name": "teacher_course_digest",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "maxLength": 700},
            "teacher_summary": {"type": "string", "maxLength": 950},
            "core_themes": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 8,
            },
            "key_concepts": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 12,
            },
            "protocols": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 10,
            },
            "study_guide": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 6,
            },
            "common_questions": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_ITEM_CHARS},
                "maxItems": 8,
            },
        },
        "required": [
            "summary",
            "teacher_summary",
            "core_themes",
            "key_concepts",
            "protocols",
            "study_guide",
            "common_questions",
        ],
        "additionalProperties": False,
    },
}


def load_client() -> OpenAI:
    if load_dotenv is not None:
        load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en el entorno o en .env")
    return OpenAI(api_key=api_key)


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini")


def list_courses() -> list[dict]:
    manifests = sorted(LIBRARY_ROOT.rglob("course_manifest.json"))
    courses = []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sources_dir = manifest_path.parent / "sources"
        sources = []
        for txt_path in sorted(sources_dir.glob("*.txt")):
            normalized_name = txt_path.stem.lower()
            if "index_modulos" in normalized_name:
                continue
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            prepared_text = prepare_source_text(txt_path.name, text)
            sources.append(
                {
                    "source_file": str(txt_path),
                    "source_title": txt_path.stem,
                    "source_type": classify_source_type(txt_path.name),
                    "text": prepared_text,
                }
            )
        sources.sort(key=lambda item: source_priority(item["source_type"], item["source_title"]))
        courses.append(
            {
                "course_id": manifest["course_id"],
                "course_name": manifest["course_name"],
                "linea": manifest.get("linea", ""),
                "tipo": manifest.get("tipo", ""),
                "sources": sources,
                "total_chars": sum(len(source["text"]) for source in sources),
            }
        )
    courses.sort(key=lambda item: (item["total_chars"], len(item["sources"]), item["course_name"]))
    return courses


def classify_source_type(filename: str) -> str:
    lowered = filename.lower()
    if "transcripcion" in lowered:
        return "transcript"
    if "manual" in lowered:
        return "manual"
    if "protocolo" in lowered:
        return "protocol"
    return "reference"


def source_priority(source_type: str, source_title: str) -> tuple[int, int, str]:
    priority = {
        "manual": 0,
        "protocol": 1,
        "reference": 2,
        "transcript": 3,
    }.get(source_type, 4)
    return (priority, len(source_title), source_title.lower())


def prepare_source_text(filename: str, text: str) -> str:
    normalized_name = filename.lower()
    cleaned = text.replace("\f", "\n")
    if "transcripcion_completa" not in normalized_name:
        return cleaned

    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]
    selected: list[str] = []

    # Keep a short intro because many transcripts explain the framework early.
    intro_lines = [line for line in lines[:220] if line]
    selected.extend(intro_lines)

    # Keep the first strong didactic paragraphs, bullets, definitions and protocols.
    for line in lines:
        if not line:
            continue
        lower = line.lower()
        if any(
            marker in lower
            for marker in [
                "¿qué es",
                "que es",
                "definicion",
                "definición",
                "protocolo",
                "chakra",
                "conflicto",
                "sintoma",
                "síntoma",
                "mente subconsciente",
                "campo de distorsion",
                "campo de distorsión",
                "masa conflictual",
                "puente energetico",
                "puente energético",
            ]
        ):
            selected.append(line)

    compact = "\n".join(dict.fromkeys(selected))
    compact = compact[:25000]
    return compact if compact.strip() else cleaned[:25000]


def chunk_text(text: str, max_chars: int = MAX_SOURCE_CHARS) -> list[str]:
    clean = re.sub(r"\s+", " ", text.replace("\f", "\n")).strip()
    if len(clean) <= max_chars:
        return [clean]

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            split = clean.rfind(". ", start, end)
            if split > start + 2000:
                end = split + 1
        chunks.append(clean[start:end].strip())
        start = end
    return chunks


def compact_text(text: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip(" ,.;:") + "…"


def compact_list(items: list[str], max_items: int, max_chars: int) -> list[str]:
    result: list[str] = []
    seen = set()
    for item in items:
        clean = compact_text(item, max_chars)
        key = clean.lower()
        if not clean or key in seen:
            continue
        seen.add(key)
        result.append(clean)
        if len(result) >= max_items:
            break
    return result


def compact_digest(digest: dict, include_title: bool = False) -> dict:
    compact = {}
    if include_title:
        compact["source_title"] = compact_text(digest.get("source_title", ""), 180)
    compact["summary"] = compact_text(digest.get("summary", ""), MAX_SUMMARY_CHARS)
    compact["key_points"] = compact_list(digest.get("key_points", []), 6, MAX_ITEM_CHARS)
    compact["key_concepts"] = compact_list(digest.get("key_concepts", []), 10, MAX_ITEM_CHARS)
    compact["protocols"] = compact_list(digest.get("protocols", []), 8, MAX_ITEM_CHARS)
    compact["glossary"] = compact_list(digest.get("glossary", []), 8, MAX_GLOSSARY_ITEM_CHARS)
    return compact


def call_schema(client: OpenAI, instructions: str, prompt: str, schema: dict) -> dict:
    last_error = None
    for max_tokens in (1200, 1800, 2600, 3600):
        response = client.responses.create(
            model=get_model(),
            instructions=instructions,
            input=prompt,
            timeout=60,
            max_output_tokens=max_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "schema": schema["schema"],
                    "strict": schema["strict"],
                }
            },
        )
        try:
            return json.loads(response.output_text)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"No se pudo parsear la salida estructurada del modelo: {last_error}")


def summarize_source(client: OpenAI, course_name: str, source_title: str, text: str) -> dict:
    chunks = chunk_text(text)
    instructions = (
        "Eres un editor academico que estudia materiales de una escuela y los convierte en memoria pedagógica. "
        "No copies frases largas del material. Sintetiza, ordena y limpia OCR. "
        "Piensa como un maestro que despues tendrá que orientar alumnos con claridad. "
        "El resumen debe ser compacto, didactico y util para enseñar, no enciclopedico. "
        "La summary debe caber idealmente en un solo parrafo breve. "
        "Cada bullet debe ser breve y concreto. "
        "Devuelve solo el JSON pedido."
    )

    if len(chunks) == 1:
        prompt = (
            f"Curso: {course_name}\n"
            f"Fuente: {source_title}\n\n"
            "Limites de salida: resumen <= 520 caracteres; bullets breves.\n\n"
            f"Contenido:\n{chunks[0]}"
        )
        return compact_digest(call_schema(client, instructions, prompt, SOURCE_SCHEMA), include_title=True)

    chunk_digests = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = (
            f"Curso: {course_name}\n"
            f"Fuente: {source_title}\n"
            f"Fragmento: {index}/{len(chunks)}\n\n"
            "Limites de salida: resumen <= 360 caracteres; bullets breves.\n\n"
            f"Contenido:\n{chunk}"
        )
        digest = compact_digest(call_schema(client, instructions, prompt, CHUNK_SCHEMA))
        chunk_digests.append(digest)

    reduce_prompt = (
        f"Curso: {course_name}\n"
        f"Fuente: {source_title}\n\n"
        "Memoria parcial de fragmentos:\n\n"
        + "\n\n".join(
            "\n".join(
                [
                    f"[Fragmento {index}]",
                    f"Resumen: {compact_text(item['summary'], 320)}",
                    f"Puntos clave: {'; '.join(compact_list(item['key_points'][:6], 4, 100))}",
                    f"Conceptos: {'; '.join(compact_list(item['key_concepts'][:10], 6, 100))}",
                    f"Protocolos: {'; '.join(compact_list(item['protocols'][:8], 4, 100))}",
                    f"Glosario: {'; '.join(compact_list(item['glossary'][:8], 4, 80))}",
                ]
            )
            for index, item in enumerate(chunk_digests, start=1)
        )
    )
    return compact_digest(call_schema(client, instructions, reduce_prompt, SOURCE_SCHEMA), include_title=True)


def summarize_course(client: OpenAI, course: dict, source_digests: list[dict]) -> dict:
    compact_sources = []
    for item in source_digests:
        compact_sources.append(
            "\n".join(
                [
                    f"Fuente: {item['source_title']}",
                    f"Resumen: {item['summary']}",
                    f"Puntos clave: {'; '.join(item['key_points'][:6])}",
                    f"Conceptos: {'; '.join(item['key_concepts'][:10])}",
                    f"Protocolos: {'; '.join(item['protocols'][:8])}",
                ]
            )
        )

    prompt = (
        f"Curso: {course['course_name']}\n"
        f"Línea: {course['linea']}\n"
        f"Tipo: {course['tipo']}\n\n"
        "Memoria previa de las fuentes:\n\n"
        + "\n\n".join(compact_sources)
    )
    instructions = (
        "Eres un sinodal y maestro senior. Tu trabajo es estudiar un curso completo y producir la memoria pedagógica "
        "que luego usará un asistente para orientar alumnos. No respondas como buscador. "
        "Entrega una síntesis madura, didáctica y útil para enseñanza. "
        "La teacher_summary debe sonar como un maestro explicando el corazón del curso en uno o dos parrafos, no como un volcado de apuntes. "
        "No hagas listados interminables: prioriza lo esencial."
    )
    course_digest = call_schema(client, instructions, prompt, COURSE_SCHEMA)
    course_digest["summary"] = compact_text(course_digest.get("summary", ""), 700)
    course_digest["teacher_summary"] = compact_text(course_digest.get("teacher_summary", ""), 950)
    course_digest["core_themes"] = compact_list(course_digest.get("core_themes", []), 8, MAX_ITEM_CHARS)
    course_digest["key_concepts"] = compact_list(course_digest.get("key_concepts", []), 12, MAX_ITEM_CHARS)
    course_digest["protocols"] = compact_list(course_digest.get("protocols", []), 10, MAX_ITEM_CHARS)
    course_digest["study_guide"] = compact_list(course_digest.get("study_guide", []), 6, MAX_ITEM_CHARS)
    course_digest["common_questions"] = compact_list(course_digest.get("common_questions", []), 8, MAX_ITEM_CHARS)
    return course_digest


def load_partial_state() -> dict:
    if not PARTIAL_PATH.exists():
        return {"metadata": {}, "course_studies": [], "source_studies": []}
    try:
        payload = json.loads(PARTIAL_PATH.read_text(encoding="utf-8"))
        payload.setdefault("metadata", {})
        payload.setdefault("course_studies", [])
        payload.setdefault("source_studies", [])
        return payload
    except Exception:
        return {"metadata": {}, "course_studies": [], "source_studies": []}


def save_partial_state(course_studies: list[dict], source_studies: list[dict], total_courses: int) -> None:
    payload = {
        "metadata": {
            "model": get_model(),
            "course_count_target": total_courses,
            "course_count_partial": len(course_studies),
            "source_count_partial": len(source_studies),
        },
        "course_studies": course_studies,
        "source_studies": source_studies,
    }
    PARTIAL_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_teacher_memory() -> dict:
    client = load_client()
    courses = list_courses()
    partial = load_partial_state()
    source_index = {item["source_file"]: item for item in partial.get("source_studies", [])}
    course_index = {item["course_id"]: item for item in partial.get("course_studies", [])}

    course_studies = list(course_index.values())
    source_studies = list(source_index.values())

    for course in courses:
        if course["course_id"] in course_index:
            continue

        digests = []
        for source in course["sources"]:
            digest = source_index.get(source["source_file"])
            if digest is None:
                digest = summarize_source(
                    client=client,
                    course_name=course["course_name"],
                    source_title=source["source_title"],
                    text=source["text"],
                )
                digest["course_id"] = course["course_id"]
                digest["course_name"] = course["course_name"]
                digest["source_file"] = source["source_file"]
                source_index[source["source_file"]] = digest
                source_studies = list(source_index.values())
                save_partial_state(course_studies, source_studies, len(courses))
            digests.append(digest)

        course_digest = summarize_course(client, course, digests)
        course_digest["course_id"] = course["course_id"]
        course_digest["course_name"] = course["course_name"]
        course_digest["linea"] = course["linea"]
        course_digest["tipo"] = course["tipo"]
        course_index[course["course_id"]] = course_digest
        course_studies = list(course_index.values())
        save_partial_state(course_studies, source_studies, len(courses))

    return {
        "metadata": {
            "model": get_model(),
            "course_count": len(course_studies),
            "source_count": len(source_studies),
        },
        "course_studies": course_studies,
        "source_studies": source_studies,
    }


def main() -> None:
    payload = build_teacher_memory()
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if PARTIAL_PATH.exists():
        PARTIAL_PATH.unlink()
    print(f"Teacher memory generated at {OUTPUT_PATH}")
    print(
        json.dumps(
            payload["metadata"],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
