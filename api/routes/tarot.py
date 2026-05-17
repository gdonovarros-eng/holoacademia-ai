"""
Rutas FastAPI para el Motor de Tarot.

POST /tarot/lectura          — lectura completa con LLM
POST /tarot/lectura-stream   — lectura en streaming SSE
GET  /tarot/perfil           — perfil tarótico sin LLM
GET  /tarot/tiradas          — catálogo de tiradas disponibles
GET  /tarot/carta/{nombre}   — datos de una carta específica
GET  /tarot/health           — health check del módulo
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tarot", tags=["Tarot"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CartaEnTirada(BaseModel):
    posicion: str = Field(..., description="Nombre de la posición en la tirada")
    carta: str = Field(..., description="Nombre completo de la carta")
    invertida: bool = Field(default=False, description="True si la carta está invertida")


class TarotRequest(BaseModel):
    pregunta: str = Field(..., min_length=5, max_length=500,
                          description="Pregunta o intención del consultante")
    tirada: str = Field(..., description="Nombre de la tirada (carta_del_dia, tres_cartas, etc.)")
    cartas: list[CartaEnTirada] = Field(..., min_length=1,
                                        description="Cartas reveladas en la tirada")
    fecha_nacimiento: Optional[str] = Field(
        default=None, description="Fecha de nacimiento del consultante — YYYY-MM-DD"
    )
    signo_solar: Optional[str] = Field(
        default=None, description="Signo zodiacal solar del consultante"
    )
    numero_alma: Optional[int] = Field(
        default=None, description="Número del alma de la numerología (del perfil numerológico)"
    )
    profundidad: str = Field(
        default="estandar",
        description="'rapida' | 'estandar' | 'profunda'"
    )
    enfoque: str = Field(
        default="terapeutico",
        description="'terapeutico' | 'orientativo' | 'espiritual'"
    )
    sistema: str = Field(
        default="rws",
        description="Sistema de tarot: 'rws' | 'marsella' | 'thoth'"
    )


class TarotResponse(BaseModel):
    ok: bool
    lectura: str
    meta: dict


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/lectura", response_model=TarotResponse)
async def lectura_tarot(
    payload: TarotRequest,
    request: Request,
):
    """
    Lectura de tarot completa con análisis del LLM.
    Incluye perfil tarótico del consultante (si hay fecha de nacimiento)
    y la lectura narrativo-terapéutica de las cartas.
    """
    from api.main import _get_session_user, _DB_PATH, _EMBED_SECRET
    from api.db import try_consume, PLAN_NAMES

    if _EMBED_SECRET:
        sess = _get_session_user(request)
        if sess:
            user_id, plan = sess
            allowed, used, limit = try_consume(_DB_PATH, user_id, "sinodal")
            if not allowed:
                plan_name = PLAN_NAMES.get(plan, plan)
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Límite mensual alcanzado. Has usado {used} de {limit} "
                        f"lecturas este mes en tu plan {plan_name}."
                    ),
                )

    try:
        from api.tarot.engine import run_tarot_reading

        cartas_raw = [c.model_dump() for c in payload.cartas]
        result = run_tarot_reading(
            pregunta=payload.pregunta,
            tirada=payload.tirada,
            cartas=cartas_raw,
            fecha_nacimiento=payload.fecha_nacimiento,
            signo_solar=payload.signo_solar or "",
            numero_alma=payload.numero_alma,
            profundidad=payload.profundidad,
            enfoque=payload.enfoque,
            sistema=payload.sistema,
        )
        return TarotResponse(
            ok=True,
            lectura=result["lectura"],
            meta=result["meta"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Tarot engine error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error en el motor de tarot: {str(e)}"
        )


@router.post("/lectura-stream")
async def lectura_tarot_stream(
    payload: TarotRequest,
    request: Request,
):
    """
    Lectura de tarot en streaming SSE.

    Eventos enviados:
    1. {"status": "Calculando perfil tarótico..."}
    2. {"perfil": {...}}  — perfil calculado (se puede renderizar antes del LLM)
    3. {"status": "Generando lectura..."}
    4. {"token": "..."} × N  — tokens del LLM
    5. [DONE]
    """
    import json
    import datetime as dt

    async def _stream():
        try:
            from api.tarot.calculator import calcular_perfil_tarot
            from api.tarot.prompt_builder import build_tarot_prompt
            from api.tarot.engine import _get_llm_client

            yield f"data: {json.dumps({'status': 'Calculando perfil tarótico...'})}\n\n"

            # Calcular perfil si hay fecha de nacimiento
            perfil: dict = {}
            if payload.fecha_nacimiento:
                try:
                    fecha = dt.date.fromisoformat(payload.fecha_nacimiento)
                    perfil = calcular_perfil_tarot(
                        dia=fecha.day,
                        mes=fecha.month,
                        anio=fecha.year,
                        signo_solar=payload.signo_solar or "",
                        numero_alma_numerologia=payload.numero_alma,
                        sistema=payload.sistema,
                    )
                    yield f"data: {json.dumps({'perfil': perfil})}\n\n"
                except Exception as e:
                    logger.warning("Error calculando perfil tarótico: %s", e)
                    yield f"data: {json.dumps({'perfil': {}})}\n\n"

            yield f"data: {json.dumps({'status': 'Generando lectura...'})}\n\n"

            cartas_raw = [c.model_dump() for c in payload.cartas]
            prompt = build_tarot_prompt(
                pregunta=payload.pregunta,
                tirada_nombre=payload.tirada,
                cartas=cartas_raw,
                perfil=perfil or None,
                profundidad=payload.profundidad,
                enfoque=payload.enfoque,
                sistema=payload.sistema,
            )

            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.76,
                max_tokens=5500,
                stream=True,
                timeout=120.0,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("Tarot stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/perfil")
async def perfil_tarotico(
    fecha: str,
    signo: str = "",
    sistema: str = "rws",
    numero_alma: int = 0,
):
    """
    Calcula el perfil tarótico completo del consultante sin generar lectura IA.
    Útil para mostrar las cartas personales en la UI antes de una tirada.

    Parámetros:
      fecha       — fecha de nacimiento en formato YYYY-MM-DD
      signo       — signo zodiacal solar (opcional)
      sistema     — rws | marsella | thoth (default: rws)
      numero_alma — número del alma de numerología (opcional, 1-22)
    """
    try:
        import datetime as dt
        if not fecha:
            raise HTTPException(status_code=400, detail="Se requiere fecha en formato YYYY-MM-DD.")

        d = dt.date.fromisoformat(fecha)
        from api.tarot.calculator import calcular_perfil_tarot

        perfil = calcular_perfil_tarot(
            dia=d.day,
            mes=d.month,
            anio=d.year,
            signo_solar=signo,
            numero_alma_numerologia=numero_alma or None,
            sistema=sistema,
        )
        return {"ok": True, "perfil": perfil}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Perfil tarótico error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiradas")
async def catalogo_tiradas():
    """
    Retorna el catálogo completo de tiradas disponibles con sus posiciones.
    """
    from api.tarot.knowledge import TIRADAS
    return {"ok": True, "tiradas": TIRADAS}


@router.get("/carta/{nombre}")
async def datos_carta(nombre: str):
    """
    Retorna los datos completos de una carta específica.
    El nombre debe ser el nombre español completo (ej: 'El Loco', 'As de Bastos').
    """
    from api.tarot.knowledge import ARCANOS_MAYORES, ARCANOS_MENORES
    import urllib.parse

    nombre_decoded = urllib.parse.unquote(nombre).strip()

    # Buscar en mayores
    if nombre_decoded in ARCANOS_MAYORES:
        return {"ok": True, "tipo": "mayor", "nombre": nombre_decoded,
                "datos": ARCANOS_MAYORES[nombre_decoded]}

    # Buscar por nombre_rws o nombre_marsella
    for k, v in ARCANOS_MAYORES.items():
        if (v.get("nombre_rws", "").lower() == nombre_decoded.lower()
                or v.get("nombre_marsella", "").lower() == nombre_decoded.lower()
                or v.get("nombre_thoth", "").lower() == nombre_decoded.lower()):
            return {"ok": True, "tipo": "mayor", "nombre": k, "datos": v}

    # Buscar en menores
    if nombre_decoded in ARCANOS_MENORES:
        return {"ok": True, "tipo": "menor", "nombre": nombre_decoded,
                "datos": ARCANOS_MENORES[nombre_decoded]}

    # Buscar insensible a mayúsculas en menores
    for k, v in ARCANOS_MENORES.items():
        if k.lower() == nombre_decoded.lower():
            return {"ok": True, "tipo": "menor", "nombre": k, "datos": v}

    raise HTTPException(
        status_code=404,
        detail=f"Carta '{nombre_decoded}' no encontrada. "
               "Usa el nombre español completo (ej: 'El Loco', 'As de Bastos')."
    )


class TarotChatMessage(BaseModel):
    role: str = Field(..., description="'user' o 'assistant'")
    content: str = Field(..., description="Contenido del mensaje")


class TarotChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1, max_length=1000,
                          description="Pregunta de seguimiento del consultante")
    contexto_lectura: str = Field(..., description="Texto completo de la lectura original")
    historial: list[TarotChatMessage] = Field(
        default_factory=list,
        description="Historial de mensajes anteriores del chat"
    )


@router.post("/chat-stream")
async def chat_sobre_lectura(
    payload: TarotChatRequest,
    request: Request,
):
    """
    Chat de seguimiento sobre una lectura de tarot completada.

    El consultante puede hacer preguntas sobre las cartas, pedir más
    profundidad sobre una posición específica, o explorar conexiones entre cartas.

    Eventos SSE:
      {"token": "..."} × N
      [DONE]
    """
    import json

    async def _stream():
        try:
            from api.tarot.engine import _get_llm_client

            sistema = (
                "Eres un tarotista terapéutico experto y acompañante de crecimiento personal. "
                "El consultante acaba de recibir la siguiente lectura de tarot:\n\n"
                f"---\n{payload.contexto_lectura}\n---\n\n"
                "Responde sus preguntas de seguimiento con profundidad, calidez y precisión. "
                "Mantén el tono terapéutico, simbólico y reflexivo. "
                "Si preguntan por una carta específica, profundiza en su simbología y relación "
                "con la pregunta original. Responde en español, en formato Markdown cuando sea útil."
            )

            messages = [{"role": "system", "content": sistema}]

            # Agregar historial previo
            for msg in payload.historial[-10:]:  # máximo 10 turnos de contexto
                messages.append({"role": msg.role, "content": msg.content})

            # Agregar la pregunta actual
            messages.append({"role": "user", "content": payload.pregunta})

            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.72,
                max_tokens=1500,
                stream=True,
                timeout=60.0,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("Tarot chat stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def tarot_health():
    """Verifica que el motor de tarot está disponible."""
    try:
        from api.tarot.calculator import calcular_perfil_tarot
        from api.tarot.knowledge import ARCANOS_MAYORES, ARCANOS_MENORES, TIRADAS

        test = calcular_perfil_tarot(21, 12, 1985, signo_solar="sagitario")
        return {
            "ok": True,
            "mayores": len(ARCANOS_MAYORES),
            "menores": len(ARCANOS_MENORES),
            "tiradas": len(TIRADAS),
            "test_personalidad": test["personalidad"]["nombre"],
            "test_zodiaco": test["carta_zodiaco"]["nombre"],
        }
    except Exception as e:
        logger.exception("Tarot health check failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)
