from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .models import CaseAnalysis, ClinicalWarning, InterpretationOutput, ReasoningOutput, TherapeuticKnowledgeBase


def _tokens(text: str) -> set:
    return {token for token in re.findall(r"[a-záéíóúñ]+", (text or "").lower()) if len(token) > 2}


def _guide_score(guide: Any, bag: set) -> Tuple[float, List[str]]:
    evidence: List[str] = []
    score = 0.0
    factors = _tokens(" ".join(guide.factores_clave))
    matched_factors = sorted(factors & bag)
    if matched_factors:
        score += min(len(matched_factors) * 0.8, 2.4)
        evidence.append(f"factores:{', '.join(matched_factors[:4])}")
    context_tokens = _tokens(guide.contexto)
    matched_context = sorted(context_tokens & bag)
    if matched_context:
        score += min(len(matched_context) * 0.35, 1.1)
        evidence.append(f"contexto:{', '.join(matched_context[:4])}")
    return score, evidence


def _warning_is_relevant(warning: ClinicalWarning, bag: set, missing_elements: List[str]) -> bool:
    if warning.tipo in {"limite_metodologico", "ambiguedad_clinica"}:
        return True
    text = f"{warning.advertencia} {warning.detalle}".lower()
    if "cirug" in text and any("antecedente" in item.lower() for item in missing_elements):
        return True
    return bool(_tokens(text) & bag)


def build_interpretation(
    case_analysis: Any,
    reasoning_output: Any,
    knowledge: TherapeuticKnowledgeBase,
) -> Dict[str, Any]:
    normalized_analysis = case_analysis if isinstance(case_analysis, CaseAnalysis) else CaseAnalysis(**case_analysis)
    normalized_reasoning = reasoning_output if isinstance(reasoning_output, ReasoningOutput) else ReasoningOutput(**reasoning_output)
    case_bag = _tokens(" ".join(normalized_analysis.key_elements + normalized_analysis.symptoms_detected + normalized_analysis.timeline_elements + normalized_analysis.context_elements + normalized_reasoning.possible_interpretive_lines))

    relevant_guides: List[Dict[str, Any]] = []
    interpretive_notes: List[str] = []
    interpretation_trace: List[Dict[str, Any]] = []
    limits: List[str] = []

    for guide in knowledge.interpretation_guides:
        score, evidence = _guide_score(guide, case_bag)
        if score < 0.8:
            continue
        relevant_guides.append(
            {
                "id": guide.id,
                "contexto": guide.contexto,
                "interpretacion": guide.interpretacion,
                "nivel_riesgo": guide.nivel_riesgo,
                "score": round(score, 3),
            }
        )
        interpretation_trace.append({"guide_id": guide.id, "score": round(score, 3), "evidence": evidence})
        if guide.interpretacion:
            interpretive_notes.append(guide.interpretacion)
        if guide.cuando_no_aplica:
            limits.extend(guide.cuando_no_aplica[:1])

    relevant_guides.sort(key=lambda item: item["score"], reverse=True)
    interpretive_notes = list(dict.fromkeys(item for item in interpretive_notes if item))[:1]
    limits = list(dict.fromkeys(item for item in limits if item))

    matched_warnings: List[Dict[str, Any]] = []
    for warning in knowledge.clinical_warnings:
        if _warning_is_relevant(warning, case_bag, normalized_analysis.missing_elements):
            matched_warnings.append(
                {
                    "id": warning.id,
                    "tipo": warning.tipo,
                    "advertencia": warning.advertencia,
                    "detalle": warning.detalle,
                }
            )

    if normalized_reasoning.confidence == "low":
        limits.append("La base disponible no alcanza todavía para una lectura interpretativa firme; conviene ampliar entrevista antes de cerrar hipótesis.")
    if normalized_analysis.missing_elements:
        limits.append("Todavía faltan datos relevantes del caso, así que cualquier lectura debe tomarse como tentativa.")

    return InterpretationOutput(
        interpretive_notes=interpretive_notes,
        relevant_guides=relevant_guides[:1],
        warnings=matched_warnings[:2],
        limits_of_interpretation=list(dict.fromkeys(limits))[:2],
        interpretation_trace=interpretation_trace[:1],
    ).to_dict()
