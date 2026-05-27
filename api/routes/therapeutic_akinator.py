"""
Endpoints REST para el motor terapéutico conversacional tipo Akinator.

Reemplaza el flujo one-shot de /therapeutic/analyze por uno conversacional:

1. POST /therapeutic/start
   Recibe el cuestionario inicial (intake) y devuelve session_id +
   hipótesis iniciales + primera pregunta dirigida.

2. POST /therapeutic/answer
   Recibe session_id + respuesta (si/no/no_se) y devuelve hipótesis
   actualizadas + siguiente pregunta. Si llega a confianza alta o
   se acaban las preguntas, devuelve la ficha clínica completa.

3. GET /therapeutic/state/{session_id}
   Devuelve estado actual de la sesión.

El endpoint /therapeutic/analyze original se mantiene operativo y ahora
también arranca una sesión Akinator si se pasa el flag `iniciar_dialogo`.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.therapy.conversation_engine import (
    start_conversation,
    answer_question,
    get_session_state,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/therapeutic", tags=["Therapeutic Akinator"])


class IntakeRequest(BaseModel):
    motivo_consulta: str | None = None
    sintomas: list[str] | None = None
    inicio: str | None = None
    duracion: str | None = None
    frecuencia: str | None = None
    antecedentes: list[str] | None = None
    contexto_emocional: str | None = None
    observaciones: str | None = None
    pregunta_del_terapeuta: str | None = None
    family_notes: str | None = None


class AnswerRequest(BaseModel):
    session_id: str
    respuesta: str = Field(..., description="si | no | no_se")


@router.post("/start")
def start(intake: IntakeRequest) -> dict[str, Any]:
    """Inicia conversación Akinator a partir del cuestionario inicial."""
    data = intake.model_dump(exclude_none=True)
    try:
        return start_conversation(data)
    except Exception as e:
        logger.exception("therapeutic_akinator_start error: %s", e)
        return {"error": "internal", "detail": str(e)}


@router.post("/answer")
def answer(req: AnswerRequest) -> dict[str, Any]:
    """Procesa una respuesta y avanza la conversación."""
    try:
        return answer_question(req.session_id, req.respuesta)
    except Exception as e:
        logger.exception("therapeutic_akinator_answer error: %s", e)
        return {"error": "internal", "detail": str(e)}


@router.get("/state/{session_id}")
def state(session_id: str) -> dict[str, Any]:
    """Estado actual sin avanzar la conversación."""
    try:
        return get_session_state(session_id)
    except Exception as e:
        logger.exception("therapeutic_akinator_state error: %s", e)
        return {"error": "internal", "detail": str(e)}
