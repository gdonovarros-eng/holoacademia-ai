from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.schemas.protocols import (
    ProtocolGuideRequest,
    ProtocolGuideResponse,
    ProtocolSearchRequest,
    ProtocolSearchResponse,
)
from api.services.protocols_service import get_catalog, run_protocol_guide, search_protocols


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protocols", tags=["Protocols"])


@router.get("/catalog")
def protocol_catalog() -> JSONResponse:
    return JSONResponse(content=get_catalog())


@router.post("/guide", response_model=ProtocolGuideResponse)
def protocol_guide(request: ProtocolGuideRequest) -> ProtocolGuideResponse:
    started = time.monotonic()
    data = request.model_dump(exclude_none=True)
    result = run_protocol_guide(data)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "protocols_guide elapsed_ms=%.2f found=%s protocol_id=%s protocol_name=%s error=%s",
        elapsed_ms,
        bool(result.get("found", False)),
        data.get("protocol_id"),
        data.get("protocol_name"),
        bool(result.get("trace", {}).get("error")),
    )
    return ProtocolGuideResponse(**result)


@router.post("/search", response_model=ProtocolSearchResponse)
def protocol_search(request: ProtocolSearchRequest) -> ProtocolSearchResponse:
    started = time.monotonic()
    result = search_protocols(
        query=request.query,
        notas=request.notas or "",
    )
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "protocols_search elapsed_ms=%.2f sistema=%s conflictos=%d protocolo=%s",
        elapsed_ms,
        result.get("sistema_detectado"),
        len(result.get("conflictos_relevantes", [])),
        result.get("protocolo_sugerido", {}).get("id") if result.get("protocolo_sugerido") else None,
    )
    return ProtocolSearchResponse(**result)
