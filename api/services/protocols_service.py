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

SOURCES_DIR = (
    BASE_DIR
    / "data"
    / "processed_library"
    / "Diplomados"
    / "diplomado-terapia-holistica-1"
    / "sources"
)

SYSTEM_MANUAL_MAP = {
    "respiratorio":       "Manual_del_Módulo_1.txt",
    "digestivo":          "Manual_del_Módulo_2.txt",
    "alimenticio":        "Manual_del_Módulo_3.txt",
    "endocrino":          "Manual_del_Módulo_4.txt",
    "cardiovascular":     "Manual_del_Módulo_5.txt",
    "osteomuscular":      "Manual_del_Módulo_6.txt",
    "dermato_lipofascial":"Manual_del_Módulo_7.txt",
    "reproductivo":       "Manual_del_Módulo_8.txt",
    "urinario":           "Manual_del_Módulo_9.txt",
    "inmunologico":       "Manual_del_Módulo_10.txt",
    "neurosensorial":     "Manual_del_Módulo_11.txt",
}

# Generic rastreo protocol file (all 8 types, from respiratorio module — same steps for all systems)
RASTREO_PROTOCOL_PATH = SOURCES_DIR / "Protocolos_de_Rastreo_-_Módulo_1.txt"

# Systems that already have their own complete rastreo sections (skip appending generic template)
SYSTEMS_WITH_FULL_RASTREO = {"digestivo"}


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

    # Build a merged list: start with procedural_protocols_db (enriched, with full notas/tablas),
    # then append any course-specific protocols not already covered by id.
    procedural = _safe_load_json(PROCEDURAL_PROTOCOLS_PATH, {"protocols": []})
    procedural_list = procedural.get("protocols", []) if isinstance(procedural, dict) else []
    procedural_ids = {p.get("id") for p in procedural_list if isinstance(p, dict)}

    course_protocols = _safe_load_json(protocol_path, [])
    if not isinstance(course_protocols, list):
        course_protocols = []
    extra = [p for p in course_protocols if isinstance(p, dict) and p.get("id") not in procedural_ids]

    merged = procedural_list + extra

    return {
        "course_dir": course_dir,
        "protocols": merged,
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

        model = os.getenv("OPENAI_MODEL", "").strip()
        base_url = None

        # Priority: OpenRouter → OpenAI → Groq (legacy)
        if os.getenv("OPENROUTER_API_KEY"):
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
            if not model:
                model = "google/gemini-2.5-flash"
        elif os.getenv("OPENAI_API_KEY"):
            api_key = os.getenv("OPENAI_API_KEY")
            if not model:
                model = "gpt-4o-mini"
        elif os.getenv("GROQ_API_KEY"):
            api_key = os.getenv("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
            if not model:
                model = "llama-3.1-70b-versatile"
        else:
            return None, None

        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        return client, model
    except Exception:
        return None, None


_SEARCH_SYSTEM_PROMPT = """Eres el Motor de Protocolos de HoloacademIA, asistente clínico para terapeutas holísticos.
Tu tarea es analizar el síntoma o problema que describe el terapeuta, identificar los conflictos psicosomáticos
más relevantes del mapa de conflictología proporcionado, y sugerir qué protocolo terapéutico es el más adecuado.

Categorías de protocolos disponibles:
- "transgeneracional": para conflictos ancestrales, patrones que se repiten en el árbol genealógico,
  exclusiones familiares, o memorias heredadas. (EFT Transgeneracional, Inclusión, Extracción de Recursos, Onirológico)
- "bioenergético": para miedos, fobias, traumas, bloqueos energéticos, cuerdas, corazas, memorias.
  (Protocolo Miedos, Fobias, Liberación de Traumas, PTSD, Coraza Energética, Vidas Pasadas,
   Cuerdas Energéticas, Memorias Energéticas/Celulares/Kármicas)
- "sesion": protocolo marco para estructurar la sesión completa. (3 Fases — Sesión Holística)

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
  "razon_protocolo": "por qué este protocolo es el más indicado para resolver el conflicto encontrado"
}

Extrae solo los conflictos que genuinamente correspondan al caso. Máximo 5 conflictos.
Si no hay conflictos claros en el mapa para el síntoma indicado, di que el rastreo general es necesario.
Elige el protocolo más específico disponible: si hay trauma → liberacion_traumas; si hay patrón
transgeneracional → eft_transgeneracional; si hay miedo puntual → protocolo_miedos; etc.
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


import re as _re

_SYSTEM_SECTION_HEADERS: List[tuple] = [
    # ── Manual structural sections ──────────────────────────────────────────
    (_re.compile(r'^FUNDAMENTOS?\s*$', _re.I),                         "Fundamentos"),
    (_re.compile(r'^PRINCIPIOS?\s*$', _re.I),                          "Principios"),
    (_re.compile(r'^ANATOM\xcdA\s*$', _re.I),                          "Anatom\xeda"),
    (_re.compile(r'^PATOLOG\xcdAS?\s*$', _re.I),                       "Patolog\xedas"),
    (_re.compile(r'^MICROBIOLOG\xcdA\s*$', _re.I),                     "Microbiolog\xeda"),
    (_re.compile(r'^BIOMAGNÉTICOS?\s*$', _re.I),                        "Biom\xe1gn\xe9tico"),
    (_re.compile(r'^GENERACIONAL\s*$', _re.I),                          "Transgeneracional"),
    (_re.compile(r'^EMOCIONAL\s*$', _re.I),                             "Emocional"),
    (_re.compile(r'^NATURISTAS?\s*$', _re.I),                           "Protocolos Naturistas"),
    (_re.compile(r'^CONFLICTOLOG\xcdA\s*$', _re.I),                    "Conflictolog\xeda"),
    # ── Protocol rastreo sections ────────────────────────────────────────────
    (_re.compile(r'RASTREO\s+CONFLICTOL[\xd3O]GICO', _re.I),          "Protocolo de Rastreo Conflictol\xf3gico"),
    (_re.compile(r'RASTREO\s+MICROBIOL[\xd3O]GICO', _re.I),           "Rastreo Microbiol\xf3gico"),
    (_re.compile(r'RASTREO\s+BIOM[A\xc1]GNETICO(?!\s+GENERAL)', _re.I), "Rastreo Biom\xe1gn\xe9tico"),
    (_re.compile(r'RASTREO\s+HOLOBIOM[A\xc1]GNETICO', _re.I),         "Rastreo Holobiom\xe1gn\xe9tico"),
    (_re.compile(r'RASTREO\s+VIBRACIONAL', _re.I),                      "Rastreo Vibracional"),
    (_re.compile(r'RASTREO\s+BIOENERG[\xc9E]TICO', _re.I),            "Rastreo Bioenerg\xe9tico"),
    (_re.compile(r'SES[I\xcd][O\xd3]N\s+TERAP', _re.I),              "Sesi\xf3n Terap\xe9utica"),
    (_re.compile(r'RASTREO\s+ORG[A\xc1]NICO', _re.I),                 "Rastreo Org\xe1nico"),
]

_AUTHOR_LINE = _re.compile(r'ALEJANDRO\s+LAV[IÍ]N', _re.I)
_PAGE_NUMBER = _re.compile(r'^\s*\d{1,3}\s*$')


def _clean_system_text(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if _AUTHOR_LINE.search(line):
            continue
        if _PAGE_NUMBER.match(line):
            continue
        cleaned.append(line.rstrip())
    result = _re.sub(r'\n{4,}', '\n\n\n', '\n'.join(cleaned))
    return result.strip()


_SENTENCE_PREFIXES = _re.compile(r'^(NO|SI|SÍ|–|-|•|\?|¿|MS:|\()', _re.I)

def _parse_system_sections(text: str) -> List[Dict[str, str]]:
    clean = _clean_system_text(text)
    lines = clean.splitlines()

    # Find where each major section starts
    breaks: List[tuple] = []  # (line_index, label)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            continue
        # Skip lines that are clearly part of a sentence (not a header)
        if _SENTENCE_PREFIXES.match(stripped):
            continue
        for pattern, label in _SYSTEM_SECTION_HEADERS:
            if pattern.search(stripped):
                if not breaks or breaks[-1][1] != label:
                    breaks.append((i, label))
                break

    if not breaks:
        return [{"id": "conflictologia", "label": "Conflictología", "content": clean}]

    sections = []
    first_break = breaks[0][0]
    if first_break > 0:
        intro_text = '\n'.join(lines[:first_break]).strip()
        if intro_text:
            sections.append({"id": "resumen", "label": "Mapa de Conflictos", "content": intro_text})

    for idx, (start, label) in enumerate(breaks):
        end = breaks[idx + 1][0] if idx + 1 < len(breaks) else len(lines)
        section_lines = lines[start:end]
        content = '\n'.join(section_lines).strip()
        section_id = _re.sub(r'\W+', '_', label.lower())[:30]
        if content:
            sections.append({"id": section_id, "label": label, "content": content})

    return sections


import re as re_mod

_SUBSYSTEM_HEADER = _re.compile(
    r'^(?:Conflictolog[i\xed]a\s+\w|CONFLICTOS?\s+(?:DE\s+)?[A-Z\xc1\xc9\xcd\xd3\xda])'
)
_RIGHT_NUM = _re.compile(r'^(.+?)\s{5,}(\d{1,2})\s*$')
_INLINE_PHRASE = _re.compile(r'^(\d{1,2})\s+"(.+?)"\s*$')


def _parse_conflicts_section(text: str) -> Optional[List[Dict[str, Any]]]:
    # Normalize curly/smart quotes (U+201C/D) to ASCII double-quote
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    lines = text.splitlines()

    # Detect genuine two-column layouts: many non-author lines have interior whitespace
    # followed by real text (not just a right-aligned digit used as conflict number).
    two_col_lines = sum(
        1 for l in lines
        if len(l) > 75
        and _re.search(r'\S {7,}[A-Za-z\xc1-\xff"(]', l)
        and not _AUTHOR_LINE.search(l)
    )
    if two_col_lines > 20:
        return None

    K_NUM, K_NAME, K_PHRASES = 'number', 'name', 'phrases'
    K_SUB, K_CONFLICTS = 'subsystem', 'conflicts'

    subsystems: List[Dict[str, Any]] = []
    current_sub: Optional[Dict[str, Any]] = None
    current_conflict: Optional[Dict[str, Any]] = None

    def flush_conflict() -> None:
        nonlocal current_conflict
        if current_conflict is not None and current_sub is not None:
            if current_conflict.get(K_PHRASES) or current_conflict.get(K_NAME):
                current_sub[K_CONFLICTS].append(current_conflict)
        current_conflict = None

    def flush_subsystem() -> None:
        nonlocal current_sub
        flush_conflict()
        if current_sub is not None and current_sub[K_CONFLICTS]:
            subsystems.append(current_sub)
        current_sub = None

    def _set_number(num: int) -> None:
        nonlocal current_conflict
        if current_conflict is None:
            current_conflict = {K_NUM: num, K_NAME: '', K_PHRASES: []}
        elif not current_conflict.get(K_NUM):
            current_conflict[K_NUM] = num
        elif current_conflict.get(K_PHRASES):
            flush_conflict()
            current_conflict = {K_NUM: num, K_NAME: '', K_PHRASES: []}
        else:
            current_conflict[K_NUM] = num

    def _add_phrase(raw: str) -> None:
        nonlocal current_conflict
        phrase = raw.strip('"').strip()
        if not phrase:
            return
        if current_conflict is None:
            current_conflict = {K_NUM: None, K_NAME: '', K_PHRASES: [phrase]}
        else:
            current_conflict[K_PHRASES].append(phrase)

    # Check whether standard subsystem headers exist in this text
    has_subsystem_headers = any(
        _SUBSYSTEM_HEADER.match(l.strip()) for l in lines if l.strip()
    )

    # If no standard headers, use a single catch-all subsystem
    if not has_subsystem_headers:
        current_sub = {K_SUB: 'Mapa de Conflictos', K_CONFLICTS: []}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _AUTHOR_LINE.search(stripped):
            continue
        if _re.match(r'^\d{3,}$', stripped):
            continue
        if any(pat.search(stripped) for pat, _ in _SYSTEM_SECTION_HEADERS):
            continue
        if _SENTENCE_PREFIXES.match(stripped):
            continue
        if len(stripped) > 130:
            continue

        # Subsystem header: "Conflictologia X" or "CONFLICTOS RENALES"
        if _SUBSYSTEM_HEADER.match(stripped):
            sub_name = ' '.join(stripped.split())
            if (
                current_sub is not None
                and current_sub[K_SUB].lower().split()[:3] == sub_name.lower().split()[:3]
            ):
                pass  # same subsystem continues on next page
            else:
                flush_subsystem()
                current_sub = {K_SUB: sub_name, K_CONFLICTS: []}
            continue

        if current_sub is None:
            continue

        # Number inline with phrase: '2 "phrase"'
        m_inline = _INLINE_PHRASE.match(stripped)
        if m_inline:
            flush_conflict()
            current_conflict = {
                K_NUM: int(m_inline.group(1)),
                K_NAME: '',
                K_PHRASES: [m_inline.group(2).strip()],
            }
            continue

        # Conflict name with right-aligned number: "Conflicto X          1"
        m_right = _RIGHT_NUM.match(stripped)
        if m_right and len(m_right.group(1).strip()) > 4:
            name_part = m_right.group(1).strip()
            num = int(m_right.group(2))
            if name_part.startswith('"'):
                _add_phrase(name_part)
                _set_number(num)
            else:
                flush_conflict()
                current_conflict = {K_NUM: num, K_NAME: name_part, K_PHRASES: []}
            continue

        # Standalone number (1-2 digits)
        if _re.match(r'^\d{1,2}$', stripped):
            _set_number(int(stripped))
            continue

        # Quoted phrase
        if stripped.startswith('"'):
            _add_phrase(stripped)
            continue

        # Text line: conflict name or continuation
        if current_conflict is not None and current_conflict.get(K_PHRASES):
            flush_conflict()
        if current_conflict is None:
            current_conflict = {K_NUM: None, K_NAME: stripped, K_PHRASES: []}
        elif not current_conflict.get(K_NAME):
            current_conflict[K_NAME] = stripped
        else:
            current_conflict[K_NAME] = current_conflict[K_NAME] + ' - ' + stripped

    flush_subsystem()
    return subsystems if subsystems else None


@lru_cache(maxsize=12)
def _load_system_text(source_filename: str) -> str:
    path = CONFLICTOLOGIA_DIR / source_filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=12)
def _load_manual_text(system_id: str) -> str:
    filename = SYSTEM_MANUAL_MAP.get(system_id)
    if not filename:
        return ""
    path = SOURCES_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_generic_rastreo_text() -> str:
    """Load the generic rastreo protocol template (microbiológico, biomagnético, etc.).
    These sections are system-agnostic and apply the same steps to every body system."""
    if not RASTREO_PROTOCOL_PATH.exists():
        return ""
    return RASTREO_PROTOCOL_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _get_generic_rastreo_sections() -> list:
    """Parse and cache the generic rastreo sections (everything except conflictológico)."""
    text = _load_generic_rastreo_text()
    if not text:
        return []
    all_sections = _parse_system_sections(text)
    # Keep only the non-conflictológico rastreo sections (microbiológico onwards)
    generic_labels = {
        "rastreo microbiológico", "rastreo biomágnético", "rastreo holobiomágnético",
        "rastreo vibracional", "rastreo bioenergético", "sesión terapéutica", "rastreo orgánico",
    }
    return [
        s for s in all_sections
        if any(g in s["label"].lower() for g in generic_labels)
    ]


def _is_conflict_label(label: str) -> bool:
    lo = label.lower()
    return "conflictolog" in lo or "protocolo de rastreo" in lo


def _attach_conflict_cards(sections: List[Dict[str, Any]]) -> bool:
    """Parse conflict cards for relevant sections; return True if meaningful cards were found."""
    found_any = False
    for sec in sections:
        if not _is_conflict_label(sec["label"]):
            continue
        parsed = _parse_conflicts_section(sec["content"])
        if not parsed:
            continue
        # Must have at least 5 conflicts with phrases, OR a named subsystem (not just the default)
        total_with_phrases = sum(
            1 for sub in parsed for c in sub.get("conflicts", []) if c.get("phrases")
        )
        has_named_subsystem = any(
            sub["subsystem"] != "Mapa de Conflictos" for sub in parsed
        )
        if total_with_phrases >= 5 or (total_with_phrases > 0 and has_named_subsystem):
            sec["conflicts_parsed"] = parsed
            found_any = True
    return found_any


def _supplement_with_conflictologia(system_id: str, source_file: str, sections: List[Dict[str, Any]]) -> None:
    """Add conflict sections from the cleaner conflictologia extract if the full manual lacks them."""
    conflit_text = _load_system_text(source_file)
    if not conflit_text:
        return
    extra = _parse_system_sections(conflit_text)
    if _attach_conflict_cards(extra):
        sections.extend(extra)


def get_system_detail(system_id: str) -> Optional[Dict[str, Any]]:
    index = _load_conflictologia_index()
    system = next((s for s in index.get("systems", []) if s["id"] == system_id), None)
    if not system:
        return None

    manual_text = _load_manual_text(system_id)

    if manual_text:
        sections = _parse_system_sections(manual_text)
        has_cards = _attach_conflict_cards(sections)
        # If the full manual lacks a good conflict section, supplement with the
        # cleaner conflictologia extract (single-column version for respiratorio etc.).
        if not has_cards:
            _supplement_with_conflictologia(system_id, system["source_file"], sections)
    else:
        sections = _parse_system_sections(_load_system_text(system["source_file"]))
        _attach_conflict_cards(sections)

    # Append generic rastreo protocol sections (microbiológico, biomagnético, etc.)
    # for systems that don't already include them from their module manual.
    if system_id not in SYSTEMS_WITH_FULL_RASTREO:
        existing_labels = {s["label"].lower() for s in sections}
        for sec in _get_generic_rastreo_sections():
            if sec["label"].lower() not in existing_labels:
                sections.append(sec)

    # Truncate very large sections (biomagnético tables etc.) to keep response manageable
    _MAX_SECTION_CHARS = 30_000
    for sec in sections:
        if len(sec.get("content", "")) > _MAX_SECTION_CHARS:
            truncated_len = len(sec["content"])
            sec["content"] = (
                sec["content"][:_MAX_SECTION_CHARS]
                + f"\n\n[Contenido truncado — {truncated_len:,} caracteres totales]"
            )
            sec["truncated"] = True

    return {
        "id": system["id"],
        "nombre": system["nombre"],
        "subsystems": system.get("subsystems", []),
        "total_conflicts": system.get("total_conflicts"),
        "keywords": system.get("keywords", []),
        "sections": sections,
    }


def get_systems_list() -> Dict[str, Any]:
    index = _load_conflictologia_index()
    systems = []
    for s in index.get("systems", []):
        systems.append({
            "id": s["id"],
            "nombre": s["nombre"],
            "subsystems": s.get("subsystems", []),
            "total_conflicts": s.get("total_conflicts"),
        })
    return {"systems": systems}


_CATEGORY_META: Dict[str, Dict[str, str]] = {
    "transgeneracional": {
        "label": "Transgeneracional",
        "descripcion": "Protocolos para liberar memorias, patrones y traumas heredados del árbol genealógico. Se trabaja sobre el campo mórfico familiar para sanar lo que se transmite de generación en generación.",
        "icono": "🌳",
    },
    "bioenergético": {
        "label": "Bioenergético",
        "descripcion": "Protocolos para limpiar y restaurar el campo energético del consultante: miedos, fobias, traumas, corazas, cuerdas, memorias celulares y presencias negativas.",
        "icono": "⚡",
    },
    "psicoemocional": {
        "label": "Psicoemocional",
        "descripcion": "Protocolos para reprocesar vivencias emocionales de infancia y adolescencia usando hipnosis, EFT y comunicación simbólica con figuras parentales.",
        "icono": "💛",
    },
    "rastreo": {
        "label": "Módulo de Rastreo",
        "descripcion": "Tablas visuales para rastreo con test muscular: hologramas, nudos psóricos, creencias limitantes, diagnóstico orgánico y protocolos especializados por sistema. El Motor muestra las tablas para que el terapeuta navegue sin soltar al consultante.",
        "icono": "🧭",
    },
    "sesion": {
        "label": "Estructura de Sesión",
        "descripcion": "Protocolo completo de una sesión holística de principio a fin: las tres fases esenciales que ordenan el trabajo terapéutico.",
        "icono": "📋",
    },
}

_CATEGORY_ORDER = ["sesion", "rastreo", "transgeneracional", "bioenergético", "psicoemocional"]


def get_catalog() -> Dict[str, Any]:
    protocols = _load_procedural_protocols()
    grouped: Dict[str, List[Dict]] = {}
    for p in protocols:
        cat = p.get("categoria", "otros")
        grouped.setdefault(cat, []).append(p)

    categories = []
    seen = set()
    for cat_id in _CATEGORY_ORDER:
        if cat_id in grouped:
            meta = _CATEGORY_META.get(cat_id, {"label": cat_id, "descripcion": "", "icono": "📌"})
            categories.append({
                "id": cat_id,
                "label": meta["label"],
                "descripcion": meta["descripcion"],
                "icono": meta["icono"],
                "protocolos": grouped[cat_id],
            })
            seen.add(cat_id)
    for cat_id, protos in grouped.items():
        if cat_id not in seen:
            meta = _CATEGORY_META.get(cat_id, {"label": cat_id, "descripcion": "", "icono": "📌"})
            categories.append({
                "id": cat_id,
                "label": meta["label"],
                "descripcion": meta["descripcion"],
                "icono": meta["icono"],
                "protocolos": protos,
            })

    return {
        "version": "3.0",
        "total": len(protocols),
        "categories": categories,
    }
