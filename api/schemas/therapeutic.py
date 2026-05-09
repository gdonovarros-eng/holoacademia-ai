from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TherapeuticRequest(BaseModel):
    motivo_consulta: Optional[str] = None
    sintomas: Optional[List[str]] = None
    inicio: Optional[str] = None
    duracion: Optional[str] = None
    frecuencia: Optional[str] = None
    antecedentes: Optional[List[str]] = None
    contexto_emocional: Optional[str] = None
    observaciones: Optional[str] = None
    pregunta_del_terapeuta: Optional[str] = None
    family_notes: Optional[str] = None


class TherapeuticResponse(BaseModel):
    answer: str
    confidence: str
    entrevista_base: Dict[str, Any] = Field(default_factory=dict)
    ruta_principal: Optional[str] = None
    lectura_inicial: Optional[str] = None
    puerta_principal: Dict[str, Any] = Field(default_factory=dict)
    ruta_sugerida: Optional[str] = None
    accion_inmediata: Optional[str] = None
    evidencias_principales: List[str] = Field(default_factory=list)
    validaciones_clave: List[str] = Field(default_factory=list)
    protocolo_principal: Dict[str, Any] = Field(default_factory=dict)
    protocolo_sugerido: Dict[str, Any] = Field(default_factory=dict)
    herramientas_clave: List[Dict[str, Any]] = Field(default_factory=list)
    herramientas_relevantes: List[Dict[str, Any]] = Field(default_factory=list)
    pasos_inmediatos: List[str] = Field(default_factory=list)
    punto_de_decision: Optional[str] = None
    si_no_confirma: Optional[str] = None
    preguntas_clave: List[str] = Field(default_factory=list)
    limites: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    priority_questions: List[str] = Field(default_factory=list)
    possible_lines: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    used_patterns: List[str] = Field(default_factory=list)
    used_guides: List[str] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)
    genogram_resolution: Optional[Dict[str, Any]] = None
