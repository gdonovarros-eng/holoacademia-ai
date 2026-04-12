from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEACHER_MEMORY_PATH = BASE_DIR / "data" / "teacher_memory.json"
OUTPUT_PATH = BASE_DIR / "data" / "manual_reference_index.json"


def compact_text(text: str, limit: int = 420) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def soft_trim(text: str, limit: int = 1200) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    for marker in (". ", "; ", ": "):
        idx = cut.rfind(marker)
        if idx >= int(limit * 0.65):
            return cut[: idx + 1].strip()
    return cut.rstrip(" ,;:") + "…"


def normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text or "")
    no_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return no_accents.lower().replace("–", "-")


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
        for separator in ("/",):
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


def extract_parenthetical_descriptor(label: str) -> str:
    match = re.search(r"\(([^)]+)\)", label)
    return match.group(1).strip() if match else ""


@lru_cache(maxsize=256)
def read_source_text(source_file: str) -> str:
    path = Path(source_file)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def split_passages(text: str) -> list[str]:
    cleaned = (text or "").replace("\r", "\n")
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", cleaned) if chunk.strip()]
    passages = [" ".join(chunk.split()) for chunk in chunks if len(" ".join(chunk.split())) >= 80]
    return passages or ([" ".join(cleaned.split())] if cleaned.strip() else [])


@lru_cache(maxsize=256)
def get_source_passages(source_file: str) -> list[tuple[str, str]]:
    text = read_source_text(source_file)
    if not text:
        return []
    return [(passage, normalize_text(passage)) for passage in split_passages(text)]


def body_keywords(body: str, limit: int = 6) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(body))
        if len(token) >= 4
    ][:limit]


def find_source_excerpt(source_file: str, label: str, body: str) -> str:
    passages = get_source_passages(source_file)
    label_norm = normalize_text(label)
    extra_terms = body_keywords(body)
    ranked: list[tuple[int, int, str]] = []
    for passage, normalized in passages:
        score = 0
        if label_norm and label_norm in normalized:
            score += 12
        for term in extra_terms:
            if term in normalized:
                score += 2
        if score > 0:
            ranked.append((score, len(passage), passage))
    if not ranked:
        return ""
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return soft_trim(ranked[0][2], 1200)


def answer_quality(answer: str) -> tuple[int, int]:
    lowered = answer.lower()
    generic_penalty = 0
    if "es un concepto importante dentro de" in lowered:
        generic_penalty += 3
    if "forma parte de las" in lowered:
        generic_penalty += 2
    if "se entiende así" in lowered or "se entiende asi" in lowered:
        generic_penalty -= 1
    return (generic_penalty, -len(answer))


def upsert_answer(index: dict[str, str], key: str, answer: str) -> None:
    existing = index.get(key)
    if existing is None or answer_quality(answer) < answer_quality(existing):
        index[key] = answer


def is_manual(source: dict) -> bool:
    title = source.get("source_title", "").lower()
    path = source.get("source_file", "").lower()
    combined = f"{title} {path}"
    return any(marker in combined for marker in ["manual", "protocolo", "modulo", "módulo", "guia", "guía", "propedeutico", "propedéutico"])


def build_index() -> dict:
    payload = json.loads(TEACHER_MEMORY_PATH.read_text(encoding="utf-8"))
    source_studies = [source for source in payload.get("source_studies", []) if is_manual(source)]

    global_term_answers: dict[str, str] = {}
    global_protocol_answers: dict[str, str] = {}
    course_term_answers: dict[str, dict[str, str]] = defaultdict(dict)
    course_protocol_answers: dict[str, dict[str, str]] = defaultdict(dict)
    manual_entries: list[dict] = []

    for source in source_studies:
        course_id = source["course_id"]
        course_name = source["course_name"]
        manual_title = source["source_title"]
        term_index: dict[str, str] = {}
        protocol_index: dict[str, str] = {}
        concepts: list[dict] = []
        protocols: list[dict] = []

        for item in source.get("key_concepts", []):
            label, body = split_label_and_body(item)
            if not label:
                continue
            descriptor = extract_parenthetical_descriptor(label)
            source_excerpt = find_source_excerpt(source.get("source_file", ""), label, body)
            answer = (
                f"{label} se entiende así: {soft_trim(body, 900)}"
                if body
                else (
                    f"{label} se entiende así: {source_excerpt}"
                    if source_excerpt
                    else f"{label} se usa en {manual_title} como criterio operativo dentro del método."
                )
            )
            concepts.append({"term": label, "answer": answer})
            for alias in expand_label_aliases(label):
                alias_answer = answer
                if not body and normalize_text(alias) != normalize_text(label) and descriptor:
                    alias_answer = (
                        f"{alias} forma parte de las {descriptor} que se usan en {manual_title} "
                        "como preparación o apoyo dentro del método."
                    )
                normalized_alias = normalize_text(alias)
                upsert_answer(term_index, normalized_alias, alias_answer)
                upsert_answer(course_term_answers[course_id], normalized_alias, alias_answer)
                upsert_answer(global_term_answers, normalized_alias, alias_answer)

        for item in source.get("glossary", []):
            label, body = split_label_and_body(item)
            if not label:
                continue
            source_excerpt = find_source_excerpt(source.get("source_file", ""), label, body)
            answer = (
                f"{label} se entiende así: {soft_trim(body, 900)}"
                if body
                else (
                    f"{label} se entiende así: {source_excerpt}"
                    if source_excerpt
                    else f"{label} se usa en {manual_title} como criterio operativo dentro del método."
                )
            )
            concepts.append({"term": label, "answer": answer})
            for alias in expand_label_aliases(label):
                normalized_alias = normalize_text(alias)
                upsert_answer(term_index, normalized_alias, answer)
                upsert_answer(course_term_answers[course_id], normalized_alias, answer)
                upsert_answer(global_term_answers, normalized_alias, answer)

        for item in source.get("protocols", []):
            label, body = split_label_and_body(item)
            if not label:
                continue
            source_excerpt = find_source_excerpt(source.get("source_file", ""), label, body)
            answer = (
                f"El protocolo {label} se trabaja así: {soft_trim(body, 1000)}"
                if body
                else (
                    f"El protocolo {label} se trabaja así: {source_excerpt}"
                    if source_excerpt
                    else f"El protocolo {label} se usa dentro de {manual_title} como una secuencia de intervención."
                )
            )
            protocols.append({"term": label, "answer": answer})
            for alias in expand_label_aliases(label):
                normalized_alias = normalize_text(alias)
                upsert_answer(protocol_index, normalized_alias, answer)
                upsert_answer(course_protocol_answers[course_id], normalized_alias, answer)
                upsert_answer(global_protocol_answers, normalized_alias, answer)

        manual_entries.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "manual_title": manual_title,
                "source_file": source["source_file"],
                "summary": source.get("summary", ""),
                "term_answers": term_index,
                "protocol_answers": protocol_index,
                "concepts": concepts,
                "protocols": protocols,
            }
        )

    return {
        "manual_count": len(manual_entries),
        "manuals": manual_entries,
        "global_term_answers": global_term_answers,
        "global_protocol_answers": global_protocol_answers,
        "course_term_answers": course_term_answers,
        "course_protocol_answers": course_protocol_answers,
    }


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexado por manual en {OUTPUT_PATH}")
    print(f"Manuales: {index['manual_count']}")
    print(f"Términos globales: {len(index['global_term_answers'])} | Protocolos globales: {len(index['global_protocol_answers'])}")


if __name__ == "__main__":
    main()
