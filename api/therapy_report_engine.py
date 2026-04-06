from __future__ import annotations

from typing import Any

from api.pair_engine import interpret_pairs
from api.therapy_engine import analyze_case


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


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
