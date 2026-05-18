"""
Motor principal del módulo de Tarot.
Orquesta: perfil tarótico → prompt → llamada al LLM → lectura final.
"""
from __future__ import annotations

import datetime
import logging
import os

from .calculator import calcular_perfil_tarot
from .prompt_builder import build_tarot_prompt

logger = logging.getLogger(__name__)


# ─── Cliente LLM ──────────────────────────────────────────────────────────────

def _get_llm_client():
    """Mismo patrón que el motor numerológico/astrológico."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed")

    openai_key  = os.getenv("OPENAI_API_KEY", "").strip()
    groq_key    = os.getenv("GROQ_API_KEY", "").strip()
    tarot_model = os.getenv("TAROT_LLM_MODEL", "").strip()
    num_model   = os.getenv("NUMEROLOGY_LLM_MODEL", "").strip()
    astro_model = os.getenv("ASTRO_LLM_MODEL", "").strip()

    if openai_key and not openai_key.startswith("gsk_"):
        model = tarot_model or num_model or astro_model or "gpt-4o-mini"
        return OpenAI(api_key=openai_key), model

    groq_or_openai = groq_key or openai_key
    if groq_or_openai:
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = tarot_model or num_model or astro_model or os.getenv(
            "OPENAI_MODEL", "llama-3.3-70b-versatile"
        )
        return OpenAI(api_key=groq_or_openai, base_url=base_url), model

    raise RuntimeError(
        "No se encontró API key válida. Define OPENAI_API_KEY o GROQ_API_KEY."
    )


def _call_llm(prompt: str) -> str:
    client, model = _get_llm_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.76,
            max_tokens=5500,
            timeout=120.0,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Tarot LLM call failed: %s", e)
        raise


# ─── API pública ───────────────────────────────────────────────────────────────

def run_tarot_reading(
    pregunta: str,
    tirada: str,
    cartas: list[dict],           # [{"posicion": str, "carta": str, "invertida": bool}]
    fecha_nacimiento: str | None = None,   # "YYYY-MM-DD"
    signo_solar: str = "",
    numero_alma: int | None = None,
    profundidad: str = "estandar",
    enfoque: str = "terapeutico",
    sistema: str = "rws",
) -> dict:
    """
    Motor principal de lectura tarótica.

    Retorna:
    {
      "ok": True,
      "lectura": "texto completo de la lectura...",
      "perfil": { perfil tarótico del consultante },
      "meta": { metadatos de la lectura }
    }
    """
    # ── Validaciones básicas ───────────────────────────────────────────────────
    pregunta = pregunta.strip()
    if len(pregunta) < 5:
        raise ValueError("La pregunta debe tener al menos 5 caracteres.")
    if not cartas:
        raise ValueError("Se requiere al menos una carta en la tirada.")

    logger.info(
        "Lectura de tarot: tirada=%s, cartas=%d, enfoque=%s, profundidad=%s",
        tirada, len(cartas), enfoque, profundidad,
    )

    # ── Perfil tarótico (si hay fecha de nacimiento) ───────────────────────────
    perfil: dict = {}
    if fecha_nacimiento:
        try:
            fecha = datetime.date.fromisoformat(fecha_nacimiento)
            perfil = calcular_perfil_tarot(
                dia=fecha.day,
                mes=fecha.month,
                anio=fecha.year,
                signo_solar=signo_solar,
                numero_alma_numerologia=numero_alma,
                sistema=sistema,
            )
        except ValueError as e:
            logger.warning("Fecha de nacimiento inválida para tarot: %s — %s", fecha_nacimiento, e)
            # No es fatal — continuamos sin perfil
            perfil = {}

    # ── Construcción del prompt ────────────────────────────────────────────────
    prompt = build_tarot_prompt(
        pregunta=pregunta,
        tirada_nombre=tirada,
        cartas=cartas,
        perfil=perfil or None,
        profundidad=profundidad,
        enfoque=enfoque,
        sistema=sistema,
    )
    logger.info("Prompt de tarot: %d chars", len(prompt))

    # ── Llamada al LLM ─────────────────────────────────────────────────────────
    lectura = _call_llm(prompt)

    # ── Metadatos ─────────────────────────────────────────────────────────────
    carta_personalidad_nombre = ""
    carta_anio_nombre = ""
    if perfil:
        carta_personalidad_nombre = perfil.get("personalidad", {}).get("nombre", "")
        anio_actual = perfil.get("anio_personal", {}).get("actual", {})
        carta_anio_nombre = anio_actual.get("nombre", "") if anio_actual else ""

    return {
        "ok": True,
        "lectura": lectura,
        "perfil": perfil,
        "meta": {
            "tirada": tirada,
            "num_cartas": len(cartas),
            "pregunta": pregunta,
            "profundidad": profundidad,
            "enfoque": enfoque,
            "sistema": sistema,
            "fecha_nacimiento": fecha_nacimiento or "",
            "signo_solar": signo_solar,
            "carta_personalidad": carta_personalidad_nombre,
            "carta_anio_personal": carta_anio_nombre,
            "cartas_usadas": [c.get("carta", "") for c in cartas],
        },
    }
