from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "course_reference_index.json"


def compact_text(text: str, limit: int = 420) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return no_accents.lower().replace("–", "-")


def split_faq_entry(item: str) -> tuple[str, str]:
    for separator in (" — ", " – ", " - "):
        if separator in item:
            left, right = item.split(separator, 1)
            return left.strip("¿? ").strip(), right.strip()
    return "", ""


def extract_defined_subject(question_text: str) -> str | None:
    lowered = normalize_text(question_text)
    patterns = [
        r"^(?:que|qué)\s+es\s+(.+)$",
        r"^(?:que|qué)\s+significa\s+(.+)$",
        r"^cual\s+es\s+la\s+diferencia\s+practica\s+entre\s+(.+)$",
        r"^cu[aá]l\s+es\s+la\s+diferencia\s+pr[aá]ctica\s+entre\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(r"\s+y\s+por\s+que.*$", "", candidate, flags=re.IGNORECASE).strip()
            candidate = re.sub(r"\s+y\s+por\s+qué.*$", "", candidate, flags=re.IGNORECASE).strip()
            candidate = re.sub(r"[?!.]+$", "", candidate).strip()
            return candidate
    return None


def split_label_and_body(item: str) -> tuple[str, str]:
    cleaned = " ".join((item or "").split()).strip("• ")
    if not cleaned:
        return "", ""
    for separator in (": ", " — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            if 2 <= len(left) <= 140:
                return left.strip(), right.strip()
    return cleaned.strip(), ""


def extract_parenthetical_descriptor(label: str) -> str:
    match = re.search(r"\(([^)]+)\)", label)
    return match.group(1).strip() if match else ""


def expand_label_aliases(label: str) -> list[str]:
    aliases = [label.strip()]
    base = re.sub(r"\([^)]*\)", "", label).strip(" ,")
    if base and base not in aliases:
        aliases.append(base)
    pending = list(aliases)
    expanded: list[str] = []
    while pending:
        current = pending.pop(0).strip(" ,")
        if not current:
            continue
        expanded.append(current)
        for separator in (",", " y ", "/"):
            if separator in current:
                pending.extend(part.strip() for part in current.split(separator) if part.strip())
    deduped: list[str] = []
    seen = set()
    for alias in expanded:
        normalized = normalize_text(alias)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(alias)
    return deduped


def build_index() -> dict:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    course_studies = payload.get("course_studies", [])
    source_studies = payload.get("source_studies", [])

    course_lookup = {course["course_id"]: course for course in course_studies}
    sources_by_course: dict[str, list[dict]] = defaultdict(list)
    for source in source_studies:
        sources_by_course[source["course_id"]].append(source)

    global_term_answers: dict[str, str] = {}
    global_protocol_answers: dict[str, str] = {}
    course_term_answers: dict[str, dict[str, str]] = defaultdict(dict)
    course_protocol_answers: dict[str, dict[str, str]] = defaultdict(dict)
    course_entries: list[dict] = []

    for course in course_studies:
        course_id = course["course_id"]
        course_name = course["course_name"]
        term_index: dict[str, str] = {}
        protocol_index: dict[str, str] = {}
        source_entries: list[dict] = []

        for question in course.get("common_questions", []):
            question_text, answer_text = split_faq_entry(question)
            if not question_text or not answer_text:
                continue
            subject = extract_defined_subject(question_text)
            if not subject:
                continue
            normalized_subject = normalize_text(subject)
            answer = f"{subject.strip().rstrip(':')} se entiende así: {compact_text(answer_text, 420)}"
            upsert_answer(term_index, normalized_subject, answer)
            upsert_answer(global_term_answers, normalized_subject, answer)

        for source in sources_by_course.get(course_id, []):
            source_record = {
                "source_title": source["source_title"],
                "source_file": source["source_file"],
                "summary": source["summary"],
                "concepts": [],
                "protocols": [],
                "glossary": source.get("glossary", []),
            }

            for item in source.get("key_concepts", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue
                descriptor = extract_parenthetical_descriptor(label)
                answer = (
                    f"{label} se entiende así: {compact_text(body, 360)}"
                    if body
                    else f"{label} es un concepto importante dentro de {course_name}."
                )
                source_record["concepts"].append({"term": label, "answer": answer})
                for alias in expand_label_aliases(label):
                    alias_answer = answer
                    if not body and normalize_text(alias) != normalize_text(label) and descriptor:
                        alias_answer = (
                            f"{alias} forma parte de las {descriptor} que se usan en {course_name} "
                            "como preparación o apoyo dentro del método."
                        )
                    normalized_alias = normalize_text(alias)
                    upsert_answer(term_index, normalized_alias, alias_answer)
                    upsert_answer(global_term_answers, normalized_alias, alias_answer)

            for item in source.get("glossary", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue
                answer = (
                    f"{label} se entiende así: {compact_text(body, 360)}"
                    if body
                    else f"{label} es un término importante dentro de {course_name}."
                )
                source_record["concepts"].append({"term": label, "answer": answer})
                for alias in expand_label_aliases(label):
                    normalized_alias = normalize_text(alias)
                    upsert_answer(term_index, normalized_alias, answer)
                    upsert_answer(global_term_answers, normalized_alias, answer)

            for item in source.get("protocols", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue
                answer = (
                    f"El protocolo {label} se trabaja así: {compact_text(body, 420)}"
                    if body
                    else f"El protocolo {label} forma parte de {course_name}."
                )
                source_record["protocols"].append({"term": label, "answer": answer})
                for alias in expand_label_aliases(label):
                    normalized_alias = normalize_text(alias)
                    upsert_answer(protocol_index, normalized_alias, answer)
                    upsert_answer(global_protocol_answers, normalized_alias, answer)

            source_entries.append(source_record)

        course_term_answers[course_id] = term_index
        course_protocol_answers[course_id] = protocol_index
        course_entries.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "linea": course.get("linea", ""),
                "tipo": course.get("tipo", ""),
                "source_count": len(source_entries),
                "sources": source_entries,
            }
        )

    return {
        "course_count": len(course_entries),
        "source_count": len(source_studies),
        "courses": course_entries,
        "global_term_answers": global_term_answers,
        "global_protocol_answers": global_protocol_answers,
        "course_term_answers": course_term_answers,
        "course_protocol_answers": course_protocol_answers,
    }


def answer_quality(answer: str) -> tuple[int, int]:
    lowered = answer.lower()
    generic_penalty = 0
    if "es un concepto importante dentro de" in lowered:
        generic_penalty += 3
    if "forma parte de las" in lowered:
        generic_penalty += 2
    if "se entiende asi" in normalize_text(answer):
        generic_penalty -= 1
    return (generic_penalty, -len(answer))


def upsert_answer(index: dict[str, str], key: str, answer: str) -> None:
    existing = index.get(key)
    if existing is None or answer_quality(answer) < answer_quality(existing):
        index[key] = answer


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado por formación en {OUTPUT_PATH}")
    print(f"Cursos: {index['course_count']} | Fuentes: {index['source_count']}")
    print(f"Términos globales: {len(index['global_term_answers'])} | Protocolos globales: {len(index['global_protocol_answers'])}")


if __name__ == "__main__":
    main()
