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
        "MATERIAL PROPIO DE REFERENCIA. Cuando sea pertinente a la pregunta, da PRIORIDAD a estos "
        "fragmentos sobre tu conocimiento general y respeta sus definiciones y enfoque. "
        "Si un fragmento NO es relevante a lo que se pregunta, ignóralo: responde SIEMPRE a la "
        "pregunta concreta, no resumas el material. "
        "NUNCA menciones cursos, autores, maestros ni nombres propios que aparezcan en el material; "
        "intégralo como conocimiento propio.\n\n" + ctx + "\n\n====\n\n"
    )
    return prefijo + prompt, len(chunks)


class BiodescoRequest(BaseModel):
    prompt: str
    query: str | None = None


# El motor dedicado se ancla SOLO en el corpus de libros de biodescodificación.
_BIODESCO_COURSE_IDS = ["libros-biodescodificacion"]


@router.post("/biodescodificacion", response_model=HolosResponse)
def motor_biodescodificacion(request: BiodescoRequest) -> HolosResponse:
    """Motor dedicado de Biodescodificación: razona en clave de descodificación
    biológica, anclado únicamente en el corpus de libros de biodescodificación."""
    from api.chat_service import generar_respuesta_biodescodificacion

    started = time.monotonic()
    q = (request.query or request.prompt or "").strip()
    prompt, fuentes = request.prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=8, course_ids=_BIODESCO_COURSE_IDS)
        ctx = format_context(chunks, max_chars=7000)
        if ctx:
            prompt = (
                "MATERIAL DE BIODESCODIFICACIÓN (base prioritaria; respeta sus definiciones "
                "y enfoque; nunca menciones autores, libros ni cursos que aparezcan en él):\n\n"
                + ctx + "\n\n====\n\n" + request.prompt
            )
            fuentes = len(chunks)
    except Exception:
        pass
    result = generar_respuesta_biodescodificacion(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("biodescodificacion elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


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
