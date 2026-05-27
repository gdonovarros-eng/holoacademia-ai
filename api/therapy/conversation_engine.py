"""
Motor de inferencia conversacional tipo Akinator para diagnóstico terapéutico.

Síntesis Hamer (Nueva Medicina Germánica) + Christian Flèche (Biodescodificación) +
Alejandro Lavín (Biodescodificación + Biomagnetismo).

Cada sesión mantiene un estado conversacional con probabilidades P(H|E) que se
actualizan vía Bayes ingenuo con cada respuesta del usuario. El motor selecciona
la siguiente pregunta que MÁS REDUCE la entropía sobre las hipótesis activas.

Cuando la probabilidad de la hipótesis líder supera CONFIDENCE_THRESHOLD, el
motor presenta la "ficha clínica" completa con protocolo + pares biomagnéticos.
"""
from __future__ import annotations

import json
import math
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from threading import Lock


# ── Carga de knowledge base ───────────────────────────────────────────────
_KB_PATH = Path(__file__).parent.parent.parent / "data" / "therapeutic" / "biological_events.json"


def _load_kb() -> dict[str, Any]:
    with open(_KB_PATH, encoding="utf-8") as f:
        return json.load(f)


_KB_CACHE: Optional[dict[str, Any]] = None


def get_kb() -> dict[str, Any]:
    global _KB_CACHE
    if _KB_CACHE is None:
        _KB_CACHE = _load_kb()
    return _KB_CACHE


# ── Constantes ────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.72  # >72% → presentar ficha clínica
PRUNE_THRESHOLD = 0.02       # <2% → quitar de activas
MAX_QUESTIONS = 12           # cap absoluto para no eternizar
SESSION_TTL = 60 * 60 * 6    # 6h


# ── Sesiones en memoria ───────────────────────────────────────────────────
# (en producción real ir a Redis; para MVP funciona perfecto in-memory)
_SESSIONS: dict[str, dict[str, Any]] = {}
_SESSIONS_LOCK = Lock()


def _gc_sessions() -> None:
    """Limpia sesiones expiradas."""
    now = time.time()
    expired = [sid for sid, s in _SESSIONS.items() if now - s["last_touch"] > SESSION_TTL]
    for sid in expired:
        _SESSIONS.pop(sid, None)


# ── Helpers de matching ───────────────────────────────────────────────────
def _normalize(s: str) -> str:
    """Lowercase, strip accents, collapse spaces."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s.lower()).strip()
    return s


def _keyword_match(text: str, keywords: list[str]) -> int:
    """Cuenta cuántas keywords aparecen en text."""
    t = _normalize(text)
    return sum(1 for k in keywords if _normalize(k) in t)


# ── Initialización: prior P(H) a partir del cuestionario inicial ─────────
def _compute_initial_priors(intake: dict[str, Any]) -> dict[str, float]:
    """
    Calcula P(H) inicial usando texto del cuestionario (motivo, síntomas, etc.).
    Cada evento recibe score por matches keyword en sus síntomas_compatibles y nombre.
    """
    kb = get_kb()
    eventos = kb["eventos"]

    # Texto combinado del intake
    parts = [
        intake.get("motivo_consulta", ""),
        " ".join(intake.get("sintomas", []) if isinstance(intake.get("sintomas"), list) else []),
        intake.get("inicio", ""),
        intake.get("duracion", ""),
        intake.get("contexto_emocional", ""),
        intake.get("observaciones", ""),
        " ".join(intake.get("antecedentes", []) if isinstance(intake.get("antecedentes"), list) else []),
        intake.get("family_notes", ""),
    ]
    text_blob = " ".join(p for p in parts if p)

    scores: dict[str, float] = {}
    for ev in eventos:
        score = 1.0  # base pequeña para no anular
        # Síntomas compatibles
        for s in ev.get("sintomas_compatibles", []):
            # Match parcial: si alguna palabra clave del síntoma aparece
            symptom_words = [w for w in _normalize(s).split() if len(w) > 4]
            for w in symptom_words:
                if w in _normalize(text_blob):
                    score += 0.5
        # Ubicaciones orgánicas (match anatómico)
        for loc in ev.get("ubicaciones_organicas", []):
            for word in _normalize(loc).split():
                if len(word) > 3 and word in _normalize(text_blob):
                    score += 0.8
        # Penalizar si menciona explícitamente síntomas excluyentes
        for s in ev.get("sintomas_excluyentes", []):
            for word in _normalize(s).split():
                if len(word) > 5 and word in _normalize(text_blob):
                    score *= 0.3
        scores[ev["id"]] = score

    # Normalizar a probabilidades
    total = sum(scores.values()) or 1.0
    return {eid: s / total for eid, s in scores.items()}


# ── Update bayesiano por respuesta ────────────────────────────────────────
def _update_with_answer(
    priors: dict[str, float],
    pregunta_idx: int,
    pregunta_evento_id: str,
    respuesta: str,
) -> dict[str, float]:
    """
    Update bayesiano simple: cada pregunta tiene pesos peso_si y peso_no (del KB).
    respuesta ∈ {'si', 'no', 'no_se'}. 'no_se' no actualiza.
    """
    if respuesta == "no_se":
        return priors

    kb = get_kb()
    target_ev = next((e for e in kb["eventos"] if e["id"] == pregunta_evento_id), None)
    if not target_ev:
        return priors

    preguntas = target_ev.get("preguntas_discriminantes", [])
    if pregunta_idx >= len(preguntas):
        return priors

    pq = preguntas[pregunta_idx]
    peso = pq.get("peso_si" if respuesta == "si" else "peso_no", 0)

    # Update: la hipótesis dueña de la pregunta sube/baja según peso
    # Las demás hipótesis se ven afectadas levemente si comparten síntomas
    new_priors: dict[str, float] = {}
    for eid, p in priors.items():
        if eid == pregunta_evento_id:
            # Factor multiplicativo basado en peso (entre 0.5 y 2.0 aprox)
            factor = math.exp(peso)
            new_priors[eid] = p * factor
        else:
            # Si la respuesta fue "sí" y aumenta probabilidad de la hipótesis dueña,
            # las otras hipótesis se reducen levemente (suma de prob es constante)
            # Si la respuesta fue "no", no penalizamos al resto
            if respuesta == "si" and peso > 0:
                new_priors[eid] = p * 0.92  # leve penalización
            else:
                new_priors[eid] = p

    # Re-normalizar
    total = sum(new_priors.values()) or 1.0
    return {eid: p / total for eid, p in new_priors.items()}


# ── Selector de pregunta óptima (entropía) ─────────────────────────────────
def _entropy(probs: list[float]) -> float:
    """Shannon entropy en bits."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


def _pick_next_question(
    priors: dict[str, float],
    asked: set[tuple[str, int]],
) -> Optional[tuple[str, int, dict]]:
    """
    Selecciona la próxima pregunta que MÁS reduce la entropía esperada.
    Retorna (evento_id, idx_pregunta, pregunta_dict) o None.
    """
    kb = get_kb()

    # Considerar solo top-N hipótesis activas
    sorted_h = sorted(priors.items(), key=lambda x: -x[1])
    top = [eid for eid, p in sorted_h if p > PRUNE_THRESHOLD][:8]
    if not top:
        return None

    best_score = -1.0
    best_q: Optional[tuple[str, int, dict]] = None

    for eid in top:
        ev = next((e for e in kb["eventos"] if e["id"] == eid), None)
        if not ev:
            continue
        for qidx, pq in enumerate(ev.get("preguntas_discriminantes", [])):
            if (eid, qidx) in asked:
                continue
            # Heurística: la pregunta es buena si tiene peso alto + viene de hipótesis con prob media
            # (preguntas de hipótesis con 50/50 son las más discriminantes)
            p_eid = priors[eid]
            distance_to_half = abs(p_eid - 0.5)
            discrimination_power = abs(pq.get("peso_si", 0)) + abs(pq.get("peso_no", 0))
            # Score: alta discriminación + prob media + no muy alta confianza ya
            score = discrimination_power * (1 - distance_to_half) * p_eid

            if score > best_score:
                best_score = score
                best_q = (eid, qidx, pq)

    return best_q


# ── Conversión a hipótesis con probabilidad para UI ──────────────────────
def _build_hipotesis_view(priors: dict[str, float], top_n: int = 4) -> list[dict[str, Any]]:
    """Devuelve top-N hipótesis con datos para UI (nombre + prob + contexto profundo)."""
    kb = get_kb()
    sorted_h = sorted(priors.items(), key=lambda x: -x[1])[:top_n]

    out: list[dict[str, Any]] = []
    for eid, p in sorted_h:
        ev = next((e for e in kb["eventos"] if e["id"] == eid), None)
        if not ev:
            continue
        out.append({
            "id": eid,
            "nombre": ev["nombre"],
            "categoria": ev["categoria"],
            "probabilidad": round(p, 4),
            "probabilidad_pct": round(p * 100, 1),
            "lectura_clinica": ev.get("lectura_clinica", ""),
            "ubicaciones_organicas": ev.get("ubicaciones_organicas", []),
            "sintomas_compatibles": ev.get("sintomas_compatibles", []),
            "ejemplos_clinicos": ev.get("ejemplos_clinicos", [])[:2],  # top 2 en vista intermedia
        })
    return out


# ── Construcción de ficha clínica final ───────────────────────────────────
def _build_ficha_clinica(evento_id: str, priors: dict[str, float], session: dict) -> dict[str, Any]:
    """Vista expandida al confirmar diagnóstico."""
    kb = get_kb()
    ev = next((e for e in kb["eventos"] if e["id"] == evento_id), None)
    if not ev:
        return {}

    # Pares biomagnéticos: enriquecer con info de DB v4.3 si está disponible
    pares = ev.get("pares_biomagneticos_sugeridos", [])
    pares_enriched = []
    try:
        db_path = Path(__file__).parent.parent.parent / "data" / "biomagnetic_pairs_db.json"
        if db_path.exists():
            with open(db_path) as f:
                db = json.load(f)
            # Index: nombre del par → metadata
            all_pairs = {}
            for r in db.get("regiones", []):
                for z in r.get("zonas", []):
                    for b in z.get("bloques", []):
                        for par in b.get("pares", []):
                            all_pairs[par.lower()] = {
                                "region": r.get("nombre"),
                                "zona": z.get("nombre"),
                                "bloque": b.get("nombre"),
                            }
            for pdata in pares:
                par_name = pdata.get("par", "")
                meta = all_pairs.get(par_name.lower(), {})
                pares_enriched.append({**pdata, **meta})
        else:
            pares_enriched = pares
    except Exception:
        pares_enriched = pares

    return {
        "id": evento_id,
        "nombre": ev["nombre"],
        "categoria": ev["categoria"],
        "probabilidad_final": round(priors.get(evento_id, 0) * 100, 1),
        "lectura_clinica": ev.get("lectura_clinica", ""),
        "ubicaciones_organicas": ev.get("ubicaciones_organicas", []),
        "sintomas_compatibles": ev.get("sintomas_compatibles", []),
        "sintomas_excluyentes": ev.get("sintomas_excluyentes", []),
        "ejemplos_clinicos": ev.get("ejemplos_clinicos", []),
        "protocolo_terapeutico": ev.get("protocolo_terapeutico", ""),
        "herramientas": ev.get("herramientas", []),
        "pares_biomagneticos": pares_enriched,
        "preguntas_respondidas": session.get("history", []),
    }


# ── API PÚBLICA ───────────────────────────────────────────────────────────
def start_conversation(intake: dict[str, Any]) -> dict[str, Any]:
    """
    Inicia una nueva sesión Akinator basada en el cuestionario inicial.
    Devuelve session_id, hipótesis iniciales y primera pregunta.
    """
    _gc_sessions()
    session_id = uuid.uuid4().hex[:16]
    priors = _compute_initial_priors(intake)
    asked: set[tuple[str, int]] = set()

    # Buscar primera pregunta
    next_q = _pick_next_question(priors, asked)
    pregunta_actual = None
    if next_q:
        eid, qidx, pq = next_q
        pregunta_actual = {
            "evento_id": eid,
            "pregunta_idx": qidx,
            "texto": pq["pregunta"],
            "opciones": ["si", "no", "no_se"],
        }
        asked = {(eid, qidx)}

    with _SESSIONS_LOCK:
        _SESSIONS[session_id] = {
            "id": session_id,
            "created": time.time(),
            "last_touch": time.time(),
            "intake": intake,
            "priors": priors,
            "asked": asked,
            "history": [],
            "completed": False,
            "ficha_final": None,
        }

    return {
        "session_id": session_id,
        "hipotesis": _build_hipotesis_view(priors),
        "siguiente_pregunta": pregunta_actual,
        "preguntas_restantes": MAX_QUESTIONS,
        "completed": False,
    }


def answer_question(session_id: str, respuesta: str) -> dict[str, Any]:
    """
    Procesa la respuesta del usuario, actualiza probabilidades y devuelve
    nueva pregunta o ficha clínica final.

    respuesta ∈ {'si', 'no', 'no_se'}
    """
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
        if not session:
            return {"error": "session_not_found", "session_id": session_id}
        if session.get("completed"):
            return {
                "session_id": session_id,
                "completed": True,
                "ficha": session.get("ficha_final"),
            }
        session["last_touch"] = time.time()

    if respuesta not in ("si", "no", "no_se"):
        return {"error": "invalid_answer", "valid": ["si", "no", "no_se"]}

    # La pregunta que vamos a procesar es la última en asked
    if not session["asked"]:
        return {"error": "no_pending_question"}

    # Tomar la última pregunta (la que se hizo más recientemente)
    last_pregunta = sorted(session["asked"])[-1] if session["asked"] else None
    if not last_pregunta:
        return {"error": "no_pending_question"}

    eid, qidx = last_pregunta
    kb = get_kb()
    target_ev = next((e for e in kb["eventos"] if e["id"] == eid), None)
    pregunta_texto = ""
    if target_ev:
        pqs = target_ev.get("preguntas_discriminantes", [])
        if qidx < len(pqs):
            pregunta_texto = pqs[qidx].get("pregunta", "")

    # Update probabilidades
    new_priors = _update_with_answer(session["priors"], qidx, eid, respuesta)
    session["priors"] = new_priors
    session["history"].append({
        "pregunta": pregunta_texto,
        "respuesta": respuesta,
        "evento_id": eid,
        "pregunta_idx": qidx,
    })

    # Chequear si terminamos por confianza alta
    top_id, top_prob = max(new_priors.items(), key=lambda x: x[1])
    questions_asked = len(session["history"])

    if top_prob >= CONFIDENCE_THRESHOLD or questions_asked >= MAX_QUESTIONS:
        ficha = _build_ficha_clinica(top_id, new_priors, session)
        session["completed"] = True
        session["ficha_final"] = ficha
        return {
            "session_id": session_id,
            "completed": True,
            "hipotesis": _build_hipotesis_view(new_priors, top_n=5),
            "ficha": ficha,
            "razon_cierre": "alta_confianza" if top_prob >= CONFIDENCE_THRESHOLD else "max_preguntas",
        }

    # Siguiente pregunta
    next_q = _pick_next_question(new_priors, session["asked"])
    if not next_q:
        # No quedan preguntas — cerrar con la hipótesis top
        ficha = _build_ficha_clinica(top_id, new_priors, session)
        session["completed"] = True
        session["ficha_final"] = ficha
        return {
            "session_id": session_id,
            "completed": True,
            "hipotesis": _build_hipotesis_view(new_priors),
            "ficha": ficha,
            "razon_cierre": "sin_mas_preguntas",
        }

    eid2, qidx2, pq2 = next_q
    session["asked"].add((eid2, qidx2))

    return {
        "session_id": session_id,
        "completed": False,
        "hipotesis": _build_hipotesis_view(new_priors),
        "siguiente_pregunta": {
            "evento_id": eid2,
            "pregunta_idx": qidx2,
            "texto": pq2["pregunta"],
            "opciones": ["si", "no", "no_se"],
        },
        "preguntas_restantes": max(0, MAX_QUESTIONS - questions_asked),
    }


def get_session_state(session_id: str) -> dict[str, Any]:
    """Devuelve estado actual sin avanzar."""
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
        if not session:
            return {"error": "session_not_found"}
        return {
            "session_id": session_id,
            "completed": session["completed"],
            "hipotesis": _build_hipotesis_view(session["priors"]),
            "ficha": session.get("ficha_final"),
            "history": session.get("history", []),
        }
