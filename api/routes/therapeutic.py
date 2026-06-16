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


class HolosResponse(BaseModel):
    answer: str
    ok: bool = True
    error: str | None = None


@router.post("/holos", response_model=HolosResponse)
def generar_cuadro_holos(request: HolosRequest) -> HolosResponse:
    """Genera el Cuadro Holos con razonamiento terapéutico libre (no pasa por
    el motor académico, restringido al contenido del curso)."""
    from api.chat_service import generar_respuesta_holos

    started = time.monotonic()
    result = generar_respuesta_holos(request.prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("therapeutic_holos elapsed_ms=%.2f ok=%s", elapsed_ms, bool(result.get("ok")))
    return HolosResponse(**result)


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
