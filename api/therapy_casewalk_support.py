from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
THERAPY_CASEWALKS_PATH = ROOT / "data" / "therapy_casewalks.json"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_sentence(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", _safe_text(value))
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return parts[0].strip()


@lru_cache
def get_therapy_casewalks() -> dict[str, Any]:
    if not THERAPY_CASEWALKS_PATH.exists():
        return {"casewalk_count": 0, "casewalks": [], "courses": []}
    return json.loads(THERAPY_CASEWALKS_PATH.read_text(encoding="utf-8"))


def _collect_relevant_course_ids(case_analysis: dict[str, Any]) -> list[str]:
    course_ids: list[str] = []
    for item in _safe_list(case_analysis.get("therapy_transcript_routes"))[:4]:
        if isinstance(item, dict) and _safe_text(item.get("course_id")):
            course_ids.append(_safe_text(item.get("course_id")))
    for item in _safe_list(case_analysis.get("therapy_manual_routes"))[:4]:
        if isinstance(item, dict) and _safe_text(item.get("course_id")):
            course_ids.append(_safe_text(item.get("course_id")))
    return list(dict.fromkeys(course_ids))


def _desired_stages(
    *,
    pair_analysis: dict[str, Any] | None,
    primary_protocol: dict[str, Any] | None,
    case_orientation: str,
) -> list[str]:
    stages = ["intake", "systemic_analysis", "conflict_synthesis"]
    if case_orientation in {"fisico_emocional", "mixto"} or pair_analysis is not None:
        stages.append("intervention")
    if primary_protocol is not None:
        stages.append("tasks_and_closure")
    return stages


def _example_score(
    item: dict[str, Any],
    *,
    relevant_course_ids: list[str],
    desired_stages: list[str],
) -> float:
    score = float(item.get("score", 0))
    stages = set(_safe_list(item.get("stages")))
    snippet = _normalize_text(_safe_text(item.get("snippet")))

    if _safe_text(item.get("course_id")) in relevant_course_ids:
        score += 8.0
    score += len(stages & set(desired_stages)) * 4.0

    if "conflict_synthesis" in stages:
        score += 3.0
    if "intervention" in stages:
        score += 3.0
    if "tasks_and_closure" in stages:
        score += 2.0

    if "setup" in stages and "tasks_and_closure" not in stages:
        score -= 4.0

    theory_tokens = (
        "voy a comenzar con teoria",
        "a lo largo de los ultimos cuatro cursos",
        "chakras",
        "meridianos",
        "teoria astrologica",
        "nodo norte",
        "nodo sur",
    )
    score -= sum(2.5 for token in theory_tokens if token in snippet)

    return score


def _build_practice_moves(examples: list[dict[str, Any]]) -> dict[str, list[str]]:
    joined_by_stage: dict[str, str] = {}
    for stage_id in ("intake", "systemic_analysis", "conflict_synthesis", "intervention", "tasks_and_closure"):
        parts: list[str] = []
        for item in examples:
            for stage in _safe_list(item.get("stage_snippets")):
                if _safe_text(stage.get("stage_id")) == stage_id and _safe_text(stage.get("snippet")):
                    parts.append(_safe_text(stage.get("snippet")))
        joined_by_stage[stage_id] = _normalize_text(" ".join(parts))

    validation_moves: list[str] = []
    intervention_moves: list[str] = []

    intake_blob = joined_by_stage["intake"]
    analysis_blob = joined_by_stage["systemic_analysis"]
    synthesis_blob = joined_by_stage["conflict_synthesis"]
    intervention_blob = joined_by_stage["intervention"]
    closure_blob = joined_by_stage["tasks_and_closure"]

    if any(token in intake_blob for token in ("nombre", "fecha", "pap", "mam", "pareja", "hijo", "hija")):
        validation_moves.append("Cruzar nombres, fechas y vínculos significativos antes de cerrar una hipótesis.")
    if "te hace sentido" in intake_blob or any("?" in _safe_text(item.get("snippet")) for item in examples):
        validation_moves.append("Devolver la hipótesis al paciente y verificar si realmente le resuena antes de seguir.")
    if any(token in analysis_blob for token in ("doble", "proyecto sentido", "repet", "fecha")):
        validation_moves.append("Cruzar repeticiones, dobles y fechas familiares para ver si sostienen la misma línea del caso.")
    if synthesis_blob:
        validation_moves.append("Reducir el caso a una frase de conflicto dominante antes de pasar a la intervención.")

    if any(token in intervention_blob for token in ("eft", "golpec", "respir", "ojos")):
        intervention_moves.append("Si la emoción ya está abierta, conviene descargarla con una intervención breve y verificable.")
    if any(token in intervention_blob for token in ("carta", "romper el pacto", "acto", "rito", "sepelio")):
        intervention_moves.append("Si aparece una deuda simbólica, abrir un acto o carta solo después de validar el conflicto central.")
    if closure_blob:
        intervention_moves.append("Cerrar con tareas concretas y observación posterior, no con más interpretación.")
    if synthesis_blob and intervention_blob:
        intervention_moves.append("Elegir protocolo o liberación solo cuando entrevista, síntesis e intervención apunten a la misma línea.")

    return {
        "validation_moves": list(dict.fromkeys(validation_moves))[:4],
        "intervention_moves": list(dict.fromkeys(intervention_moves))[:4],
        "intake_examples": [
            _first_sentence(_safe_text(stage.get("snippet")))
            for item in examples
            for stage in _safe_list(item.get("stage_snippets"))
            if _safe_text(stage.get("stage_id")) == "intake" and _first_sentence(_safe_text(stage.get("snippet")))
        ][:2],
    }


def _build_question_priorities(
    examples: list[dict[str, Any]],
    *,
    case_orientation: str,
) -> list[dict[str, str]]:
    joined_by_stage: dict[str, str] = {}
    for stage_id in ("intake", "systemic_analysis", "conflict_synthesis"):
        parts: list[str] = []
        for item in examples:
            for stage in _safe_list(item.get("stage_snippets")):
                if _safe_text(stage.get("stage_id")) == stage_id and _safe_text(stage.get("snippet")):
                    parts.append(_safe_text(stage.get("snippet")))
        joined_by_stage[stage_id] = _normalize_text(" ".join(parts))

    intake_blob = joined_by_stage["intake"]
    analysis_blob = joined_by_stage["systemic_analysis"]
    synthesis_blob = joined_by_stage["conflict_synthesis"]

    priorities: list[dict[str, str]] = [
        {
            "slot": "cronologia_y_detonante",
            "why": "Los casos guía arrancan ubicando inicio, detonante y primer episodio antes de interpretar.",
        },
        {
            "slot": "emocion_y_conflicto",
            "why": "Después conviene nombrar la emoción dominante y llevarla hacia el conflicto central.",
        },
    ]

    if any(token in intake_blob for token in ("frecuencia", "caracteristica", "derecha", "izquierda", "dolor")):
        priorities.insert(
            1,
            {
                "slot": "caracteristicas_del_sintoma",
                "why": "En los casos parecidos primero se precisan frecuencia, características y factores que cambian el síntoma.",
            },
        )

    if any(token in analysis_blob for token in ("nombre", "fecha", "padre", "madre", "pareja", "hijo", "doble")):
        priorities.append(
            {
                "slot": "fechas_y_vinculos",
                "why": "Los ejemplos muestran que nombres, dobles y fechas familiares ayudan a confirmar la hipótesis.",
            }
        )

    if any(token in synthesis_blob for token in ("te hace sentido", "resuena", "drama", "verdadero motivo")):
        priorities.append(
            {
                "slot": "verificacion_con_paciente",
                "why": "Antes de avanzar, el terapeuta devuelve la lectura para ver si realmente le hace sentido al paciente.",
            }
        )

    if case_orientation == "emocional":
        priorities = [
            item for item in priorities if item["slot"] != "caracteristicas_del_sintoma"
        ]

    seen: set[str] = set()
    cleaned: list[dict[str, str]] = []
    for item in priorities:
        slot = _safe_text(item.get("slot"))
        if not slot or slot in seen:
            continue
        seen.add(slot)
        cleaned.append(item)
    return cleaned[:5]


def build_casewalk_support(
    *,
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any] | None = None,
    primary_protocol: dict[str, Any] | None = None,
    case_orientation: str = "",
) -> dict[str, Any]:
    payload = get_therapy_casewalks()
    relevant_course_ids = _collect_relevant_course_ids(case_analysis)
    desired = _desired_stages(
        pair_analysis=pair_analysis,
        primary_protocol=primary_protocol,
        case_orientation=case_orientation,
    )

    examples = _safe_list(payload.get("casewalks"))
    ranked = sorted(
        examples,
        key=lambda item: (
            -_example_score(item, relevant_course_ids=relevant_course_ids, desired_stages=desired),
            _safe_text(item.get("course_name")),
            _safe_text(item.get("casewalk_id")),
        ),
    )

    selected: list[dict[str, Any]] = []
    seen_courses: set[str] = set()
    for item in ranked:
        course_id = _safe_text(item.get("course_id"))
        if course_id in seen_courses and len(selected) < 2:
            continue
        seen_courses.add(course_id)
        stage_snippets = [
            stage
            for stage in _safe_list(item.get("stage_snippets"))
            if _safe_text(stage.get("stage_id")) in desired
        ]
        if not stage_snippets:
            stage_snippets = _safe_list(item.get("stage_snippets"))[:4]

        selected.append(
            {
                "casewalk_id": _safe_text(item.get("casewalk_id")),
                "course_id": course_id,
                "course_name": _safe_text(item.get("course_name")),
                "track": _safe_text(item.get("track")),
                "score": int(item.get("score", 0)),
                "learning_value": _safe_text(item.get("learning_value")),
                "stages": _safe_list(item.get("stages")),
                "stage_snippets": [
                    {
                        "stage_id": _safe_text(stage.get("stage_id")),
                        "label": _safe_text(stage.get("label")),
                        "snippet": _safe_text(stage.get("snippet")),
                    }
                    for stage in stage_snippets[:4]
                ],
                "snippet": _safe_text(item.get("snippet")),
            }
        )
        if len(selected) >= 2:
            break

    return {
        "relevant_course_ids": relevant_course_ids,
        "desired_stages": desired,
        "examples": selected,
        "practice_moves": _build_practice_moves(selected),
        "question_priorities": _build_question_priorities(selected, case_orientation=case_orientation),
    }


__all__ = ["build_casewalk_support", "get_therapy_casewalks"]
