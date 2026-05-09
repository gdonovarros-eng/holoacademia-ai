from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from api.schemas.protocols import ProtocolGuideRequest, ProtocolGuideResponse
from api.services.protocols_service import run_protocol_guide


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protocols", tags=["Protocols"])


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
