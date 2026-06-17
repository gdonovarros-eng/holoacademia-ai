from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel

from api.schemas.therapeutic import TherapeuticRequest, TherapeuticResponse
from api.services.therapeutic_service import run_therapeutic_analysis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/therapeutic", tags=["Therapeutic"])


class HolosRequest(BaseModel):
    prompt: str
    # Consulta opcional para recuperar material propio (RAG). Si viene, se
    # buscan fragmentos relevantes y se inyectan al prompt con prioridad.
    query: str | None = None


class HolosResponse(BaseModel):
    answer: str
    ok: bool = True
    error: str | None = None
    fuentes: int = 0


def _inyectar_material(prompt: str, query: str | None) -> tuple[str, int]:
    """Recupera material propio relevante y lo antepone al prompt con prioridad.
    Motor propio: instruye no citar cursos ni autores. Si no hay material o el
    RAG no está disponible, devuelve el prompt sin cambios."""
    if not query:
        return prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(query, k=6)
        ctx = format_context(chunks)
    except Exception:  # nunca romper la respuesta por el RAG
        return prompt, 0
    if not ctx:
        return prompt, 0
    prefijo = (
        "MATERIAL PROPIO DE REFERENCIA. Tiene PRIORIDAD sobre tu conocimiento general: "
        "apóyate en estos fragmentos para responder y respeta sus definiciones y enfoque. "
        "NUNCA menciones cursos, autores, maestros ni nombres propios que aparezcan en el material; "
        "intégralo como conocimiento propio.\n\n" + ctx + "\n\n====\n\n"
    )
    return prefijo + prompt, len(chunks)


@router.post("/holos", response_model=HolosResponse)
def generar_cuadro_holos(request: HolosRequest) -> HolosResponse:
    """Genera el Cuadro Holos con razonamiento terapéutico libre (no pasa por
    el motor académico). Si llega `query`, se ancla en el material propio (RAG)."""
    from api.chat_service import generar_respuesta_holos

    started = time.monotonic()
    prompt, fuentes = _inyectar_material(request.prompt, request.query)
    result = generar_respuesta_holos(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("therapeutic_holos elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


@router.post("/analyze", response_model=TherapeuticResponse)
def analyze_case(request: TherapeuticRequest) -> TherapeuticResponse:
    started = time.monotonic()
    data = request.model_dump(exclude_none=True)
    result = run_therapeutic_analysis(data)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "therapeutic_analyze elapsed_ms=%.2f error=%s",
        elapsed_ms,
        bool(result.get("trace", {}).get("error")),
    )
    return TherapeuticResponse(**result)
