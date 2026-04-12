from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "course_reference_index.json"


def clean_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def compact_text(text: str, limit: int = 600) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return no_accents.lower().replace("–", "-").strip()


def split_faq_entry(item: str) -> tuple[str, str]:
    cleaned = clean_text(item)
    for separator in (" — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
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
            return candidate or None
    return None


def split_label_and_body(item: str) -> tuple[str, str]:
    cleaned = clean_text(item).strip("• ")
    if not cleaned:
        return "", ""

    if re.match(r"^\d+\)", cleaned):
        return "", ""

    for separator in (": ", " — ", " – ", " - "):
        if separator in cleaned:
            left, right = cleaned.split(separator, 1)
            if 2 <= len(left.strip()) <= 160:
                return left.strip(), right.strip()

    return cleaned, ""


def expand_label_aliases(label: str) -> list[str]:
    """
    Alias conservadores:
    - etiqueta original
    - etiqueta sin paréntesis
    - divisiones por coma solamente
    """

    aliases = [clean_text(label)]
    base = re.sub(r"\([^)]*\)", "", label).strip(" ,")
    if base and base not in aliases:
        aliases.append(base)

    comma_parts = [part.strip() for part in base.split(",") if part.strip()]
    if 1 < len(comma_parts) <= 4:
        aliases.extend(comma_parts)

    deduped: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        normalized = normalize_text(alias)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(alias)

    return deduped


def make_answer(label: str, body: str) -> str:
    cleaned_body = clean_text(body)
    if not cleaned_body:
        return ""
    normalized_label = normalize_text(label)
    normalized_body = normalize_text(cleaned_body)
    if normalized_body.startswith(normalized_label):
        return cleaned_body
    return f"{label}: {cleaned_body}"


def make_evidence(
    *,
    course_id: str,
    course_name: str,
    source_title: str,
    source_file: str,
    kind: str,
    label: str,
    alias: str,
    body: str,
) -> dict[str, Any]:
    answer = make_answer(label, body)
    return {
        "course_id": course_id,
        "course_name": course_name,
        "source_title": source_title,
        "source_file": source_file,
        "kind": kind,
        "label": label,
        "alias": alias,
        "body": clean_text(body),
        "answer": answer,
        "snippet": compact_text(body, 600) if body else "",
    }


def add_evidence(index: dict[str, list[dict[str, Any]]], key: str, evidence: dict[str, Any]) -> None:
    if not key:
        return
    index[key].append(evidence)


def select_best_evidence(evidences: list[dict[str, Any]]) -> dict[str, Any] | None:
    with_body = [item for item in evidences if item.get("answer")]
    if not with_body:
        return None

    priority = {
        "faq_subject": 5,
        "glossary": 4,
        "concept": 3,
        "protocol": 2,
        "faq_question": 1,
    }

    return max(
        with_body,
        key=lambda item: (
            priority.get(item.get("kind", ""), 0),
            len(item.get("answer", "")),
        ),
    )


def build_answers(evidence_map: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for key, evidences in evidence_map.items():
        best = select_best_evidence(evidences)
        if best:
            answers[key] = best["answer"]
    return answers


def build_unique_global_answers(evidence_map: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for key, evidences in evidence_map.items():
        with_body = [item for item in evidences if item.get("answer")]
        if not with_body:
            continue

        distinct_answers = {item["answer"] for item in with_body}
        distinct_courses = {item["course_id"] for item in with_body}
        distinct_files = {item["source_file"] for item in with_body}

        if len(distinct_answers) == 1 and len(distinct_courses) == 1 and len(distinct_files) == 1:
            answers[key] = with_body[0]["answer"]

    return answers


def serialize_nested_evidence(
    payload: dict[str, dict[str, list[dict[str, Any]]]]
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    return {outer_key: dict(inner_map) for outer_key, inner_map in payload.items()}


def build_index() -> dict[str, Any]:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    course_studies = payload.get("course_studies", [])
    source_studies = payload.get("source_studies", [])

    sources_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in source_studies:
        sources_by_course[source["course_id"]].append(source)

    global_term_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    global_protocol_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    course_term_evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    course_protocol_evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    course_question_evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    course_entries: list[dict[str, Any]] = []

    for course in course_studies:
        course_id = course["course_id"]
        course_name = course["course_name"]

        term_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        protocol_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        question_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        source_entries: list[dict[str, Any]] = []

        for question in course.get("common_questions", []):
            question_text, answer_text = split_faq_entry(question)
            if not question_text or not answer_text:
                continue

            normalized_question = normalize_text(question_text)
            faq_question_evidence = make_evidence(
                course_id=course_id,
                course_name=course_name,
                source_title="common_questions",
                source_file="teacher_memory.json",
                kind="faq_question",
                label=question_text,
                alias=question_text,
                body=answer_text,
            )
            add_evidence(question_evidence, normalized_question, faq_question_evidence)
            add_evidence(course_question_evidence[course_id], normalized_question, faq_question_evidence)

            subject = extract_defined_subject(question_text)
            if subject:
                normalized_subject = normalize_text(subject)
                faq_subject_evidence = make_evidence(
                    course_id=course_id,
                    course_name=course_name,
                    source_title="common_questions",
                    source_file="teacher_memory.json",
                    kind="faq_subject",
                    label=subject,
                    alias=subject,
                    body=answer_text,
                )
                add_evidence(term_evidence, normalized_subject, faq_subject_evidence)
                add_evidence(course_term_evidence[course_id], normalized_subject, faq_subject_evidence)
                add_evidence(global_term_evidence, normalized_subject, faq_subject_evidence)

        for source in sources_by_course.get(course_id, []):
            source_title = source["source_title"]
            source_file = source["source_file"]

            source_record = {
                "source_title": source_title,
                "source_file": source_file,
                "summary": source.get("summary", ""),
                "concepts": [],
                "protocols": [],
                "glossary": source.get("glossary", []),
            }

            for item in source.get("key_concepts", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue

                aliases = expand_label_aliases(label)
                source_record["concepts"].append(
                    {
                        "term": label,
                        "body": clean_text(body),
                        "answer": make_answer(label, body),
                        "aliases": aliases,
                    }
                )

                for alias in aliases:
                    normalized_alias = normalize_text(alias)
                    evidence = make_evidence(
                        course_id=course_id,
                        course_name=course_name,
                        source_title=source_title,
                        source_file=source_file,
                        kind="concept",
                        label=label,
                        alias=alias,
                        body=body,
                    )
                    add_evidence(term_evidence, normalized_alias, evidence)
                    add_evidence(course_term_evidence[course_id], normalized_alias, evidence)
                    add_evidence(global_term_evidence, normalized_alias, evidence)

            for item in source.get("glossary", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue

                aliases = expand_label_aliases(label)
                source_record["concepts"].append(
                    {
                        "term": label,
                        "body": clean_text(body),
                        "answer": make_answer(label, body),
                        "aliases": aliases,
                    }
                )

                for alias in aliases:
                    normalized_alias = normalize_text(alias)
                    evidence = make_evidence(
                        course_id=course_id,
                        course_name=course_name,
                        source_title=source_title,
                        source_file=source_file,
                        kind="glossary",
                        label=label,
                        alias=alias,
                        body=body,
                    )
                    add_evidence(term_evidence, normalized_alias, evidence)
                    add_evidence(course_term_evidence[course_id], normalized_alias, evidence)
                    add_evidence(global_term_evidence, normalized_alias, evidence)

            for item in source.get("protocols", []):
                label, body = split_label_and_body(item)
                if not label:
                    continue

                aliases = expand_label_aliases(label)
                source_record["protocols"].append(
                    {
                        "term": label,
                        "body": clean_text(body),
                        "answer": make_answer(label, body),
                        "aliases": aliases,
                    }
                )

                for alias in aliases:
                    normalized_alias = normalize_text(alias)
                    evidence = make_evidence(
                        course_id=course_id,
                        course_name=course_name,
                        source_title=source_title,
                        source_file=source_file,
                        kind="protocol",
                        label=label,
                        alias=alias,
                        body=body,
                    )
                    add_evidence(protocol_evidence, normalized_alias, evidence)
                    add_evidence(course_protocol_evidence[course_id], normalized_alias, evidence)
                    add_evidence(global_protocol_evidence, normalized_alias, evidence)

            source_entries.append(source_record)

        course_entries.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "linea": course.get("linea", ""),
                "tipo": course.get("tipo", ""),
                "source_count": len(source_entries),
                "sources": source_entries,
                "term_answers": build_answers(term_evidence),
                "protocol_answers": build_answers(protocol_evidence),
                "question_answers": build_answers(question_evidence),
                "term_evidence": dict(term_evidence),
                "protocol_evidence": dict(protocol_evidence),
                "question_evidence": dict(question_evidence),
            }
        )

    return {
        "course_count": len(course_entries),
        "source_count": len(source_studies),
        "courses": course_entries,
        "global_term_answers": build_unique_global_answers(global_term_evidence),
        "global_protocol_answers": build_unique_global_answers(global_protocol_evidence),
        "global_term_evidence": dict(global_term_evidence),
        "global_protocol_evidence": dict(global_protocol_evidence),
        "course_term_answers": {
            course_id: build_answers(evidence_map) for course_id, evidence_map in course_term_evidence.items()
        },
        "course_protocol_answers": {
            course_id: build_answers(evidence_map) for course_id, evidence_map in course_protocol_evidence.items()
        },
        "course_question_answers": {
            course_id: build_answers(evidence_map) for course_id, evidence_map in course_question_evidence.items()
        },
        "course_term_evidence": serialize_nested_evidence(course_term_evidence),
        "course_protocol_evidence": serialize_nested_evidence(course_protocol_evidence),
        "course_question_evidence": serialize_nested_evidence(course_question_evidence),
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado por formación en {OUTPUT_PATH}")
    print(f"Cursos: {index['course_count']} | Fuentes: {index['source_count']}")
    print(
        f"Términos globales únicos: {len(index['global_term_answers'])} | "
        f"Protocolos globales únicos: {len(index['global_protocol_answers'])}"
    )


if __name__ == "__main__":
    main()
