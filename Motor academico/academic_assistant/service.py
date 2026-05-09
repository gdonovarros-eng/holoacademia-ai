from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .answer_generator import AcademicLLMClient, generate_academic_answer
from .context_builder import build_academic_context
from .loader import load_academic_course_data
from .models import AcademicKnowledgeBase
from .retriever import detect_query_intent, search_academic_context

logger = logging.getLogger(__name__)

DEEP_MODE_SIGNALS = (
    "explicame mas",
    "explícame más",
    "dame mas detalle",
    "dame más detalle",
    "profundiza",
    "completo",
    "a fondo",
    "detalladamente",
    "extiendete",
    "extiéndete",
    "quiero entenderlo mejor",
)


def detect_response_mode(query: str) -> str:
    text = (query or "").strip().lower()
    if any(signal in text for signal in DEEP_MODE_SIGNALS):
        return "deep"
    return "fast"


class AcademicAssistantService:
    def __init__(self, course_dir: str | Path | None = None, llm_client: AcademicLLMClient | None = None) -> None:
        self.knowledge: AcademicKnowledgeBase = load_academic_course_data(course_dir)
        self.llm_client = llm_client or AcademicLLMClient()

    def _invalid_query_response(self) -> dict[str, Any]:
        return {
            "answer": "Necesito una pregunta académica más clara para poder ayudarte. Por ejemplo: un concepto, un módulo o una diferencia entre temas.",
            "confidence": "low",
            "sources_used": [],
            "concepts_used": [],
            "suggested_followups": [
                "¿Qué es un concepto específico de este curso?",
                "Resume un módulo del curso",
                "Explícame un tema más fácil",
            ],
            "retrieval_trace": [],
            "context": {},
            "course_id": self.knowledge.course_id,
            "warnings": self.knowledge.warnings,
        }

    def _is_valid_query(self, query: str) -> bool:
        text = (query or "").strip()
        if not text:
            return False
        return any(char.isalnum() for char in text)

    def answer_academic_query(self, query: str, top_k: int = 8, history: list | None = None) -> dict[str, Any]:
        if not self._is_valid_query(query):
            return self._invalid_query_response()

        total_started = time.monotonic()
        response_mode = detect_response_mode(query)
        retrieval_started = time.monotonic()
        intent_data = detect_query_intent(query, knowledge=self.knowledge)
        results = search_academic_context(
            query=query,
            knowledge=self.knowledge,
            top_k=max(1, top_k),
            intent_data=intent_data,
        )
        retrieval_ms = round((time.monotonic() - retrieval_started) * 1000, 2)

        context_started = time.monotonic()
        context = build_academic_context(query=query, results=results, intent_data=intent_data, response_mode=response_mode)
        context["history"] = history or []
        context_ms = round((time.monotonic() - context_started) * 1000, 2)

        llm_started = time.monotonic()
        try:
            response = generate_academic_answer(query=query, context=context, llm_client=self.llm_client, response_mode=response_mode)
        except Exception:
            fallback_client = AcademicLLMClient()
            fallback_client.enabled = False
            fallback_client.client = None
            response = generate_academic_answer(query=query, context=context, llm_client=fallback_client, response_mode=response_mode)
        llm_ms = round((time.monotonic() - llm_started) * 1000, 2)
        total_ms = round((time.monotonic() - total_started) * 1000, 2)

        timings = {
            "retrieval_ms": retrieval_ms,
            "context_building_ms": context_ms,
            "llm_ms": llm_ms,
            "total_ms": total_ms,
        }
        response["course_id"] = self.knowledge.course_id
        response["warnings"] = self.knowledge.warnings
        response["intent"] = intent_data
        response["target_resolution_trace"] = intent_data.get("target_resolution_trace", [])
        response["concept_resolution"] = intent_data.get("concept_resolution", {})
        response["mode_used"] = response_mode
        response["timings"] = timings
        response["retrieval_ms"] = retrieval_ms
        response["context_building_ms"] = context_ms
        response["llm_ms"] = llm_ms
        response["total_ms"] = total_ms
        if "generation" in response:
            response["used_fallback"] = bool(response["generation"].get("used_fallback", False))
        logger.info(
            "academic_query course=%s intent=%s mode=%s retrieval_ms=%.2f context_ms=%.2f llm_ms=%.2f total_ms=%.2f",
            self.knowledge.course_id,
            intent_data.get("intent", "general_academic"),
            response_mode,
            retrieval_ms,
            context_ms,
            llm_ms,
            total_ms,
        )
        return response


def answer_academic_query(query: str, top_k: int = 8, course_dir: str | Path | None = None, history: list | None = None) -> dict[str, Any]:
    service = AcademicAssistantService(course_dir=course_dir)
    return service.answer_academic_query(query=query, top_k=top_k, history=history)
