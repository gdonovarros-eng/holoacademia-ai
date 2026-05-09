from __future__ import annotations

from typing import Any, Dict, List, Set

from .models import CaseAnalysis, CaseInput


def _clean_list(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        item = str(value).strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            ordered.append(item)
    return ordered


def _build_case_summary(case_input: CaseInput) -> str:
    fragments: List[str] = []
    if case_input.motivo_consulta:
        fragments.append(f"Motivo de consulta: {case_input.motivo_consulta}.")
    if case_input.sintomas:
        fragments.append(f"Síntomas referidos: {', '.join(case_input.sintomas)}.")
    timeline_parts = [part for part in [case_input.inicio, case_input.duracion, case_input.frecuencia] if part]
    if timeline_parts:
        fragments.append(f"Datos de evolución: {' | '.join(timeline_parts)}.")
    if case_input.contexto_emocional:
        fragments.append(f"Contexto emocional referido: {case_input.contexto_emocional}.")
    if case_input.antecedentes:
        fragments.append(f"Antecedentes relevantes: {', '.join(case_input.antecedentes)}.")
    if case_input.observaciones:
        fragments.append(f"Observaciones adicionales: {case_input.observaciones}.")
    if case_input.pregunta_del_terapeuta:
        fragments.append(f"Pregunta del terapeuta: {case_input.pregunta_del_terapeuta}.")
    return " ".join(fragments).strip()


def build_case_analysis(case_input: Any) -> Dict[str, Any]:
    normalized_case = case_input if isinstance(case_input, CaseInput) else CaseInput.from_dict(case_input)
    symptoms_detected = _clean_list(normalized_case.sintomas)
    timeline_elements = _clean_list([normalized_case.inicio, normalized_case.duracion, normalized_case.frecuencia])
    context_elements = _clean_list(normalized_case.antecedentes + [normalized_case.contexto_emocional, normalized_case.observaciones])

    key_elements = _clean_list(
        [normalized_case.motivo_consulta]
        + symptoms_detected
        + timeline_elements
        + [normalized_case.contexto_emocional]
        + normalized_case.antecedentes[:3]
    )

    missing_elements: List[str] = []
    if not symptoms_detected and not normalized_case.motivo_consulta:
        missing_elements.append("descripción clara del motivo o síntoma principal")
    if not timeline_elements:
        missing_elements.append("cronología básica del cuadro")
    if not normalized_case.contexto_emocional:
        missing_elements.append("contexto emocional o detonantes")
    if not normalized_case.antecedentes:
        missing_elements.append("antecedentes relevantes")

    attention_points: List[str] = []
    if normalized_case.inicio and not normalized_case.frecuencia:
        attention_points.append("Hay un inicio referido, pero todavía falta precisar frecuencia o recurrencia.")
    if symptoms_detected and not normalized_case.observaciones:
        attention_points.append("Hay síntomas descritos, pero faltan moduladores, agravantes o aliviantes.")
    if normalized_case.contexto_emocional and not normalized_case.inicio:
        attention_points.append("Aparece contexto emocional, pero falta ubicar mejor la cronología del cuadro.")

    analysis_trace = [
        {"step": "summary", "used_fields": [field for field in ("motivo_consulta", "sintomas", "inicio", "duracion", "frecuencia", "contexto_emocional", "antecedentes", "observaciones", "pregunta_del_terapeuta") if getattr(normalized_case, field)]},
        {"step": "missing_elements", "items": missing_elements},
        {"step": "attention_points", "items": attention_points},
    ]

    return CaseAnalysis(
        case_summary=_build_case_summary(normalized_case),
        key_elements=key_elements,
        symptoms_detected=symptoms_detected,
        timeline_elements=timeline_elements,
        context_elements=context_elements,
        missing_elements=missing_elements,
        attention_points=attention_points,
        analysis_trace=analysis_trace,
    ).to_dict()
