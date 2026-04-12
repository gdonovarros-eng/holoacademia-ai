from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "manual_reference_index.json"


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
    Evita separar por ' y ' o '/' porque vuelve el índice demasiado ambiguo.
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
    manual_title: str,
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
        "manual_title": manual_title,
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

    priority = {"glossary": 4, "concept": 3, "protocol": 2}
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
    """
    Solo publica respuesta global si ese término no compite entre varios cursos/fuentes.
    Así evitas contaminación entre cursos.
    """

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


def is_manual(source: dict[str, Any]) -> bool:
    source_type = normalize_text(
        str(source.get("source_type") or source.get("tipo") or source.get("kind") or "")
    )
    title = normalize_text(source.get("source_title", ""))
    path = normalize_text(source.get("source_file", ""))

    if source_type in {"manual", "pdf"}:
        return True

    keywords = ("manual", "cuaderno", "workbook")
    return any(keyword in title or keyword in path for keyword in keywords)


def build_index() -> dict[str, Any]:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    source_studies = [source for source in payload.get("source_studies", []) if is_manual(source)]

    global_term_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    global_protocol_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    course_term_evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    course_protocol_evidence: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    manual_entries: list[dict[str, Any]] = []

    for source in source_studies:
        course_id = source["course_id"]
        course_name = source["course_name"]
        manual_title = source["source_title"]
        source_file = source["source_file"]

        term_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        protocol_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        concepts: list[dict[str, Any]] = []
        protocols: list[dict[str, Any]] = []

        for item in source.get("key_concepts", []):
            label, body = split_label_and_body(item)
            if not label:
                continue

            aliases = expand_label_aliases(label)
            entry = {
                "term": label,
                "body": clean_text(body),
                "answer": make_answer(label, body),
                "aliases": aliases,
            }
            concepts.append(entry)

            for alias in aliases:
                normalized_alias = normalize_text(alias)
                evidence = make_evidence(
                    course_id=course_id,
                    course_name=course_name,
                    manual_title=manual_title,
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
            entry = {
                "term": label,
                "body": clean_text(body),
                "answer": make_answer(label, body),
                "aliases": aliases,
            }
            concepts.append(entry)

            for alias in aliases:
                normalized_alias = normalize_text(alias)
                evidence = make_evidence(
                    course_id=course_id,
                    course_name=course_name,
                    manual_title=manual_title,
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
            entry = {
                "term": label,
                "body": clean_text(body),
                "answer": make_answer(label, body),
                "aliases": aliases,
            }
            protocols.append(entry)

            for alias in aliases:
                normalized_alias = normalize_text(alias)
                evidence = make_evidence(
                    course_id=course_id,
                    course_name=course_name,
                    manual_title=manual_title,
                    source_file=source_file,
                    kind="protocol",
                    label=label,
                    alias=alias,
                    body=body,
                )
                add_evidence(protocol_evidence, normalized_alias, evidence)
                add_evidence(course_protocol_evidence[course_id], normalized_alias, evidence)
                add_evidence(global_protocol_evidence, normalized_alias, evidence)

        manual_entries.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "manual_title": manual_title,
                "source_file": source_file,
                "summary": source.get("summary", ""),
                "term_answers": build_answers(term_evidence),
                "protocol_answers": build_answers(protocol_evidence),
                "term_evidence": dict(term_evidence),
                "protocol_evidence": dict(protocol_evidence),
                "concepts": concepts,
                "protocols": protocols,
            }
        )

    return {
        "manual_count": len(manual_entries),
        "manuals": manual_entries,
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
        "course_term_evidence": serialize_nested_evidence(course_term_evidence),
        "course_protocol_evidence": serialize_nested_evidence(course_protocol_evidence),
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado por manual en {OUTPUT_PATH}")
    print(f"Manuales: {index['manual_count']}")
    print(
        f"Términos globales únicos: {len(index['global_term_answers'])} | "
        f"Protocolos globales únicos: {len(index['global_protocol_answers'])}"
    )


if __name__ == "__main__":
    main()
