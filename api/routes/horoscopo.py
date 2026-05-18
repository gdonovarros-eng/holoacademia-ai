"""
Rutas FastAPI para el Módulo de Horóscopo Zodiacal.

POST /horoscopo/lectura          — lectura completa síncrona
POST /horoscopo/lectura-stream   — lectura en streaming SSE (principal)
GET  /horoscopo/health           — verificación del módulo
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/horoscopo", tags=["Horóscopo"])


# ─── Sistema de prompt ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Eres un astrólogo experto especializado en horóscopo zodiacal y psicología arquetípica.\n"
    "Tu base de conocimiento incluye a Robert Hand, Louise Huber, Donna Cunningham y la tradición\n"
    "astrológica clásica hispanohablante. Generas lecturas personalizadas, profundas y terapéuticas\n"
    "— no predicciones frívolas de revista. Redacta siempre en español, con calidez y profundidad\n"
    "psicológica. Usa Markdown con headers ##."
)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class HoroscopoRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120,
                        description="Nombre del consultante")
    fecha_nacimiento: str = Field(..., description="Fecha de nacimiento — YYYY-MM-DD")
    hora_nacimiento: Optional[str] = Field(
        default=None,
        description="Hora de nacimiento — HH:MM (opcional, mejora la lectura)"
    )
    lugar_nacimiento: Optional[str] = Field(
        default=None,
        description="Ciudad, País (opcional, permite incluir tránsitos locales)"
    )
    tipo: str = Field(
        default="completo",
        description="'diario' | 'semanal' | 'completo'"
    )


class HoroscopoResponse(BaseModel):
    ok: bool
    lectura: str
    meta: dict


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_user_prompt(
    nombre: str,
    signo: str,
    elemento: str,
    modalidad: str,
    fecha_nacimiento: str,
    tipo: str,
    conocimiento: str,
    transits_section: str = "",
) -> str:
    """Construye el prompt de usuario para la lectura horoscópica."""
    return (
        f"Consultante: {nombre}\n"
        f"Signo Solar: {signo} ({elemento}, {modalidad})\n"
        f"Fecha de nacimiento: {fecha_nacimiento}\n"
        f"{transits_section}"
        f"\nCONOCIMIENTO DEL SIGNO:\n{conocimiento}\n\n"
        f"Genera un horóscopo personalizado completo para {nombre} con las siguientes secciones:\n"
        f"## Perfil de {signo}\n"
        f"## Energías Actuales\n"
        f"## Amor y Relaciones\n"
        f"## Trabajo y Propósito\n"
        f"## Salud y Cuerpo\n"
        f"## Mensaje Espiritual\n\n"
        f"Tipo de lectura: {tipo}. Si es \"diario\" sé conciso (1 párrafo por sección). "
        f"Si es \"semanal\" o \"completo\", desarrolla 2-3 párrafos por sección con profundidad.\n"
        f"Personaliza usando el nombre {nombre} en varias secciones."
    )


def _get_signo_meta(signo: str) -> tuple[str, str]:
    """Devuelve (elemento, modalidad) para un signo dado."""
    from api.astro.horoscopo_knowledge import SIGNOS
    data = SIGNOS.get(signo, {})
    return data.get("elemento", ""), data.get("modalidad", "")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/lectura", response_model=HoroscopoResponse)
async def lectura_horoscopo(
    payload: HoroscopoRequest,
    request: Request,
):
    """
    Lectura horoscópica completa — respuesta síncrona.
    Incluye: Perfil del Signo, Energías Actuales, Amor y Relaciones,
    Trabajo y Propósito, Salud y Cuerpo, Mensaje Espiritual.
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
                        f"análisis este mes en tu plan {plan_name}."
                    ),
                )

    try:
        from api.astro.horoscopo_knowledge import get_signo_solar, build_horoscopo_context
        from api.astro.engine import _get_llm_client

        # Calcular signo solar (toma el string "YYYY-MM-DD", devuelve nombre del signo)
        signo = get_signo_solar(payload.fecha_nacimiento)
        elemento, modalidad = _get_signo_meta(signo)

        # Tránsitos opcionales (requieren hora y lugar)
        transits_section = ""
        if payload.hora_nacimiento and payload.lugar_nacimiento:
            try:
                from api.astro.calculator import get_transits_today
                from api.astro.engine import _geocode
                lat, lng, tz = _geocode(payload.lugar_nacimiento)
                transitos = get_transits_today(lat, lng, tz)
                if transitos:
                    transits_section = f"Tránsitos actuales:\n{transitos}\n"
            except Exception as exc:
                logger.warning("Tránsitos no disponibles: %s", exc)

        conocimiento = build_horoscopo_context(signo)
        prompt = _build_user_prompt(
            nombre=payload.nombre,
            signo=signo,
            elemento=elemento,
            modalidad=modalidad,
            fecha_nacimiento=payload.fecha_nacimiento,
            tipo=payload.tipo,
            conocimiento=conocimiento,
            transits_section=transits_section,
        )

        client, model = _get_llm_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.72,
            max_tokens=5500,
            timeout=120.0,
        )
        lectura = response.choices[0].message.content or ""

        return HoroscopoResponse(
            ok=True,
            lectura=lectura,
            meta={
                "nombre":        payload.nombre,
                "signo":         signo,
                "elemento":      elemento,
                "modalidad":     modalidad,
                "tipo":          payload.tipo,
                "con_transitos": bool(transits_section),
            },
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Horoscopo engine error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error en el motor de horóscopo: {str(exc)}"
        )


@router.post("/lectura-stream")
async def lectura_horoscopo_stream(
    payload: HoroscopoRequest,
    request: Request,
):
    """Lectura horoscópica en streaming SSE — endpoint principal para el frontend."""

    # Validar sesión antes de crear el generador para poder devolver HTTP 429
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
                        f"análisis este mes en tu plan {plan_name}."
                    ),
                )

    async def _stream():
        try:
            from api.astro.horoscopo_knowledge import get_signo_solar, build_horoscopo_context
            from api.astro.engine import _get_llm_client

            yield f"data: {json.dumps({'status': 'Calculando signo solar…'})}\n\n"

            # get_signo_solar toma "YYYY-MM-DD" y devuelve el nombre del signo
            signo = get_signo_solar(payload.fecha_nacimiento)
            elemento, modalidad = _get_signo_meta(signo)

            yield f"data: {json.dumps({'signo': signo, 'elemento': elemento, 'modalidad': modalidad})}\n\n"

            # Tránsitos opcionales
            transits_section = ""
            if payload.hora_nacimiento and payload.lugar_nacimiento:
                try:
                    from api.astro.calculator import get_transits_today
                    from api.astro.engine import _geocode
                    lat, lng, tz = _geocode(payload.lugar_nacimiento)
                    transitos = get_transits_today(lat, lng, tz)
                    if transitos:
                        transits_section = f"Tránsitos actuales:\n{transitos}\n"
                        yield f"data: {json.dumps({'status': 'Tránsitos planetarios incluidos.'})}\n\n"
                except Exception as exc:
                    logger.warning("Tránsitos no disponibles en stream: %s", exc)

            yield f"data: {json.dumps({'status': 'Generando lectura horoscópica…'})}\n\n"

            conocimiento = build_horoscopo_context(signo)
            prompt = _build_user_prompt(
                nombre=payload.nombre,
                signo=signo,
                elemento=elemento,
                modalidad=modalidad,
                fecha_nacimiento=payload.fecha_nacimiento,
                tipo=payload.tipo,
                conocimiento=conocimiento,
                transits_section=transits_section,
            )

            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.72,
                max_tokens=5500,
                stream=True,
                timeout=120.0,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.exception("Horoscopo stream error: %s", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def horoscopo_health():
    """Verifica que el módulo de horóscopo está disponible."""
    try:
        from api.astro.horoscopo_knowledge import get_signo_solar, build_horoscopo_context

        # Test con una fecha conocida: 21 de marzo → Aries
        signo = get_signo_solar("1990-03-21")
        elemento, modalidad = _get_signo_meta(signo)
        ctx = build_horoscopo_context(signo)
        return {
            "ok":              True,
            "test_signo":      signo,
            "test_elemento":   elemento,
            "test_modalidad":  modalidad,
            "conocimiento_ok": len(ctx) > 0,
        }
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
