from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .models import RetrievalHit
from .retriever import tokenize


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for item in items:
        key = str(item.get("id", ""))
        if key and key not in seen:
            seen[key] = item
    return list(seen.values())


def _concept_terms(main_concepts: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for item in main_concepts:
        terms.update(tokenize(item.get("title", "")))
        terms.update(tokenize(item.get("content", ""))[:6])
    return terms


def _support_score(entry: dict[str, Any], concept_ids: set[str], concept_terms: set[str]) -> tuple[int, float]:
    score = float(entry.get("score", 0.0))
    bonus = 0
    reference = str(entry.get("reference_concept") or "")
    if reference and reference in concept_ids:
        bonus += 30
    overlap = len(concept_terms & set(tokenize(entry.get("title", "") + " " + entry.get("content", ""))))
    bonus += min(18, overlap * 6)
    return (-bonus, -score)


def _compact_text(text: str, max_chars: int) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    cut = normalized[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut or normalized[:max_chars]).rstrip(" ,;:") + "..."


def _compact_entry(entry: dict[str, Any], max_chars: int) -> dict[str, Any]:
    compacted = dict(entry)
    compacted["content"] = _compact_text(compacted.get("content", ""), max_chars)
    return compacted


def _match_target_entry(entries: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    target_tokens = set(tokenize(target))
    for entry in entries:
        searchable = f"{entry.get('title', '')} {entry.get('id', '')} {entry.get('content', '')}"
        entry_tokens = set(tokenize(searchable))
        if target_tokens and target_tokens <= entry_tokens:
            return entry
    for entry in entries:
        title = " ".join(tokenize(entry.get("title", "")))
        if target and (target in title or title in target):
            return entry
    return None


def build_academic_context(
    query: str,
    results: list[RetrievalHit],
    intent_data: dict | None = None,
    response_mode: str = "fast",
) -> dict[str, Any]:
    intent_data = intent_data or {"intent": "general_academic", "targets": [], "module_hint": None, "needs_simple_language": False}
    concept_resolution = intent_data.get("concept_resolution") or {}
    main_concepts: list[dict[str, Any]] = []
    supporting_glossary: list[dict[str, Any]] = []
    module_summaries: list[dict[str, Any]] = []
    faq_support: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    retrieval_trace: list[dict[str, Any]] = []
    course_context: dict[str, Any] = {}

    retrieval_trace.append(
        {
            "source": "intent",
            "id": intent_data.get("intent", "general_academic"),
            "score": 0.0,
            "modulo": intent_data.get("module_hint"),
            "targets": intent_data.get("targets", []),
            "target_resolution_trace": intent_data.get("target_resolution_trace", []),
            "concept_resolution": concept_resolution,
        }
    )

    for hit in results:
        trace = hit.to_trace()
        if hit.metadata.get("aliases"):
            trace["aliases"] = hit.metadata.get("aliases", [])
        retrieval_trace.append(trace)
        citations.append(
            {
                "source_type": hit.source_type,
                "id": hit.id,
                "title": hit.title,
                "modulo": hit.modulo,
                "score": round(hit.score, 4),
            }
        )
        entry = {
            "id": hit.id,
            "title": hit.title,
            "content": hit.content,
            "modulo": hit.modulo,
            "score": round(hit.score, 4),
            "source": hit.source,
            "metadata": hit.metadata,
        }
        if hit.source_type == "concepts":
            main_concepts.append(entry)
        elif hit.source_type == "glossary":
            supporting_glossary.append(entry)
        elif hit.source_type == "module_summaries":
            module_summaries.append(entry)
        elif hit.source_type == "faq_candidates":
            faq_support.append(entry)
        elif hit.source_type in {"course_overview", "course_manifest"} and not course_context:
            course_context = {
                "id": hit.id,
                "title": hit.title,
                "content": hit.content,
                "source_type": hit.source_type,
            }

    concept_limit = 2 if response_mode == "fast" else 3
    glossary_limit = 2 if response_mode == "fast" else 3
    module_limit = 1 if response_mode == "fast" else 2
    faq_limit = 1 if response_mode == "fast" else 2
    concept_chars = 520 if response_mode == "fast" else 760
    glossary_chars = 180 if response_mode == "fast" else 260
    module_chars = 280 if response_mode == "fast" else 420
    faq_chars = 180 if response_mode == "fast" else 260
    course_context_chars = 180 if response_mode == "fast" else 260

    main_concepts = _dedupe_by_id(main_concepts)
    resolved_id = str(concept_resolution.get("resolved_concept_id") or "")
    if resolved_id:
        main_concepts = sorted(
            main_concepts,
            key=lambda item: 0 if item.get("id") == resolved_id else 1,
        )
    main_concepts = [_compact_entry(item, concept_chars) for item in main_concepts[:concept_limit]]
    concept_ids = {item["id"] for item in main_concepts}
    concept_terms = _concept_terms(main_concepts)
    supporting_glossary = [
        {
            **item,
            "reference_concept": item.get("metadata", {}).get("referencia_concepto", ""),
        }
        for item in _dedupe_by_id(supporting_glossary)
        if item["id"] not in concept_ids
    ]
    supporting_glossary = sorted(
        supporting_glossary,
        key=lambda item: (
            0 if resolved_id and item.get("reference_concept") == resolved_id else 1,
            *_support_score(item, concept_ids, concept_terms),
        ),
    )[:glossary_limit]
    supporting_glossary = [_compact_entry(item, glossary_chars) for item in supporting_glossary]
    module_summaries = sorted(
        _dedupe_by_id(module_summaries),
        key=lambda item: (
            0 if resolved_id and item.get("id") == resolved_id else 1,
            *_support_score(item, concept_ids, concept_terms),
        ),
    )[:module_limit]
    module_summaries = [_compact_entry(item, module_chars) for item in module_summaries]
    faq_support = [_compact_entry(item, faq_chars) for item in _dedupe_by_id(faq_support)[:faq_limit]]
    citations = _dedupe_by_id(citations)[:8]
    if course_context:
        course_context = {
            **course_context,
            "content": _compact_text(course_context.get("content", ""), course_context_chars),
        }

    intent = intent_data.get("intent", "general_academic")
    comparison_notes: list[str] = []
    concept_a = None
    concept_b = None
    missing_targets: list[str] = []
    target_module = intent_data.get("module_hint")
    target_module_summary = None
    supporting_topics: list[str] = []

    if intent == "comparison":
        targets = [str(target) for target in intent_data.get("targets", []) if target]
        if targets:
            concept_a = _match_target_entry(main_concepts, targets[0])
        if len(targets) > 1:
            remaining = [item for item in main_concepts if item != concept_a]
            concept_b = _match_target_entry(remaining, targets[1])
        if targets and concept_a is None:
            missing_targets.append(targets[0])
        if len(targets) > 1 and concept_b is None:
            missing_targets.append(targets[1])
        if concept_a and concept_a.get("modulo"):
            comparison_notes.append(f"{concept_a['title']} aparece en {concept_a['modulo']}.")
        if concept_b and concept_b.get("modulo"):
            comparison_notes.append(f"{concept_b['title']} aparece en {concept_b['modulo']}.")

    retrieval_trace[0]["missing_targets"] = missing_targets

    if intent in {"module_summary", "locate_in_course"}:
        if target_module:
            target_module_summary = next(
                (item for item in module_summaries if item.get("id") == target_module or item.get("modulo") == target_module),
                None,
            )
        if target_module_summary is None and module_summaries:
            target_module_summary = module_summaries[0]
        if target_module_summary:
            target_module = target_module_summary.get("id") or target_module_summary.get("modulo") or target_module
            raw_topics = (target_module_summary.get("metadata") or {}).get("temas_clave", [])
            supporting_topics = [str(topic) for topic in raw_topics if topic][:5]

    if intent == "simple_explanation":
        simple_sorted = sorted(
            main_concepts,
            key=lambda item: 0 if item.get("metadata", {}).get("explicacion_simple") else 1,
        )
        main_concepts = simple_sorted[:2]

    for item in main_concepts + supporting_glossary + module_summaries + faq_support:
        item.pop("metadata", None)

    return {
        "query": query,
        "response_mode": response_mode,
        "intent": intent_data,
        "concept_resolution": concept_resolution,
        "main_concepts": main_concepts,
        "concept_a": concept_a,
        "concept_b": concept_b,
        "supporting_glossary": supporting_glossary,
        "glossary_support": supporting_glossary,
        "module_summaries": module_summaries,
        "target_module": target_module,
        "module_summary": target_module_summary,
        "supporting_topics": supporting_topics,
        "comparison_notes": comparison_notes,
        "missing_targets": missing_targets,
        "target_resolution_trace": intent_data.get("target_resolution_trace", []),
        "faq_support": faq_support,
        "course_context": course_context,
        "citations": citations,
        "retrieval_trace": retrieval_trace,
    }
