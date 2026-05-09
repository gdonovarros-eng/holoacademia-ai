from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from api.schemas.academic import AcademicRequest, AcademicResponse
from api.services.academic_service import run_academic_query


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/academic", tags=["Academic"])


@router.post("/ask", response_model=AcademicResponse)
def ask_academic(request: AcademicRequest) -> AcademicResponse:
    started = time.monotonic()
    result = run_academic_query(request.query, history=request.history)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "academic_ask elapsed_ms=%.2f used_fallback=%s query=%s",
        elapsed_ms,
        bool(result.get("used_fallback", False)),
        (request.query or "")[:120],
    )
    return AcademicResponse(**result)
