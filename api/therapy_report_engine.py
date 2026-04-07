from __future__ import annotations

import re
from typing import Any

from api.pair_engine import interpret_pairs
from api.therapy_engine import analyze_case


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_non_empty(values: list[str]) -> str:
    for value in values:
        text = _safe_text(value)
        if text:
            return text
    return ""


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def _first_sentence(text: str) -> str:
    clean = re.sub(r"\s+", " ", _safe_text(text))
    if not clean:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", clean)
    return parts[0].strip()


def _protocol_steps(protocol_body: str) -> list[str]:
    body = _safe_text(protocol_body)
    if not body:
        return []

    normalized = body.replace("●", "\n●").replace("•", "\n•")
    lines = [re.sub(r"\s+", " ", line).strip(" .") for line in normalized.splitlines()]
    steps = [line.lstrip("●•- ").strip() for line in lines if line.strip().startswith(("●", "•", "-"))]
    if steps:
        return _dedupe_keep_order(steps)

    fragments = [fragment.strip() for fragment in re.split(r"\.\s+", body) if fragment.strip()]
    return _dedupe_keep_order(fragments[:6])


def _select_primary_protocol(
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any],
) -> dict[str, Any] | None:
    protocols = _safe_list(pair_analysis.get("suggested_protocols"))
    if not protocols:
        return None

    family_axes_blob = " ".join(_safe_list(case_analysis.get("family_axes"))).lower()
    conflict_blob = " ".join(_safe_list(case_analysis.get("probable_conflicts"))).lower()
    related_blob = " ".join(_safe_list(pair_analysis.get("related_conditions"))).lower()

    if "transgeneracional" in family_axes_blob:
        for protocol in protocols:
            if "transgeneracional" in _safe_text(protocol.get("title")).lower():
                return protocol

    trauma_terms = ("trauma", "postraumatico", "estrés postraumático", "tept")
    if any(term in conflict_blob or term in related_blob for term in trauma_terms):
        for protocol in protocols:
            title = _safe_text(protocol.get("title")).lower()
            if "postraum" in title or "emocion" in title:
                return protocol

    sentimental_terms = ("pareja", "abandono", "rechazo", "humillacion", "traicion", "vínculos")
    if any(term in family_axes_blob or term in conflict_blob for term in sentimental_terms):
        for protocol in protocols:
            title = _safe_text(protocol.get("title")).lower()
            if any(token in title for token in ("sentimental", "conexiones", "cordones", "cuerdas")):
                return protocol

    for protocol in protocols:
        title = _safe_text(protocol.get("title")).lower()
        if "sistemic" in title:
            return protocol

    return protocols[0]


def _build_liberation_plan(
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any],
    primary_protocol: dict[str, Any] | None,
) -> dict[str, Any]:
    protocol_title = _safe_text(primary_protocol.get("title")) if primary_protocol else ""
    protocol_body = _safe_text(primary_protocol.get("body")) if primary_protocol else ""
    protocol_steps = _protocol_steps(protocol_body)

    focus_issue = _first_non_empty(
        _safe_list(case_analysis.get("priority_symptoms"))
        + _safe_list(pair_analysis.get("related_conditions"))
        + _safe_list(case_analysis.get("probable_conflicts"))
    )
    emotional_axis = _first_non_empty(_safe_list(case_analysis.get("probable_conflicts")))
    family_axis = _first_non_empty(_safe_list(case_analysis.get("family_axes")))

    intention_parts = []
    if focus_issue:
        intention_parts.append(f"trabajar {focus_issue}")
    if emotional_axis:
        intention_parts.append(f"liberar la carga asociada a {emotional_axis}")
    if family_axis:
        intention_parts.append(f"manteniendo presente el eje {family_axis}")

    patient_explanation = " ".join(
        part for part in [
            "El objetivo de esta liberación es ayudar al paciente a soltar la carga emocional que el cuerpo sigue sosteniendo.",
            f"En este caso conviene {', '.join(intention_parts)}." if intention_parts else "",
            f"El protocolo sugerido para empezar es {protocol_title}." if protocol_title else "",
        ] if part
    ).strip()

    home_recommendations = [
        "Aplicar el protocolo con presencia, sin forzar respuestas y verificando cada liberación antes de continuar.",
        "Si una emoción o sensación cambia de intensidad, ajustar el lenguaje del trabajo a lo que el paciente siente en ese momento.",
        "Si el caso sigue cargado, repetir el protocolo en días posteriores solo si el rastreo lo confirma.",
    ]

    return {
        "protocol_title": protocol_title,
        "protocol_source_file": _safe_text(primary_protocol.get("source_file")) if primary_protocol else "",
        "route": _safe_text(primary_protocol.get("route")) if primary_protocol else "",
        "therapeutic_intention": patient_explanation,
        "focus_issue": focus_issue,
        "emotional_axis": emotional_axis,
        "family_axis": family_axis,
        "therapist_steps": protocol_steps,
        "patient_explanation": patient_explanation,
        "home_recommendations": home_recommendations,
    }


EFT_TAPPING_POINTS = [
    "Punto karate: lateral de la mano entre meñique y muñeca.",
    "Coronilla.",
    "Inicio de la ceja.",
    "Lado del ojo.",
    "Debajo del ojo.",
    "Entre nariz y labio superior.",
    "Debajo del labio, en la barbilla.",
    "Clavícula.",
    "Debajo de la axila.",
]


def _build_eft_script(
    case_payload: dict[str, Any],
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any],
    liberation_plan: dict[str, Any],
) -> dict[str, Any]:
    patient_name = _safe_text(case_payload.get("patient_name")) or _safe_text(
        case_payload.get("consultant", {}).get("full_name") if isinstance(case_payload.get("consultant"), dict) else ""
    )
    focus_issue = _first_non_empty(
        [
            _safe_text(liberation_plan.get("focus_issue")),
            *_safe_list(case_analysis.get("priority_symptoms")),
            *_safe_list(pair_analysis.get("related_conditions")),
        ]
    )
    emotional_axis = _first_non_empty(
        [
            _safe_text(liberation_plan.get("emotional_axis")),
            *_safe_list(case_analysis.get("probable_conflicts")),
        ]
    )
    reference_causes = _safe_list(case_analysis.get("reference_emotional_causes"))
    reference_line = ""
    if reference_causes and isinstance(reference_causes[0], dict):
        reference_line = _first_sentence(_safe_text(reference_causes[0].get("body")))

    route = _safe_text(liberation_plan.get("route")).lower()
    if "transgeneracional" in route:
        route_phrase = "esta carga repetida de mi sistema familiar"
    elif "sentimental" in route:
        route_phrase = "este dolor vincular que sigo cargando"
    elif "postraum" in route or "estres" in route:
        route_phrase = "el impacto que esta situación dejó en mí"
    else:
        route_phrase = "este conflicto que mi cuerpo sigue sosteniendo"

    setup_phrase = (
        f"Aunque sigo cargando {route_phrase}"
        + (f" y esto se expresa como {focus_issue}" if focus_issue else "")
        + (f", especialmente en relación con {emotional_axis}" if emotional_axis else "")
        + ", me abro a reconocerlo, liberarlo y darme permiso de estar en paz."
    )

    reminder_base = _first_non_empty(
        [
            focus_issue,
            emotional_axis,
            "esta carga emocional",
        ]
    )
    reminder_phrases = _dedupe_keep_order(
        [
            f"Este {reminder_base}",
            f"Lo que mi cuerpo sigue sosteniendo de {reminder_base}" if reminder_base else "",
            f"Me permito reconocer {emotional_axis}" if emotional_axis else "",
            "Me abro a soltar esta tensión paso a paso.",
            "Puedo bajar la intensidad sin perder conciencia de lo que siento.",
            "Le doy espacio a una respuesta más tranquila y clara.",
        ]
    )

    rounds = [
        {
            "title": "Ronda 1: reconocer lo que está cargado",
            "focus": f"Nombrar el problema tal como hoy se siente{f' en {patient_name}' if patient_name else ''}.",
            "phrase": reminder_phrases[0] if reminder_phrases else "Este malestar.",
        },
        {
            "title": "Ronda 2: contactar la emoción dominante",
            "focus": emotional_axis or "explorar la emoción principal detrás del síntoma.",
            "phrase": reminder_phrases[2] if len(reminder_phrases) > 2 else "Me permito sentirlo sin pelear con ello.",
        },
        {
            "title": "Ronda 3: abrir espacio a la liberación",
            "focus": "invitar al sistema a bajar intensidad y recuperar seguridad interna.",
            "phrase": reminder_phrases[-1] if reminder_phrases else "Me doy permiso de estar en paz.",
        },
    ]

    usage_notes = [
        "Antes de empezar, pedir al paciente que ponga intensidad de 0 a 10 al malestar que se va a trabajar.",
        "Hacer una ronda completa con la frase de preparación en punto karate y luego recorrer los puntos básicos con la frase recordatoria.",
        "Después de cada ronda, volver a medir intensidad y ajustar la frase si el síntoma o la emoción cambian.",
    ]
    if reference_line:
        usage_notes.append(f"Referencia útil para la entrevista: {reference_line}")

    return {
        "title": "Guion EFT sugerido para el paciente",
        "focus_issue": focus_issue,
        "emotional_axis": emotional_axis,
        "setup_phrase": setup_phrase,
        "reminder_phrases": reminder_phrases,
        "tapping_points": EFT_TAPPING_POINTS,
        "rounds": rounds,
        "usage_notes": usage_notes,
    }


def _build_integrative_chart(
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for system_name in _safe_list(case_analysis.get("probable_systems"))[:5]:
        rows.append(
            {
                "dimension": "Sistema probable",
                "value": system_name,
                "meaning": "Sistema que conviene revisar primero durante el rastreo y la integración terapéutica.",
            }
        )

    for conflict in _safe_list(case_analysis.get("probable_conflicts"))[:5]:
        rows.append(
            {
                "dimension": "Conflicto probable",
                "value": conflict,
                "meaning": "Tema emocional o vivencial que podría estar sosteniendo parte de la carga del caso.",
            }
        )

    for pair in _safe_list(pair_analysis.get("interpreted_pairs"))[:6]:
        if not pair.get("found"):
            meaning = "Par aún no reconocido en el catálogo; conviene validarlo manualmente."
        else:
            pair_type = _safe_text(pair.get("pair_type")) or "tipo no especificado"
            related_condition = _safe_text(pair.get("related_condition")) or "sin condición explícita"
            meaning = f"{pair_type}. Relacionado con {related_condition}."
        rows.append(
            {
                "dimension": "Par biomagnético",
                "value": _safe_text(pair.get("pair_name")),
                "meaning": meaning,
            }
        )

    return rows


def _build_pair_visual_summary(pair_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for pair in _safe_list(pair_analysis.get("interpreted_pairs")):
        visual = pair.get("visual") if isinstance(pair.get("visual"), dict) else {}
        point_a = visual.get("point_a") if isinstance(visual.get("point_a"), dict) else {}
        point_b = visual.get("point_b") if isinstance(visual.get("point_b"), dict) else {}
        summaries.append(
            {
                "pair_name": _safe_text(pair.get("pair_name")),
                "found": bool(pair.get("found")),
                "pair_type": _safe_text(pair.get("pair_type")),
                "related_condition": _safe_text(pair.get("related_condition")),
                "point_a_label": _safe_text(point_a.get("label")),
                "point_a_region": _safe_text(point_a.get("region_hint")),
                "point_b_label": _safe_text(point_b.get("label")),
                "point_b_region": _safe_text(point_b.get("region_hint")),
                "image_candidates": _safe_list(visual.get("image_candidates")),
                "has_reference_images": bool(visual.get("has_reference_images")),
                "visual_status": _safe_text(visual.get("status")),
                "visual_source_mode": _safe_text(visual.get("source_mode")),
            }
        )
    return summaries


def _build_patient_delivery(
    case_payload: dict[str, Any],
    case_analysis: dict[str, Any],
    pair_analysis: dict[str, Any],
    primary_protocol: dict[str, Any] | None,
) -> dict[str, Any]:
    patient_name = _safe_text(case_payload.get("patient_name")) or "el paciente"
    focus_points = _dedupe_keep_order(
        _safe_list(case_analysis.get("probable_systems"))[:3]
        + _safe_list(case_analysis.get("probable_conflicts"))[:3]
    )
    pair_focus = _dedupe_keep_order(_safe_list(pair_analysis.get("related_conditions"))[:3])

    summary_parts = [f"La sesión de {patient_name} apunta a trabajar"]
    if focus_points:
        summary_parts.append(", ".join(focus_points))
    else:
        summary_parts.append("los ejes principales detectados en entrevista")
    if pair_focus:
        summary_parts.append(f"y a profundizar en {', '.join(pair_focus)}")

    summary = " ".join(summary_parts).strip() + "."

    delivery = {
        "patient_summary": summary,
        "therapeutic_focus": focus_points,
        "pair_focus": pair_focus,
        "recommended_protocol_name": _safe_text(primary_protocol.get("title")) if primary_protocol else "",
        "recommended_protocol_body": _safe_text(primary_protocol.get("body")) if primary_protocol else "",
    }
    return delivery


def build_therapy_report(
    case_payload: dict[str, Any],
    pairs_input: list[Any] | None = None,
) -> dict[str, Any]:
    case_analysis = analyze_case(case_payload)
    pair_analysis = interpret_pairs(case_analysis, pairs_input or [])
    primary_protocol = _select_primary_protocol(case_analysis, pair_analysis)
    liberation_plan = _build_liberation_plan(case_analysis, pair_analysis, primary_protocol)
    eft_script = _build_eft_script(case_payload, case_analysis, pair_analysis, liberation_plan)
    integrative_chart = _build_integrative_chart(case_analysis, pair_analysis)

    therapist_summary_parts = [
        case_analysis.get("reading", ""),
        case_analysis.get("mass_conflict_hypothesis", ""),
        pair_analysis.get("integrated_reading", ""),
    ]
    therapist_summary = " ".join(part for part in therapist_summary_parts if part).strip()

    next_steps = []
    if _safe_list(case_analysis.get("guiding_questions")):
        next_steps.append("Profundizar con las preguntas guía antes de cerrar la lectura del caso.")
    if _safe_list(pair_analysis.get("interpreted_pairs")):
        next_steps.append("Validar cuáles pares se repiten o sostienen el patrón dominante del caso.")
    if primary_protocol:
        next_steps.append(
            f"Preparar la aplicación del protocolo sugerido: {primary_protocol['title']}."
        )

    report = {
        "case_analysis": case_analysis,
        "pair_analysis": pair_analysis,
        "therapist_summary": therapist_summary,
        "integrative_chart": integrative_chart,
        "pair_visual_summary": _build_pair_visual_summary(pair_analysis),
        "primary_protocol": primary_protocol,
        "liberation_plan": liberation_plan,
        "eft_script": eft_script,
        "next_steps": next_steps,
        "patient_delivery": _build_patient_delivery(
            case_payload=case_payload,
            case_analysis=case_analysis,
            pair_analysis=pair_analysis,
            primary_protocol=primary_protocol,
        ),
    }
    return report


__all__ = ["build_therapy_report"]
