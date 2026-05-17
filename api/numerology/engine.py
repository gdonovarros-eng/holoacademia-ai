"""
Motor principal del módulo de Numerología.
Orquesta: cálculo → ensamblaje del prompt → llamada al LLM → reporte final.
"""
from __future__ import annotations

import datetime
import logging
import os

from .calculator import calcular_numeroscopio
from .prompt_builder import build_numerology_prompt

logger = logging.getLogger(__name__)


# ─── Cliente LLM ──────────────────────────────────────────────────────────────

def _get_llm_client():
    """Mismo patrón que el motor astrológico."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed")

    openai_key  = os.getenv("OPENAI_API_KEY", "").strip()
    groq_key    = os.getenv("GROQ_API_KEY", "").strip()
    num_model   = os.getenv("NUMEROLOGY_LLM_MODEL", "").strip()
    astro_model = os.getenv("ASTRO_LLM_MODEL", "").strip()

    if openai_key and not openai_key.startswith("gsk_"):
        model = num_model or astro_model or "gpt-4o-mini"
        return OpenAI(api_key=openai_key), model

    groq_or_openai = groq_key or openai_key
    if groq_or_openai:
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = num_model or astro_model or os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
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
            temperature=0.72,
            max_tokens=5000,
            timeout=120.0,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("Numerology LLM call failed: %s", e)
        raise


# ─── API pública ───────────────────────────────────────────────────────────────

def run_numerology_analysis(
    nombre: str,
    fecha_nacimiento: str,   # "YYYY-MM-DD"
    profundidad: str = "completo",
    apellido_paterno: str = "",
    apellido_materno: str = "",
) -> dict:
    """
    Motor principal de numerología.

    Retorna:
    {
      "ok": True,
      "reporte": "texto completo del análisis...",
      "datos": { numeroscopio completo },
      "meta": {...}
    }
    """
    # ── Parse fecha ────────────────────────────────────────────────────────────
    try:
        fecha = datetime.date.fromisoformat(fecha_nacimiento)
    except ValueError:
        raise ValueError(f"Fecha inválida: {fecha_nacimiento} — usa formato YYYY-MM-DD")

    dia, mes, anio = fecha.day, fecha.month, fecha.year

    # ── Validaciones básicas ───────────────────────────────────────────────────
    nombre = nombre.strip()
    if len(nombre) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres.")
    if anio < 1900 or anio > datetime.date.today().year:
        raise ValueError(f"Año de nacimiento inválido: {anio}")

    logger.info("Calculando numeroscopio para %s (%s)", nombre, fecha_nacimiento)

    # ── Cálculo numerológico ───────────────────────────────────────────────────
    datos = calcular_numeroscopio(
        nombre, dia, mes, anio,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
    )

    # ── Construcción del prompt ────────────────────────────────────────────────
    prompt = build_numerology_prompt(nombre, datos, profundidad)
    logger.info("Prompt numerológico: %d chars", len(prompt))

    # ── Llamada al LLM ─────────────────────────────────────────────────────────
    reporte = _call_llm(prompt)

    edad = datetime.date.today().year - anio

    cp = datos["ciclos_personales"]
    return {
        "ok": True,
        "reporte": reporte,
        "datos": datos,
        "meta": {
            "nombre": nombre,
            "fecha_nacimiento": fecha_nacimiento,
            "edad": edad,
            "profundidad": profundidad,
            "mision":      datos["nacimiento"]["mision"],
            "expresion":   datos["nombre"]["expresion"],
            "impulso":     datos["nombre"]["impulso"],
            "impresion":   datos["nombre"]["impresion"],
            "alma":        datos["nacimiento"]["alma"],
            "karma":       datos["nacimiento"]["karma"],
            "latente":     datos["vibracion_latente"],
            "esencia":     datos["nombre"]["esencia"],
            "locomotora":  datos["nombre"]["locomotora"],
            "año_personal": cp["año_personal"],
            "mes_personal": cp["mes_personal"],
            "dia_personal": cp["dia_personal"],
            "año_universal": cp["año_universal"],
            "deudas_karmicas": [dk["codigo"] for dk in datos["deudas_karmicas"]],
        },
    }
