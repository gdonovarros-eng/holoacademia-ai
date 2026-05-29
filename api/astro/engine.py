"""
Motor principal de análisis astrológico.
Orquesta: cálculo → ensamblaje del prompt → llamada al LLM → reporte final.
"""
from __future__ import annotations

import datetime
import os
import logging
from typing import Optional

from .calculator import (
    get_natal_data,
    get_solar_return,
    get_rsp,
    get_mensal,
    get_transits_today,
    compute_house_superposition,
)
from .prompt_builder import build_mega_prompt

logger = logging.getLogger(__name__)

# ─── Cliente LLM (mismo patrón que el resto de Holoacademia) ────────────────────
def _get_llm_client():
    """
    Cliente LLM para el motor astrológico.
    Prioridad: ASTRO_LLM_MODEL (si definido) → OpenAI directo → Groq.
    El motor astrológico necesita respuestas largas y coherentes;
    se prefiere OpenAI directo sobre Groq cuando está disponible.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed")

    astro_model   = os.getenv("ASTRO_LLM_MODEL", "").strip()
    default_model = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")

    # 1. OpenRouter (prioridad principal)
    or_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if or_key:
        model = astro_model or default_model
        return OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1"), model

    # 2. OpenAI directo
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        model = astro_model or "gpt-4o-mini"
        return OpenAI(api_key=openai_key), model

    # 3. Groq (legacy)
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = astro_model or "llama-3.3-70b-versatile"
        return OpenAI(api_key=groq_key, base_url=base_url), model

    raise RuntimeError(
        "No se encontró API key válida. Define OPENROUTER_API_KEY u OPENAI_API_KEY."
    )


def _call_llm(prompt: str) -> str:
    """Llama al LLM y retorna el texto generado."""
    client, model = _get_llm_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=6000,
            timeout=120.0,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise


# ─── Geocodificación simple por nombre de ciudad ─────────────────────────────────
_CITY_COORDS: dict[str, tuple[float, float, str]] = {
    # ── México ───────────────────────────────────────────────────────────────────
    "ciudad de mexico": (19.4326, -99.1332, "America/Mexico_City"),
    "mexico city": (19.4326, -99.1332, "America/Mexico_City"),
    "cdmx": (19.4326, -99.1332, "America/Mexico_City"),
    "guadalajara": (20.6597, -103.3496, "America/Mexico_City"),
    "monterrey": (25.6866, -100.3161, "America/Mexico_City"),
    "puebla": (19.0414, -98.2063, "America/Mexico_City"),
    "tijuana": (32.5027, -117.0062, "America/Tijuana"),
    "cancun": (21.1619, -86.8515, "America/Cancun"),
    "merida": (20.9674, -89.5926, "America/Merida"),
    "leon": (21.1221, -101.6823, "America/Mexico_City"),
    "toluca": (19.2826, -99.6557, "America/Mexico_City"),
    "queretaro": (20.5888, -100.3899, "America/Mexico_City"),
    "san luis potosi": (22.1565, -100.9855, "America/Mexico_City"),
    "hermosillo": (29.0729, -110.9559, "America/Hermosillo"),
    "chihuahua": (28.6320, -106.0691, "America/Chihuahua"),
    "culiacan": (24.8091, -107.3940, "America/Mazatlan"),
    "acapulco": (16.8531, -99.8237, "America/Mexico_City"),
    "veracruz": (19.1738, -96.1342, "America/Mexico_City"),
    "oaxaca": (17.0732, -96.7266, "America/Mexico_City"),
    # ── Colombia ─────────────────────────────────────────────────────────────────
    "bogota": (4.7110, -74.0721, "America/Bogota"),
    "medellin": (6.2442, -75.5812, "America/Bogota"),
    "cali": (3.4516, -76.5320, "America/Bogota"),
    "barranquilla": (10.9685, -74.7813, "America/Bogota"),
    "cartagena": (10.3910, -75.4794, "America/Bogota"),
    # ── Argentina ────────────────────────────────────────────────────────────────
    "buenos aires": (-34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    "cordoba": (-31.4135, -64.1811, "America/Argentina/Cordoba"),
    "rosario": (-32.9468, -60.6393, "America/Argentina/Cordoba"),
    "mendoza": (-32.8908, -68.8272, "America/Argentina/Mendoza"),
    "tucuman": (-26.8083, -65.2176, "America/Argentina/Tucuman"),
    # ── Chile ────────────────────────────────────────────────────────────────────
    "santiago": (-33.4489, -70.6693, "America/Santiago"),
    "valparaiso": (-33.0472, -71.6127, "America/Santiago"),
    "concepcion": (-36.8201, -73.0444, "America/Santiago"),
    # ── Perú ─────────────────────────────────────────────────────────────────────
    "lima": (-12.0464, -77.0428, "America/Lima"),
    "arequipa": (-16.4090, -71.5375, "America/Lima"),
    "trujillo": (-8.1159, -79.0300, "America/Lima"),
    # ── Venezuela ────────────────────────────────────────────────────────────────
    "caracas": (10.4806, -66.9036, "America/Caracas"),
    "maracaibo": (10.6314, -71.6412, "America/Caracas"),
    "valencia venezuela": (10.1579, -68.0076, "America/Caracas"),
    # ── Ecuador ──────────────────────────────────────────────────────────────────
    "quito": (-0.2295, -78.5243, "America/Guayaquil"),
    "guayaquil": (-2.1710, -79.9224, "America/Guayaquil"),
    # ── Bolivia ──────────────────────────────────────────────────────────────────
    "la paz": (-16.5000, -68.1500, "America/La_Paz"),
    "cochabamba": (-17.3895, -66.1568, "America/La_Paz"),
    "santa cruz": (-17.7833, -63.1833, "America/La_Paz"),
    # ── Paraguay ─────────────────────────────────────────────────────────────────
    "asuncion": (-25.2867, -57.6470, "America/Asuncion"),
    # ── Uruguay ──────────────────────────────────────────────────────────────────
    "montevideo": (-34.9011, -56.1645, "America/Montevideo"),
    # ── Costa Rica ───────────────────────────────────────────────────────────────
    "san jose": (9.9281, -84.0907, "America/Costa_Rica"),
    # ── Panamá ───────────────────────────────────────────────────────────────────
    "panama": (8.9936, -79.5197, "America/Panama"),
    "ciudad de panama": (8.9936, -79.5197, "America/Panama"),
    # ── Cuba ─────────────────────────────────────────────────────────────────────
    "havana": (23.1136, -82.3666, "America/Havana"),
    "habana": (23.1136, -82.3666, "America/Havana"),
    # ── R. Dominicana / Puerto Rico ───────────────────────────────────────────────
    "santo domingo": (18.4861, -69.9312, "America/Santo_Domingo"),
    "san juan": (18.4655, -66.1057, "America/Puerto_Rico"),
    # ── Guatemala / Honduras / El Salvador / Nicaragua ───────────────────────────
    "guatemala": (14.6349, -90.5069, "America/Guatemala"),
    "tegucigalpa": (14.0818, -87.2068, "America/Tegucigalpa"),
    "san salvador": (13.6929, -89.2182, "America/El_Salvador"),
    "managua": (12.1364, -86.2179, "America/Managua"),
    # ── España ───────────────────────────────────────────────────────────────────
    "madrid": (40.4168, -3.7038, "Europe/Madrid"),
    "barcelona": (41.3851, 2.1734, "Europe/Madrid"),
    "sevilla": (37.3886, -5.9823, "Europe/Madrid"),
    "valencia": (39.4699, -0.3763, "Europe/Madrid"),
    "bilbao": (43.2630, -2.9350, "Europe/Madrid"),
    "malaga": (36.7213, -4.4217, "Europe/Madrid"),
    "zaragoza": (41.6561, -0.8773, "Europe/Madrid"),
    "granada": (37.1773, -3.5986, "Europe/Madrid"),
    "murcia": (37.9922, -1.1307, "Europe/Madrid"),
    "alicante": (38.3452, -0.4815, "Europe/Madrid"),
    # ── USA ──────────────────────────────────────────────────────────────────────
    "miami": (25.7617, -80.1918, "America/New_York"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "los angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "chicago": (41.8781, -87.6298, "America/Chicago"),
    "houston": (29.7604, -95.3698, "America/Chicago"),
    "dallas": (32.7767, -96.7970, "America/Chicago"),
}

def _geocode(city_str: str) -> tuple[float, float, str]:
    """
    Retorna (lat, lng, tz_str) para una ciudad.
    Lanza ValueError si la ciudad no está en el catálogo.
    """
    key = city_str.lower().strip()
    # Eliminar palabras genéricas como país para búsqueda más limpia
    for noise in [", mexico", ", colombia", ", argentina", ", chile", ", peru",
                  ", españa", ", spain", ", venezuela", ", ecuador", ", bolivia"]:
        key = key.replace(noise, "")
    key = key.strip()
    # Búsqueda exacta primero, luego parcial
    if key in _CITY_COORDS:
        return _CITY_COORDS[key]
    for k, v in _CITY_COORDS.items():
        if k in key or key in k:
            return v
    raise ValueError(
        f"Ciudad '{city_str}' no encontrada en el geocodificador. "
        "Por favor escribe el nombre de la ciudad principal más cercana "
        "(ej: 'Ciudad de México', 'Buenos Aires', 'Madrid', 'Bogotá')."
    )


# ─── API pública ──────────────────────────────────────────────────────────────────

def run_astro_analysis(
    nombre: str,
    fecha_nacimiento: str,      # "YYYY-MM-DD"
    hora_nacimiento: str,       # "HH:MM"
    lugar_nacimiento: str,      # "Ciudad, País"
    lugar_actual: Optional[str] = None,
    profundidad: str = "completo",  # "basico" | "completo"
    incluir_rsp: bool = True,
    incluir_mensal: bool = True,
) -> dict:
    """
    Motor principal. Devuelve:
    {
      "ok": True,
      "reporte": "texto completo del análisis...",
      "datos": {natal, rs, rsp, mensal, superposicion},
      "meta": {...}
    }
    """
    # ── Parse fecha/hora ────────────────────────────────────────────────────────
    try:
        fecha = datetime.date.fromisoformat(fecha_nacimiento)
    except ValueError:
        raise ValueError(f"Fecha inválida: {fecha_nacimiento} — usa formato YYYY-MM-DD")

    try:
        h, m = [int(x) for x in hora_nacimiento.split(":")]
    except Exception:
        raise ValueError(f"Hora inválida: {hora_nacimiento} — usa formato HH:MM")

    year, month, day = fecha.year, fecha.month, fecha.day
    lugar_rs = lugar_actual or lugar_nacimiento

    # ── Geocodificación ─────────────────────────────────────────────────────────
    lat_n, lng_n, tz_n = _geocode(lugar_nacimiento)
    lat_rs, lng_rs, tz_rs = _geocode(lugar_rs)

    logger.info("Calculando carta natal para %s (%s)", nombre, fecha_nacimiento)

    # ── Cálculo natal ───────────────────────────────────────────────────────────
    natal = get_natal_data(nombre, year, month, day, h, m, lat_n, lng_n, tz_n)
    natal_sun_abs = natal["planetas"].get("sun", {}).get("abs_pos", 0.0)

    # ── Revolución Solar ────────────────────────────────────────────────────────
    sr_year = datetime.date.today().year
    # Si el aniversario ya pasó este año, calculamos el del año actual igualmente
    logger.info("Calculando RS %d para %s", sr_year, nombre)
    rs = get_solar_return(natal_sun_abs, sr_year, lat_rs, lng_rs, tz_rs, nombre=f"RS-{nombre}")

    # ── RSP ─────────────────────────────────────────────────────────────────────
    rsp = None
    if incluir_rsp:
        edad = sr_year - year
        if edad > 0:
            try:
                logger.info("Calculando RSP para edad %d", edad)
                rsp = get_rsp(natal_sun_abs, edad, sr_year, lat_n, lng_n, tz_n, nombre=f"RSP-{nombre}")
            except Exception as e:
                logger.warning("RSP calculation failed: %s", e)

    # ── Mensal ──────────────────────────────────────────────────────────────────
    mensal = None
    if incluir_mensal:
        rs_moon_abs = rs["planetas"].get("moon", {}).get("abs_pos", 0.0)
        if rs_moon_abs:
            try:
                logger.info("Calculando Mensal próximo")
                mensal = get_mensal(rs_moon_abs, rs["fecha"], lat_rs, lng_rs, tz_rs, nombre=f"RL-{nombre}")
            except Exception as e:
                logger.warning("Mensal calculation failed: %s", e)

    # ── Tránsitos ───────────────────────────────────────────────────────────────
    transitos = None
    if profundidad == "completo":
        try:
            transitos = get_transits_today(lat_rs, lng_rs, tz_rs)
        except Exception as e:
            logger.warning("Transits calculation failed: %s", e)

    # ── Superposición casas RS→natal ────────────────────────────────────────────
    superposicion = compute_house_superposition(
        rs.get("casas", {}),
        natal.get("casas", {}),
    )

    # ── Construcción del mega-prompt ────────────────────────────────────────────
    edad = sr_year - year
    prompt = build_mega_prompt(
        nombre=nombre,
        natal=natal,
        rs=rs,
        rsp=rsp,
        mensal=mensal,
        transitos=transitos,
        superposicion=superposicion,
        edad=edad,
        fecha_nacimiento=fecha_nacimiento,
        lugar_nacimiento=lugar_nacimiento,
        lugar_actual=lugar_rs,
        profundidad=profundidad,
    )

    # ── Llamada al LLM ──────────────────────────────────────────────────────────
    logger.info("Enviando prompt al LLM (%d chars)", len(prompt))
    reporte = _call_llm(prompt)

    return {
        "ok": True,
        "reporte": reporte,
        "datos": {
            "natal": natal,
            "rs": rs,
            "rsp": rsp,
            "mensal": mensal,
            "superposicion": superposicion,
        },
        "meta": {
            "nombre": nombre,
            "fecha_nacimiento": fecha_nacimiento,
            "lugar_nacimiento": lugar_nacimiento,
            "lugar_actual": lugar_rs,
            "edad": edad,
            "sr_year": sr_year,
            "profundidad": profundidad,
            "incluyo_rsp": rsp is not None,
            "incluyo_mensal": mensal is not None,
        },
    }
