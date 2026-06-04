"""
Rutas FastAPI para el Motor de Análisis Astrológico.

POST /astro/analisis    — análisis completo (natal + RS + RSP + Mensal)
GET  /astro/health      — verificación del motor
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/astro", tags=["Astrología"])


# ─── Schemas ─────────────────────────────────────────────────────────────────────

class AstroRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre del consultante")
    fecha_nacimiento: str = Field(..., description="Fecha de nacimiento — formato YYYY-MM-DD")
    hora_nacimiento: str = Field(..., description="Hora de nacimiento local — formato HH:MM")
    lugar_nacimiento: str = Field(..., description="Ciudad y país de nacimiento (ej: 'Ciudad de Mexico, Mexico')")
    lugar_actual: Optional[str] = Field(
        default=None,
        description="Ciudad actual para la RS (si difiere del lugar de nacimiento)"
    )
    profundidad: str = Field(
        default="completo",
        description="Nivel del análisis: 'basico' (solo natal+RS) | 'completo' (natal+RS+RSP+Mensal)"
    )
    incluir_rsp: bool = Field(default=True, description="Incluir RSP sidérea (método Froger)")
    incluir_mensal: bool = Field(default=True, description="Incluir Mensal del mes actual (método Privat)")


class AstroResponse(BaseModel):
    ok: bool
    reporte: str
    meta: dict


# ─── Endpoints ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def astro_health():
    """Verifica que el motor astrológico y las efémeras están disponibles."""
    try:
        import swisseph as swe
        import kerykeion
        return {"ok": True, "ephemeris": "Swiss Ephemeris disponible", "kerykeion": "OK"}
    except ImportError as e:
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=503,
        )


@router.post("/analisis", response_model=AstroResponse)
async def analisis_astrologico(
    payload: AstroRequest,
    request: Request,
):
    """
    Motor de análisis astrológico completo.

    Calcula y analiza:
    - Carta natal (planetas, casas, aspectos, dignidades, figuras)
    - Revolución Solar del año actual (Volguine)
    - RSP sidérea con corrección por precesión (Froger)
    - Mensal / Revolución Lunar del mes actual (Privat)

    Retorna un análisis narrativo completo en español redactado por IA.
    """
    # Control de uso (usa el mismo sistema de sesión de Holoacademia)
    from api.main import _get_session_user, _DB_PATH, _EMBED_SECRET
    from api.db import try_consume, PLAN_NAMES

    if _EMBED_SECRET:
        sess = _get_session_user(request)
        if sess:
            user_id, plan = sess
            # El análisis astrológico consume del mismo cupo que el modo "terapeuta"
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
        from api.astro.engine import run_astro_analysis

        result = run_astro_analysis(
            nombre=payload.nombre,
            fecha_nacimiento=payload.fecha_nacimiento,
            hora_nacimiento=payload.hora_nacimiento,
            lugar_nacimiento=payload.lugar_nacimiento,
            lugar_actual=payload.lugar_actual,
            profundidad=payload.profundidad,
            incluir_rsp=payload.incluir_rsp,
            incluir_mensal=payload.incluir_mensal,
        )

        return AstroResponse(
            ok=True,
            reporte=result["reporte"],
            meta=result["meta"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Astro engine error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error en el motor astrológico: {str(e)}"
        )


@router.post("/analisis-stream")
async def analisis_astrologico_stream(
    payload: AstroRequest,
    request: Request,
):
    """
    Versión streaming del análisis astrológico.
    Calcula primero los datos (sin streaming) y luego emite el reporte token a token.
    """
    import json
    from api.astro.calculator import (
        get_natal_data, get_solar_return, get_rsp, get_mensal,
        compute_house_superposition,
    )
    from api.astro.engine import _geocode
    from api.astro.prompt_builder import build_mega_prompt
    import datetime

    async def _stream():
        try:
            # Parse
            fecha = datetime.date.fromisoformat(payload.fecha_nacimiento)
            h, m = [int(x) for x in payload.hora_nacimiento.split(":")]
            year, month, day = fecha.year, fecha.month, fecha.day
            lugar_rs = payload.lugar_actual or payload.lugar_nacimiento

            lat_n, lng_n, tz_n = _geocode(payload.lugar_nacimiento)
            lat_rs, lng_rs, tz_rs = _geocode(lugar_rs)

            yield f"data: {json.dumps({'status': 'Calculando carta natal...'})}\n\n"
            natal = get_natal_data(payload.nombre, year, month, day, h, m, lat_n, lng_n, tz_n)
            natal_sun_abs = natal["planetas"].get("sun", {}).get("abs_pos", 0.0)

            sr_year = datetime.date.today().year
            yield f"data: {json.dumps({'status': 'Calculando Revolución Solar...'})}\n\n"
            rs = get_solar_return(natal_sun_abs, sr_year, lat_rs, lng_rs, tz_rs)

            rsp = None
            if payload.incluir_rsp:
                edad = sr_year - year
                if edad > 0:
                    yield f"data: {json.dumps({'status': 'Calculando RSP sidérea...'})}\n\n"
                    try:
                        rsp = get_rsp(natal_sun_abs, edad, sr_year, lat_n, lng_n, tz_n)
                    except Exception:
                        pass

            mensal = None
            if payload.incluir_mensal:
                rs_moon_abs = rs["planetas"].get("moon", {}).get("abs_pos", 0.0)
                if rs_moon_abs:
                    yield f"data: {json.dumps({'status': 'Calculando Mensal...'})}\n\n"
                    try:
                        mensal = get_mensal(rs_moon_abs, rs["fecha"], lat_rs, lng_rs, tz_rs)
                    except Exception:
                        pass

            superposicion = compute_house_superposition(rs.get("casas", {}), natal.get("casas", {}))
            edad = sr_year - year
            prompt = build_mega_prompt(
                nombre=payload.nombre, natal=natal, rs=rs, rsp=rsp, mensal=mensal,
                transitos=None, superposicion=superposicion, edad=edad,
                fecha_nacimiento=payload.fecha_nacimiento,
                lugar_nacimiento=payload.lugar_nacimiento,
                lugar_actual=lugar_rs, profundidad=payload.profundidad,
            )

            yield f"data: {json.dumps({'status': 'Generando análisis...'})}\n\n"

            # LLM streaming
            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=6000,
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


# ─── Carta natal SVG ──────────────────────────────────────────────────────────

@router.get("/carta")
async def carta_natal_svg(
    nombre: str = "Consultante",
    fecha: str = "",          # YYYY-MM-DD
    hora: str = "12:00",      # HH:MM
    lugar: str = "",
    tipo: str = "natal",      # natal | rs
):
    """
    Devuelve el SVG de la carta natal (o RS) para mostrar en el navegador.
    Parámetros via query string: nombre, fecha, hora, lugar, tipo.
    """
    import datetime
    import warnings
    from fastapi.responses import Response
    from api.astro.engine import _geocode
    from api.astro.calculator import _kerykeion_subject

    if not fecha or not lugar:
        raise HTTPException(status_code=400, detail="Se requieren fecha y lugar.")

    try:
        d = datetime.date.fromisoformat(fecha)
        h, m = [int(x) for x in hora.split(":")]
        lat, lng, tz_str = _geocode(lugar)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from kerykeion import KerykeionChartSVG

            if tipo == "rs":
                from api.astro.calculator import get_natal_data, get_solar_return
                natal_data = get_natal_data(nombre, d.year, d.month, d.day, h, m, lat, lng, tz_str)
                natal_sun_abs = natal_data["planetas"].get("sun", {}).get("abs_pos", 0.0)
                sr_year = datetime.date.today().year
                rs_data = get_solar_return(natal_sun_abs, sr_year, lat, lng, tz_str)
                rs_fecha = datetime.date.fromisoformat(rs_data["fecha"])
                # "hora" viene como "HH:MM" string — parsear correctamente
                rs_hora_str = rs_data.get("hora") or "12:00"
                rs_h, rs_min = [int(x) for x in str(rs_hora_str).split(":")]
                subj = _kerykeion_subject(
                    f"{nombre} RS {sr_year}",
                    rs_fecha.year, rs_fecha.month, rs_fecha.day,
                    rs_h, rs_min, lat, lng, tz_str,
                )
            else:
                subj = _kerykeion_subject(
                    nombre, d.year, d.month, d.day, h, m, lat, lng, tz_str,
                )

            chart = KerykeionChartSVG(
                subj,
                chart_type="Natal",
                theme="dark",
                chart_language="ES",
            )
            svg = chart.makeWheelOnlyTemplate()

        # Ajustar viewBox para mejor centrado y quitar márgenes
        svg = svg.replace(
            "viewBox='75 25 530 530'",
            "viewBox='50 0 580 580'",
        )

        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"},
        )

    except Exception as e:
        logger.exception("Error generando carta SVG: %s", e)
        raise HTTPException(status_code=500, detail=f"Error generando carta: {str(e)}")


# ─── Datos crudos de la carta (tabla de posiciones) ──────────────────────────

@router.get("/datos-carta")
async def datos_carta(
    nombre: str = "Consultante",
    fecha: str = "",
    hora: str = "12:00",
    lugar: str = "",
):
    """Devuelve planetas, casas y aspectos de la carta natal como JSON."""
    import datetime
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    if not fecha or not lugar:
        raise HTTPException(status_code=400, detail="Se requieren fecha y lugar.")

    try:
        d = datetime.date.fromisoformat(fecha)
        h, m = [int(x) for x in hora.split(":")]
        lat, lng, tz_str = _geocode(lugar)
        natal = get_natal_data(nombre, d.year, d.month, d.day, h, m, lat, lng, tz_str)
        return {"ok": True, "natal": natal}
    except Exception as e:
        logger.exception("Error calculando datos carta: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Interpretación por planeta (streaming IA) ────────────────────────────────

@router.get("/interpretacion-stream")
async def interpretacion_stream(
    nombre: str = "Consultante",
    fecha: str = "",
    hora: str = "12:00",
    lugar: str = "",
):
    """
    Genera una interpretación planeta a planeta de la carta natal en streaming SSE.
    Más concisa que el análisis completo — enfocada en el perfil de personalidad.
    """
    import datetime
    import json
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    if not fecha or not lugar:
        raise HTTPException(status_code=400, detail="Se requieren fecha y lugar.")

    async def _stream():
        try:
            d = datetime.date.fromisoformat(fecha)
            h, m = [int(x) for x in hora.split(":")]
            lat, lng, tz_str = _geocode(lugar)

            yield f"data: {json.dumps({'status': 'Calculando carta natal...'})}\n\n"
            natal = get_natal_data(nombre, d.year, d.month, d.day, h, m, lat, lng, tz_str)

            yield f"data: {json.dumps({'status': 'Generando interpretación...'})}\n\n"

            # Construir tabla de posiciones para el prompt
            planetas = natal.get("planetas", {})
            casas    = natal.get("casas", {})
            aspectos = natal.get("aspectos", [])

            NOMBRE_PLANETA = {
                "sun": "Sol", "moon": "Luna", "mercury": "Mercurio",
                "venus": "Venus", "mars": "Marte", "jupiter": "Júpiter",
                "saturn": "Saturno", "uranus": "Urano", "neptune": "Neptuno",
                "pluto": "Plutón", "true_node": "Nodo Norte", "chiron": "Quirón",
            }

            tabla = []
            for pk, pd in planetas.items():
                nombre_p = NOMBRE_PLANETA.get(pk, pk.title())
                grado   = pd.get("grado", 0)
                signo   = pd.get("signo", "?")
                casa    = pd.get("casa", "?")
                retro   = " ℞" if pd.get("retrogrado") else ""
                dignidad = pd.get("dignidad", "")
                tabla.append(
                    f"  {nombre_p:12s} {grado:5.1f}° {signo:12s} Casa {casa}{retro}"
                    + (f" [{dignidad}]" if dignidad else "")
                )

            asc = casas.get(1, {})
            mc  = casas.get(10, {})
            angulos = (
                f"  ASC: {asc.get('grado', 0):.1f}° {asc.get('signo', '?')}\n"
                f"  MC:  {mc.get('grado', 0):.1f}° {mc.get('signo', '?')}"
            )

            aspectos_str = ""
            if aspectos:
                asp_lines = []
                for a in aspectos[:12]:  # top 12
                    p1 = NOMBRE_PLANETA.get(a.get("planeta1", ""), a.get("planeta1", ""))
                    p2 = NOMBRE_PLANETA.get(a.get("planeta2", ""), a.get("planeta2", ""))
                    tipo = a.get("tipo", "")
                    orbe = a.get("orbe", 0)
                    asp_lines.append(f"  {p1} {tipo} {p2} (orbe {orbe:.1f}°)")
                aspectos_str = "\n".join(asp_lines)

            prompt = f"""Eres un astrólogo experto de tradición clásica. Analiza la carta natal de {nombre} e interpreta cada posición planetaria de forma clara y directa para un terapeuta holístico.

CARTA NATAL DE {nombre.upper()}
Fecha: {fecha}  Hora: {hora}  Lugar: {lugar}

PLANETAS:
{chr(10).join(tabla)}

ÁNGULOS:
{angulos}

ASPECTOS PRINCIPALES:
{aspectos_str if aspectos_str else '  (sin aspectos calculados)'}

INSTRUCCIONES:
- Interpreta primero la Tríada de personalidad: Sol (esencia/propósito), Luna (mundo emocional/necesidades), ASC (máscara/apariencia física)
- Luego interpreta cada planeta en su signo y casa: qué energía expresa, cómo la vive, qué aprendizaje o tensión genera
- Para planetas retrógrados indica la revisión interna que implica
- Para dignidades (domicilio, exaltación, caída, exilio) indica el impacto en la expresión del planeta
- Usa lenguaje directo, empático y orientado al crecimiento personal
- Estructura con encabezados markdown (## para cada planeta)
- Sé conciso por planeta (3-5 líneas), no redundante
- Al final añade una sección ## Síntesis con el patrón central del mapa natal en 3-4 frases

Responde solo en español."""

            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
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


# ═══════════════════════════════════════════════════════════════════════════════
# SINASTRÍA — Compatibilidad de parejas
# ═══════════════════════════════════════════════════════════════════════════════

class SinastriaRequest(BaseModel):
    nombre_a: str = Field(..., min_length=2, max_length=100)
    fecha_a:  str = Field(..., description="YYYY-MM-DD")
    hora_a:   str = Field(..., description="HH:MM")
    lugar_a:  str = Field(...)
    nombre_b: str = Field(..., min_length=2, max_length=100)
    fecha_b:  str = Field(..., description="YYYY-MM-DD")
    hora_b:   str = Field(..., description="HH:MM")
    lugar_b:  str = Field(...)


def _cross_aspects(natalA: dict, natalB: dict) -> list[dict]:
    ASPECT_ORBS = {
        "conjunción": (0, 8), "oposición": (180, 8),
        "trígono": (120, 7), "cuadrado": (90, 7),
        "sextil": (60, 5),   "quincuncio": (150, 3),
    }
    def ang_dist(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)
    cross = []
    for pk_a, pd_a in natalA["planetas"].items():
        for pk_b, pd_b in natalB["planetas"].items():
            dist = ang_dist(pd_a.get("abs_pos", 0.0), pd_b.get("abs_pos", 0.0))
            for asp_name, (angle, orb) in ASPECT_ORBS.items():
                diff = abs(dist - angle)
                if diff <= orb:
                    cross.append({
                        "planeta_a": pk_a, "planeta_b": pk_b,
                        "aspecto": asp_name, "orbe": round(diff, 2),
                        "signo_a": pd_a.get("signo",""), "signo_b": pd_b.get("signo",""),
                        "casa_a": pd_a.get("casa",""), "casa_b": pd_b.get("casa",""),
                    })
    cross.sort(key=lambda x: x["orbe"])
    return cross


@router.post("/carta-sinastria")
async def carta_sinastria_svg(payload: SinastriaRequest):
    import datetime, warnings
    from fastapi.responses import Response
    from api.astro.engine import _geocode
    from api.astro.calculator import _kerykeion_subject
    try:
        dA = datetime.date.fromisoformat(payload.fecha_a)
        hA, mA = [int(x) for x in payload.hora_a.split(":")]
        latA, lngA, tzA = _geocode(payload.lugar_a)
        dB = datetime.date.fromisoformat(payload.fecha_b)
        hB, mB = [int(x) for x in payload.hora_b.split(":")]
        latB, lngB, tzB = _geocode(payload.lugar_b)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from kerykeion import KerykeionChartSVG
            subjA = _kerykeion_subject(payload.nombre_a, dA.year, dA.month, dA.day, hA, mA, latA, lngA, tzA)
            subjB = _kerykeion_subject(payload.nombre_b, dB.year, dB.month, dB.day, hB, mB, latB, lngB, tzB)
            svg = KerykeionChartSVG(subjA, chart_type="Synastry", second_obj=subjB,
                                    theme="dark", chart_language="ES").makeWheelOnlyTemplate()
        return Response(content=svg, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=300"})
    except Exception as e:
        logger.exception("Sinastría SVG error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sinastria-stream")
async def sinastria_stream(payload: SinastriaRequest):
    import datetime, json
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    async def _stream():
        try:
            dA = datetime.date.fromisoformat(payload.fecha_a)
            hA, mA = [int(x) for x in payload.hora_a.split(":")]
            latA, lngA, tzA = _geocode(payload.lugar_a)
            dB = datetime.date.fromisoformat(payload.fecha_b)
            hB, mB = [int(x) for x in payload.hora_b.split(":")]
            latB, lngB, tzB = _geocode(payload.lugar_b)

            yield f"data: {json.dumps({'status': f'Calculando carta de {payload.nombre_a}...'})}\n\n"
            natalA = get_natal_data(payload.nombre_a, dA.year, dA.month, dA.day, hA, mA, latA, lngA, tzA)
            yield f"data: {json.dumps({'status': f'Calculando carta de {payload.nombre_b}...'})}\n\n"
            natalB = get_natal_data(payload.nombre_b, dB.year, dB.month, dB.day, hB, mB, latB, lngB, tzB)
            yield f"data: {json.dumps({'status': 'Calculando aspectos cruzados...'})}\n\n"
            cross = _cross_aspects(natalA, natalB)
            # Enviar aspectos al cliente para la tabla
            yield f"data: {json.dumps({'cross': cross})}\n\n"
            yield f"data: {json.dumps({'status': 'Generando análisis de compatibilidad...'})}\n\n"

            NOMBRE_P = {
                "sun":"Sol","moon":"Luna","mercury":"Mercurio","venus":"Venus",
                "mars":"Marte","jupiter":"Júpiter","saturn":"Saturno",
                "uranus":"Urano","neptune":"Neptuno","pluto":"Plutón",
                "true_node":"Nodo Norte","chiron":"Quirón",
            }
            def resumen(nombre, natal):
                lines = [
                    f"  {NOMBRE_P.get(k,k):12} {v.get('signo','?'):12} Casa {v.get('casa','?')}"
                    + (" ℞" if v.get("retrogrado") else "")
                    for k, v in natal["planetas"].items()
                ]
                asc = natal["casas"].get(1,{}); mc = natal["casas"].get(10,{})
                lines.append(f"  ASC {asc.get('signo','?')}  MC {mc.get('signo','?')}")
                return "\n".join(lines)

            asp_txt = "\n".join(
                f"  {NOMBRE_P.get(a['planeta_a'],a['planeta_a']):12} de {payload.nombre_a}"
                f" {a['aspecto']:12} {NOMBRE_P.get(a['planeta_b'],a['planeta_b']):12}"
                f" de {payload.nombre_b} (orbe {a['orbe']}°)"
                for a in cross[:20]
            ) or "  (sin aspectos significativos)"

            edad_a = datetime.date.today().year - dA.year
            edad_b = datetime.date.today().year - dB.year

            prompt = f"""Eres astrólogo experto en sinastría y terapia de pareja. Analiza la compatibilidad entre {payload.nombre_a} y {payload.nombre_b}.

═══ {payload.nombre_a.upper()} ({payload.fecha_a}, {edad_a} años) ═══
{resumen(payload.nombre_a, natalA)}

═══ {payload.nombre_b.upper()} ({payload.fecha_b}, {edad_b} años) ═══
{resumen(payload.nombre_b, natalB)}

═══ ASPECTOS CRUZADOS ═══
{asp_txt}

Estructura el reporte:

## 1. Compatibilidad General
Tono de la relación y energía que se genera entre ellos.

## 2. Vínculo emocional y afectivo
Sol-Luna, Luna-Luna, Venus-Luna entre ambas cartas.

## 3. Atracción y química
Venus-Marte, planetas personales. Tipo de atracción.

## 4. Comunicación y mente compartida
Mercurio, ASC. ¿Se entienden? ¿Hay fluidez?

## 5. Tensiones y aprendizajes
Cuadrados y oposiciones exactos como crecimiento mutuo.

## 6. Propósito conjunto
Nodos, Saturno, Júpiter: qué vienen a construir juntos.

## 7. Síntesis para el terapeuta
3-5 frases: fortalezas clave, desafío central, sugerencia terapéutica.

Tono empático, profundo, orientado al crecimiento. Solo en español."""

            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model, messages=[{"role":"user","content":prompt}],
                temperature=0.7, max_tokens=5000, stream=True, timeout=120.0,
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


# ═══════════════════════════════════════════════════════════════════════════════
# TRÁNSITOS PLANETARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TransitosRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    fecha_nacimiento: str = Field(..., description="YYYY-MM-DD")
    hora_nacimiento:  str = Field(..., description="HH:MM")
    lugar_nacimiento: str = Field(...)
    fecha_transito:   Optional[str] = Field(default=None, description="YYYY-MM-DD (default: hoy)")
    hora_transito:    str = Field(default="12:00",        description="HH:MM")
    lugar_transito:   Optional[str] = Field(default=None, description="Ciudad para el tránsito (default: lugar de nacimiento)")


def _transit_aspects(natal: dict, transito: dict) -> list[dict]:
    """Aspectos entre planetas en tránsito (exterior) y planetas natales (interior).
    Usa orbes más estrechos que la sinastría — los tránsitos requieren precisión."""
    ASPECT_ORBS = {
        "conjunción": (0,   3.0),
        "oposición":  (180, 3.0),
        "trígono":    (120, 2.5),
        "cuadrado":   (90,  2.5),
        "sextil":     (60,  1.5),
        "quincuncio": (150, 1.5),
    }
    # Peso para ordenar por importancia astrológica
    PESO_T = {"saturn":5,"neptune":5,"uranus":5,"pluto":6,"jupiter":4,
              "true_node":3,"mars":3,"sun":2,"moon":2,"venus":1,"mercury":1,"chiron":3}
    PESO_N = {"sun":6,"moon":6,"mercury":4,"venus":4,"mars":4,
              "jupiter":3,"saturn":3,"true_node":2,"chiron":3,
              "uranus":1,"neptune":1,"pluto":1}

    def ang_dist(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)

    aspects = []
    for pk_t, pd_t in transito["planetas"].items():
        for pk_n, pd_n in natal["planetas"].items():
            dist = ang_dist(pd_t.get("abs_pos", 0.0), pd_n.get("abs_pos", 0.0))
            for asp_name, (angle, orb) in ASPECT_ORBS.items():
                diff = abs(dist - angle)
                if diff <= orb:
                    aspects.append({
                        "planeta_transito": pk_t,
                        "planeta_natal":    pk_n,
                        "aspecto":          asp_name,
                        "orbe":             round(diff, 2),
                        "signo_transito":   pd_t.get("signo", ""),
                        "signo_natal":      pd_n.get("signo", ""),
                        "casa_natal":       pd_n.get("casa", ""),
                        "retrogrado":       pd_t.get("retrogrado", False),
                        "importancia":      PESO_T.get(pk_t, 1) + PESO_N.get(pk_n, 1),
                    })
    aspects.sort(key=lambda x: (-x["importancia"], x["orbe"]))
    return aspects


@router.get("/carta-transitos")
async def carta_transitos_svg(
    nombre:          str = "Consultante",
    fecha_nac:       str = "",        # YYYY-MM-DD
    hora_nac:        str = "12:00",   # HH:MM
    lugar_nac:       str = "",
    fecha_transito:  str = "",        # YYYY-MM-DD  (default: hoy)
    hora_transito:   str = "12:00",
    lugar_transito:  str = "",
):
    """SVG de carta de tránsitos: rueda natal interior + planetas en tránsito exterior."""
    import datetime, warnings
    from fastapi.responses import Response
    from api.astro.engine import _geocode
    from api.astro.calculator import _kerykeion_subject

    if not fecha_nac or not lugar_nac:
        raise HTTPException(status_code=400, detail="Se requieren fecha_nac y lugar_nac.")

    try:
        d_nac = datetime.date.fromisoformat(fecha_nac)
        h_n, m_n = [int(x) for x in hora_nac.split(":")]
        lat_n, lng_n, tz_n = _geocode(lugar_nac)

        # Fecha de tránsito: hoy si no se especifica
        fecha_t_str = fecha_transito or datetime.date.today().isoformat()
        d_t = datetime.date.fromisoformat(fecha_t_str)
        h_t, m_t = [int(x) for x in hora_transito.split(":")]
        lugar_t = lugar_transito or lugar_nac
        lat_t, lng_t, tz_t = _geocode(lugar_t)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from kerykeion import KerykeionChartSVG
            subj_natal   = _kerykeion_subject(nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat_n, lng_n, tz_n)
            subj_transito = _kerykeion_subject(
                f"Tránsitos {fecha_t_str}",
                d_t.year, d_t.month, d_t.day, h_t, m_t, lat_t, lng_t, tz_t,
            )
            svg = KerykeionChartSVG(
                subj_natal,
                chart_type="Transit",
                second_obj=subj_transito,
                theme="dark",
                chart_language="ES",
            ).makeWheelOnlyTemplate()

        return Response(content=svg, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=60"})

    except Exception as e:
        logger.exception("carta-transitos error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transitos-data")
async def transitos_data(
    nombre:         str = "Consultante",
    fecha_nac:      str = "",
    hora_nac:       str = "12:00",
    lugar_nac:      str = "",
    fecha_transito: str = "",
    hora_transito:  str = "12:00",
    lugar_transito: str = "",
):
    """Devuelve planetas natales, planetas en tránsito y aspectos como JSON."""
    import datetime
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    if not fecha_nac or not lugar_nac:
        raise HTTPException(status_code=400, detail="Se requieren fecha_nac y lugar_nac.")
    try:
        d_nac = datetime.date.fromisoformat(fecha_nac)
        h_n, m_n = [int(x) for x in hora_nac.split(":")]
        lat_n, lng_n, tz_n = _geocode(lugar_nac)

        fecha_t_str = fecha_transito or datetime.date.today().isoformat()
        d_t = datetime.date.fromisoformat(fecha_t_str)
        h_t, m_t = [int(x) for x in hora_transito.split(":")]
        lugar_t = lugar_transito or lugar_nac
        lat_t, lng_t, tz_t = _geocode(lugar_t)

        natal   = get_natal_data(nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat_n, lng_n, tz_n)
        transito = get_natal_data(
            f"Tránsitos {fecha_t_str}",
            d_t.year, d_t.month, d_t.day, h_t, m_t, lat_t, lng_t, tz_t,
        )
        aspectos = _transit_aspects(natal, transito)
        return {"ok": True, "natal": natal, "transito": transito, "aspectos": aspectos}
    except Exception as e:
        logger.exception("transitos-data error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transitos-stream")
async def transitos_stream(payload: TransitosRequest):
    """
    SSE: calcula tránsitos del día (o fecha dada) sobre la carta natal
    y genera interpretación IA de los tránsitos activos más importantes.
    """
    import datetime, json
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    async def _stream():
        try:
            NOMBRE_P = {
                "sun":"Sol","moon":"Luna","mercury":"Mercurio","venus":"Venus",
                "mars":"Marte","jupiter":"Júpiter","saturn":"Saturno",
                "uranus":"Urano","neptune":"Neptuno","pluto":"Plutón",
                "true_node":"Nodo Norte","chiron":"Quirón",
            }

            # ── Natal ──────────────────────────────────────────────────────────
            d_nac = datetime.date.fromisoformat(payload.fecha_nacimiento)
            h_n, m_n = [int(x) for x in payload.hora_nacimiento.split(":")]
            lat_n, lng_n, tz_n = _geocode(payload.lugar_nacimiento)

            yield f"data: {json.dumps({'status': 'Calculando carta natal...'})}\n\n"
            natal = get_natal_data(
                payload.nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat_n, lng_n, tz_n
            )

            # ── Tránsito ───────────────────────────────────────────────────────
            fecha_t_str = payload.fecha_transito or datetime.date.today().isoformat()
            d_t = datetime.date.fromisoformat(fecha_t_str)
            h_t, m_t = [int(x) for x in payload.hora_transito.split(":")]
            lugar_t = payload.lugar_transito or payload.lugar_nacimiento
            lat_t, lng_t, tz_t = _geocode(lugar_t)

            yield f"data: {json.dumps({'status': f'Calculando posiciones para {fecha_t_str}...'})}\n\n"
            transito = get_natal_data(
                f"Tránsitos {fecha_t_str}",
                d_t.year, d_t.month, d_t.day, h_t, m_t, lat_t, lng_t, tz_t,
            )

            yield f"data: {json.dumps({'status': 'Calculando aspectos activos...'})}\n\n"
            aspectos = _transit_aspects(natal, transito)

            # Enviar tabla al cliente
            yield f"data: {json.dumps({'transitos': aspectos})}\n\n"

            # ── Prompt ─────────────────────────────────────────────────────────
            yield f"data: {json.dumps({'status': 'Generando interpretación astrológica...'})}\n\n"

            # Resumen de posiciones natales (planetas personales)
            personales = ["sun","moon","mercury","venus","mars"]
            natal_resumen = "\n".join(
                f"  {NOMBRE_P.get(k,k):12} natal en {v.get('signo','?')} Casa {v.get('casa','?')}"
                + (" ℞" if v.get("retrogrado") else "")
                for k, v in natal["planetas"].items()
                if k in personales
            )
            asc_n = natal["casas"].get(1, {})
            natal_resumen += f"\n  ASC natal: {asc_n.get('grado',0):.1f}° {asc_n.get('signo','?')}"

            # Posiciones actuales de planetas en tránsito
            lentos = ["jupiter","saturn","uranus","neptune","pluto","true_node","chiron"]
            transito_resumen = "\n".join(
                f"  {NOMBRE_P.get(k,k):12} en tránsito por {v.get('signo','?')} {v.get('grado',0):.1f}°"
                + (" ℞" if v.get("retrogrado") else "")
                for k, v in transito["planetas"].items()
            )

            # Top aspectos activos (máx 15)
            asp_txt = "\n".join(
                f"  {NOMBRE_P.get(a['planeta_transito'],a['planeta_transito']):12} en tránsito"
                f" {a['aspecto']:12} {NOMBRE_P.get(a['planeta_natal'],a['planeta_natal']):12} natal"
                f" (orbe {a['orbe']}°{'  ℞' if a['retrogrado'] else ''})"
                for a in aspectos[:15]
            ) or "  (sin aspectos activos en este momento)"

            edad = datetime.date.today().year - d_nac.year

            prompt = f"""Eres astrólogo experto en tránsitos planetarios. Interpreta los tránsitos activos de {payload.nombre} para el {fecha_t_str}.

═══ CARTA NATAL — {payload.nombre.upper()} ═══
Nacimiento: {payload.fecha_nacimiento} {payload.hora_nacimiento} en {payload.lugar_nacimiento}
Edad: {edad} años

PLANETAS PERSONALES NATALES:
{natal_resumen}

═══ CIELO ACTUAL — {fecha_t_str} ═══
PLANETAS EN TRÁNSITO:
{transito_resumen}

═══ ASPECTOS ACTIVOS (tránsito → natal) ═══
{asp_txt}

INSTRUCCIONES DE INTERPRETACIÓN:
- Prioriza los tránsitos de planetas lentos (Saturno, Urano, Neptuno, Plutón, Júpiter, Nodo Norte) sobre planetas personales natales (Sol, Luna, ASC, Venus, Marte).
- Para cada aspecto relevante indica: qué energía activa, cómo la vive {payload.nombre}, y cuánto tiempo puede durar el influjo.
- Distingue aspectos armónicos (trígono, sextil, conjunción benefífica) de tensionales (cuadrado, oposición).
- Para planetas retrógrados (℞) indica la revisión interna que implica.
- Cierra con una síntesis práctica: ¿cuál es el tema principal de este período? ¿qué recomiendas al terapeuta para acompañar a {payload.nombre}?

Estructura con encabezados markdown (## para cada tránsito importante, ### para subtemas).
Tono empático, directo y orientado al crecimiento. Solo en español."""

            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=5000,
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


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESIONES SECUNDARIAS (método día = año)
# ═══════════════════════════════════════════════════════════════════════════════

class ProgresionesRequest(BaseModel):
    nombre:           str           = Field(..., min_length=2, max_length=100)
    fecha_nacimiento: str           = Field(..., description="YYYY-MM-DD")
    hora_nacimiento:  str           = Field(..., description="HH:MM")
    lugar_nacimiento: str           = Field(...)
    fecha_objetivo:   Optional[str] = Field(default=None, description="YYYY-MM-DD para la que se calculan las progresiones (default: hoy)")


def _progressed_date(fecha_nacimiento: str, fecha_objetivo: Optional[str] = None):
    """
    Calcula la fecha progresada usando el método día-por-año (progresiones secundarias).
    Edad en años → misma cantidad de días sumados al nacimiento.
    """
    import datetime as _dt
    d_nac = _dt.date.fromisoformat(fecha_nacimiento)
    d_obj = _dt.date.fromisoformat(fecha_objetivo) if fecha_objetivo else _dt.date.today()
    age_in_years = (d_obj - d_nac).days / 365.25
    return d_nac + _dt.timedelta(days=age_in_years)


def _progressed_aspects(natal: dict, progresado: dict) -> list[dict]:
    """
    Aspectos entre planetas PROGRESADOS (exterior) y NATALES (interior).
    Orbes estrechos — las progresiones se mueven lentamente y requieren precisión.
    """
    ASPECT_ORBS = {
        "conjunción": (0,   1.5),
        "oposición":  (180, 1.5),
        "trígono":    (120, 1.0),
        "cuadrado":   (90,  1.0),
        "sextil":     (60,  0.75),
    }
    PESO_P = {"sun":6,"moon":6,"mercury":3,"venus":3,"mars":3,
              "jupiter":2,"saturn":2,"true_node":2,"chiron":2}
    PESO_N = {"sun":6,"moon":6,"mercury":4,"venus":4,"mars":4,
              "jupiter":3,"saturn":3,"true_node":2,"chiron":2}

    def ang_dist(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)

    aspects = []
    for pk_p, pd_p in progresado["planetas"].items():
        for pk_n, pd_n in natal["planetas"].items():
            dist = ang_dist(pd_p.get("abs_pos", 0.0), pd_n.get("abs_pos", 0.0))
            for asp_name, (angle, orb) in ASPECT_ORBS.items():
                diff = abs(dist - angle)
                if diff <= orb:
                    aspects.append({
                        "planeta_progresado": pk_p,
                        "planeta_natal":      pk_n,
                        "aspecto":            asp_name,
                        "orbe":               round(diff, 2),
                        "signo_progresado":   pd_p.get("signo", ""),
                        "signo_natal":        pd_n.get("signo", ""),
                        "casa_natal":         pd_n.get("casa", ""),
                        "retrogrado":         pd_p.get("retrogrado", False),
                        "importancia":        PESO_P.get(pk_p, 1) + PESO_N.get(pk_n, 1),
                    })
    aspects.sort(key=lambda x: (-x["importancia"], x["orbe"]))
    return aspects


def _fase_lunar_progresada(sol_abs: float, luna_abs: float) -> dict:
    """Determina la fase de la Luna Progresada respecto al Sol Progresado."""
    angulo = (luna_abs - sol_abs) % 360
    fases = [
        (0,   45,  "Luna Nueva Progresada",    "Inicio de nuevo ciclo vital de ~30 años. Semilla plantada internamente."),
        (45,  90,  "Creciente Progresada",     "Fase de construcción y acción. Empuje hacia nuevas formas de ser."),
        (90,  135, "Cuarto Creciente",         "Crisis de acción. Ruptura con estructuras antiguas."),
        (135, 180, "Gibosa Progresada",        "Perfeccionamiento y análisis. Ajuste fino antes de la culminación."),
        (180, 225, "Luna Llena Progresada",    "Culminación y plena consciencia. Punto de madurez y revelación."),
        (225, 270, "Diseminante Progresada",   "Difusión y transmisión de lo aprendido en el ciclo."),
        (270, 315, "Último Cuarto",            "Crisis de conciencia. Revisión profunda y soltar."),
        (315, 360, "Balsámica Progresada",     "Preparación del próximo ciclo. Sabiduría acumulada."),
    ]
    for f_min, f_max, nombre, desc in fases:
        if f_min <= angulo < f_max:
            return {"nombre": nombre, "descripcion": desc, "angulo": round(angulo, 2)}
    return {"nombre": "Desconocida", "descripcion": "", "angulo": round(angulo, 2)}


@router.get("/carta-progresada")
async def carta_progresada_svg(
    nombre:         str = "Consultante",
    fecha_nac:      str = "",       # YYYY-MM-DD
    hora_nac:       str = "12:00",  # HH:MM
    lugar_nac:      str = "",
    fecha_objetivo: str = "",       # YYYY-MM-DD (default: hoy)
):
    """SVG de carta progresada: rueda natal interior + planetas progresados exterior."""
    import datetime, warnings
    from fastapi.responses import Response
    from api.astro.engine import _geocode
    from api.astro.calculator import _kerykeion_subject

    if not fecha_nac or not lugar_nac:
        raise HTTPException(status_code=400, detail="Se requieren fecha_nac y lugar_nac.")

    try:
        d_nac = datetime.date.fromisoformat(fecha_nac)
        h_n, m_n = [int(x) for x in hora_nac.split(":")]
        lat, lng, tz_str = _geocode(lugar_nac)

        d_obj_str = fecha_objetivo or datetime.date.today().isoformat()
        d_prog    = _progressed_date(fecha_nac, d_obj_str)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from kerykeion import KerykeionChartSVG
            subj_natal = _kerykeion_subject(
                nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat, lng, tz_str,
            )
            subj_prog = _kerykeion_subject(
                f"{nombre} Prog.",
                d_prog.year, d_prog.month, d_prog.day, h_n, m_n, lat, lng, tz_str,
            )
            svg = KerykeionChartSVG(
                subj_natal,
                chart_type="Transit",
                second_obj=subj_prog,
                theme="dark",
                chart_language="ES",
            ).makeWheelOnlyTemplate()

        return Response(
            content=svg, media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"},
        )

    except Exception as e:
        logger.exception("carta-progresada error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progresiones-data")
async def progresiones_data(
    nombre:         str = "Consultante",
    fecha_nac:      str = "",
    hora_nac:       str = "12:00",
    lugar_nac:      str = "",
    fecha_objetivo: str = "",
):
    """JSON con natal, carta progresada, aspectos activos y fase lunar progresada."""
    import datetime
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    if not fecha_nac or not lugar_nac:
        raise HTTPException(status_code=400, detail="Se requieren fecha_nac y lugar_nac.")
    try:
        d_nac = datetime.date.fromisoformat(fecha_nac)
        h_n, m_n = [int(x) for x in hora_nac.split(":")]
        lat, lng, tz_str = _geocode(lugar_nac)

        d_obj_str = fecha_objetivo or datetime.date.today().isoformat()
        d_prog    = _progressed_date(fecha_nac, d_obj_str)

        natal     = get_natal_data(nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat, lng, tz_str)
        progresado = get_natal_data(
            f"{nombre} Prog.",
            d_prog.year, d_prog.month, d_prog.day, h_n, m_n, lat, lng, tz_str,
        )
        aspectos  = _progressed_aspects(natal, progresado)
        sol_prog  = progresado["planetas"].get("sun",  {}).get("abs_pos", 0.0)
        luna_prog = progresado["planetas"].get("moon", {}).get("abs_pos", 0.0)
        fase      = _fase_lunar_progresada(sol_prog, luna_prog)

        return {
            "ok":               True,
            "natal":            natal,
            "progresado":       progresado,
            "fecha_progresada": d_prog.isoformat(),
            "aspectos":         aspectos,
            "fase_lunar":       fase,
        }
    except Exception as e:
        logger.exception("progresiones-data error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progresiones-stream")
async def progresiones_stream(payload: ProgresionesRequest):
    """SSE: calcula la carta progresada y genera interpretación IA."""
    import datetime, json
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    async def _stream():
        try:
            NOMBRE_P = {
                "sun":"Sol","moon":"Luna","mercury":"Mercurio","venus":"Venus",
                "mars":"Marte","jupiter":"Júpiter","saturn":"Saturno",
                "uranus":"Urano","neptune":"Neptuno","pluto":"Plutón",
                "true_node":"Nodo Norte","chiron":"Quirón",
            }

            d_nac = datetime.date.fromisoformat(payload.fecha_nacimiento)
            h_n, m_n = [int(x) for x in payload.hora_nacimiento.split(":")]
            lat, lng, tz_str = _geocode(payload.lugar_nacimiento)
            edad = (datetime.date.today() - d_nac).days // 365

            yield f"data: {json.dumps({'status': 'Calculando carta natal...'})}\n\n"
            natal = get_natal_data(
                payload.nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat, lng, tz_str,
            )

            d_obj_str = payload.fecha_objetivo or datetime.date.today().isoformat()
            d_prog    = _progressed_date(payload.fecha_nacimiento, d_obj_str)

            yield f"data: {json.dumps({'status': f'Calculando carta progresada ({d_prog.isoformat()})...'})}\n\n"
            progresado = get_natal_data(
                f"{payload.nombre} Prog.",
                d_prog.year, d_prog.month, d_prog.day, h_n, m_n, lat, lng, tz_str,
            )

            yield f"data: {json.dumps({'status': 'Calculando aspectos progresados...'})}\n\n"
            aspectos  = _progressed_aspects(natal, progresado)
            sol_prog  = progresado["planetas"].get("sun",  {}).get("abs_pos", 0.0)
            luna_prog = progresado["planetas"].get("moon", {}).get("abs_pos", 0.0)
            fase      = _fase_lunar_progresada(sol_prog, luna_prog)

            yield f"data: {json.dumps({'progresiones': aspectos, 'fase': fase['nombre']})}\n\n"
            yield f"data: {json.dumps({'status': 'Generando interpretación de progresiones...'})}\n\n"

            # ── Construir prompt ───────────────────────────────────────────────
            PERSONALES = ["sun","moon","mercury","venus","mars","jupiter","saturn","true_node"]
            natal_resumen = "\n".join(
                f"  {NOMBRE_P.get(k,k):12} natal  {v.get('signo','?'):12} Casa {v.get('casa','?')}"
                for k, v in natal["planetas"].items() if k in PERSONALES
            )
            prog_resumen = "\n".join(
                f"  {NOMBRE_P.get(k,k):12} prog.  {v.get('signo','?'):12} {v.get('grado',0):.1f}°"
                f"  Casa {v.get('casa','?')}"
                + (" ℞" if v.get("retrogrado") else "")
                for k, v in progresado["planetas"].items() if k in PERSONALES
            )
            asp_txt = "\n".join(
                f"  {NOMBRE_P.get(a['planeta_progresado'],a['planeta_progresado']):12} prog."
                f" {a['aspecto']:12}"
                f" {NOMBRE_P.get(a['planeta_natal'],a['planeta_natal']):12} natal"
                f" (orbe {a['orbe']}°)"
                for a in aspectos[:12]
            ) or "  (sin aspectos exactos activos en este período)"

            prompt = f"""Eres astrólogo experto en progresiones secundarias (método día = año de vida).
Interpreta la carta progresada de {payload.nombre} para {d_obj_str}.

═══ CARTA NATAL — {payload.nombre.upper()} ═══
Nacimiento: {payload.fecha_nacimiento} {payload.hora_nacimiento}  Lugar: {payload.lugar_nacimiento}
Edad: {edad} años

POSICIONES NATALES (referencia):
{natal_resumen}

═══ CARTA PROGRESADA — {d_prog.isoformat()} ═══
(Método: {edad} días después del nacimiento = {edad} años de vida progresados)

POSICIONES PROGRESADAS:
{prog_resumen}

FASE LUNAR PROGRESADA: {fase['nombre']} ({fase['angulo']}°)
{fase['descripcion']}

═══ ASPECTOS EXACTOS ACTIVOS (progresado → natal) ═══
{asp_txt}

INSTRUCCIONES DE INTERPRETACIÓN:
1. **Fase Lunar Progresada**: qué capítulo vital vive {payload.nombre}, su duración aproximada dentro del ciclo de 30 años y el tema arquetípico central.
2. **Sol Progresado**: en qué signo y casa está actualmente y qué nueva identidad o propósito está emergiendo respecto al natal.
3. **Luna Progresada**: signo y casa actual vs natal; qué necesidades emocionales y patrones internos están evolucionando.
4. **Aspectos exactos activos**: para cada aspecto progresado→natal relevante, explica qué activa en la psique de {payload.nombre}, cómo se puede manifestar y por cuánto tiempo seguirá activo (las progresiones se mueven ~1°/año).
5. **Síntesis terapéutica**: cuál es el tema central de transformación en este período, qué está madurando en {payload.nombre} y qué sugerirías al terapeuta para acompañar este proceso.

Usa encabezados markdown (## para secciones principales).
Tono empático, profundo, orientado al crecimiento. Solo en español."""

            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.65,
                max_tokens=5000,
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


# ═══════════════════════════════════════════════════════════════════════════════
# ASTROLOGÍA DE LA SALUD
# ═══════════════════════════════════════════════════════════════════════════════

class SaludRequest(BaseModel):
    nombre:           str = Field(..., min_length=2, max_length=100)
    fecha_nacimiento: str = Field(..., description="YYYY-MM-DD")
    hora_nacimiento:  str = Field(..., description="HH:MM")
    lugar_nacimiento: str = Field(...)
    incluir_transitos: bool = Field(default=True, description="Incluir análisis de tránsitos actuales de salud")


# ── Tablas de correspondencia médica ─────────────────────────────────────────

_SIGNO_CUERPO = {
    "Aries":       "Cabeza, cara, cerebro, ojos, dientes",
    "Tauro":       "Cuello, garganta, tiroides, laringe, oídos",
    "Géminis":     "Pulmones, bronquios, brazos, manos, sistema nervioso",
    "Cáncer":      "Estómago, senos, sistema digestivo, fluidos, pleura",
    "Leo":         "Corazón, columna vertebral, espalda superior, médula",
    "Virgo":       "Intestinos, páncreas, bazo, sistema digestivo inferior",
    "Libra":       "Riñones, vejiga, zona lumbar, glándulas suprarrenales",
    "Escorpio":    "Órganos reproductivos, colon, próstata, nariz, garganta",
    "Sagitario":   "Caderas, muslos, hígado, nervio ciático, arterias",
    "Capricornio": "Rodillas, huesos, piel, sistema esquelético, articulaciones",
    "Acuario":     "Tobillos, pantorrillas, circulación, sistema nervioso autónomo",
    "Piscis":      "Pies, sistema linfático, sistema inmune, glándulas endocrinas",
}

_PLANETA_SISTEMA = {
    "sun":      ("Corazón, columna, ojos (derecho), vitalidad central",           "Arritmias, problemas cardíacos, debilidad vital, columna"),
    "moon":     ("Estómago, senos, fluidos corporales, sistema linfático",        "Digestión, retención de líquidos, ciclos hormonales, ansiedad"),
    "mercury":  ("Sistema nervioso periférico, pulmones, manos, habla",           "Nerviosismo, ansiedad, problemas respiratorios, insomnio"),
    "venus":    ("Riñones, garganta, hormonas, piel, venas",                      "Problemas renales, desequilibrios hormonales, afecciones de piel"),
    "mars":     ("Músculos, sangre, adrenales, fiebre, sistema inmune activo",    "Inflamaciones, accidentes, fiebre, infecciones agudas, anemia"),
    "jupiter":  ("Hígado, vesícula biliar, sangre arterial, metabolismo",         "Exceso, hígado, colesterol, sobreindulgencia, tumores benignos"),
    "saturn":   ("Huesos, dientes, piel, sistema esquelético, articulaciones",    "Artritis, osteoporosis, piel seca, depresión, carencias crónicas"),
    "uranus":   ("Sistema nervioso central, espasmos, electricidad corporal",     "Espasmos, nerviosismo extremo, accidentes súbitos, convulsiones"),
    "neptune":  ("Sistema inmune, glándulas, pies, inconsciente somático",        "Infecciones virales, alergias, sistema inmune débil, adicciones"),
    "pluto":    ("Sistema reproductivo, colon, regeneración celular, toxinas",    "Procesos regenerativos profundos, tumores, intoxicaciones, colon"),
    "chiron":   ("Heridas crónicas, dolor persistente, sanación profunda",        "Dolor crónico, heridas que no cierran, traumas somáticos"),
    "true_node":("Karma somático, patrones heredados de salud",                   "Tendencias heredadas, desequilibrios kármicos en el cuerpo"),
}

_CASA_SALUD = {
    1:  "Constitución física, vitalidad, aspecto corporal general",
    6:  "Salud cotidiana, enfermedades crónicas, hábitos, trabajo corporal",
    8:  "Crisis agudas, cirugías, regeneración, transformaciones físicas",
    12: "Enfermedades ocultas, hospitalización, sistema inmune, karma somático",
}


@router.post("/salud-stream")
async def salud_stream(payload: SaludRequest):
    """
    SSE: análisis astrológico de salud — vulnerabilidades constitucionales,
    sistemas orgánicos a cuidar y tránsitos de salud actuales.
    """
    import datetime, json
    from api.astro.engine import _geocode
    from api.astro.calculator import get_natal_data

    async def _stream():
        try:
            NOMBRE_P = {
                "sun":"Sol","moon":"Luna","mercury":"Mercurio","venus":"Venus",
                "mars":"Marte","jupiter":"Júpiter","saturn":"Saturno",
                "uranus":"Urano","neptune":"Neptuno","pluto":"Plutón",
                "true_node":"Nodo Norte","chiron":"Quirón",
            }

            d_nac = datetime.date.fromisoformat(payload.fecha_nacimiento)
            h_n, m_n = [int(x) for x in payload.hora_nacimiento.split(":")]
            lat, lng, tz_str = _geocode(payload.lugar_nacimiento)
            edad = (datetime.date.today() - d_nac).days // 365

            yield f"data: {json.dumps({'status': 'Calculando carta natal...'})}\n\n"
            natal = get_natal_data(
                payload.nombre, d_nac.year, d_nac.month, d_nac.day, h_n, m_n, lat, lng, tz_str,
            )

            # ── Construir mapa de salud ────────────────────────────────────────
            planetas  = natal.get("planetas", {})
            casas     = natal.get("casas", {})
            aspectos  = natal.get("aspectos", [])

            # Planetas en casas de salud (1, 6, 8, 12)
            casas_salud_activas = {}
            for pk, pd in planetas.items():
                casa = pd.get("casa")
                if casa in (1, 6, 8, 12):
                    casas_salud_activas.setdefault(casa, []).append(pk)

            # Signos en casas de salud (ASC, cúspide 6, 8, 12)
            signos_casas = {
                c: casas.get(c, {}).get("signo", "?")
                for c in (1, 6, 8, 12)
            }

            # Aspectos difíciles (cuadrado, oposición) a luminarias y ASC
            aspectos_duros = [
                a for a in aspectos
                if a.get("tipo") in ("cuadrado", "oposición")
                and (a.get("planeta1") in ("sun","moon") or a.get("planeta2") in ("sun","moon"))
            ]

            # Zonas corporales activadas por planetas en casa 6/8/12
            zonas_riesgo = set()
            for pk, pd in planetas.items():
                if pd.get("casa") in (6, 8, 12):
                    sistema = _PLANETA_SISTEMA.get(pk)
                    if sistema:
                        zonas_riesgo.add(sistema[0].split(",")[0].strip())
                signo = pd.get("signo", "")
                if pd.get("casa") in (6, 8, 12) and signo in _SIGNO_CUERPO:
                    zonas_riesgo.add(_SIGNO_CUERPO[signo].split(",")[0].strip())

            # Enviar mapa de salud al cliente
            mapa = {
                "casas_salud": {
                    str(c): {
                        "signo": signos_casas.get(c, "?"),
                        "planetas": [NOMBRE_P.get(p, p) for p in casas_salud_activas.get(c, [])],
                        "descripcion": _CASA_SALUD[c],
                    }
                    for c in (1, 6, 8, 12)
                },
                "zonas_riesgo": list(zonas_riesgo),
            }
            yield f"data: {json.dumps({'mapa_salud': mapa})}\n\n"

            # ── Tránsitos de salud actuales (opcional) ─────────────────────────
            transitos_salud_txt = ""
            if payload.incluir_transitos:
                yield f"data: {json.dumps({'status': 'Calculando tránsitos de salud actuales...'})}\n\n"
                try:
                    hoy = datetime.date.today()
                    transito = get_natal_data(
                        "Tránsitos", hoy.year, hoy.month, hoy.day, 12, 0, lat, lng, tz_str,
                    )
                    asp_salud = _transit_aspects(natal, transito)
                    # Filtrar solo los relevantes para salud (Saturno, Marte, Neptuno sobre luminarias y ASC)
                    planetas_salud_t = {"saturn","mars","neptune","pluto","uranus"}
                    planetas_salud_n = {"sun","moon","mercury","venus","mars","jupiter","saturn"}
                    asp_salud_filtrados = [
                        a for a in asp_salud
                        if a["planeta_transito"] in planetas_salud_t
                        and a["planeta_natal"] in planetas_salud_n
                    ][:8]
                    if asp_salud_filtrados:
                        transitos_salud_txt = "\n".join(
                            f"  {NOMBRE_P.get(a['planeta_transito'],a['planeta_transito']):12} en tránsito"
                            f" {a['aspecto']:12} {NOMBRE_P.get(a['planeta_natal'],a['planeta_natal']):12} natal"
                            f" (orbe {a['orbe']}°{'  ℞' if a['retrogrado'] else ''})"
                            for a in asp_salud_filtrados
                        )
                except Exception:
                    pass

            yield f"data: {json.dumps({'status': 'Generando análisis de salud...'})}\n\n"

            # ── Construir prompt completo ──────────────────────────────────────
            # Tabla de posiciones natales
            tabla_natal = "\n".join(
                f"  {NOMBRE_P.get(k,k):12} en {v.get('signo','?'):12} Casa {v.get('casa','?')}"
                + (" ℞" if v.get("retrogrado") else "")
                + (f"  [{v.get('dignidad','')}]" if v.get("dignidad") else "")
                for k, v in planetas.items()
            )
            asc = casas.get(1, {})
            mc  = casas.get(10, {})
            tabla_natal += f"\n  ASC: {asc.get('grado',0):.1f}° {asc.get('signo','?')}   MC: {mc.get('grado',0):.1f}° {mc.get('signo','?')}"

            # Casas de salud pobladas
            casas_txt = ""
            for c in (1, 6, 8, 12):
                signo_c = signos_casas.get(c, "?")
                planets_c = casas_salud_activas.get(c, [])
                desc_c = _CASA_SALUD[c]
                ps_txt = ", ".join(NOMBRE_P.get(p,p) for p in planets_c) if planets_c else "vacía"
                casas_txt += f"\n  Casa {c} ({signo_c}) — {desc_c}\n    Planetas: {ps_txt}\n"

            # Aspectos difíciles a luminarias
            asp_txt = ""
            if aspectos_duros:
                asp_txt = "\n".join(
                    f"  {NOMBRE_P.get(a.get('planeta1',''),a.get('planeta1','')):12}"
                    f" {a.get('tipo',''):12}"
                    f" {NOMBRE_P.get(a.get('planeta2',''),a.get('planeta2','')):12}"
                    f" (orbe {a.get('orbe',0):.1f}°)"
                    for a in aspectos_duros[:8]
                )
            else:
                asp_txt = "  (sin aspectos difíciles exactos a luminarias)"

            # Pre-computar secciones opcionales (evita f-strings anidados — no válidos en Python 3.9)
            seccion_transitos = (
                "\n═══ TRÁNSITOS DE SALUD ACTUALES ═══\n" + transitos_salud_txt + "\n"
                if transitos_salud_txt else ""
            )
            seccion_5 = (
                "\n## 5. Tránsitos de Salud Actuales\n"
                "Interpreta los tránsitos activos más relevantes para la salud de "
                + payload.nombre
                + " en este momento. ¿Hay algún período de mayor vulnerabilidad o de recuperación activa?\n"
                if transitos_salud_txt else ""
            )

            prompt = (
                f"Eres astrólogo médico experto en la tradición clásica (Volguine, Navarro, escuela española de astrología médica). "
                f"Analiza el mapa natal de {payload.nombre} desde la perspectiva de la salud.\n\n"
                f"IMPORTANTE: Este análisis es una guía de predisposiciones constitucionales para el terapeuta holístico — NO un diagnóstico médico.\n\n"
                f"═══ CARTA NATAL — {payload.nombre.upper()} ═══\n"
                f"Nacimiento: {payload.fecha_nacimiento} {payload.hora_nacimiento}  Lugar: {payload.lugar_nacimiento}\n"
                f"Edad: {edad} años\n\n"
                f"POSICIONES PLANETARIAS:\n{tabla_natal}\n\n"
                f"═══ CASAS DE SALUD ═══\n{casas_txt}\n"
                f"═══ ASPECTOS DIFÍCILES A LUMINARIAS ═══\n{asp_txt}\n"
                + seccion_transitos +
                f"\nESTRUCTURA DEL ANÁLISIS:\n\n"
                f"## 1. Constitución y Vitalidad General\n"
                f"Analiza el ASC y su regente, el Sol y la Luna. ¿Qué tipo constitucional es {payload.nombre}? "
                f"¿Cuál es su nivel de vitalidad base? ¿Qué tendencias físicas generales muestra la carta?\n\n"
                f"## 2. Sistemas Orgánicos Prioritarios\n"
                f"Identifica los 3-4 sistemas orgánicos o zonas corporales que requieren mayor atención, basándote en:\n"
                f"- Signos de las cúspides de casas 1, 6, 8, 12\n"
                f"- Planetas ubicados en esas casas y los sistemas que rigen\n"
                f"- Aspectos difíciles a luminarias\n\n"
                f"## 3. Vulnerabilidades Específicas\n"
                f"Para cada vulnerabilidad identificada:\n"
                f"- Qué planeta o signo la señala\n"
                f"- En qué parte del cuerpo se manifiesta\n"
                f"- Qué tipo de desequilibrio es más probable (inflamatorio, crónico, emocional-somático, etc.)\n"
                f"- Cómo puede prevenirse o equilibrarse\n\n"
                f"## 4. Conexión Terapéutica\n"
                f"Sugiere cómo el terapeuta holístico puede usar esta información:\n"
                f"- Qué zonas corporales priorizar en el rastreo biomagnético\n"
                f"- Qué patrones emocionales (biodescodificación) pueden estar relacionados\n"
                f"- Qué sistemas de la terapia holística son más afines a este perfil\n"
                + seccion_5 +
                f"\n## Síntesis para el Terapeuta\n"
                f"3-4 frases con el perfil de salud central de {payload.nombre} y las prioridades terapéuticas más importantes.\n\n"
                f"Recuerda incluir al final un aviso claro: \"Este análisis es orientativo para el terapeuta holístico y no sustituye el diagnóstico médico profesional.\"\n\n"
                f"Tono profesional, empático, orientado a la práctica terapéutica. Solo en español."
            )

            from api.astro.engine import _get_llm_client
            client, model = _get_llm_client()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=6000,
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

# ─── Diario Lunar — fase actual en tiempo real ────────────────────────────────

@router.get("/luna/hoy", include_in_schema=False)
async def luna_hoy():
    """Devuelve la fase lunar actual con datos astronómicos reales."""
    from datetime import datetime, timezone
    try:
        import swisseph as swe
    except ImportError:
        raise HTTPException(status_code=503, detail="Swiss Ephemeris no disponible")

    now = datetime.now(timezone.utc)
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60.0)

    sun_pos, _ = swe.calc_ut(jd, swe.SUN)
    moon_pos, _ = swe.calc_ut(jd, swe.MOON)

    sun_lon = sun_pos[0]
    moon_lon = moon_pos[0]
    phase_angle = (moon_lon - sun_lon) % 360
    illumination = round((1 - abs(180 - phase_angle) / 180) * 100, 1)

    SIGNS = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo",
             "Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]
    SIGNS_EN = ["aries","tauro","geminis","cancer","leo","virgo",
                "libra","escorpio","sagitario","capricornio","acuario","piscis"]
    ELEMENTS = ["fuego","tierra","aire","agua","fuego","tierra",
                "aire","agua","fuego","tierra","aire","agua"]
    MODALITIES = ["cardinal","fijo","mutable","cardinal","fijo","mutable",
                  "cardinal","fijo","mutable","cardinal","fijo","mutable"]

    moon_sign_idx = int(moon_lon / 30)
    sun_sign_idx  = int(sun_lon / 30)

    # Phase determination
    phases = [
        (0,   45,  "Luna Nueva",             "nueva",       "🌑", "Siembra, intención, inicio"),
        (45,  90,  "Cuarto Creciente",        "creciente",   "🌒", "Acción, crecimiento, impulso"),
        (90,  135, "Gibosa Creciente",        "gibosa_crec", "🌓", "Refinamiento, ajuste, desarrollo"),
        (135, 180, "Gibosa Creciente Plena",  "gibosa_crec", "🌔", "Acumulación, expansión, abundancia"),
        (180, 225, "Luna Llena",              "llena",       "🌕", "Manifestación, revelación, cosecha"),
        (225, 270, "Gibosa Menguante",        "menguante",   "🌖", "Gratitud, compartir, entrega"),
        (270, 315, "Cuarto Menguante",        "cuarto_men",  "🌗", "Liberación, integración, soltar"),
        (315, 360, "Luna Balsámica",          "balsamica",   "🌘", "Descanso, rendición, preparación"),
    ]

    phase_data = phases[-1]
    for p_min, p_max, nombre, id_, emoji, keyword in phases:
        if p_min <= phase_angle < p_max:
            phase_data = (p_min, p_max, nombre, id_, emoji, keyword)
            break

    _, _, phase_nombre, phase_id, phase_emoji, phase_keyword = phase_data

    # Next new and full moon (approximate)
    remaining_to_full  = (180 - phase_angle) % 360
    remaining_to_new   = (360 - phase_angle) % 360
    days_to_full = round(remaining_to_full / (360 / 29.5), 1)
    days_to_new  = round(remaining_to_new  / (360 / 29.5), 1)

    return JSONResponse(content={
        "fecha": now.strftime("%Y-%m-%d"),
        "hora_utc": now.strftime("%H:%M"),
        "luna": {
            "longitud": round(moon_lon, 2),
            "signo": SIGNS[moon_sign_idx],
            "signo_id": SIGNS_EN[moon_sign_idx],
            "elemento": ELEMENTS[moon_sign_idx],
            "modalidad": MODALITIES[moon_sign_idx],
            "grado": round(moon_lon % 30, 1),
        },
        "sol": {
            "longitud": round(sun_lon, 2),
            "signo": SIGNS[sun_sign_idx],
            "elemento": ELEMENTS[sun_sign_idx],
        },
        "fase": {
            "angulo": round(phase_angle, 1),
            "iluminacion": illumination,
            "nombre": phase_nombre,
            "id": phase_id,
            "emoji": phase_emoji,
            "keyword": phase_keyword,
        },
        "proximos": {
            "dias_luna_llena": days_to_full if days_to_full > 0.5 else None,
            "dias_luna_nueva": days_to_new if days_to_new > 0.5 else None,
        }
    })
