from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _list_of_str(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


@dataclass
class IntakeQuestion:
    id: str
    pregunta: str
    objetivo: str = ""
    cuando_usarla: List[str] = field(default_factory=list)
    curso: str = ""
    linea: str = ""
    modulo: str = ""
    seccion: str = ""
    source: str = "merged"
    confidence: str = "low"
    flujo: str = "inicio"
    prioridad: str = "media"
    siguiente_posible: List[str] = field(default_factory=list)
    relacionado_conceptos: List[str] = field(default_factory=list)
    relacionado_reasoning: List[str] = field(default_factory=list)
    relacionado_protocolos: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntakeQuestion":
        return cls(
            id=str(data.get("id", "")),
            pregunta=str(data.get("pregunta", "")),
            objetivo=str(data.get("objetivo", "")),
            cuando_usarla=_list_of_str(data.get("cuando_usarla")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            modulo=str(data.get("modulo", "")),
            seccion=str(data.get("seccion", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            flujo=str(data.get("flujo", "inicio")),
            prioridad=str(data.get("prioridad", "media")),
            siguiente_posible=_list_of_str(data.get("siguiente_posible")),
            relacionado_conceptos=_list_of_str(data.get("relacionado_conceptos")),
            relacionado_reasoning=_list_of_str(data.get("relacionado_reasoning")),
            relacionado_protocolos=_list_of_str(data.get("relacionado_protocolos")),
        )


@dataclass
class ReasoningPattern:
    id: str
    trigger: str
    interpretacion: str = ""
    que_observar: List[str] = field(default_factory=list)
    acciones_sugeridas: List[str] = field(default_factory=list)
    curso: str = ""
    linea: str = ""
    modulo: str = ""
    seccion: str = ""
    source: str = "merged"
    confidence: str = "low"
    preguntas_clave: List[str] = field(default_factory=list)
    nivel_confianza: str = "medio"
    relacionado_conceptos: List[str] = field(default_factory=list)
    relacionado_protocolos: List[str] = field(default_factory=list)
    errores_comunes: List[str] = field(default_factory=list)
    relacionado_intake: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReasoningPattern":
        return cls(
            id=str(data.get("id", "")),
            trigger=str(data.get("trigger", "")),
            interpretacion=str(data.get("interpretacion", "")),
            que_observar=_list_of_str(data.get("que_observar")),
            acciones_sugeridas=_list_of_str(data.get("acciones_sugeridas")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            modulo=str(data.get("modulo", "")),
            seccion=str(data.get("seccion", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            preguntas_clave=_list_of_str(data.get("preguntas_clave")),
            nivel_confianza=str(data.get("nivel_confianza", "medio")),
            relacionado_conceptos=_list_of_str(data.get("relacionado_conceptos")),
            relacionado_protocolos=_list_of_str(data.get("relacionado_protocolos")),
            errores_comunes=_list_of_str(data.get("errores_comunes")),
            relacionado_intake=_list_of_str(data.get("relacionado_intake")),
        )


@dataclass
class InterpretationGuide:
    id: str
    contexto: str
    interpretacion: str = ""
    factores_clave: List[str] = field(default_factory=list)
    errores_comunes: List[str] = field(default_factory=list)
    curso: str = ""
    linea: str = ""
    modulo: str = ""
    seccion: str = ""
    source: str = "merged"
    confidence: str = "low"
    cuando_no_aplica: List[str] = field(default_factory=list)
    nivel_riesgo: str = "medio"
    relacionado_conceptos: List[str] = field(default_factory=list)
    relacionado_protocolos: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterpretationGuide":
        return cls(
            id=str(data.get("id", "")),
            contexto=str(data.get("contexto", "")),
            interpretacion=str(data.get("interpretacion", "")),
            factores_clave=_list_of_str(data.get("factores_clave")),
            errores_comunes=_list_of_str(data.get("errores_comunes")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            modulo=str(data.get("modulo", "")),
            seccion=str(data.get("seccion", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            cuando_no_aplica=_list_of_str(data.get("cuando_no_aplica")),
            nivel_riesgo=str(data.get("nivel_riesgo", "medio")),
            relacionado_conceptos=_list_of_str(data.get("relacionado_conceptos")),
            relacionado_protocolos=_list_of_str(data.get("relacionado_protocolos")),
        )


@dataclass
class TherapeuticObservation:
    id: str
    observacion: str
    utilidad_terapeutica: str = ""
    relacionado_con: List[str] = field(default_factory=list)
    curso: str = ""
    linea: str = ""
    modulo: str = ""
    seccion: str = ""
    source: str = "merged"
    confidence: str = "low"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TherapeuticObservation":
        return cls(
            id=str(data.get("id", "")),
            observacion=str(data.get("observacion", "")),
            utilidad_terapeutica=str(data.get("utilidad_terapeutica", "")),
            relacionado_con=_list_of_str(data.get("relacionado_con")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            modulo=str(data.get("modulo", "")),
            seccion=str(data.get("seccion", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
        )


@dataclass
class ClinicalWarning:
    id: str
    tipo: str
    advertencia: str
    detalle: str = ""
    curso: str = ""
    linea: str = ""
    modulo: str = ""
    seccion: str = ""
    source: str = "merged"
    confidence: str = "low"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClinicalWarning":
        return cls(
            id=str(data.get("id", "")),
            tipo=str(data.get("tipo", "")),
            advertencia=str(data.get("advertencia", "")),
            detalle=str(data.get("detalle", "")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            modulo=str(data.get("modulo", "")),
            seccion=str(data.get("seccion", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
        )


@dataclass
class CaseInput:
    motivo_consulta: str = ""
    sintomas: List[str] = field(default_factory=list)
    inicio: str = ""
    duracion: str = ""
    frecuencia: str = ""
    antecedentes: List[str] = field(default_factory=list)
    contexto_emocional: str = ""
    observaciones: str = ""
    pregunta_del_terapeuta: str = ""
    historial_conversacional: List[Dict[str, Any]] = field(default_factory=list)
    curso: str = ""
    linea: str = ""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CaseInput":
        payload = data or {}
        return cls(
            motivo_consulta=str(payload.get("motivo_consulta", "")).strip(),
            sintomas=_list_of_str(payload.get("sintomas")),
            inicio=str(payload.get("inicio", "")).strip(),
            duracion=str(payload.get("duracion", "")).strip(),
            frecuencia=str(payload.get("frecuencia", "")).strip(),
            antecedentes=_list_of_str(payload.get("antecedentes")),
            contexto_emocional=str(payload.get("contexto_emocional", "")).strip(),
            observaciones=str(payload.get("observaciones", "")).strip(),
            pregunta_del_terapeuta=str(payload.get("pregunta_del_terapeuta", "")).strip(),
            historial_conversacional=payload.get("historial_conversacional", []) if isinstance(payload.get("historial_conversacional"), list) else [],
            curso=str(payload.get("curso", "")).strip(),
            linea=str(payload.get("linea", "")).strip(),
        )

    def to_text_fragments(self) -> List[str]:
        fragments = [self.motivo_consulta, self.inicio, self.duracion, self.frecuencia, self.contexto_emocional, self.observaciones, self.pregunta_del_terapeuta]
        fragments.extend(self.sintomas)
        fragments.extend(self.antecedentes)
        return [item.strip() for item in fragments if item and item.strip()]


@dataclass
class IntakeAnalysis:
    present_data: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    priority_questions: List[Dict[str, Any]] = field(default_factory=list)
    secondary_questions: List[Dict[str, Any]] = field(default_factory=list)
    intake_trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaseAnalysis:
    case_summary: str = ""
    key_elements: List[str] = field(default_factory=list)
    symptoms_detected: List[str] = field(default_factory=list)
    timeline_elements: List[str] = field(default_factory=list)
    context_elements: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    attention_points: List[str] = field(default_factory=list)
    analysis_trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningOutput:
    matched_patterns: List[Dict[str, Any]] = field(default_factory=list)
    possible_interpretive_lines: List[str] = field(default_factory=list)
    recommended_followup_questions: List[str] = field(default_factory=list)
    entrevista_base: Dict[str, Any] = field(default_factory=dict)
    ruta_principal: str = ""
    puerta_principal: Dict[str, Any] = field(default_factory=dict)
    ruta_sugerida: str = ""
    accion_inmediata: str = ""
    validaciones_clave: List[str] = field(default_factory=list)
    protocolos_sugeridos: List[Dict[str, Any]] = field(default_factory=list)
    herramientas_relevantes: List[Dict[str, Any]] = field(default_factory=list)
    pasos_inmediatos: List[str] = field(default_factory=list)
    punto_de_decision: str = ""
    si_no_confirma: str = ""
    reasoning_trace: List[Dict[str, Any]] = field(default_factory=list)
    confidence: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InterpretationOutput:
    interpretive_notes: List[str] = field(default_factory=list)
    relevant_guides: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    limits_of_interpretation: List[str] = field(default_factory=list)
    interpretation_trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TherapeuticResponse:
    answer: str
    confidence: str
    entrevista_base: Dict[str, Any] = field(default_factory=dict)
    ruta_principal: str = ""
    lectura_inicial: str = ""
    puerta_principal: Dict[str, Any] = field(default_factory=dict)
    ruta_sugerida: str = ""
    accion_inmediata: str = ""
    evidencias_principales: List[str] = field(default_factory=list)
    validaciones_clave: List[str] = field(default_factory=list)
    protocolo_principal: Dict[str, Any] = field(default_factory=dict)
    protocolo_sugerido: Dict[str, Any] = field(default_factory=dict)
    herramientas_clave: List[Dict[str, Any]] = field(default_factory=list)
    herramientas_relevantes: List[Dict[str, Any]] = field(default_factory=list)
    pasos_inmediatos: List[str] = field(default_factory=list)
    punto_de_decision: str = ""
    si_no_confirma: str = ""
    preguntas_clave: List[str] = field(default_factory=list)
    limites: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    priority_questions: List[str] = field(default_factory=list)
    possible_lines: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    used_patterns: List[str] = field(default_factory=list)
    used_guides: List[str] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TherapeuticKnowledgeBase:
    course_dir: Path
    course_id: str
    line: str
    intake_questions: List[IntakeQuestion] = field(default_factory=list)
    reasoning_patterns: List[ReasoningPattern] = field(default_factory=list)
    interpretation_guides: List[InterpretationGuide] = field(default_factory=list)
    therapeutic_observations: List[TherapeuticObservation] = field(default_factory=list)
    clinical_warnings: List[ClinicalWarning] = field(default_factory=list)
    course_manifest: Dict[str, Any] = field(default_factory=dict)
    connection_map: Dict[str, Any] = field(default_factory=dict)
    course_overview: Dict[str, Any] = field(default_factory=dict)
    module_summaries: List[Dict[str, Any]] = field(default_factory=list)
    concepts: List[Dict[str, Any]] = field(default_factory=list)
    protocols: List[Dict[str, Any]] = field(default_factory=list)
    structured_case_protocols: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
