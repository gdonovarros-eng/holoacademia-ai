from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


DEFAULT_LIBRARY_ROOT = Path("/Users/m2/Desktop/holo_pipeline/04_holoacademia_app/data/knowledge_units")

GENERIC_MODULE_TITLES = {
    "modulo 1",
    "modulo 2",
    "modulo 3",
    "modulo 4",
    "modulo 5",
    "modulo 6",
    "modulo 7",
    "modulo 8",
    "modulo 9",
    "modulo 10",
    "modulo 11",
    "modulo 12",
    "módulo 1",
    "módulo 2",
    "módulo 3",
    "módulo 4",
    "módulo 5",
    "módulo 6",
    "módulo 7",
    "módulo 8",
    "módulo 9",
    "módulo 10",
    "módulo 11",
    "módulo 12",
}

STOPWORDS = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "y",
    "en",
    "con",
    "para",
    "por",
    "un",
    "una",
}

MODULE_LABEL_RE = re.compile(r"^(modulo|módulo)\s+\d+$", re.IGNORECASE)


def load_json(path: Path):
    return json.loads(path.read_text())


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(value: str) -> str:
    return normalize_text(value).replace(" ", "_")


def split_sentences(text: str) -> list[str]:
    normalized = " ".join((text or "").split())
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def merge_unique(values: list[str], additions: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in [*(values or []), *(additions or [])]:
        text = str(value).strip()
        if not text:
            continue
        key = normalize_text(text)
        if key in seen:
            continue
        seen.add(key)
        merged.append(text)
    return merged


def accentless_variant(term: str) -> str:
    text = " ".join(term.split()).strip()
    accentless = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in accentless if not unicodedata.combining(ch))


def _pluralize_word(word: str) -> str:
    if not word:
        return word
    if word.endswith("z"):
        return word[:-1] + "ces"
    if word.endswith(("a", "e", "i", "o", "u")):
        return word + "s"
    return word + "es"


def _singularize_word(word: str) -> str:
    if word.endswith("ces") and len(word) > 4:
        return word[:-3] + "z"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def _last_word_variants(term: str) -> set[str]:
    words = normalize_text(term).split()
    if not words:
        return set()
    singular = _singularize_word(words[-1])
    plural = _pluralize_word(words[-1])
    variants = {
        " ".join(words[:-1] + [singular]).strip(),
        " ".join(words[:-1] + [plural]).strip(),
    }
    variants.discard(normalize_text(term))
    return {variant for variant in variants if variant}


def safe_generated_aliases(term: str) -> list[str]:
    text = " ".join(term.split()).strip()
    if not text:
        return []
    if text.startswith("●") or looks_like_module_label(text):
        return []
    aliases: list[str] = []
    accentless = accentless_variant(text)
    if accentless and accentless != text:
        aliases.append(accentless)
    return merge_unique([], aliases)


def clean_aliases(term: str, aliases: list[str]) -> list[str]:
    cleaned: list[str] = []
    term_norm = normalize_text(term)
    morph_variants = _last_word_variants(term)
    for alias in aliases or []:
        raw = str(alias).strip()
        if not raw:
            continue
        alias_norm = normalize_text(raw)
        if not alias_norm or alias_norm == term_norm:
            continue
        if raw.startswith("●"):
            continue
        if looks_like_module_label(raw):
            continue
        if alias_norm in morph_variants:
            continue
        cleaned.append(raw)
    return merge_unique([], cleaned)


def first_sentence(text: str) -> str:
    sentences = split_sentences(text)
    return sentences[0] if sentences else " ".join((text or "").split())


def is_generic_title(title: str) -> bool:
    return normalize_text(title) in GENERIC_MODULE_TITLES


def looks_like_module_label(text: str) -> bool:
    value = " ".join((text or "").split()).strip()
    return bool(MODULE_LABEL_RE.match(value))


def is_artificial_module_concept(concept: dict) -> bool:
    concept_id = str(concept.get("id", "")).strip()
    term = str(concept.get("termino", "")).strip()
    return bool(re.fullmatch(r"modulo_\d+", concept_id) and looks_like_module_label(term))


def artificial_summary_title_concept_ids(summaries: list[dict]) -> set[str]:
    ids: set[str] = set()
    for summary in summaries:
        title = str(summary.get("titulo", "")).strip()
        if not title or is_generic_title(title):
            continue
        ids.add(slugify(title))
    return ids


def concept_index(concepts: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for concept in concepts:
        candidates = [concept.get("termino", ""), *(concept.get("aliases", []) or []), concept.get("id", "")]
        for candidate in candidates:
            norm = normalize_text(str(candidate))
            if norm:
                index[norm] = concept
    return index


def glossary_index(glossary: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for entry in glossary:
        norm = normalize_text(entry.get("termino", ""))
        if norm:
            index[norm] = entry
    return index


def qa_support(term: str, faqs: list[dict]) -> list[dict]:
    norm_term = normalize_text(term)
    matches: list[dict] = []
    for faq in faqs:
        haystack = " ".join(
            [
                str(faq.get("pregunta", "")),
                str(faq.get("respuesta", "")),
                " ".join(map(str, faq.get("relacionado_conceptos", []) or [])),
            ]
        )
        if norm_term and norm_term in normalize_text(haystack):
            matches.append(faq)
    return matches


def summary_support(term: str, summaries: list[dict]) -> list[dict]:
    norm_term = normalize_text(term)
    matches: list[dict] = []
    for summary in summaries:
        haystack = " ".join(
            [
                str(summary.get("titulo", "")),
                str(summary.get("resumen", "")),
                " ".join(map(str, summary.get("temas_clave", []) or [])),
            ]
        )
        if norm_term and norm_term in normalize_text(haystack):
            matches.append(summary)
    return matches


def concept_is_weak(concept: dict) -> bool:
    definicion = " ".join(str(concept.get("definicion", "")).split())
    simple = " ".join(str(concept.get("explicacion_simple", "")).split())
    return len(definicion) < 35 or len(simple) < 20


def derive_definition(term: str, glossary_entry: dict | None, faq_matches: list[dict], summary_matches: list[dict]) -> tuple[str, str, str, str]:
    if glossary_entry:
        definicion_corta = str(glossary_entry.get("definicion_corta", "")).strip()
        faq_text = first_sentence(str(faq_matches[0].get("respuesta", ""))) if faq_matches else ""
        summary_text = first_sentence(str(summary_matches[0].get("resumen", ""))) if summary_matches else ""
        definicion = definicion_corta or faq_text or summary_text or f"Concepto académico tratado en el curso alrededor de {term}."
        explicacion_simple = faq_text or definicion_corta or summary_text or definicion
        explicacion_extendida = ""
        if faq_matches:
            explicacion_extendida = " ".join(split_sentences(str(faq_matches[0].get("respuesta", "")))[:2]).strip()
        if not explicacion_extendida and summary_matches:
            explicacion_extendida = " ".join(split_sentences(str(summary_matches[0].get("resumen", "")))[:2]).strip()
        confidence = "high" if glossary_entry.get("confidence") == "high" or faq_matches else "medium"
        return definicion, explicacion_simple, explicacion_extendida or explicacion_simple, confidence

    if faq_matches:
        answer = str(faq_matches[0].get("respuesta", "")).strip()
        definicion = first_sentence(answer) or f"Concepto tratado en el curso alrededor de {term}."
        explicacion_simple = definicion
        explicacion_extendida = " ".join(split_sentences(answer)[:2]).strip() or definicion
        return definicion, explicacion_simple, explicacion_extendida, "medium"

    if summary_matches:
        summary = summary_matches[0]
        module_title = str(summary.get("titulo", "")).strip()
        base = f"Tema académico trabajado en {module_title or summary.get('id', 'el curso')}."
        resumen = str(summary.get("resumen", "")).strip()
        definicion = base
        explicacion_simple = first_sentence(resumen) or base
        explicacion_extendida = " ".join(split_sentences(resumen)[:2]).strip() or explicacion_simple
        return definicion, explicacion_simple, explicacion_extendida, "low"

    fallback = f"Tema académico referido en el curso como {term}."
    return fallback, fallback, fallback, "low"


def derive_modulo(glossary_entry: dict | None, faq_matches: list[dict], summary_matches: list[dict]) -> str:
    if glossary_entry and glossary_entry.get("modulo"):
        return str(glossary_entry.get("modulo"))
    for faq in faq_matches:
        modulo = str(faq.get("modulo", "")).strip()
        if modulo:
            return modulo
    for summary in summary_matches:
        modulo = str(summary.get("modulo") or summary.get("id") or "").strip()
        if modulo:
            return modulo
    return ""


def derive_related_concepts(term: str, faq_matches: list[dict], summary_matches: list[dict], known_ids: set[str]) -> list[str]:
    related: list[str] = []
    for faq in faq_matches:
        related.extend([concept_id for concept_id in faq.get("relacionado_conceptos", []) or [] if concept_id in known_ids])
    for summary in summary_matches:
        for topic in summary.get("temas_clave", []) or []:
            topic_id = slugify(str(topic))
            if topic_id in known_ids:
                related.append(topic_id)
    related = [item for item in related if item != slugify(term)]
    return merge_unique([], related)


def enrich_course(course_dir: Path) -> dict:
    academic_dir = course_dir / "03_academic"
    concepts_path = academic_dir / "concepts.json"
    glossary_path = academic_dir / "glossary.json"
    summaries_path = academic_dir / "module_summaries.json"
    faq_path = academic_dir / "faq_candidates.json"

    concepts = load_json(concepts_path)
    glossary = load_json(glossary_path)
    summaries = load_json(summaries_path)
    faqs = load_json(faq_path) if faq_path.exists() else []

    removed_concept_ids = {str(item.get("id", "")) for item in concepts if is_artificial_module_concept(item)}
    removed_concept_ids.update(
        {
            str(item.get("id", ""))
            for item in concepts
            if str(item.get("id", "")) in artificial_summary_title_concept_ids(summaries)
            and normalize_text(str(item.get("termino", ""))) in {normalize_text(str(summary.get("titulo", ""))) for summary in summaries}
        }
    )
    if removed_concept_ids:
        concepts = [item for item in concepts if str(item.get("id", "")) not in removed_concept_ids]
        glossary = [
            item
            for item in glossary
            if str(item.get("referencia_concepto", "")) not in removed_concept_ids
            and str(item.get("id", "")) not in {f"glosario_{concept_id}" for concept_id in removed_concept_ids}
        ]

    report = {
        "concepts_added": [],
        "concepts_strengthened": [],
        "glossary_entries_added": [],
        "aliases_added": [],
        "weak_points_remaining": [],
        "ready_for_academic_v1_close": True,
    }

    concepts_by_id = {str(item.get("id", "")): item for item in concepts}
    concepts_lookup = concept_index(concepts)
    glossary_lookup = glossary_index(glossary)
    known_ids = set(concepts_by_id)

    # 1) Strengthen existing concepts with glossary, FAQ, summary support and safe aliases.
    for concept in concepts:
        concept_id = str(concept.get("id", ""))
        term = str(concept.get("termino", "")).strip()
        if not term:
            continue
        gentry = glossary_lookup.get(normalize_text(term))
        faq_matches = qa_support(term, faqs)
        summary_matches = summary_support(term, summaries)

        existing_aliases = clean_aliases(term, concept.get("aliases", []) or [])
        before_aliases = set(normalize_text(alias) for alias in existing_aliases)
        safe_aliases = safe_generated_aliases(term)
        if faq_matches:
            question = normalize_text(str(faq_matches[0].get("pregunta", "")))
            if question.startswith("que es "):
                extracted = str(faq_matches[0].get("pregunta", "")).strip()
                extracted = re.sub(r"^[¿? ]*(qué es|que es)\s+", "", extracted, flags=re.IGNORECASE).rstrip(" ?¿")
                if (
                    normalize_text(extracted)
                    and normalize_text(extracted) != normalize_text(term)
                    and not extracted.startswith("●")
                    and not looks_like_module_label(extracted)
                ):
                    safe_aliases = merge_unique(safe_aliases, [extracted, accentless_variant(extracted)])
        concept["aliases"] = merge_unique(existing_aliases, safe_aliases)
        for alias in concept.get("aliases", []) or []:
            if normalize_text(alias) not in before_aliases:
                report["aliases_added"].append({"concept_id": concept_id, "alias": alias})

        if concept_is_weak(concept):
            definicion, explicacion_simple, explicacion_extendida, confidence = derive_definition(term, gentry, faq_matches, summary_matches)
            if not str(concept.get("definicion", "")).strip() or len(str(concept.get("definicion", "")).strip()) < len(definicion):
                concept["definicion"] = definicion
            if not str(concept.get("explicacion_simple", "")).strip() or len(str(concept.get("explicacion_simple", "")).strip()) < len(explicacion_simple):
                concept["explicacion_simple"] = explicacion_simple
            if not str(concept.get("explicacion_extendida", "")).strip():
                concept["explicacion_extendida"] = explicacion_extendida
            if not str(concept.get("modulo", "")).strip():
                concept["modulo"] = derive_modulo(gentry, faq_matches, summary_matches)
            if confidence == "high" or concept.get("confidence") not in {"high", "medium"}:
                concept["confidence"] = confidence
            report["concepts_strengthened"].append(concept_id)

        concept["relacionado_conceptos"] = merge_unique(
            concept.get("relacionado_conceptos", []) or [],
            derive_related_concepts(term, faq_matches, summary_matches, known_ids),
        )

    # 2) Add missing concepts from glossary.
    for entry in glossary:
        term = str(entry.get("termino", "")).strip()
        if not term:
            continue
        norm = normalize_text(term)
        if norm in concepts_lookup:
            concept = concepts_lookup[norm]
            if not entry.get("referencia_concepto"):
                entry["referencia_concepto"] = concept.get("id", "")
            continue

        faq_matches = qa_support(term, faqs)
        summary_matches = summary_support(term, summaries)
        definicion, explicacion_simple, explicacion_extendida, confidence = derive_definition(term, entry, faq_matches, summary_matches)
        concept_id = slugify(term)
        related_concepts = derive_related_concepts(term, faq_matches, summary_matches, known_ids)
        related_protocols = []
        for faq in faq_matches:
            related_protocols.extend([item for item in faq.get("relacionado_protocolos", []) or [] if item])
        new_concept = {
            "id": concept_id,
            "termino": term,
            "aliases": safe_generated_aliases(term),
            "definicion": definicion,
            "explicacion_simple": explicacion_simple,
            "explicacion_extendida": explicacion_extendida,
            "modulo": derive_modulo(entry, faq_matches, summary_matches),
            "seccion": "",
            "curso": course_dir.name.replace("course_", "", 1),
            "linea": concepts[0].get("linea", "salud") if concepts else "salud",
            "source": entry.get("source", "merged"),
            "confidence": confidence,
            "relacionado_conceptos": related_concepts,
            "relacionado_protocolos": merge_unique([], related_protocols),
            "relacionado_reasoning": [],
        }
        concepts.append(new_concept)
        concepts_lookup[norm] = new_concept
        known_ids.add(concept_id)
        entry["referencia_concepto"] = concept_id
        report["concepts_added"].append(concept_id)
        report["aliases_added"].extend({"concept_id": concept_id, "alias": alias} for alias in new_concept["aliases"])

    # 3) Add missing concepts from module topics when clearly academic and absent elsewhere.
    for summary in summaries:
        temas = summary.get("temas_clave", []) or []
        for term in temas:
            text = str(term).strip()
            if not text:
                continue
            norm = normalize_text(text)
            if not norm or norm in concepts_lookup or norm in glossary_lookup:
                continue
            if looks_like_module_label(text):
                continue
            if normalize_text(text) == normalize_text(str(summary.get("titulo", ""))):
                continue
            if len(norm.split()) == 1 and len(norm) < 4:
                continue
            faq_matches = qa_support(text, faqs)
            summary_matches = [summary]
            definicion, explicacion_simple, explicacion_extendida, confidence = derive_definition(text, None, faq_matches, summary_matches)
            concept_id = slugify(text)
            new_concept = {
                "id": concept_id,
                "termino": text,
                "aliases": safe_generated_aliases(text),
                "definicion": definicion,
                "explicacion_simple": explicacion_simple,
                "explicacion_extendida": explicacion_extendida,
                "modulo": str(summary.get("modulo") or summary.get("id") or ""),
                "seccion": "",
                "curso": course_dir.name.replace("course_", "", 1),
                "linea": concepts[0].get("linea", "salud") if concepts else "salud",
                "source": summary.get("source", "merged"),
                "confidence": "low" if not faq_matches else "medium",
                "relacionado_conceptos": derive_related_concepts(text, faq_matches, summary_matches, known_ids),
                "relacionado_protocolos": merge_unique([], [p for faq in faq_matches for p in faq.get("relacionado_protocolos", []) or []]),
                "relacionado_reasoning": [],
            }
            concepts.append(new_concept)
            concepts_lookup[norm] = new_concept
            known_ids.add(concept_id)
            report["concepts_added"].append(concept_id)
            report["aliases_added"].extend({"concept_id": concept_id, "alias": alias} for alias in new_concept["aliases"])

    # 4) Ensure glossary support exists for every concept.
    glossary_ids = {str(item.get("id", "")) for item in glossary}
    glossary_norms = {normalize_text(item.get("termino", "")) for item in glossary}
    for concept in concepts:
        term = str(concept.get("termino", "")).strip()
        norm = normalize_text(term)
        if not term or norm in glossary_norms:
            continue
        glossary_id = f"glosario_{concept.get('id', slugify(term))}"
        if glossary_id in glossary_ids:
            continue
        glossary_entry = {
            "id": glossary_id,
            "termino": term,
            "definicion_corta": first_sentence(str(concept.get("definicion", "")).strip() or str(concept.get("explicacion_simple", "")).strip()),
            "curso": concept.get("curso", course_dir.name.replace("course_", "", 1)),
            "linea": concept.get("linea", "salud"),
            "modulo": concept.get("modulo", ""),
            "seccion": concept.get("seccion", ""),
            "source": concept.get("source", "merged"),
            "confidence": concept.get("confidence", "medium"),
            "referencia_concepto": concept.get("id", ""),
            "uso": "rápido",
        }
        glossary.append(glossary_entry)
        glossary_ids.add(glossary_id)
        glossary_norms.add(norm)
        report["glossary_entries_added"].append(glossary_id)

    # 5) Strengthen module summaries from linked concepts.
    module_to_terms: dict[str, list[str]] = {}
    for concept in concepts:
        modulo = str(concept.get("modulo", "")).strip()
        term = str(concept.get("termino", "")).strip()
        if modulo and term:
            module_to_terms.setdefault(modulo, []).append(term)

    for summary in summaries:
        summary_id = str(summary.get("id") or summary.get("modulo") or "")
        terms = module_to_terms.get(summary_id, [])
        summary["temas_clave"] = merge_unique(summary.get("temas_clave", []) or [], terms[:6])
        if not str(summary.get("resumen", "")).strip():
            title = str(summary.get("titulo", "")).strip()
            summary["resumen"] = f"Módulo dedicado a {title or summary_id}."

    # 6) Weak points note.
    if len(report["concepts_added"]) == 0 and len(report["concepts_strengthened"]) == 0:
        report["weak_points_remaining"].append("La base ya estaba relativamente consolidada y no requirió refuerzos sustanciales.")

    report["concepts_added"] = sorted(set(report["concepts_added"]))
    report["concepts_strengthened"] = sorted(set(report["concepts_strengthened"]))
    report["glossary_entries_added"] = sorted(set(report["glossary_entries_added"]))
    alias_seen: set[tuple[str, str]] = set()
    deduped_aliases: list[dict] = []
    for item in sorted(report["aliases_added"], key=lambda x: (x["concept_id"], normalize_text(x["alias"]))):
        key = (item["concept_id"], normalize_text(item["alias"]))
        if key in alias_seen:
            continue
        alias_seen.add(key)
        deduped_aliases.append(item)
    report["aliases_added"] = deduped_aliases

    concepts.sort(key=lambda item: str(item.get("id", "")))
    glossary.sort(key=lambda item: str(item.get("id", "")))
    summaries.sort(key=lambda item: str(item.get("id", "")))

    dump_json(concepts_path, concepts)
    dump_json(glossary_path, glossary)
    dump_json(summaries_path, summaries)
    dump_json(course_dir / "10_academic_enrichment_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library-root", default=str(DEFAULT_LIBRARY_ROOT))
    args = parser.parse_args()
    library_root = Path(args.library_root)
    courses = sorted([path for path in library_root.iterdir() if path.is_dir()])

    summary = {}
    for course_dir in courses:
        summary[course_dir.name] = enrich_course(course_dir)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
