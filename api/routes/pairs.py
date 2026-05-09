from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from api.schemas.pairs import PairsInterpretRequest, PairsInterpretResponse
from api.services.pairs_service import interpret_found_pairs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pairs", tags=["Pairs"])


@router.post("/interpret", response_model=PairsInterpretResponse)
def interpret_pairs_endpoint(request: PairsInterpretRequest) -> PairsInterpretResponse:
    started = time.monotonic()
    result = interpret_found_pairs(
        pares_encontrados=request.pares_encontrados,
        notas=request.notas or "",
    )
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "pairs_interpret encontrados=%d no_encontrados=%d elapsed_ms=%.2f",
        result["encontrados"],
        len(result["no_encontrados"]),
        elapsed_ms,
    )
    return PairsInterpretResponse(**result)
