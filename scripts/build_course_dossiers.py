from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "course_dossiers.json"


def normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return no_accents.lower().replace("–", "-").replace("—", "-")


def compact_text(text: str, limit: int = 420) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip(" ,;:") + "…"


def split_label_and_body(item: str) -> tuple[str, str]:
    cleaned = " ".join((item or "").split()).strip("• ")
    if not cleaned:
        return "", ""
    if re.match(r"^\d+\)", cleaned):
        return "", ""
    for separator in (": ", " — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            if 2 <= len(left) <= 140:
                return left.strip(), right.strip()
    return cleaned.strip(), ""


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
        for separator in (" y ", "/", ","):
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


def quality_score(answer: str) -> tuple[int, int]:
    lowered = normalize_text(answer)
    generic_penalty = 0
    if "es un concepto importante dentro de" in lowered:
        generic_penalty += 5
    if "forma parte de" in lowered:
        generic_penalty += 3
    if "se entiende asi" in lowered or "se entiende así" in lowered:
        generic_penalty -= 2
    if "dicho de forma practica" in lowered or "dicho de forma práctica" in lowered:
        generic_penalty -= 1
    return (generic_penalty, -len(answer))


def upsert(index: dict[str, dict], key: str, payload: dict) -> None:
    existing = index.get(key)
    if existing is None or quality_score(payload["answer"]) < quality_score(existing["answer"]):
        index[key] = payload


def clean_summary_seed(text: str) -> str:
    cleaned = " ".join((text or "").split())
    cleaned = re.sub(
        r"^(como\s+(?:docente|maestro|facilitador)\s*(?:diria|diría)?[:,]?\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^este\s+(?:curso|diplomado|taller)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^te\s+diria\s+que\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^te\s+diría\s+que\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(el\s+corazon|el\s+corazón)\s+del\s+(?:curso|diplomado|taller)\s+es\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned
    return compact_text(cleaned, 420)


def strip_course_type_prefix(course_name: str) -> str:
    cleaned = re.sub(r"^(Diplomado|Curso|Taller)\s+", "", course_name, flags=re.IGNORECASE).strip()
    return cleaned or course_name


def extract_parenthetical_aliases(text: str) -> list[str]:
    aliases: list[str] = []
    for match in re.findall(r"\(([^)]+)\)", text or ""):
        candidate = match.strip()
        if 2 <= len(candidate) <= 40:
            aliases.append(candidate)
    return aliases


def build_fallback_term_answer(
    alias: str,
    course_name: str,
    teacher_summary: str,
    source_summary: str,
    themes: list[str],
) -> str:
    summary_seed = source_summary or teacher_summary
    summary_seed = clean_summary_seed(summary_seed)
    theme_hint = ""
    if themes:
        theme_hint = f" En la práctica se relaciona con {', '.join(themes[:2])}."
    return (
        f"{alias} dentro de {course_name} se trabaja como {summary_seed}{theme_hint}"
    )


def build_fallback_protocol_answer(
    label: str,
    course_name: str,
    source_summary: str,
) -> str:
    summary_seed = clean_summary_seed(source_summary)
    return f"El protocolo {label} dentro de {course_name} se usa así: {summary_seed}"


def build_index() -> dict:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    courses = payload.get("course_studies", [])
    sources = payload.get("source_studies", [])
    sources_by_course: dict[str, list[dict]] = defaultdict(list)
    for source in sources:
        sources_by_course[source["course_id"]].append(source)

    dossiers: list[dict] = []
    global_term_answers: dict[str, dict] = {}
    global_protocol_answers: dict[str, dict] = {}

    for course in courses:
        course_id = course["course_id"]
        course_name = course["course_name"]
        teacher_summary = course.get("teacher_summary", "") or course.get("summary", "")
        course_summary = course.get("summary", "")
        themes = course.get("core_themes", [])[:6]
        course_term_answers: dict[str, dict] = {}
        course_protocol_answers: dict[str, dict] = {}

        for faq in course.get("common_questions", []):
            if " — " not in faq and " - " not in faq and " – " not in faq:
                continue
            left, right = "", ""
            for sep in (" — ", " - ", " – "):
                if sep in faq:
                    left, right = faq.split(sep, 1)
                    break
            left = left.strip("¿? ").strip()
            right = right.strip()
            if not left or not right:
                continue
            subject = None
            lowered = normalize_text(left)
            for pattern in (
                r"^(?:que|qué)\s+es\s+(.+)$",
                r"^(?:que|qué)\s+significa\s+(.+)$",
                r"^cual\s+es\s+la\s+diferencia\s+practica\s+entre\s+(.+)$",
                r"^cu[aá]l\s+es\s+la\s+diferencia\s+pr[aá]ctica\s+entre\s+(.+)$",
            ):
                match = re.search(pattern, lowered, flags=re.IGNORECASE)
                if match:
                    subject = match.group(1).strip().strip("?.! ")
                    break
            if not subject:
                continue
            answer = f"{subject.strip().capitalize()} se entiende así: {compact_text(right, 420)}"
            upsert(
                course_term_answers,
                normalize_text(subject),
                {"term": subject, "answer": answer, "course_id": course_id, "course_name": course_name},
            )
            upsert(
                global_term_answers,
                normalize_text(subject),
                {"term": subject, "answer": answer, "course_id": course_id, "course_name": course_name},
            )

        for concept in course.get("key_concepts", []):
            label, body = split_label_and_body(concept)
            if not label:
                continue
            aliases = expand_label_aliases(label)
            aliases.extend(extract_parenthetical_aliases(label))
            for alias in aliases:
                normalized_alias = normalize_text(alias)
                if not normalized_alias:
                    continue
                answer = (
                    f"{alias} se entiende así: {compact_text(body, 360)}"
                    if body
                    else build_fallback_term_answer(
                        alias=alias,
                        course_name=course_name,
                        teacher_summary=teacher_summary,
                        source_summary=course_summary,
                        themes=themes,
                    )
                )
                payload = {
                    "term": alias,
                    "answer": answer,
                    "course_id": course_id,
                    "course_name": course_name,
                    "source_title": course_name,
                }
                upsert(course_term_answers, normalized_alias, payload)
                upsert(global_term_answers, normalized_alias, payload)

        for source in sources_by_course.get(course_id, []):
            source_summary = source.get("summary", "")
            for bucket_name in ("key_concepts", "glossary"):
                for item in source.get(bucket_name, []):
                    label, body = split_label_and_body(item)
                    if not label:
                        continue
                    for alias in expand_label_aliases(label):
                        if body:
                            answer = f"{alias} se entiende así: {compact_text(body, 360)}"
                        else:
                            answer = build_fallback_term_answer(
                                alias=alias,
                                course_name=course_name,
                                teacher_summary=teacher_summary,
                                source_summary=source_summary,
                                themes=themes,
                            )
                        normalized_alias = normalize_text(alias)
                        payload = {
                            "term": alias,
                            "answer": answer,
                            "course_id": course_id,
                            "course_name": course_name,
                            "source_title": source.get("source_title", ""),
                        }
                        upsert(course_term_answers, normalized_alias, payload)
                        upsert(global_term_answers, normalized_alias, payload)

            for item in source.get("protocols", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue
                answer = (
                    f"El protocolo {label} se trabaja así: {compact_text(body, 420)}"
                    if body
                    else build_fallback_protocol_answer(label, course_name, source_summary)
                )
                for alias in expand_label_aliases(label):
                    normalized_alias = normalize_text(alias)
                    payload = {
                        "term": alias,
                        "answer": answer,
                        "course_id": course_id,
                        "course_name": course_name,
                        "source_title": source.get("source_title", ""),
                    }
                    upsert(course_protocol_answers, normalized_alias, payload)
                    upsert(global_protocol_answers, normalized_alias, payload)

        dossier_summary = (
            f"{strip_course_type_prefix(course_name)} es una formación orientada a "
            f"{clean_summary_seed(teacher_summary or course_summary)}"
        )
        dossiers.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "linea": course.get("linea", ""),
                "tipo": course.get("tipo", ""),
                "dossier_summary": dossier_summary,
                "teacher_summary": compact_text(teacher_summary, 520),
                "core_themes": course.get("core_themes", [])[:8],
                "key_concepts": course.get("key_concepts", [])[:12],
                "protocols": course.get("protocols", [])[:12],
                "study_guide": course.get("study_guide", [])[:8],
                "common_questions": course.get("common_questions", [])[:10],
                "term_answers": course_term_answers,
                "protocol_answers": course_protocol_answers,
                "source_count": len(sources_by_course.get(course_id, [])),
            }
        )

    return {
        "course_count": len(dossiers),
        "courses": dossiers,
        "global_term_answers": global_term_answers,
        "global_protocol_answers": global_protocol_answers,
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dossiers construidos en {OUTPUT_PATH}")
    print(f"Cursos: {index['course_count']} | términos: {len(index['global_term_answers'])} | protocolos: {len(index['global_protocol_answers'])}")


if __name__ == "__main__":
    main()
