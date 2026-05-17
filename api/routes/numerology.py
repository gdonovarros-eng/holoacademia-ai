"""
Rutas FastAPI para el Motor de Numerología.

POST /numerology/analisis          — análisis completo del numeroscopio
POST /numerology/analisis-stream   — análisis en streaming SSE
GET  /numerology/calcular          — datos crudos del numeroscopio (sin LLM)
GET  /numerology/casa              — número numerológico de una dirección
POST /numerology/compatibilidad-stream — compatibilidad entre dos personas
GET  /numerology/health            — verificación del motor
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/numerology", tags=["Numerología"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class NumerologyRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120,
                        description="Nombre completo del consultante")
    fecha_nacimiento: str = Field(..., description="Fecha de nacimiento — YYYY-MM-DD")
    profundidad: str = Field(
        default="completo",
        description="'basico' | 'completo'"
    )
    apellido_paterno: Optional[str] = Field(
        default="",
        description="Apellido paterno (para calcular Herencia Paterna)"
    )
    apellido_materno: Optional[str] = Field(
        default="",
        description="Apellido materno (para calcular Herencia Materna)"
    )


class NumerologyResponse(BaseModel):
    ok: bool
    reporte: str
    meta: dict


class CompatibilidadRequest(BaseModel):
    nombre_a: str = Field(..., min_length=2, max_length=120)
    fecha_a:  str = Field(..., description="YYYY-MM-DD")
    nombre_b: str = Field(..., min_length=2, max_length=120)
    fecha_b:  str = Field(..., description="YYYY-MM-DD")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analisis", response_model=NumerologyResponse)
async def analisis_numerologico(
    payload: NumerologyRequest,
    request: Request,
):
    """
    Análisis numerológico completo. Incluye todos los indicadores:
    Expresión, Impulso, Impresión, Esencia, Locomotora, Planos,
    Alma, Karma, Misión, Vibración Latente, Herencias, Pináculos,
    Desafíos, Ciclos de vida, Ciclos personales (Año/Mes/Día Personal),
    Deudas Kármicas, Potencias y Carencias.
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
        from api.numerology.engine import run_numerology_analysis

        result = run_numerology_analysis(
            nombre=payload.nombre,
            fecha_nacimiento=payload.fecha_nacimiento,
            profundidad=payload.profundidad,
            apellido_paterno=payload.apellido_paterno or "",
            apellido_materno=payload.apellido_materno or "",
        )

        return NumerologyResponse(
            ok=True,
            reporte=result["reporte"],
            meta=result["meta"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Numerology engine error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error en el motor numerológico: {str(e)}"
        )


@router.post("/analisis-stream")
async def analisis_numerologico_stream(
    payload: NumerologyRequest,
    request: Request,
):
    """Análisis numerológico en streaming SSE."""
    import json, datetime

    async def _stream():
        try:
            from api.numerology.calculator import calcular_numeroscopio
            from api.numerology.prompt_builder import build_numerology_prompt
            from api.numerology.engine import _get_llm_client

            yield f"data: {json.dumps({'status': 'Calculando numeroscopio...'})}\n\n"

            fecha = datetime.date.fromisoformat(payload.fecha_nacimiento)
            datos = calcular_numeroscopio(
                payload.nombre,
                fecha.day, fecha.month, fecha.year,
                apellido_paterno=payload.apellido_paterno or "",
                apellido_materno=payload.apellido_materno or "",
            )

            # Enviar datos crudos al cliente para renderizar la tabla
            yield f"data: {json.dumps({'datos': datos['resumen']})}\n\n"

            # Enviar deudas kármicas si las hay
            if datos["deudas_karmicas"]:
                yield f"data: {json.dumps({'deudas': datos['deudas_karmicas']})}\n\n"

            yield f"data: {json.dumps({'status': 'Generando análisis numerológico...'})}\n\n"

            prompt = build_numerology_prompt(payload.nombre, datos, payload.profundidad)

            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
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

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/calcular")
async def calcular_numeroscopio_raw(
    nombre: str,
    fecha: str,
    apellido_paterno: str = "",
    apellido_materno: str = "",
):
    """
    Retorna todos los datos numerológicos sin generar el reporte IA.
    Útil para mostrar la tabla completa en la UI antes del análisis.
    """
    try:
        import datetime
        from api.numerology.calculator import calcular_numeroscopio

        if not nombre or len(nombre.strip()) < 2:
            raise HTTPException(status_code=400, detail="Se requiere nombre (mínimo 2 caracteres).")
        if not fecha:
            raise HTTPException(status_code=400, detail="Se requiere fecha en formato YYYY-MM-DD.")

        d = datetime.date.fromisoformat(fecha)
        datos = calcular_numeroscopio(
            nombre.strip(), d.day, d.month, d.year,
            apellido_paterno=apellido_paterno.strip(),
            apellido_materno=apellido_materno.strip(),
        )

        return {"ok": True, "datos": datos}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("calcular error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/casa")
async def numero_de_casa(numero: str):
    """
    Calcula el número numerológico de un hogar.
    Pasa el número de calle/puerta como query param.
    Ejemplo: /numerology/casa?numero=638  →  8
    """
    try:
        from api.numerology.calculator import numero_casa
        if not numero or not any(ch.isdigit() for ch in numero):
            raise HTTPException(status_code=400, detail="Se requiere al menos un dígito en el número de casa.")
        val = numero_casa(numero)
        return {"ok": True, "numero_casa": val, "input": numero}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compatibilidad-stream")
async def compatibilidad_stream(payload: CompatibilidadRequest):
    """SSE: análisis de compatibilidad numerológica entre dos personas."""
    import json, datetime

    async def _stream():
        try:
            from api.numerology.calculator import calcular_numeroscopio
            from api.numerology.engine import _get_llm_client
            from api.numerology.prompt_builder import _nombre_num, _star

            yield f"data: {json.dumps({'status': f'Calculando numeroscopio de {payload.nombre_a}...'})}\n\n"
            fa = datetime.date.fromisoformat(payload.fecha_a)
            da = calcular_numeroscopio(payload.nombre_a, fa.day, fa.month, fa.year)

            yield f"data: {json.dumps({'status': f'Calculando numeroscopio de {payload.nombre_b}...'})}\n\n"
            fb = datetime.date.fromisoformat(payload.fecha_b)
            db = calcular_numeroscopio(payload.nombre_b, fb.day, fb.month, fb.year)

            yield f"data: {json.dumps({'status': 'Generando análisis de compatibilidad...'})}\n\n"

            ra = da["resumen"]
            rb = db["resumen"]
            edad_a = datetime.date.today().year - fa.year
            edad_b = datetime.date.today().year - fb.year

            def resumen_persona(nombre, r, edad):
                return (
                    f"═══ {nombre.upper()} ({edad} años) ═══\n"
                    f"  Misión:          {r['mision']} — {_nombre_num(r['mision'])}\n"
                    f"  Expresión:       {r['expresion']} — {_nombre_num(r['expresion'])}\n"
                    f"  Impulso:         {r['impulso']} — {_nombre_num(r['impulso'])}\n"
                    f"  Impresión:       {r['impresion']} — {_nombre_num(r['impresion'])}\n"
                    f"  Alma:            {r['alma']} — {_nombre_num(r['alma'])}\n"
                    f"  Karma:           {r['karma']} — {_nombre_num(r['karma'])}\n"
                    f"  Vibr. Latente:   {r['latente']} — {_nombre_num(r['latente'])}\n"
                    f"  Año Personal:    {r['año_personal']}\n"
                )

            prompt = f"""Eres numerólogo experto en compatibilidad (Numerhología + Pythagorean).
Analiza la compatibilidad entre {payload.nombre_a} y {payload.nombre_b}.

{resumen_persona(payload.nombre_a, ra, edad_a)}
{resumen_persona(payload.nombre_b, rb, edad_b)}

## 1. Compatibilidad de Misión de Vida
¿Sus misiones son complementarias o en tensión? ¿Pueden apoyarse mutuamente en su propósito?

## 2. Dinámica Expresión e Impulso
Cómo se complementan o chocan sus formas de manifestarse y sus motivaciones internas.

## 3. Lo que se perciben mutuamente
La Impresión que A genera en B y viceversa. ¿Se reconocen o se malinterpretan?

## 4. Alma y Karma — Intimidad y vida pública
¿Sus personalidades privadas y públicas son compatibles?

## 5. Vibración Latente compartida
¿Qué potencial emergen juntos cuando maduran?

## 6. Momento actual
Año Personal de cada uno ({ra['año_personal']} y {rb['año_personal']}): ¿están en fases complementarias o divergentes de su ciclo vital?

## 7. Aprendizajes mutuos
¿Qué viene cada uno a enseñarle al otro? ¿Qué heridas pueden activarse?

## 8. Síntesis para el terapeuta
3-4 frases: potencial de esta relación, desafío central y sugerencia terapéutica.

Tono empático y orientado al crecimiento. Solo en español."""

            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.72,
                max_tokens=4000,
                stream=True,
                timeout=120.0,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {json.dumps({'token': delta})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def numerology_health():
    """Verifica que el motor numerológico está disponible."""
    try:
        from api.numerology.calculator import calcular_numeroscopio
        test = calcular_numeroscopio("Alejandro", 11, 11, 1984)
        r = test["resumen"]
        return {
            "ok": True,
            "test_mision":    r["mision"],
            "test_expresion": r["expresion"],
            "test_año_pers":  r["año_personal"],
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)
