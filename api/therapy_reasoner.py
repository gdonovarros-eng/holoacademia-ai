from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from api.therapy_casewalk_support import build_casewalk_support
from api.therapy_method_support import build_method_support


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_value).strip()


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _safe_text(value)
        key = _normalize_text(text)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _first_non_empty(values: list[str]) -> str:
    for value in values:
        text = _safe_text(value)
        if text:
            return text
    return ""


def _first_sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", _safe_text(value))
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return parts[0].strip().strip('"')


def _to_strings(values: list[Any], limit: int | None = None) -> list[str]:
    texts = _dedupe_keep_order([_safe_text(item) for item in values if _safe_text(item)])
    return texts[:limit] if limit is not None else texts


def _extract_symptom_timeline(case_payload: dict[str, Any]) -> list[str]:
    timeline: list[str] = []
    for item in _safe_list(case_payload.get("current_symptoms"))[:3]:
        if not isinstance(item, dict):
            continue
        symptom_name = _safe_text(item.get("symptom_name"))
        onset = _safe_text(item.get("onset_age_or_date"))
        frequency = _safe_text(item.get("frequency"))
        trigger = _safe_text(item.get("triggering_factors"))
        parts = [part for part in [symptom_name, onset, frequency, trigger] if part]
        if parts:
            timeline.append(" | ".join(parts))
    return timeline


def _infer_case_orientation(case_payload: dict[str, Any], case_analysis: dict[str, Any]) -> str:
    symptoms = _safe_list(case_payload.get("current_symptoms"))
    priority_symptoms = _to_strings(_safe_list(case_analysis.get("priority_symptoms")))
    main_emotion = _safe_text(case_payload.get("main_emotion"))
    session_goal = _normalize_text(_safe_text(case_payload.get("session_goal")))

    if priority_symptoms or symptoms:
        return "fisico_emocional"
    if any(token in session_goal for token in ("emoc", "ansiedad", "duelo", "pareja", "miedo")) or main_emotion:
        return "emocional"
    return "mixto"


def _build_supporting_evidence(
    case_payload: dict[str, Any],
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any] | None,
) -> list[str]:
    evidence: list[str] = []
    symptom_focus = _first_non_empty(_to_strings(_safe_list(case_analysis.get("priority_symptoms"))))
    if symptom_focus:
        evidence.append(f"Sintoma eje reportado: {symptom_focus}.")

    recent_trigger = _safe_text(case_payload.get("recent_trigger"))
    if recent_trigger:
        evidence.append(f"Detonante reciente declarado: {recent_trigger}.")

    main_emotion = _safe_text(case_payload.get("main_emotion"))
    if main_emotion:
        evidence.append(f"Emocion dominante referida: {main_emotion}.")

    family_axes = _to_strings(_safe_list(case_analysis.get("family_axes")), limit=2)
    if family_axes:
        evidence.append("Ejes familiares activos: " + ", ".join(family_axes) + ".")

    genogram_resolution = case_analysis.get("genogram_resolution") if isinstance(case_analysis.get("genogram_resolution"), dict) else {}
    genogram_summary = _safe_text(genogram_resolution.get("summary"))
    if genogram_summary:
        evidence.append("Resolucion del genograma: " + genogram_summary)

    if pair_analysis:
        pair_names = [
            _safe_text(item.get("pair_name"))
            for item in _safe_list(pair_analysis.get("interpreted_pairs"))
            if _safe_text(item.get("pair_name")) and item.get("found")
        ][:2]
        if pair_names:
            evidence.append("Pares con mayor peso clinico en rastreo: " + ", ".join(pair_names) + ".")

    return evidence[:5]


def _build_contradictions(case_payload: dict[str, Any], case_analysis: dict[str, Any]) -> list[str]:
    contradictions: list[str] = []
    priority_symptoms = _to_strings(_safe_list(case_analysis.get("priority_symptoms")))
    probable_conflicts = _to_strings(_safe_list(case_analysis.get("probable_conflicts")))
    current_emotional_context = _safe_text(case_payload.get("current_emotional_context"))
    emotional_context_at_onset = _safe_text(case_payload.get("emotional_context_at_onset"))

    if priority_symptoms and not probable_conflicts:
        contradictions.append("Hay sintoma eje, pero aun no aparece un conflicto emocional suficientemente claro.")

    if current_emotional_context and not emotional_context_at_onset:
        contradictions.append("Se conoce el contexto emocional actual, pero falta el contexto emocional del inicio.")

    if probable_conflicts and not current_emotional_context and not emotional_context_at_onset:
        contradictions.append("Hay hipotesis conflictual, pero falta validarla con relato emocional directo del paciente.")

    return contradictions[:3]


def _build_missing_data(case_payload: dict[str, Any], pair_analysis: dict[str, Any] | None) -> list[str]:
    missing: list[str] = []
    if not _safe_text(case_payload.get("recent_trigger")):
        missing.append("Precisar el detonante mas cercano al inicio del padecimiento.")
    if not _safe_text(case_payload.get("emotional_context_at_onset")):
        missing.append("Explorar que estaba viviendo el paciente exactamente cuando comenzo el cuadro.")
    if not _safe_text(case_payload.get("main_emotion")):
        missing.append("Nombrar la emocion dominante que aparece al recordar el inicio.")
    if pair_analysis is not None and not _safe_list(pair_analysis.get("interpreted_pairs")):
        missing.append("Todavia no hay pares validados para confirmar o descartar la hipotesis.")
    return missing[:4]


def _question_slot(question: str) -> str:
    normalized = _normalize_text(question)
    if any(token in normalized for token in ("origen", "comenzo", "comenzó", "inicio", "detonante", "primer episodio")):
        return "cronologia_y_detonante"
    if any(token in normalized for token in ("duracion", "duración", "frecuencia", "caracter", "derecha", "izquierda", "relacion de este sintoma", "relación de este síntoma")):
        return "caracteristicas_del_sintoma"
    if any(token in normalized for token in ("emocion", "emoción", "conflicto", "se siente", "parte del cuerpo")):
        return "emocion_y_conflicto"
    if any(token in normalized for token in ("linea paterna", "linea materna", "linea", "padre", "madre", "pareja", "transgeneracional", "duelo", "fecha", "doble", "sistema familiar")):
        return "fechas_y_vinculos"
    if any(token in normalized for token in ("que paso en el arbol", "qué pasó en el árbol", "repite", "repetirse")):
        return "fechas_y_vinculos"
    if any(token in normalized for token in ("te hace sentido", "resuena", "parece estar repitiendo")):
        return "verificacion_con_paciente"
    return "otros"


def _rank_interview_questions(
    questions: list[str],
    question_priorities: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    if not questions:
        return [], []

    priority_order = [_safe_text(item.get("slot")) for item in question_priorities if _safe_text(item.get("slot"))]
    if not priority_order:
        return questions[:5], []

    slot_rank = {slot: idx for idx, slot in enumerate(priority_order)}
    ranked = sorted(
        questions,
        key=lambda question: (
            slot_rank.get(_question_slot(question), 99),
            len(question),
            _normalize_text(question),
        ),
    )

    sequence = []
    for item in question_priorities:
        slot = _safe_text(item.get("slot"))
        why = _safe_text(item.get("why"))
        if not slot or not why:
            continue
        sequence.append(why)

    return ranked[:5], sequence[:4]


@dataclass
class CaseSignals:
    symptom_focus: list[str]
    symptom_timeline: list[str]
    recent_trigger: str
    dominant_emotion: str
    probable_systems: list[str]
    probable_conflicts: list[str]
    family_axes: list[str]
    family_date_clues: list[str]
    case_orientation: str
    supporting_evidence: list[str]
    contradictions: list[str]
    missing_data: list[str]


@dataclass
class CaseHypotheses:
    primary_system: str
    secondary_systems: list[str]
    emotional_origin: str
    relational_axis: str
    transgenerational_hypothesis: str
    biomagnetic_hypothesis: str
    sustaining_evidence: list[str]
    contradicting_evidence: list[str]
    to_verify_first: list[str]


@dataclass
class ValidationPlan:
    interview_questions: list[str]
    pair_targets: list[str]
    early_magnet_targets: list[str]
    parallel_interview_slots: list[str]
    magnet_first_rationale: str
    tracking_hints: list[str]
    confirmation_targets: list[str]
    decision_gate: str
    method_moves: list[str]
    question_priority_sequence: list[str]


@dataclass
class InterventionDecision:
    opening_route: str
    initial_method: str
    followup_method: str
    wait_before_protocol: str
    validation_sequence: list[str]
    primary_protocol_title: str
    liberation_focus: str
    defer_for_later: list[str]
    rationale: str
    casewalk_lessons: list[str]


def build_therapy_reasoning(
    case_payload: dict[str, Any],
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any] | None = None,
    primary_protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    probable_systems = _to_strings(_safe_list(case_analysis.get("probable_systems")), limit=3)
    probable_conflicts = _to_strings(_safe_list(case_analysis.get("probable_conflicts")), limit=3)
    family_axes = _to_strings(_safe_list(case_analysis.get("family_axes")), limit=3)
    family_date_clues = [
        _first_sentence(_safe_text(item.get("summary")))
        for item in _safe_list(case_analysis.get("family_date_guidance"))
        if isinstance(item, dict) and _first_sentence(_safe_text(item.get("summary")))
    ][:3]
    case_orientation = _infer_case_orientation(case_payload, case_analysis)
    casewalk_support = build_casewalk_support(
        case_analysis=case_analysis,
        pair_analysis=pair_analysis,
        primary_protocol=primary_protocol,
        case_orientation=case_orientation,
    )
    practice_moves = casewalk_support.get("practice_moves", {}) if isinstance(casewalk_support, dict) else {}
    question_priorities = casewalk_support.get("question_priorities", []) if isinstance(casewalk_support, dict) else []

    supporting_evidence = _build_supporting_evidence(case_payload, case_analysis, pair_analysis)
    contradictions = _build_contradictions(case_payload, case_analysis)
    missing_data = _build_missing_data(case_payload, pair_analysis)
    genogram_resolution = case_analysis.get("genogram_resolution") if isinstance(case_analysis.get("genogram_resolution"), dict) else {}

    signals = CaseSignals(
        symptom_focus=_to_strings(_safe_list(case_analysis.get("priority_symptoms")), limit=3),
        symptom_timeline=_extract_symptom_timeline(case_payload),
        recent_trigger=_safe_text(case_payload.get("recent_trigger")),
        dominant_emotion=_safe_text(case_payload.get("main_emotion")),
        probable_systems=probable_systems,
        probable_conflicts=probable_conflicts,
        family_axes=family_axes,
        family_date_clues=family_date_clues,
        case_orientation=case_orientation,
        supporting_evidence=supporting_evidence,
        contradictions=contradictions,
        missing_data=missing_data,
    )

    interpreted_pairs = _safe_list(pair_analysis.get("interpreted_pairs")) if pair_analysis else []
    pair_targets = [
        _safe_text(item.get("pair_name"))
        for item in interpreted_pairs
        if _safe_text(item.get("pair_name"))
    ][:4]
    if not pair_targets:
        pair_targets = [
            _safe_text(item.get("pair_name"))
            for item in _safe_list(case_analysis.get("suggested_pairs_to_validate"))
            if _safe_text(item.get("pair_name"))
        ][:4]

    tracking_hints = _dedupe_keep_order(
        [
            _safe_text(hint)
            for card in _safe_list(case_analysis.get("organ_sweep_summary"))
            if isinstance(card, dict)
            for hint in _safe_list(card.get("pair_focus"))
        ]
    )[:4]

    primary_system = _first_non_empty(probable_systems)
    relational_axis = (
        _safe_text(genogram_resolution.get("summary"))
        or _safe_text(genogram_resolution.get("repair_target"))
        or _first_non_empty(family_axes)
    )
    emotional_origin = (
        " / ".join(probable_conflicts[:2])
        if probable_conflicts
        else "Aun no hay un origen emocional suficientemente delimitado."
    )
    transgenerational_hypothesis = (
        _first_non_empty([axis for axis in family_axes if "transgener" in _normalize_text(axis)])
        or "No aparece una hipotesis transgeneracional dominante todavia."
    )

    biomagnetic_hypothesis = (
        "Conviene usar el rastreo biomagnetico para confirmar si el sistema dominante se sostiene con pares reales."
        if pair_targets
        else "Antes de abrir intervencion biomagnetica, falta validar si el caso requiere pares o solo entrevista profunda."
    )

    hypotheses = CaseHypotheses(
        primary_system=primary_system,
        secondary_systems=probable_systems[1:3],
        emotional_origin=emotional_origin,
        relational_axis=relational_axis,
        transgenerational_hypothesis=transgenerational_hypothesis,
        biomagnetic_hypothesis=biomagnetic_hypothesis,
        sustaining_evidence=supporting_evidence[:4],
        contradicting_evidence=contradictions,
        to_verify_first=missing_data[:3]
        or _to_strings(_safe_list(case_analysis.get("guiding_questions")), limit=3),
    )

    pair_related_conditions = _to_strings(_safe_list(pair_analysis.get("related_conditions")) if pair_analysis else [], limit=3)
    base_interview_questions = _dedupe_keep_order(
        _to_strings(_safe_list(case_analysis.get("guiding_questions")), limit=4)
        + _to_strings(_safe_list(practice_moves.get("intake_examples")), limit=2)
    )[:6]
    interview_questions, question_priority_sequence = _rank_interview_questions(
        base_interview_questions,
        question_priorities if isinstance(question_priorities, list) else [],
    )
    confirmation_targets = _dedupe_keep_order(
        [
            f"Confirmar si {emotional_origin} coincide con el inicio real del padecimiento."
            if probable_conflicts
            else "",
            f"Validar si {primary_system} sigue siendo la puerta clinica dominante."
            if primary_system
            else "",
            *[f"Confirmar en rastreo: {name}." for name in pair_targets[:2]],
            *[f"Explorar clinicamente: {item}." for item in pair_related_conditions[:2]],
        ]
    )[:5]
    decision_gate = (
        "No cerrar intervencion hasta que la entrevista y el rastreo apunten a la misma linea dominante."
    )
    early_magnet_targets = pair_targets[:4]
    parallel_interview_slots = _dedupe_keep_order(
        [
            "cronologia_y_detonante",
            "caracteristicas_del_sintoma",
            "emocion_y_conflicto",
            "fechas_y_vinculos",
        ]
    )
    magnet_first_rationale = (
        "Conviene empezar con imanes y sostener entrevista en paralelo para ahorrar tiempo clínico sin cerrar todavía la hipótesis."
        if case_analysis.get("route_recommendation", {}).get("dominant_route") in {"bioenergetica", "mixta"} or pair_targets
        else "En este caso primero conviene aclarar mejor la entrevista antes de sostener rastreo prolongado."
    )
    validation_plan = ValidationPlan(
        interview_questions=interview_questions,
        pair_targets=pair_targets,
        early_magnet_targets=early_magnet_targets,
        parallel_interview_slots=parallel_interview_slots,
        magnet_first_rationale=magnet_first_rationale,
        tracking_hints=tracking_hints,
        confirmation_targets=confirmation_targets,
        decision_gate=decision_gate,
        method_moves=_to_strings(_safe_list(practice_moves.get("validation_moves")), limit=4),
        question_priority_sequence=question_priority_sequence,
    )

    protocol_title = _safe_text(primary_protocol.get("title")) if primary_protocol else ""
    if case_analysis.get("route_recommendation", {}).get("dominant_route") == "bioenergetica":
        opening_route = "imanes_primero_y_entrevista_en_paralelo"
    elif case_orientation == "emocional":
        opening_route = "entrevista_emocional_y_liberacion"
    elif pair_targets:
        opening_route = "entrevista_y_validacion_biomagnetica"
    else:
        opening_route = "entrevista_clinica_y_definicion_de_rastreo"

    validation_sequence = _dedupe_keep_order(
        [
            "Precisar sintoma eje, cronologia y detonante.",
            "Nombrar la emocion dominante y verificar si coincide con el inicio.",
            "Cruzar la hipotesis con ejes familiares o relacionales activos." if family_axes else "",
            "Validar pares dominantes en rastreo." if pair_targets else "",
            "Elegir protocolo solo despues de confirmar la misma linea clinica.",
            *_to_strings(_safe_list(practice_moves.get("validation_moves")), limit=2),
        ]
    )
    liberation_focus = _first_non_empty(
        [
            emotional_origin if probable_conflicts else "",
            relational_axis,
            primary_system,
        ]
    )
    defer_for_later = _dedupe_keep_order(
        [
            "Protocolos alternativos no congruentes con el sistema dominante.",
            "Lecturas transgeneracionales mas profundas" if family_axes and not _normalize_text(transgenerational_hypothesis).startswith("no aparece") else "",
            "Intervenciones microbiologicas secundarias" if case_orientation == "emocional" else "",
        ]
    )[:3]
    rationale = (
        f"Se prioriza {primary_system or 'la linea dominante del caso'} porque es donde hoy coinciden sintoma, conflicto y plan de validacion."
    )
    casewalk_lessons = _to_strings(_safe_list(practice_moves.get("intervention_moves")), limit=4)
    if casewalk_lessons:
        rationale = (
            rationale
            + " "
            + "Los casos guía muestran que conviene sostener el mismo hilo clínico hasta la liberación."
        )
    intervention_decision = InterventionDecision(
        opening_route=opening_route,
        initial_method=(
            "Empieza con imanes y con el barrido del sistema/órgano dominante."
            if opening_route == "imanes_primero_y_entrevista_en_paralelo"
            else "Empieza por entrevista y definición del conflicto dominante."
        ),
        followup_method="Mientras avanza la sesión, mantén entrevista objetiva, valida pares reales y solo después decide protocolo.",
        wait_before_protocol="No cierres protocolo todavía; primero confirma que entrevista, rastreo y respuesta clínica sostienen la misma línea.",
        validation_sequence=validation_sequence,
        primary_protocol_title=protocol_title,
        liberation_focus=liberation_focus,
        defer_for_later=defer_for_later,
        rationale=rationale,
        casewalk_lessons=casewalk_lessons,
    )

    return {
        "schema_version": "therapy_reasoner_v1",
        "case_signals": asdict(signals),
        "case_hypotheses": asdict(hypotheses),
        "validation_plan": asdict(validation_plan),
        "intervention_decision": asdict(intervention_decision),
        "method_support": build_method_support(
            case_analysis=case_analysis,
            pair_analysis=pair_analysis,
            primary_protocol=primary_protocol,
            case_orientation=case_orientation,
        ),
        "casewalk_support": casewalk_support,
    }


__all__ = ["build_therapy_reasoning"]
