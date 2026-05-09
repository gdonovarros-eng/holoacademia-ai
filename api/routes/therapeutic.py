from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from api.schemas.therapeutic import TherapeuticRequest, TherapeuticResponse
from api.services.therapeutic_service import run_therapeutic_analysis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/therapeutic", tags=["Therapeutic"])


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
