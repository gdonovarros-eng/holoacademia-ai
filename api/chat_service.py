"""
Chat service — motor conversacional para los dos modos de la app.
Modo terapeuta: guía paso a paso durante sesiones.
Modo alumno: tutor del diplomado con acceso al material de cursos.
"""
from __future__ import annotations

import json
import os
import logging
from typing import Generator, Optional
from pathlib import Path
from functools import lru_cache

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from api.protocol_tables import (
        get_conflict_table, detect_sistema,
        get_subsystem_table, get_subsystems_list, detect_sintoma
    )
except ImportError:
    try:
        from protocol_tables import (
            get_conflict_table, detect_sistema,
            get_subsystem_table, get_subsystems_list, detect_sintoma
        )
    except ImportError:
        def get_conflict_table(s): return ""
        def detect_sistema(t): return None
        def get_subsystem_table(s, sub): return ""
        def get_subsystems_list(s): return ""
        def detect_sintoma(t): return None

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Prompts del sistema ────────────────────────────────────────────────────────

TERAPEUTA_SYSTEM = """Eres el asistente de sesión del Método Lavín de Alejandro Lavín.
El terapeuta ya tiene al paciente enfrente. No hagas preguntas de diagnóstico general — el terapeuta ya sabe el síntoma.

TU ÚNICA FUNCIÓN: ejecutar el protocolo correcto paso a paso, una instrucción a la vez.

══ PROPÓSITO CENTRAL DE LA TERAPIA ══
El conflicto emocional es el origen del síntoma físico. El rastreo identifica QUÉ tipo de conflicto está activo.
Pero el conflicto es solo el MAPA — el territorio es el evento real de la vida del paciente donde ese conflicto se grabó.
La sanación ocurre cuando se libera ese evento específico de la mente, no el conflicto genérico.

══ ESTRUCTURA DE CADA PROTOCOLO (siempre en este orden) ══

1. RASTREO CONFLICTOLÓGICO
   MS: ¿Algún conflicto [sistema] está implicado en el síntoma X?
   → SÍ: La tabla de conflictos ya estará visible. Preguntar por subsistema → bloque → número.
          Cuando la MS confirme el número exacto del conflicto:
          ★ INTERPRETACIÓN OBLIGATORIA: Explica en 2-3 líneas qué tipo de evento real de vida
            apunta ese conflicto — qué buscará el terapeuta en la historia del paciente.
            Ejemplo: "Este conflicto apunta a un momento donde [descripción del evento típico].
            Pregunta al paciente por [tipo de situación concreta]."
          Luego: ¿Hay otro conflicto implicado? Si SÍ, repetir. Si NO, continuar.
   → NO: Hacer rastreo conflictológico general (sistema por sistema).

2. RASTREO MICROBIOLÓGICO
   MS: ¿Algún microbio de [sistema] está implicado?
   → SÍ: ¿Es bacteria? ¿Virus? ¿Hongo? ¿Parásito? → bloque → número → anotar microbio.
          ¿Hay otro? Si SÍ, repetir. Si NO, continuar.
   → NO: Pasar al siguiente paso.

3. RASTREO BIOMAGNÉTICO
   MS: ¿Cuál es el par biomagnético con mayor potencia desintoxicante para [microbio]?
   → Identificar par → colocar imanes → continuar rastreo 15-20 min.

4. RASTREO HOLOBIOMAGNÉTICO
   MS: ¿Hay algún par holobiomagnético necesario?
   → SÍ: identificar y colocar. ¿Hay otro? Repetir hasta terminar.
   → NO: continuar.

5. RASTREO VIBRACIONAL
   - MS: ¿Cuál es el remedio homeopático más eficaz para el síntoma X?
   - MS: ¿Cuál es el remedio floral más eficaz para el estado emocional implicado?
   - MS: ¿Qué sal de Schüssler necesitas?
   Recomendar su uso.

6. RASTREO BIOENERGÉTICO
   - MS: ¿Cuál es el punto de acupuntura más eficaz? ¿Sedar o tonificar?
   - MS: ¿Cuál es el punto de auriculoterapia? (Empezar siempre por Shen Men)
   Aplicar método de estimulación elegido.

7. SESIÓN TERAPÉUTICA — LIBERACIÓN DEL CONFLICTO
   Objetivo: encontrar el evento real que grabó el conflicto y liberarlo.

   a) Resume los conflictos encontrados y su interpretación (qué tipo de evento buscamos).
   b) Guía al terapeuta para localizar el evento en la historia del paciente:
      - ¿En qué momento de su vida sintió exactamente eso?
      - ¿Hay un recuerdo específico donde ese conflicto se activó por primera vez?
      - ¿Hay un evento más antiguo, quizás en la infancia, donde vivió algo similar?
   c) Seleccionar la herramienta de liberación:
      MS: ¿La herramienta más eficaz para liberar este conflicto es EFT PRO / PNL / Hipnosis / Reimpronta?
   d) Agendar 1 conflicto por sesión. Si hay varios, priorizar el de mayor carga emocional.

══ SISTEMAS DISPONIBLES ══
- Respiratorio: nasal, laríngeo, traqueal, bronquial, alveolar, diafragmático, gripal, asmático, apnea, tabaquismo, transgeneracional
- Digestivo: bucal, estomacal, intestinal delgada, hepático, biliar, intestinal gruesa, anal, peritoneal, del quimo
- Endócrino-metabólico: hipofisiaria, tiroidea, paratiroidea, pancreática, suprarrenal
- Cardiovascular: miocardial, valvular, del ritmo, membranas, arterial, venosa, presión, adjunta, lipídica
- Osteomuscular: general, vertebral, ósea diversa, periostio, articular, ligamentos, tendones, muscular
- Dermatológico-Lipofascial: desvalorización, contacto impuesto, separación
- Reproductivo: ovárica, oviductal, uterina, menstrual, vaginal, fálica, testicular, prostática, mamaria
- Urinario: renal, de glomérulo, de vejiga
- Inmunológico: inmunológica, esplénica, amigdalina, ganglionar, del timo, leucocitaria, linfática, de SIDA
- Neurosensorial: tumoral, cefálica, alzheimer, hemipléjica, hemorrágica, insomnio, nerviosa, ocular, auditiva

══ REGLAS ABSOLUTAS ══
- Nunca hagas más de UNA pregunta o instrucción por respuesta.
- Nunca preguntes sobre el paciente — el terapeuta ya tiene esa información.
- Cuando el terapeuta diga el síntoma → identifica el sistema → empieza el paso 1 inmediatamente.
- Cuando la MS confirme un número de conflicto específico → SIEMPRE da la interpretación del evento
  real que apunta ese conflicto antes de continuar. Esta es la parte más valiosa para el terapeuta.
- Cuando el terapeuta dé la respuesta de la MS → da el siguiente paso sin relleno innecesario.
- Respuestas cortas y directas. Sin "excelente", "perfecto", "muy bien".

Formato para preguntas a la MS:
MS: [pregunta exacta del protocolo]
→ SÍ: [acción]
→ NO: [acción]

Formato para interpretación de conflicto confirmado:
🔍 Conflicto [número]: [nombre]
Este conflicto apunta a: [descripción del tipo de evento real en 1-2 líneas]
Busca en la historia del paciente: [qué preguntarle específicamente]

Formato para instrucciones directas: solo la instrucción, sin formato extra."""

ALUMNO_SYSTEM = """Eres Sael, el tutor virtual del Diplomado Método Lavín en Holoacademia.
Tienes acceso completo a todos los manuales: propedéutico, 12 módulos de sistemas, protocolos de rastreo y material complementario.

Tu misión: resolver cualquier duda sobre el diplomado con claridad, profundidad y calidez.

Cómo responder:
- Si la pregunta tiene respuesta concreta → dala directo en la primera línea
- Si es un concepto → explícalo con ejemplo práctico
- Cita el módulo cuando ayude: "En el Módulo 2 – Sistema Digestivo..."
- Si la pregunta es amplia → organiza en pasos o secciones claras
- Si no está en el material → dilo honestamente y responde desde principios generales

Tono: didáctico, cálido, paciente. Como el maestro que siempre tiene tiempo para explicar bien."""


# ── Cliente Groq ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_client() -> "OpenAI | None":
    if OpenAI is None:
        return None
    # Usar OpenAI directamente (más confiable y económico con gpt-4o-mini)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        return OpenAI(api_key=api_key)
    # Fallback: intentar con Groq
    groq_key = os.getenv("GROQ_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    if groq_key:
        return OpenAI(api_key=groq_key, base_url=base_url)
    logger.warning("No se encontró API key válida.")
    return None


def _model() -> str:
    # gpt-4o-mini: excelente calidad, muy bajo costo (~$0.15/1M tokens)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key.startswith("sk-"):
        return "gpt-4o-mini"
    # Groq fallback
    return os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")


# ── KB compartido (lo provee main.py para no cargarlo dos veces) ─────────────

_shared_kb = None  # Referencia al KB ya cargado por main.py


def set_shared_kb(kb) -> None:
    """Llamado desde main.py una vez que el KB ya está cargado en caché."""
    global _shared_kb
    _shared_kb = kb


# ── Búsqueda de contexto en la base de conocimiento ──────────────────────────

def _get_context(message: str) -> str:
    """Busca fragmentos relevantes. Usa el KB compartido; si no está listo, devuelve ''."""
    import threading

    kb = _shared_kb
    if kb is None:
        return ""

    result: dict = {"ctx": ""}

    def _search():
        try:
            results = kb.search(message, limit=3)
            parts = []
            for r in results[:3]:
                src = getattr(r, "source_file", "")
                text = getattr(r, "text", "")
                if text.strip():
                    parts.append(f"[{src}]\n{text.strip()}")
            result["ctx"] = "\n\n---\n\n".join(parts)
        except Exception as exc:
            logger.debug("Error en búsqueda de contexto: %s", exc)

    t = threading.Thread(target=_search, daemon=True)
    t.start()
    t.join(timeout=2.5)  # máximo 2.5 s; si no, se sigue sin contexto
    return result["ctx"]


# ── Streaming ─────────────────────────────────────────────────────────────────

def _detect_sistema_from_conversation(message: str, history: list[dict]) -> Optional[str]:
    """
    Busca el sistema corporal en el mensaje actual y en el historial reciente.
    """
    # Primero el mensaje actual
    sistema = detect_sistema(message)
    if sistema:
        return sistema
    # Luego los últimos 6 mensajes del historial
    for turn in reversed(history[-6:]):
        content = turn.get("content", "")
        if isinstance(content, str):
            sistema = detect_sistema(content)
            if sistema:
                return sistema
    return None


def _user_confirmed_yes(message: str) -> bool:
    """Detecta si el terapeuta confirmó un SÍ de la MS."""
    msg = message.lower().strip()
    affirmatives = ["sí", "si", "yes", "confirmado", "afirmativo", "así es",
                    "positivo", "correcto", "exacto", "sip", "aha"]
    if len(msg) < 30 and any(msg == a or msg.startswith(a) for a in affirmatives):
        return True
    if "ms dijo" in msg or "dijo sí" in msg or "dijo si" in msg:
        return True
    return False


def _user_said_no(message: str) -> bool:
    """Detecta si el terapeuta respondió NO de la MS."""
    msg = message.lower().strip()
    negatives = ["no", "nope", "negativo", "no confirmó", "no hay", "ninguno", "nada"]
    if len(msg) < 20 and any(msg == n or msg.startswith(n) for n in negatives):
        return True
    return False


def _get_sistema_from_last_ai_message(history: list[dict]) -> Optional[str]:
    """
    Busca el sistema en el último mensaje del asistente (cuando preguntó sobre él).
    """
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            content = turn.get("content", "")
            if "conflicto" in content.lower():
                return detect_sistema(content)
    return None


def stream_chat(message: str, history: list[dict], mode: str) -> Generator[str, None, None]:
    """
    Genera la respuesta token a token como Server-Sent Events.
    Cada evento tiene el formato:  data: {"text": "..."}
    Al terminar envía:             data: [DONE]
    """
    client = _get_client()
    if client is None:
        yield 'data: {"text": "⚠️ El servicio de IA no está disponible en este momento."}\n\n'
        yield "data: [DONE]\n\n"
        return

    system_prompt = TERAPEUTA_SYSTEM if mode == "terapeuta" else ALUMNO_SYSTEM

    # ── Para el modo terapeuta: inyectar tabla cuando se identifica el sistema ──
    tabla_a_emitir = ""
    sistema_sesion = None
    subsistema_sesion = None
    usuario_dijo_no = _user_said_no(message)

    if mode == "terapeuta":
        # 1. Intentar detección fina: síntoma específico → subsistema concreto
        sintoma_result = detect_sintoma(message)

        if sintoma_result and not usuario_dijo_no:
            sistema_sesion, subsistema_sesion = sintoma_result
            # Mostrar SOLO los conflictos del subsistema específico
            tabla_a_emitir = get_subsystem_table(sistema_sesion, subsistema_sesion)
        else:
            # 2. Detección de sistema general (sin subsistema conocido)
            sistema_en_mensaje = detect_sistema(message)
            sistema_en_historia = _get_sistema_from_last_ai_message(history)

            if sistema_en_mensaje and not usuario_dijo_no:
                sistema_sesion = sistema_en_mensaje
                # Mostrar lista de subsistemas para que terapeuta pregunte a la MS cuál
                tabla_a_emitir = get_subsystems_list(sistema_sesion)
            elif sistema_en_historia and not usuario_dijo_no:
                # Continuar sesión existente: no volver a mostrar tabla
                sistema_sesion = sistema_en_historia

        if sistema_sesion and not usuario_dijo_no:
            # Añadir referencia completa al AI (para que sepa qué sistema/subsistema está activo)
            if subsistema_sesion:
                tabla_ref = get_subsystem_table(sistema_sesion, subsistema_sesion)
                ref_label = f"{sistema_sesion.upper()} — {subsistema_sesion}"
            else:
                tabla_ref = get_conflict_table(sistema_sesion)
                ref_label = sistema_sesion.upper()
            system_prompt += (
                f"\n\n══ REFERENCIA DE CONFLICTOS {ref_label} ══"
                f"{tabla_ref}"
                f"\n══ FIN DE REFERENCIA ══\n\n"
                f"{'La tabla ya fue enviada al terapeuta y está visible en pantalla. No la repitas.' if tabla_a_emitir else 'El terapeuta ya tiene la tabla de referencia visible.'} "
                f"Ejecuta el protocolo: cuando la MS confirme subsistema, indica bloque y número."
            )
        elif usuario_dijo_no:
            # MS dijo NO al sistema: guiar al rastreo general
            sistema_en_mensaje = detect_sistema(message)
            sistema_en_historia = _get_sistema_from_last_ai_message(history)
            sistema_rechazado = sistema_en_mensaje or sistema_en_historia or ""
            system_prompt += (
                f"\n\nINSTRUCCIÓN: La MS dijo NO al sistema {sistema_rechazado}. "
                f"Ahora debes guiar el RASTREO CONFLICTOLÓGICO GENERAL: "
                f"pregunta por cada sistema uno a uno (respiratorio, digestivo, endócrino, "
                f"cardiovascular, osteomuscular, dermatológico, reproductivo, urinario, "
                f"inmunológico, neurosensorial) hasta que la MS confirme alguno. "
                f"Empieza por el primer sistema que NO se ha preguntado todavía. "
                f"Una sola pregunta MS por respuesta."
            )

    context = _get_context(message)
    if context:
        system_prompt += f"\n\n--- CONTEXTO DEL MANUAL ---\n{context}\n---"

    # Limitar historial a las últimas 12 interacciones (6 turnos)
    trimmed_history = history[-12:] if len(history) > 12 else history

    # Emitir la tabla ANTES de la respuesta del AI (solo para síntomas nuevos)
    if tabla_a_emitir:
        tabla_payload = json.dumps({"text": tabla_a_emitir}, ensure_ascii=False)
        yield f"data: {tabla_payload}\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        *trimmed_history,
        {"role": "user", "content": message},
    ]

    max_tokens = 800 if mode == "terapeuta" else 1200

    try:
        stream = client.chat.completions.create(
            model=_model(),
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=0.4 if mode == "terapeuta" else 0.6,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                payload = json.dumps({"text": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
    except Exception as exc:
        logger.error("Error en stream_chat: %s", exc)
        payload = json.dumps({"text": "\n\n⚠️ Ocurrió un error. Intenta de nuevo."})
        yield f"data: {payload}\n\n"

    yield "data: [DONE]\n\n"
