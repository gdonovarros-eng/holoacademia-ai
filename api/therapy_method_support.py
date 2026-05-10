from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
THERAPY_METHOD_CORPUS_PATH = ROOT / "data" / "therapy_method_corpus.json"


CATEGORY_LABELS = {
    "espacio_terapeutico": "Espacio terapéutico",
    "preguntas_base_del_sintoma": "Preguntas base del síntoma",
    "pistas_e_investigacion": "Pistas e investigación",
    "analisis_sistemico": "Análisis sistémico",
    "masa_conflictual": "Masa conflictual",
    "decision_fisico_vs_emocional": "Decisión físico vs emocional",
    "rastreo_y_pares": "Rastreo y pares",
    "liberacion_emocional": "Liberación emocional",
    "protocolos_y_liberaciones": "Protocolos y liberaciones",
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


@lru_cache
def get_therapy_method_corpus() -> dict[str, Any]:
    if not THERAPY_METHOD_CORPUS_PATH.exists():
        return {"categories": {}, "courses": []}
    return json.loads(THERAPY_METHOD_CORPUS_PATH.read_text(encoding="utf-8"))


def _dedupe_snippets(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in snippets:
        key = _normalize_text(_safe_text(item.get("snippet")))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _collect_relevant_course_ids(case_analysis: dict[str, Any]) -> list[str]:
    course_ids: list[str] = []
    for item in _safe_list(case_analysis.get("therapy_transcript_routes"))[:4]:
        if isinstance(item, dict) and _safe_text(item.get("course_id")):
            course_ids.append(_safe_text(item.get("course_id")))
    for item in _safe_list(case_analysis.get("therapy_manual_routes"))[:4]:
        if isinstance(item, dict) and _safe_text(item.get("course_id")):
            course_ids.append(_safe_text(item.get("course_id")))
    return list(dict.fromkeys(course_ids))


def build_method_support(
    *,
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any] | None = None,
    primary_protocol: dict[str, Any] | None = None,
    case_orientation: str = "",
) -> dict[str, Any]:
    corpus = get_therapy_method_corpus()
    categories = corpus.get("categories", {})
    relevant_course_ids = _collect_relevant_course_ids(case_analysis)

    selected_category_ids = [
        "espacio_terapeutico",
        "preguntas_base_del_sintoma",
        "pistas_e_investigacion",
        "analisis_sistemico",
        "masa_conflictual",
    ]

    if case_orientation in {"fisico_emocional", "mixto"}:
        selected_category_ids.extend(["decision_fisico_vs_emocional", "rastreo_y_pares"])
    if case_orientation == "emocional" or primary_protocol is not None:
        selected_category_ids.extend(["liberacion_emocional", "protocolos_y_liberaciones"])
    elif pair_analysis is not None:
        selected_category_ids.append("protocolos_y_liberaciones")

    selected_category_ids = list(dict.fromkeys(selected_category_ids))
    category_entries: list[dict[str, Any]] = []

    for category_id in selected_category_ids:
        payload = categories.get(category_id) or {}
        snippets = _safe_list(payload.get("snippets"))
        if relevant_course_ids:
            snippets = [item for item in snippets if _safe_text(item.get("course_id")) in relevant_course_ids]
        if not snippets:
            snippets = _safe_list(payload.get("snippets"))[:]
        snippets = sorted(
            snippets,
            key=lambda item: (
                -int(item.get("score", 0)),
                _safe_text(item.get("course_name")),
                int(item.get("paragraph_index", 0)),
            ),
        )
        snippets = _dedupe_snippets(snippets)[:2]
        if not snippets:
            continue
        category_entries.append(
            {
                "category_id": category_id,
                "label": CATEGORY_LABELS.get(category_id, category_id.replace("_", " ")),
                "description": _safe_text(payload.get("description")),
                "snippets": [
                    {
                        "course_id": _safe_text(item.get("course_id")),
                        "course_name": _safe_text(item.get("course_name")),
                        "score": int(item.get("score", 0)),
                        "block": _safe_text(item.get("block")),
                        "matched_terms": _safe_list(item.get("matched_terms")),
                        "snippet": _safe_text(item.get("snippet")),
                        "source_file": _safe_text(item.get("source_file")),
                    }
                    for item in snippets
                ],
            }
        )

    return {
        "relevant_course_ids": relevant_course_ids,
        "categories": category_entries,
    }


__all__ = ["build_method_support", "get_therapy_method_corpus"]
