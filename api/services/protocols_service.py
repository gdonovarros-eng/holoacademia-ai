from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_COURSE_SLUG = "course_holobiomagnetismo_2021"

CONFLICTOLOGIA_DIR = BASE_DIR / "data" / "conflictologia"
CONFLICTOLOGIA_INDEX_PATH = CONFLICTOLOGIA_DIR / "index.json"
PROCEDURAL_PROTOCOLS_PATH = BASE_DIR / "data" / "procedural_protocols_db.json"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _course_dir(course_slug: str = DEFAULT_COURSE_SLUG) -> Path:
    direct = BASE_DIR / "data" / "knowledge_units" / course_slug
    if direct.exists():
        return direct
    holo_app = BASE_DIR / "04_holoacademia_app" / "data" / "knowledge_units" / course_slug
    if holo_app.exists():
        return holo_app
    return direct


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def _safe_load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Existing protocol guide (lookup by id/name)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def _load_protocols(course_slug: str = DEFAULT_COURSE_SLUG) -> Dict[str, Any]:
    course_dir = _course_dir(course_slug)
    protocol_path = course_dir / "05_protocols" / "protocols.json"
    manifest_path = course_dir / "06_catalog" / "course_manifest.json"
    connection_path = course_dir / "09_connection_map.json"
    return {
        "course_dir": course_dir,
        "protocols": _safe_load_json(protocol_path, []),
        "manifest": _safe_load_json(manifest_path, {}),
        "connection_map": _safe_load_json(connection_path, {}),
    }


def _protocol_aliases(protocol: Dict[str, Any]) -> List[str]:
    aliases = protocol.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = []
    values = [protocol.get("id", ""), protocol.get("nombre", "")]
    values.extend(aliases)
    return [str(item).strip() for item in values if str(item).strip()]


def _match_protocol(protocol: Dict[str, Any], protocol_id: str, protocol_name: str) -> Dict[str, Any]:
    id_query = _normalize_text(protocol_id)
    name_query = _normalize_text(protocol_name)
    protocol_id_norm = _normalize_text(str(protocol.get("id", "")))
    protocol_name_norm = _normalize_text(str(protocol.get("nombre", "")))
    aliases = [_normalize_text(alias) for alias in _protocol_aliases(protocol)]

    score = 0.0
    reason = "no_match"

    if id_query:
        if id_query == protocol_id_norm:
            return {"score": 100.0, "reason": "protocol_id_exact"}
        if id_query in aliases:
            return {"score": 95.0, "reason": "protocol_id_alias"}
        if id_query and id_query in protocol_id_norm:
            score = max(score, 86.0)
            reason = "protocol_id_contains"

    if name_query:
        if name_query == protocol_name_norm:
            return {"score": 98.0, "reason": "protocol_name_exact"}
        if name_query in aliases:
            return {"score": 92.0, "reason": "protocol_name_alias"}
        if name_query and name_query in protocol_name_norm:
            score = max(score, 84.0)
            reason = "protocol_name_contains"
        elif protocol_name_norm and protocol_name_norm in name_query:
            score = max(score, 82.0)
            reason = "protocol_name_reverse_contains"

    return {"score": score, "reason": reason}


def _serialize_steps(steps: Any) -> List[Dict[str, Any]]:
    if not isinstance(steps, list):
        return []
    serialized: List[Dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        instruction = str(step.get("instruccion", "")).strip()
        title = str(step.get("titulo", "")).strip()
        if not instruction or not title:
            continue
        serialized.append(
            {
                "orden": int(step.get("orden", len(serialized) + 1)),
                "titulo": title,
                "instruccion": instruction,
                "objetivo_del_paso": str(step.get("objetivo_del_paso", "")).strip(),
                "que_observar": [str(item).strip() for item in step.get("que_observar", []) if str(item).strip()],
                "que_registrar": [str(item).strip() for item in step.get("que_registrar", []) if str(item).strip()],
                "notas": [str(item).strip() for item in step.get("notas", []) if str(item).strip()],
                "decision_points": [str(item).strip() for item in step.get("decision_points", []) if str(item).strip()],
                "criterios_de_avance": [str(item).strip() for item in step.get("criterios_de_avance", []) if str(item).strip()],
                "errores_comunes": [str(item).strip() for item in step.get("errores_comunes", []) if str(item).strip()],
            }
        )
    return serialized


def _build_answer(protocol: Dict[str, Any], case_context: Optional[Dict[str, Any]], found: bool) -> str:
    if not found:
        return (
            "No encontré un protocolo con base suficiente usando ese nombre o id. "
            "Si quieres, prueba con el nombre exacto del protocolo o con un identificador más específico."
        )

    intro = "Encontré el protocolo solicitado. Te dejo una guía clara del objetivo, cuándo se usa y los pasos principales para seguirlo con orden."
    if case_context:
        intro = (
            "Encontré el protocolo solicitado. Tomé en cuenta que compartiste un contexto breve del caso, "
            "pero mantengo la guía fiel al protocolo, sin modificar sus pasos."
        )
    usage = protocol.get("cuando_usarlo", [])
    usage_text = ""
    if usage:
        usage_text = f" Se utiliza sobre todo en situaciones como: {usage[0]}"
    return intro + usage_text


def run_protocol_guide(request_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        course_slug = str(request_data.get("course_slug") or DEFAULT_COURSE_SLUG).strip() or DEFAULT_COURSE_SLUG
        protocol_id = str(request_data.get("protocol_id", "")).strip()
        protocol_name = str(request_data.get("protocol_name", "")).strip()
        case_context = request_data.get("case_context") if isinstance(request_data.get("case_context"), dict) else None

        loaded = _load_protocols(course_slug)
        protocols = loaded.get("protocols", [])
        manifest = loaded.get("manifest", {})
        if not isinstance(protocols, list) or not protocols:
            return {
                "found": False,
                "protocol_id": None,
                "protocol_name": None,
                "answer": "La base de protocolos no está disponible en este momento.",
                "confidence": "low",
                "objetivo": None,
                "descripcion": None,
                "cuando_usarlo": [],
                "prerequisitos": [],
                "pasos": [],
                "observaciones": [],
                "advertencias": [],
                "trace": {"error": "protocols_unavailable", "course_slug": course_slug},
            }

        best_protocol = None
        best_meta = {"score": 0.0, "reason": "no_match"}
        for protocol in protocols:
            if not isinstance(protocol, dict):
                continue
            meta = _match_protocol(protocol, protocol_id=protocol_id, protocol_name=protocol_name)
            if meta["score"] > best_meta["score"]:
                best_protocol = protocol
                best_meta = meta

        if best_protocol is None or best_meta["score"] < 82.0:
            return {
                "found": False,
                "protocol_id": None,
                "protocol_name": None,
                "answer": _build_answer({}, case_context, found=False),
                "confidence": "low",
                "objetivo": None,
                "descripcion": None,
                "cuando_usarlo": [],
                "prerequisitos": [],
                "pasos": [],
                "observaciones": [],
                "advertencias": [],
                "trace": {
                    "course_slug": course_slug,
                    "requested_protocol_id": protocol_id,
                    "requested_protocol_name": protocol_name,
                    "match_reason": best_meta["reason"],
                    "score": best_meta["score"],
                },
            }

        steps = _serialize_steps(best_protocol.get("pasos", []))
        confidence = "high" if best_meta["score"] >= 95.0 else "medium"
        return {
            "found": True,
            "protocol_id": str(best_protocol.get("id", "")).strip() or None,
            "protocol_name": str(best_protocol.get("nombre", "")).strip() or None,
            "answer": _build_answer(best_protocol, case_context, found=True),
            "confidence": confidence,
            "objetivo": str(best_protocol.get("objetivo", "")).strip() or None,
            "descripcion": str(best_protocol.get("descripcion", "")).strip() or None,
            "cuando_usarlo": [str(item).strip() for item in best_protocol.get("cuando_usarlo", []) if str(item).strip()],
            "prerequisitos": [str(item).strip() for item in best_protocol.get("prerequisitos", []) if str(item).strip()],
            "pasos": steps,
            "observaciones": [str(item).strip() for item in best_protocol.get("observaciones", []) if str(item).strip()],
            "advertencias": [str(item).strip() for item in best_protocol.get("advertencias", []) if str(item).strip()],
            "trace": {
                "course_slug": course_slug,
                "course_name": manifest.get("nombre_del_curso", ""),
                "requested_protocol_id": protocol_id,
                "requested_protocol_name": protocol_name,
                "match_reason": best_meta["reason"],
                "score": best_meta["score"],
                "case_context_used": bool(case_context),
                "steps_count": len(steps),
            },
        }
    except Exception as exc:
        return {
            "found": False,
            "protocol_id": None,
            "protocol_name": None,
            "answer": "Hubo un problema al procesar la guía de protocolos. Intenta nuevamente.",
            "confidence": "low",
            "objetivo": None,
            "descripcion": None,
            "cuando_usarlo": [],
            "prerequisitos": [],
            "pasos": [],
            "observaciones": [],
            "advertencias": [],
            "trace": {"error": str(exc)},
        }


# ---------------------------------------------------------------------------
# Protocol search (symptom → conflict + procedural protocol)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_conflictologia_index() -> Dict[str, Any]:
    return _safe_load_json(CONFLICTOLOGIA_INDEX_PATH, {"systems": []})


@lru_cache(maxsize=1)
def _load_procedural_protocols() -> List[Dict[str, Any]]:
    data = _safe_load_json(PROCEDURAL_PROTOCOLS_PATH, {"protocols": []})
    return data.get("protocols", [])


def _detect_body_system(query: str) -> Optional[Dict[str, Any]]:
    index = _load_conflictologia_index()
    query_lower = query.lower()
    best_system = None
    best_score = 0

    for system in index.get("systems", []):
        score = 0
        for kw in system.get("keywords", []):
            if kw.lower() in query_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_system = system

    return best_system if best_score > 0 else None


def _load_conflictologia_text(source_filename: str) -> str:
    path = CONFLICTOLOGIA_DIR / source_filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _build_llm_client():
    """Build an LLM client for protocol search using the same env vars as the rest of the app."""
    try:
        import openai

        api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = None
        model = os.getenv("THERAPEUTIC_ASSISTANT_USE_MODEL", "")

        if os.getenv("GROQ_API_KEY"):
            base_url = "https://api.groq.com/openai/v1"
            if not model:
                model = "llama-3.1-70b-versatile"
        elif os.getenv("OPENAI_API_KEY"):
            if not model:
                model = "gpt-4o-mini"

        if not api_key:
            return None, None

        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        return client, model
    except Exception:
        return None, None


_SEARCH_SYSTEM_PROMPT = """Eres un asistente especializado en Método Lavín de Terapia Holística.
Tu tarea es analizar el síntoma o problema que describe el terapeuta, identificar los conflictos psicosomáticos
más relevantes del mapa de conflictología proporcionado, y sugerir qué protocolo terapéutico es el más adecuado.

Responde SIEMPRE en JSON con esta estructura exacta:
{
  "conflictos_relevantes": [
    {
      "nombre": "nombre del conflicto",
      "subsistema": "subsistema corporal (ej: nasal, estomacal)",
      "frase_conflicto": "la frase exacta del conflicto según el mapa",
      "relevancia": "explicación breve de por qué aplica al caso"
    }
  ],
  "lectura_general": "una síntesis integradora de los conflictos encontrados",
  "protocolo_sugerido_id": "id del protocolo sugerido (o null si no aplica)",
  "protocolo_sugerido_nombre": "nombre del protocolo sugerido",
  "razon_protocolo": "por qué este protocolo es el más indicado"
}

Extrae solo los conflictos que genuinamente correspondan al caso. Máximo 5 conflictos.
Si no hay conflictos claros en el mapa para el síntoma indicado, di que el rastreo general es necesario.
"""


def _call_llm_for_conflicts(
    query: str,
    system_text: str,
    system_name: str,
    procedural_protocols: List[Dict[str, Any]],
    notas: str,
) -> Dict[str, Any]:
    client, model = _build_llm_client()
    if not client:
        return {}

    protocols_summary = "\n".join(
        f"- id: {p['id']} | nombre: {p['nombre']} | cuando_usarlo: {'; '.join(p.get('cuando_usarlo', [])[:2])}"
        for p in procedural_protocols
    )

    user_msg = f"""Sistema corporal identificado: {system_name}

Síntoma / problema del consultante: {query}
{f"Notas adicionales: {notas}" if notas else ""}

MAPA DE CONFLICTOLOGÍA ({system_name}):
{system_text[:6000]}

PROTOCOLOS TERAPÉUTICOS DISPONIBLES:
{protocols_summary}

Identifica los conflictos más relevantes y sugiere el protocolo adecuado."""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        logger.warning("LLM call failed in protocol search: %s", exc)
        return {}


def _fallback_response(query: str, system: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not system:
        return {
            "sistema_detectado": None,
            "sistema_nombre": None,
            "conflictos_relevantes": [],
            "lectura_general": (
                "No pude identificar un sistema corporal específico. "
                "Realiza el rastreo conflictológico general (Módulo 0) para localizar el conflicto implicado."
            ),
            "protocolo_sugerido": None,
            "razon_protocolo": None,
        }

    return {
        "sistema_detectado": system["id"],
        "sistema_nombre": system["nombre"],
        "conflictos_relevantes": [],
        "lectura_general": (
            f"Se detectó un posible conflicto en el {system['nombre']}. "
            "Usa el mapa de conflictología correspondiente para localizar el conflicto específico mediante rastreo."
        ),
        "protocolo_sugerido": None,
        "razon_protocolo": None,
    }


def search_protocols(query: str, notas: str = "") -> Dict[str, Any]:
    """
    Given a symptom/problem, find relevant conflictología conflicts and suggest
    which procedural protocol to use.
    """
    try:
        system = _detect_body_system(query + " " + notas)
        procedural_protocols = _load_procedural_protocols()

        system_text = ""
        system_name = system["nombre"] if system else ""
        if system:
            system_text = _load_conflictologia_text(system["source_file"])

        if not system_text and not system:
            return _fallback_response(query, system)

        llm_result = _call_llm_for_conflicts(
            query=query,
            system_text=system_text,
            system_name=system_name,
            procedural_protocols=procedural_protocols,
            notas=notas,
        )

        if not llm_result:
            return _fallback_response(query, system)

        # Attach full protocol steps if suggested
        suggested_protocol = None
        suggested_id = llm_result.get("protocolo_sugerido_id")
        if suggested_id:
            for p in procedural_protocols:
                if p.get("id") == suggested_id:
                    suggested_protocol = {
                        "id": p["id"],
                        "nombre": p["nombre"],
                        "objetivo": p.get("objetivo", ""),
                        "cuando_usarlo": p.get("cuando_usarlo", []),
                        "prerequisitos": p.get("prerequisitos", []),
                        "pasos": p.get("pasos", []),
                        "observaciones": p.get("observaciones", []),
                    }
                    break

        return {
            "sistema_detectado": system["id"] if system else None,
            "sistema_nombre": system_name,
            "conflictos_relevantes": llm_result.get("conflictos_relevantes", []),
            "lectura_general": llm_result.get("lectura_general", ""),
            "protocolo_sugerido": suggested_protocol,
            "razon_protocolo": llm_result.get("razon_protocolo"),
        }

    except Exception as exc:
        logger.exception("Error in search_protocols: %s", exc)
        return {
            "sistema_detectado": None,
            "sistema_nombre": None,
            "conflictos_relevantes": [],
            "lectura_general": "Error procesando la búsqueda. Intenta nuevamente.",
            "protocolo_sugerido": None,
            "razon_protocolo": None,
        }
