from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[2]
ACADEMIC_ENGINE_DIR = BASE_DIR / "Motor academico"

if str(ACADEMIC_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ACADEMIC_ENGINE_DIR))

# Reutilizamos el prompt pedagógico ya afinado del motor académico.
from academic_assistant.prompt_builder import ACADEMIC_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Refuerzo: el Sinodal responde SOLO con el material del curso (índice curado),
# nunca cita cursos/autores/maestros, y si no hay base lo dice con honestidad.
_REFUERZO = (
    "\n\nResponde ÚNICAMENTE con base en el MATERIAL DEL CURSO que se te entrega abajo. "
    "Si el material no cubre la pregunta, dilo con honestidad y no inventes. "
    "Nunca menciones cursos, autores, maestros ni nombres propios que aparezcan en el material."
)

_SIN_BASE = (
    "No encontré base suficiente dentro del material del curso para responder eso con "
    "precisión. ¿Puedes reformular la pregunta o darme un poco más de contexto?"
)


def _empty(answer: str, confidence: str = "low", used_fallback: bool = False) -> Dict[str, Any]:
    return {
        "answer": answer, "confidence": confidence, "sources_used": [],
        "concepts_used": [], "suggested_followups": [], "retrieval_trace": [],
        "intent": "academic_rag", "mode_used": "rag", "used_fallback": used_fallback,
        "concept_resolution": {}, "target_resolution_trace": [], "timings": {},
    }


def _historia(history: List[Dict[str, Any]] | None) -> str:
    if not history:
        return ""
    lineas = []
    for item in history[-6:]:
        rol = "Alumno" if str(item.get("role", "")).lower() in ("user", "alumno") else "Asistente"
        txt = str(item.get("content") or item.get("answer") or "").strip()
        if txt:
            lineas.append(f"{rol}: {txt}")
    return ("\nCONVERSACIÓN PREVIA\n" + "\n".join(lineas)) if lineas else ""


def run_academic_query(query: str, history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return _empty("Escribe una pregunta sobre el contenido del curso.")

    # 1) Recuperar del índice curado (mismo material que el Motor Terapéutico)
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(query, k=8)
        ctx = format_context(chunks, max_chars=7000)
    except Exception as exc:
        logger.error("RAG académico falló: %s", exc)
        return _empty("Hubo un problema al consultar el material. Intenta de nuevo.", used_fallback=True)

    if not ctx:
        return _empty(_SIN_BASE, confidence="low")

    # 2) Generar respuesta académica anclada en el material
    try:
        from api.chat_service import _get_client, _model
        client = _get_client()
        if client is None:
            return _empty("El asistente no está configurado. Intenta más tarde.", used_fallback=True)
        user = f"{_historia(history)}\n\nMATERIAL DEL CURSO\n{ctx}\n\nPREGUNTA DEL ALUMNO\n{query}"
        resp = client.chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": ACADEMIC_SYSTEM_PROMPT + _REFUERZO},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.error("LLM académico falló: %s", exc)
        return _empty("Hubo un problema al generar la respuesta. Intenta de nuevo.", used_fallback=True)

    if not answer:
        return _empty(_SIN_BASE, confidence="low")

    result = _empty(answer, confidence="high")
    result["used_fallback"] = False
    return result
