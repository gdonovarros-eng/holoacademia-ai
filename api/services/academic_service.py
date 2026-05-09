from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[2]
ACADEMIC_ENGINE_DIR = BASE_DIR / "Motor academico"

if str(ACADEMIC_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ACADEMIC_ENGINE_DIR))

from academic_assistant.service import answer_academic_query


def _normalize_sources(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    normalized: List[str] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(text)
            continue
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("source_type", "")).strip()
        identifier = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        modulo = str(item.get("modulo", "")).strip()
        pieces = [piece for piece in [source_type, identifier or title, modulo] if piece]
        if pieces:
            normalized.append(" | ".join(pieces))
    return normalized


def run_academic_query(query: str, history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    try:
        result = answer_academic_query(query, history=history or [])
        intent_value = result.get("intent")
        if isinstance(intent_value, dict):
            intent_value = intent_value.get("intent")
        return {
            "answer": str(result.get("answer", "")),
            "confidence": str(result.get("confidence", "low")),
            "sources_used": _normalize_sources(result.get("sources_used", [])),
            "concepts_used": list(result.get("concepts_used", [])),
            "suggested_followups": list(result.get("suggested_followups", [])),
            "retrieval_trace": list(result.get("retrieval_trace", [])),
            "intent": intent_value,
            "mode_used": result.get("mode_used"),
            "used_fallback": bool(result.get("used_fallback", False)),
            "concept_resolution": dict(result.get("concept_resolution", {})),
            "target_resolution_trace": list(result.get("target_resolution_trace", [])),
            "timings": dict(result.get("timings", {})),
        }
    except Exception as exc:
        return {
            "answer": "Hubo un problema al procesar la pregunta. Intenta nuevamente.",
            "confidence": "low",
            "sources_used": [],
            "concepts_used": [],
            "suggested_followups": [],
            "retrieval_trace": [],
            "intent": None,
            "mode_used": None,
            "used_fallback": True,
            "concept_resolution": {},
            "target_resolution_trace": [],
            "timings": {"error": str(exc)},
        }
