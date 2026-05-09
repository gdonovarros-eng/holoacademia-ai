from __future__ import annotations

from typing import Any, Dict, List, Set

from .models import CaseInput, IntakeAnalysis, IntakeQuestion, TherapeuticKnowledgeBase


FIELD_LABELS: Dict[str, str] = {
    "motivo_consulta": "motivo de consulta",
    "sintomas": "síntomas",
    "inicio": "inicio del síntoma",
    "duracion": "duración",
    "frecuencia": "frecuencia o recurrencia",
    "antecedentes": "antecedentes relevantes",
    "contexto_emocional": "contexto emocional",
    "observaciones": "observaciones clínicas",
    "pregunta_del_terapeuta": "pregunta del terapeuta",
}

FIELD_IMPORTANCE: Dict[str, int] = {
    "motivo_consulta": 2,
    "sintomas": 3,
    "inicio": 3,
    "duracion": 2,
    "frecuencia": 3,
    "antecedentes": 1,
    "contexto_emocional": 2,
    "observaciones": 2,
}


QUESTION_FIELD_HINTS: Dict[str, tuple] = {
    "intake_sintoma_principal": ("motivo_consulta", "sintomas"),
    "intake_tipo_sintoma": ("motivo_consulta", "sintomas"),
    "intake_caracteristicas": ("sintomas", "observaciones"),
    "intake_frecuencia": ("frecuencia",),
    "intake_recurrencia": ("frecuencia",),
    "intake_origen": ("inicio",),
    "intake_factores": ("observaciones",),
    "intake_conflicto_critico": ("inicio", "contexto_emocional"),
    "intake_vida_post_conflicto": ("contexto_emocional", "observaciones"),
    "intake_emocion_actual": ("contexto_emocional",),
    "intake_relacion_elemental": ("contexto_emocional", "observaciones"),
    "intake_antecedentes_control": ("antecedentes",),
}

QUESTION_PRIORITY_BONUS: Dict[str, int] = {
    "intake_caracteristicas": 2,
    "intake_frecuencia": 2,
    "intake_origen": 3,
    "intake_factores": 2,
    "intake_antecedentes_control": 1,
    "intake_conflicto_critico": 1,
    "intake_vida_post_conflicto": -1,
    "intake_relacion_elemental": -1,
}


def _field_present(case_input: CaseInput, field_name: str) -> bool:
    value = getattr(case_input, field_name, "")
    if isinstance(value, list):
        return bool(value)
    return bool(str(value).strip())


def _infer_question_fields(question: IntakeQuestion) -> List[str]:
    explicit = list(QUESTION_FIELD_HINTS.get(question.id, ()))
    if explicit:
        return explicit
    text = f"{question.pregunta} {question.objetivo}".lower()
    inferred: List[str] = []
    if any(token in text for token in ("síntoma", "sintoma", "duele", "se siente")):
        inferred.append("sintomas")
    if any(token in text for token in ("desde cuándo", "cuando empezó", "inicio", "origen")):
        inferred.append("inicio")
    if any(token in text for token in ("frecuencia", "recur", "cada cuánto")):
        inferred.append("frecuencia")
    if any(token in text for token in ("antecedente", "cirug", "embarazo", "marcapasos", "trasplante")):
        inferred.append("antecedentes")
    if any(token in text for token in ("emoción", "emocion", "conflicto")):
        inferred.append("contexto_emocional")
    if any(token in text for token in ("agrava", "alivia", "deton", "dispara")):
        inferred.append("observaciones")
    return list(dict.fromkeys(inferred))


def _priority_weight(value: str) -> int:
    mapping = {"alta": 3, "media": 2, "baja": 1}
    return mapping.get((value or "").strip().lower(), 1)


def _question_already_covered(question: IntakeQuestion, case_input: CaseInput) -> bool:
    fields = _infer_question_fields(question)
    return bool(fields) and all(_field_present(case_input, field_name) for field_name in fields)


def analyze_case_intake(case_input: Any, knowledge: TherapeuticKnowledgeBase) -> Dict[str, Any]:
    normalized_case = case_input if isinstance(case_input, CaseInput) else CaseInput.from_dict(case_input)

    present_data = [label for field_name, label in FIELD_LABELS.items() if _field_present(normalized_case, field_name)]
    missing_data = [label for field_name, label in FIELD_LABELS.items() if field_name not in {"pregunta_del_terapeuta"} and not _field_present(normalized_case, field_name)]

    priority_questions: List[Dict[str, Any]] = []
    secondary_questions: List[Dict[str, Any]] = []
    intake_trace: List[Dict[str, Any]] = []
    seen_questions: Set[str] = set()

    for question in knowledge.intake_questions:
        if question.id in seen_questions or not question.pregunta:
            continue
        seen_questions.add(question.id)
        fields = _infer_question_fields(question)
        covered = _question_already_covered(question, normalized_case)
        unlocked_fields = [FIELD_LABELS[field_name] for field_name in fields if not _field_present(normalized_case, field_name)]
        score = _priority_weight(question.prioridad)
        score += QUESTION_PRIORITY_BONUS.get(question.id, 0)
        if unlocked_fields:
            score += min(len(unlocked_fields), 2)
            score += sum(FIELD_IMPORTANCE.get(field_name, 1) for field_name in fields if not _field_present(normalized_case, field_name))
        if question.flujo == "inicio":
            score += 1
        if covered:
            score -= 3
        question_payload = {
            "id": question.id,
            "pregunta": question.pregunta,
            "objetivo": question.objetivo,
            "prioridad": question.prioridad,
            "flujo": question.flujo,
            "relacionado_reasoning": question.relacionado_reasoning,
            "desbloquea": unlocked_fields,
        }
        intake_trace.append(
            {
                "question_id": question.id,
                "mapped_fields": fields,
                "covered": covered,
                "score": score,
                "reason": "campos faltantes" if unlocked_fields else "pregunta complementaria",
            }
        )
        if covered:
            continue
        if question.prioridad == "alta" or score >= 4:
            priority_questions.append(question_payload)
        else:
            secondary_questions.append(question_payload)

    question_scores = {item["question_id"]: item["score"] for item in intake_trace}
    priority_questions.sort(
        key=lambda item: (
            -question_scores.get(item["id"], 0),
            -_priority_weight(item["prioridad"]),
            item["flujo"] != "inicio",
            item["pregunta"],
        )
    )
    secondary_questions.sort(
        key=lambda item: (
            -question_scores.get(item["id"], 0),
            -_priority_weight(item["prioridad"]),
            item["pregunta"],
        )
    )

    return IntakeAnalysis(
        present_data=present_data,
        missing_data=missing_data,
        priority_questions=priority_questions[:6],
        secondary_questions=secondary_questions[:6],
        intake_trace=intake_trace,
    ).to_dict()
