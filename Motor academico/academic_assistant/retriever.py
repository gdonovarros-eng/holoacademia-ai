from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .models import AcademicKnowledgeBase, RetrievalHit


SOURCE_PRIORITY = {
    "concepts": 0,
    "glossary": 1,
    "module_summaries": 2,
    "faq_candidates": 3,
    "course_overview": 4,
    "course_manifest": 5,
    "inventory": 6,
    "clean_text": 7,
}

RESOLUTION_SOURCE_PRIORITY = {
    "concept": 0,
    "alias": 1,
    "glossary": 2,
    "faq": 3,
    "summary": 4,
    "overview": 5,
    "manifest": 6,
}

DIRECT_RESOLUTION_SOURCES = {"concept", "alias"}
NEARBY_RESOLUTION_SOURCES = {"glossary", "faq", "summary"}
WEAK_RESOLUTION_SOURCES = {"overview", "manifest"}

STOPWORDS = {
    "a",
    "al",
    "como",
    "con",
    "cual",
    "cuales",
    "cuál",
    "cuáles",
    "de",
    "del",
    "dentro",
    "el",
    "en",
    "es",
    "este",
    "esta",
    "estos",
    "estas",
    "explicame",
    "explicamelo",
    "explicalo",
    "la",
    "las",
    "lo",
    "los",
    "mas",
    "más",
    "para",
    "por",
    "que",
    "qué",
    "resume",
    "resumelo",
    "se",
    "un",
    "una",
    "y",
}

SIMPLE_LANGUAGE_PATTERNS = (
    "explicamelo facil",
    "explicamelo mas facil",
    "explicamelo fácil",
    "no entendi",
    "no entendi",
    "apenas estoy empezando",
    "como si apenas estuviera empezando",
    "en palabras simples",
    "mas simple",
    "más simple",
)

ANAPHORIC_PATTERNS = (
    "explicamelo mejor",
    "explícamelo mejor",
    "eso no lo entendi",
    "eso no lo entendí",
    "y esa parte",
    "eso mejor",
)

GENERIC_TARGET_WORDS = {
    "eso",
    "esto",
    "mejor",
    "parte",
    "tema",
    "cosa",
    "cosas",
    "esa parte",
    "esta parte",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: str) -> list[str]:
    output: list[str] = []
    for token in normalize_text(value).split():
        if not token or token in STOPWORDS:
            continue
        if token.endswith("es") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        if token and token not in STOPWORDS:
            output.append(token)
    return output


def _score_text_match(query: str, text: str, aliases: Iterable[str] | None = None) -> float:
    query_norm = normalize_text(query)
    text_norm = normalize_text(text)
    alias_norms = [normalize_text(alias) for alias in aliases or [] if alias]
    query_tokens = set(tokenize(query_norm))
    text_tokens = set(tokenize(text_norm))

    if not query_norm or not text_norm:
        return 0.0
    if query_norm == text_norm:
        return 100.0
    if query_norm in alias_norms:
        return 96.0
    if text_norm in query_norm:
        return 94.0
    if query_norm in text_norm:
        return 88.0

    token_overlap = len(query_tokens & text_tokens)
    if token_overlap:
        overlap_ratio = token_overlap / max(1, len(query_tokens))
        base = 42.0 + min(36.0, token_overlap * 10.0) + (overlap_ratio * 10.0)
        if len(query_tokens) > 1 and query_tokens <= text_tokens:
            base += 8.0
        return min(92.0, base)

    for alias in alias_norms:
        if alias and (alias in query_norm or query_norm in alias):
            return 76.0
    return 0.0


def _module_hint_score(query: str, modulo: str, title: str) -> float:
    query_norm = normalize_text(query)
    if not modulo and not title:
        return 0.0
    score = 0.0
    modulo_norm = normalize_text(modulo)
    title_norm = normalize_text(title)
    if modulo_norm and modulo_norm in query_norm:
        score += 20.0
    if title_norm and title_norm in query_norm:
        score += 12.0
    return score


def _dedupe_hits(hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
    best: dict[tuple[str, str], RetrievalHit] = {}
    for hit in hits:
        key = (hit.source_type, hit.id)
        current = best.get(key)
        if current is None or hit.score > current.score:
            best[key] = hit
    return sorted(
        best.values(),
        key=lambda item: (-item.score, SOURCE_PRIORITY.get(item.source_type, 99), item.id),
    )[:top_k]


def _snippet(text: str, query: str, radius: int = 180) -> str:
    if not text:
        return ""
    query_norm = normalize_text(query)
    text_norm = normalize_text(text)
    if not query_norm or query_norm not in text_norm:
        return text[:radius].strip()
    direct_idx = text.lower().find(query.lower())
    if direct_idx < 0:
        return text[:radius].strip()
    start = max(0, direct_idx - radius // 2)
    end = min(len(text), start + radius)
    return text[start:end].strip()


def _clean_target_text(value: str) -> str:
    cleaned = normalize_text(value)
    cleaned = re.sub(r"^(el|la|los|las|un|una)\s+", "", cleaned).strip()
    cleaned = re.sub(r"^(eso de|lo de|lo del|lo de la|lo de los|lo de las)\s+", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _pluralize_token(token: str) -> str:
    if not token:
        return token
    if token.endswith("z"):
        return token[:-1] + "ces"
    if token.endswith(("a", "e", "i", "o", "u")):
        return token + "s"
    return token + "es"


def _variant_forms(text: str) -> set[str]:
    forms: set[str] = set()
    norm = normalize_text(text)
    if not norm:
        return forms
    forms.add(norm)
    tokens = tokenize(norm)
    if tokens:
        joined = " ".join(tokens)
        forms.add(joined)
        if len(tokens) >= 2:
            forms.add(tokens[0])
            forms.add(_pluralize_token(tokens[0]))
            for size in (2, 3):
                if len(tokens) >= size:
                    for index in range(len(tokens) - size + 1):
                        window = " ".join(tokens[index:index + size]).strip()
                        if window:
                            forms.add(window)
        for token in tokens:
            if len(token) >= 5:
                forms.add(token)
    return {form for form in forms if form}


def _build_resolution_candidates(knowledge: AcademicKnowledgeBase) -> list[dict]:
    candidates: list[dict] = []
    glossary_by_concept: dict[str, list[str]] = {}
    for entry in knowledge.glossary:
        if entry.referencia_concepto:
            glossary_by_concept.setdefault(entry.referencia_concepto, []).append(entry.termino)

    for concept in knowledge.concepts:
        variants = set()
        variants.update(_variant_forms(concept.termino))
        for alias in concept.aliases:
            variants.update(_variant_forms(alias))
        for term in glossary_by_concept.get(concept.id, []):
            variants.update(_variant_forms(term))
        candidates.append(
            {
                "id": concept.id,
                "kind": "concept",
                "source": "concept",
                "label": normalize_text(concept.termino),
                "display": concept.termino,
                "variants": variants,
            }
        )
        for alias in concept.aliases:
            alias_variants = _variant_forms(alias)
            if alias_variants:
                candidates.append(
                    {
                        "id": concept.id,
                        "kind": "concept",
                        "source": "alias",
                        "label": normalize_text(concept.termino),
                        "display": concept.termino,
                        "variants": alias_variants,
                    }
                )

    for entry in knowledge.glossary:
        variants = set()
        variants.update(_variant_forms(entry.termino))
        if entry.referencia_concepto:
            candidates.append(
                {
                    "id": entry.referencia_concepto,
                    "kind": "concept",
                    "source": "glossary",
                    "label": normalize_text(entry.termino),
                    "display": entry.termino,
                    "variants": variants,
                }
            )
        else:
            candidates.append(
                {
                    "id": entry.id,
                    "kind": "glossary",
                    "source": "glossary",
                    "label": normalize_text(entry.termino),
                    "display": entry.termino,
                    "variants": variants,
                }
            )

    for faq in knowledge.faq_candidates:
        if len(faq.relacionado_conceptos) == 1:
            candidates.append(
                {
                    "id": faq.relacionado_conceptos[0],
                    "kind": "concept",
                    "source": "faq",
                    "label": normalize_text(faq.pregunta),
                    "display": faq.pregunta,
                    "variants": _variant_forms(faq.pregunta),
                }
            )

    for summary in knowledge.module_summaries:
        variants = set()
        variants.update(_variant_forms(summary.titulo))
        for topic in summary.temas_clave:
            variants.update(_variant_forms(topic))
        candidates.append(
            {
                "id": summary.id,
                "kind": "module",
                "source": "summary",
                "label": normalize_text(summary.titulo or summary.id),
                "display": summary.titulo or summary.id,
                "variants": variants,
            }
        )

    overview_terms = []
    overview_terms.extend(knowledge.course_overview.get("temas_principales", []) or [])
    manifest_terms = []
    manifest_terms.extend(knowledge.course_manifest.get("temas_principales", []) or [])
    for term in overview_terms:
        candidates.append(
            {
                "id": "course_overview",
                "kind": "overview",
                "source": "overview",
                "label": normalize_text(str(term)),
                "display": str(term),
                "variants": _variant_forms(str(term)),
            }
        )
    for term in manifest_terms:
        candidates.append(
            {
                "id": "course_manifest",
                "kind": "manifest",
                "source": "manifest",
                "label": normalize_text(str(term)),
                "display": str(term),
                "variants": _variant_forms(str(term)),
            }
        )
    return candidates


def _score_resolution(raw_target: str, candidate: dict) -> tuple[float, str]:
    cleaned = _clean_target_text(raw_target)
    if not cleaned:
        return 0.0, "empty"
    target_tokens = set(tokenize(cleaned))
    best_score = 0.0
    best_reason = ""
    for variant in candidate.get("variants", set()):
        if not variant:
            continue
        variant_tokens = set(tokenize(variant))
        if cleaned == variant:
            return 100.0, "exact_variant"
        if cleaned in variant or variant in cleaned:
            score = 88.0 if len(cleaned) >= 5 else 72.0
            if score > best_score:
                best_score = score
                best_reason = "partial_variant"
        overlap = len(target_tokens & variant_tokens)
        if overlap:
            if len(target_tokens) >= 2 and overlap < 2:
                continue
            ratio = overlap / max(1, len(target_tokens))
            score = 56.0 + min(24.0, overlap * 10.0) + (ratio * 8.0)
            if len(target_tokens) == 1 and len(next(iter(target_tokens), "")) <= 4:
                score -= 10.0
            if score > best_score:
                best_score = score
                best_reason = "token_overlap"
    return best_score, best_reason or "no_match"


def resolve_target(raw_target: str, knowledge: AcademicKnowledgeBase) -> dict:
    cleaned = _clean_target_text(raw_target)
    if not cleaned:
        return {
            "raw_target": raw_target,
            "resolved_target": "",
            "resolved_target_label": "",
            "resolved_kind": "",
            "resolution_source": "",
            "resolution_confidence": "low",
            "reason": "empty_target",
            "supporting_matches": [],
        }

    best_candidate = None
    best_score = 0.0
    best_reason = "no_match"
    scored_candidates: list[tuple[float, dict, str]] = []
    for candidate in _build_resolution_candidates(knowledge):
        score, reason = _score_resolution(cleaned, candidate)
        if score > 0:
            scored_candidates.append((score, candidate, reason))
        if score > best_score or (
            score == best_score
            and best_candidate is not None
            and RESOLUTION_SOURCE_PRIORITY.get(candidate.get("source", ""), 99)
            < RESOLUTION_SOURCE_PRIORITY.get(best_candidate.get("source", ""), 99)
        ):
            best_score = score
            best_candidate = candidate
            best_reason = reason

    cleaned_tokens = tokenize(cleaned)
    if (
        best_candidate is None
        or best_score < 72.0
        or (best_reason == "partial_variant" and len(cleaned_tokens) >= 2 and best_score < 90.0)
    ):
        return {
            "raw_target": raw_target,
            "resolved_target": "",
            "resolved_target_label": "",
            "resolved_kind": "",
            "resolution_source": "",
            "resolution_confidence": "low",
            "reason": "unresolved",
            "supporting_matches": [
                {
                    "id": candidate["id"],
                    "source": candidate.get("source", ""),
                    "kind": candidate.get("kind", ""),
                    "label": candidate.get("display", ""),
                    "score": round(score, 4),
                    "reason": reason,
                }
                for score, candidate, reason in sorted(
                    scored_candidates,
                    key=lambda item: (-item[0], RESOLUTION_SOURCE_PRIORITY.get(item[1].get("source", ""), 99), item[1]["id"]),
                )[:5]
            ],
        }

    source = str(best_candidate.get("source", ""))
    if source in DIRECT_RESOLUTION_SOURCES:
        confidence = "high" if best_score >= 90.0 else "medium"
    elif source in NEARBY_RESOLUTION_SOURCES:
        confidence = "medium" if best_score >= 88.0 else "low"
    elif source in WEAK_RESOLUTION_SOURCES:
        confidence = "low"
    else:
        confidence = "medium" if best_score >= 90.0 else "low"
    supporting_matches = [
        {
            "id": candidate["id"],
            "source": candidate.get("source", ""),
            "kind": candidate.get("kind", ""),
            "label": candidate.get("display", ""),
            "score": round(score, 4),
            "reason": reason,
        }
        for score, candidate, reason in sorted(
            scored_candidates,
            key=lambda item: (-item[0], RESOLUTION_SOURCE_PRIORITY.get(item[1].get("source", ""), 99), item[1]["id"]),
        )[:5]
    ]
    return {
        "raw_target": raw_target,
        "resolved_target": best_candidate["id"],
        "resolved_target_label": best_candidate["label"],
        "resolved_kind": best_candidate["kind"],
        "resolution_source": source,
        "resolution_confidence": confidence,
        "reason": best_reason,
        "supporting_matches": supporting_matches,
    }


def resolve_course_concept(query: str, knowledge: AcademicKnowledgeBase) -> dict:
    raw_query = normalize_text(query)
    primary_target = _extract_primary_target(query)
    if not primary_target:
        return {
            "raw_query": raw_query,
            "resolved": False,
            "resolved_concept_id": "",
            "resolved_label": "",
            "resolution_source": "",
            "resolution_confidence": "low",
            "supporting_matches": [],
        }

    resolution = resolve_target(primary_target, knowledge)
    return {
        "raw_query": raw_query,
        "resolved": bool(resolution.get("resolved_target")),
        "resolved_concept_id": resolution.get("resolved_target", ""),
        "resolved_label": resolution.get("resolved_target_label", ""),
        "resolution_source": resolution.get("resolution_source", ""),
        "resolution_confidence": resolution.get("resolution_confidence", "low"),
        "supporting_matches": resolution.get("supporting_matches", []),
    }


def _extract_primary_target(query: str) -> str:
    text = query.strip()
    patterns = [
        r"(?:que es|qué es|define|significa)\s+(.+)",
        r"(?:explicame|explícame|explicamelo|explícamelo)\s+(.+)",
        r"(?:eso de|lo de|lo del|lo de la)\s+(.+)",
        r"(?:hablame de|háblame de)\s+(.+)",
        r"sobre\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            target = _clean_target_text(match.group(1))
            if target and target not in GENERIC_TARGET_WORDS and set(tokenize(target)) - GENERIC_TARGET_WORDS:
                return target
    return ""


def _extract_module_hint(query: str) -> str | None:
    match = re.search(r"\b(modulo|módulo|clase)\s+(\d+)\b", query, flags=re.IGNORECASE)
    if match:
        return f"modulo_{match.group(2)}"
    match = re.search(r"\bparte\s+(\d+)\b", query, flags=re.IGNORECASE)
    if match:
        return f"parte_{match.group(1)}"
    return None


def _extract_comparison_targets(query: str) -> list[str]:
    text = query.strip()
    patterns = [
        r"diferencia\s+entre\s+(.+?)\s+y\s+(.+)",
        r"compara\s+(.+?)\s+con\s+(.+)",
        r"comparar\s+(.+?)\s+con\s+(.+)",
        r"(.+?)\s+vs\.?\s+(.+)",
        r"(.+?)\s+versus\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            targets = [_clean_target_text(match.group(1)), _clean_target_text(match.group(2))]
            return [target for target in targets if target]
    return []


def _extract_locate_targets(query: str) -> list[str]:
    text = query.strip()
    patterns = [
        r"se habla de\s+(.+)",
        r"se ve\s+(.+)",
        r"aparece\s+(.+)",
        r"sobre\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            target = _clean_target_text(match.group(1))
            if target:
                return [target]
    return []


def detect_query_intent(query: str, knowledge: AcademicKnowledgeBase | None = None) -> dict:
    raw = (query or "").strip()
    norm = normalize_text(raw)
    needs_simple_language = any(pattern in norm for pattern in map(normalize_text, SIMPLE_LANGUAGE_PATTERNS))
    targets = _extract_comparison_targets(raw)
    module_hint = _extract_module_hint(raw)
    target_resolution_trace: list[dict] = []
    concept_resolution = {
        "raw_query": norm,
        "resolved": False,
        "resolved_concept_id": "",
        "resolved_label": "",
        "resolution_source": "",
        "resolution_confidence": "low",
        "supporting_matches": [],
    }

    if targets:
        intent = "comparison"
    elif any(phrase in norm for phrase in ("en que parte del curso", "en qué parte del curso", "donde se habla", "dónde se habla", "en que modulo", "en qué módulo", "donde aparece", "dónde aparece")):
        intent = "locate_in_course"
        targets = _extract_locate_targets(raw)
    elif any(term in norm for term in ("resume", "resumen", "resumelo", "resúmelo")) or module_hint:
        intent = "module_summary"
    elif any(term in norm for term in ("que es", "qué es", "define", "definicion", "definición", "significa", "significado")):
        intent = "definition"
    elif needs_simple_language:
        intent = "simple_explanation"
    else:
        intent = "general_academic"

    if not targets and intent in {"definition", "simple_explanation", "general_academic", "locate_in_course"}:
        primary_target = _extract_primary_target(raw)
        if primary_target:
            targets = [primary_target]

    anaphoric_without_target = any(pattern in norm for pattern in map(normalize_text, ANAPHORIC_PATTERNS)) and not targets
    if anaphoric_without_target:
        intent = "general_academic"

    if knowledge is not None and targets:
        resolved_targets: list[str] = []
        for target in targets:
            resolution = resolve_target(target, knowledge)
            target_resolution_trace.append(resolution)
            if resolution["resolved_target_label"]:
                resolved_targets.append(resolution["resolved_target_label"])
            else:
                cleaned_target = _clean_target_text(target)
                resolved_targets.append(cleaned_target or target)
        if resolved_targets:
            targets = resolved_targets

    if knowledge is not None and not anaphoric_without_target:
        concept_resolution = resolve_course_concept(query, knowledge)

    return {
        "intent": intent,
        "targets": targets,
        "module_hint": module_hint,
        "needs_simple_language": needs_simple_language,
        "target_resolution_trace": target_resolution_trace,
        "anaphoric_without_target": anaphoric_without_target,
        "concept_resolution": concept_resolution,
    }


def _intent_boost(intent_data: dict, source_type: str, *, modulo: str = "", title: str = "", matched_targets: int = 0, has_simple_explanation: bool = False, inventory_type: str = "") -> float:
    intent = intent_data.get("intent", "general_academic")
    module_hint = str(intent_data.get("module_hint") or "")
    bonus = 0.0

    if intent == "definition":
        if source_type == "concepts":
            bonus += 24.0
        elif source_type == "glossary":
            bonus += 18.0
    elif intent == "comparison":
        if source_type == "concepts":
            bonus += 26.0 + (matched_targets * 10.0)
        elif source_type == "glossary":
            bonus += 16.0 + (matched_targets * 8.0)
        elif source_type == "module_summaries":
            bonus += 6.0
    elif intent == "module_summary":
        if source_type == "module_summaries":
            bonus += 34.0
        elif source_type == "course_overview":
            bonus += 16.0
        elif source_type == "course_manifest":
            bonus += 12.0
        elif source_type == "concepts":
            bonus += 4.0
    elif intent == "locate_in_course":
        if source_type == "inventory":
            bonus += 30.0
            if inventory_type == "module_inventory":
                bonus += 8.0
        elif source_type == "module_summaries":
            bonus += 18.0
    elif intent == "simple_explanation":
        if source_type == "concepts":
            bonus += 18.0
            if has_simple_explanation:
                bonus += 14.0
        elif source_type == "glossary":
            bonus += 14.0
        elif source_type == "faq_candidates":
            bonus += 8.0

    if module_hint:
        modulo_norm = normalize_text(modulo)
        title_norm = normalize_text(title)
        if module_hint in {modulo_norm, title_norm}:
            bonus += 26.0
        elif module_hint.replace("_", " ") in title_norm:
            bonus += 18.0
    return bonus


def _best_target_label(hit: RetrievalHit) -> str:
    return normalize_text(hit.title or hit.id)


def _ensure_comparison_coverage(hits: list[RetrievalHit], all_hits: list[RetrievalHit], intent_data: dict, top_k: int) -> list[RetrievalHit]:
    targets = [normalize_text(target) for target in intent_data.get("targets", []) if target]
    if intent_data.get("intent") != "comparison" or len(targets) < 2:
        return hits

    selected: list[RetrievalHit] = []
    covered: set[str] = set()
    pool = sorted(all_hits, key=lambda item: (-item.score, SOURCE_PRIORITY.get(item.source_type, 99), item.id))

    for target in targets[:2]:
        target_best = None
        for hit in pool:
            label = _best_target_label(hit)
            aliases = [normalize_text(alias) for alias in hit.metadata.get("aliases", [])] if isinstance(hit.metadata, dict) else []
            if target == label or target in label or label in target or target in aliases:
                target_best = hit
                break
        if target_best is not None and (target_best.source_type, target_best.id) not in covered:
            selected.append(target_best)
            covered.add((target_best.source_type, target_best.id))

    for hit in hits:
        key = (hit.source_type, hit.id)
        if key not in covered:
            selected.append(hit)
            covered.add(key)
        if len(selected) >= top_k:
            break
    return selected[:top_k]


def search_academic_context(
    query: str,
    knowledge: AcademicKnowledgeBase,
    top_k: int = 5,
    intent_data: dict | None = None,
) -> list[RetrievalHit]:
    query = (query or "").strip()
    if not query:
        return []
    intent_data = intent_data or detect_query_intent(query)
    resolved_anchor_id = ((intent_data.get("concept_resolution") or {}).get("resolved_concept_id") or "").strip()

    hits: list[RetrievalHit] = []

    for concept in knowledge.concepts:
        title = concept.termino
        preferred_explanation = concept.explicacion_simple if intent_data.get("needs_simple_language") and concept.explicacion_simple else ""
        content = " ".join(
            part for part in [
                preferred_explanation,
                concept.definicion,
                concept.explicacion_simple,
                concept.explicacion_extendida,
                concept.cuando_se_aplica,
            ] if part
        )
        title_score = 0.0 if intent_data.get("intent") == "comparison" else _score_text_match(query, title, concept.aliases)
        content_score = 0.0 if intent_data.get("intent") == "comparison" else _score_text_match(query, content, concept.aliases)
        target_scores = [
            max(
                _score_text_match(target, title, concept.aliases),
                _score_text_match(target, content, concept.aliases) - 10.0,
            )
            for target in intent_data.get("targets", [])
        ]
        matched_targets = sum(1 for score in target_scores if score > 0)
        score = title_score
        if title_score > 0:
            score = max(score, content_score - 6.0)
        elif content_score > 0:
            score = min(48.0, content_score - 18.0)
        score += _module_hint_score(query, concept.modulo, title)
        score += max(target_scores, default=0.0)
        if resolved_anchor_id and concept.id == resolved_anchor_id:
            score += 40.0
        score += _intent_boost(
            intent_data,
            "concepts",
            modulo=concept.modulo,
            title=title,
            matched_targets=matched_targets,
            has_simple_explanation=bool(concept.explicacion_simple),
        )
        if intent_data.get("intent") == "comparison" and matched_targets == 0:
            continue
        if score > 0:
            hits.append(
                RetrievalHit(
                    id=concept.id,
                    source_type="concepts",
                    score=min(score, 100.0),
                    title=concept.termino,
                    content=content,
                    modulo=concept.modulo,
                    source=concept.source,
                    confidence=concept.confidence,
                    curso=concept.curso,
                    linea=concept.linea,
                    metadata={
                        "aliases": concept.aliases,
                        "relacionado_reasoning": concept.relacionado_reasoning,
                        "relacionado_protocolos": concept.relacionado_protocolos,
                        "explicacion_simple": concept.explicacion_simple,
                    },
                )
            )

    for entry in knowledge.glossary:
        content = entry.definicion_corta
        target_scores = [
            max(_score_text_match(target, entry.termino), _score_text_match(target, content) - 6.0)
            for target in intent_data.get("targets", [])
        ]
        matched_targets = sum(1 for score in target_scores if score > 0)
        score = 0.0 if intent_data.get("intent") == "comparison" else max(
            _score_text_match(query, entry.termino),
            _score_text_match(query, content) - 8.0,
        )
        score += max(target_scores, default=0.0)
        if resolved_anchor_id and resolved_anchor_id in {entry.id, entry.referencia_concepto}:
            score += 36.0
        score += _intent_boost(
            intent_data,
            "glossary",
            title=entry.termino,
            matched_targets=matched_targets,
        )
        if intent_data.get("intent") == "comparison" and matched_targets == 0:
            continue
        if score > 0:
            hits.append(
                RetrievalHit(
                    id=entry.id,
                    source_type="glossary",
                    score=min(score, 95.0),
                    title=entry.termino,
                    content=content,
                    source=entry.source,
                    confidence=entry.confidence,
                    curso=entry.curso,
                    linea=entry.linea,
                    metadata={"referencia_concepto": entry.referencia_concepto},
                )
            )

    for summary in knowledge.module_summaries:
        score = max(
            _score_text_match(query, summary.titulo),
            _score_text_match(query, summary.resumen) - 4.0,
        )
        score += _module_hint_score(query, summary.id, summary.titulo)
        if resolved_anchor_id and summary.id == resolved_anchor_id:
            score += 28.0
        score += _intent_boost(intent_data, "module_summaries", modulo=summary.id, title=summary.titulo)
        if score > 0:
            hits.append(
                RetrievalHit(
                    id=summary.id,
                    source_type="module_summaries",
                    score=min(score, 94.0),
                    title=summary.titulo or summary.id,
                    content=summary.resumen,
                    modulo=summary.id,
                    source=summary.source,
                    confidence=summary.confidence,
                    curso=summary.curso,
                    linea=summary.linea,
                    metadata={"temas_clave": summary.temas_clave},
                )
            )

    for faq in knowledge.faq_candidates:
        score = max(
            _score_text_match(query, faq.pregunta),
            _score_text_match(query, faq.respuesta) - 4.0,
        )
        if resolved_anchor_id and resolved_anchor_id in set(faq.relacionado_conceptos):
            score += 22.0
        score += _intent_boost(intent_data, "faq_candidates")
        if score > 0:
            hits.append(
                RetrievalHit(
                    id=faq.id,
                    source_type="faq_candidates",
                    score=min(score, 90.0),
                    title=faq.pregunta,
                    content=faq.respuesta,
                    source=faq.source,
                    confidence=faq.confidence,
                    curso=faq.curso,
                    linea=faq.linea,
                    metadata={"relacionado_conceptos": faq.relacionado_conceptos},
                )
            )

    overview_title = str(
        knowledge.course_overview.get("titulo")
        or knowledge.course_overview.get("nombre_del_curso")
        or knowledge.course_manifest.get("nombre_del_curso")
        or knowledge.course_id
    )
    overview_content = " ".join(
        str(part)
        for part in [
            knowledge.course_overview.get("descripcion"),
            knowledge.course_overview.get("resumen"),
            " ".join(knowledge.course_overview.get("temas_principales", []) or []),
            " ".join(knowledge.course_manifest.get("temas_principales", []) or []),
        ]
        if part
    ).strip()
    overview_score = max(
        _score_text_match(query, overview_title),
        _score_text_match(query, overview_content) - 12.0,
    )
    overview_score += _intent_boost(intent_data, "course_overview", title=overview_title)
    if overview_score > 0:
        hits.append(
            RetrievalHit(
                id="course_overview",
                source_type="course_overview",
                score=min(overview_score, 85.0),
                title=overview_title,
                content=overview_content,
                source=str(knowledge.course_overview.get("source", "merged")),
                confidence=str(knowledge.course_overview.get("confidence", "medium")),
                curso=knowledge.course_id,
                linea=knowledge.line,
                metadata={"manifest_entry_points": knowledge.course_manifest.get("entry_points", {})},
            )
        )

    manifest_content = " ".join(
        str(part)
        for part in [
            knowledge.course_manifest.get("observacion_general"),
            " ".join(knowledge.course_manifest.get("ambiguedades_detectadas", []) or []),
            " ".join(str(item) for item in (knowledge.course_manifest.get("modulos_detectados", []) or [])),
        ]
        if part
    ).strip()
    manifest_score = _score_text_match(query, manifest_content)
    manifest_score += _intent_boost(intent_data, "course_manifest")
    if manifest_score > 0:
        hits.append(
            RetrievalHit(
                id="course_manifest",
                source_type="course_manifest",
                score=min(manifest_score, 78.0),
                title="Contexto del curso",
                content=manifest_content,
                source=str(knowledge.course_manifest.get("source", "merged")),
                confidence=str(knowledge.course_manifest.get("confidence", "medium")),
                curso=knowledge.course_id,
                linea=knowledge.line,
                metadata={"mapa_conocimiento": knowledge.course_manifest.get("mapa_conocimiento", {})},
            )
        )

    for inventory_name, rows in (
        ("module_inventory", knowledge.module_inventory),
        ("transcript_inventory", knowledge.transcript_inventory),
    ):
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            title = str(row.get("titulo") or row.get("title") or row.get("modulo") or row.get("id") or f"{inventory_name}_{index}")
            content = " ".join(str(value) for value in row.values() if isinstance(value, (str, int, float)))
            score = max(_score_text_match(query, title), _score_text_match(query, content) - 14.0)
            score += _intent_boost(intent_data, "inventory", modulo=str(row.get("modulo", "")), title=title, inventory_type=inventory_name)
            if score > 0:
                hits.append(
                    RetrievalHit(
                        id=str(row.get("id") or f"{inventory_name}_{index}"),
                        source_type="inventory",
                        score=min(score, 72.0),
                        title=title,
                        content=content,
                        modulo=str(row.get("modulo", "")),
                        source="merged",
                        confidence=str(row.get("confidence", "medium")),
                        curso=knowledge.course_id,
                        linea=knowledge.line,
                        metadata={"inventory_type": inventory_name},
                    )
                )

    for text_key, text_value in knowledge.clean_fallback_texts.items():
        score = _score_text_match(query, text_value)
        if score > 0:
            hits.append(
                RetrievalHit(
                    id=text_key,
                    source_type="clean_text",
                    score=min(score, 65.0),
                    title=text_key,
                    content=_snippet(text_value, query),
                    source="merged",
                    confidence="low",
                    curso=knowledge.course_id,
                    linea=knowledge.line,
                    metadata={"fallback": True},
                )
            )

    deduped = _dedupe_hits(hits, top_k=max(top_k, 8))
    final_hits = _ensure_comparison_coverage(deduped, hits, intent_data, top_k)
    return final_hits[:top_k]
