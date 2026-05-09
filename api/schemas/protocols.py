from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ProtocolGuideRequest(BaseModel):
    protocol_id: Optional[str] = None
    protocol_name: Optional[str] = None
    user_goal: Optional[str] = None
    case_context: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_protocol_selector(self) -> "ProtocolGuideRequest":
        if not (self.protocol_id or self.protocol_name):
            raise ValueError("protocol_id o protocol_name es requerido.")
        return self


class ProtocolStep(BaseModel):
    orden: int
    titulo: str
    instruccion: str
    objetivo_del_paso: Optional[str] = ""
    que_observar: List[str] = Field(default_factory=list)
    que_registrar: List[str] = Field(default_factory=list)
    notas: List[str] = Field(default_factory=list)
    decision_points: List[str] = Field(default_factory=list)
    criterios_de_avance: List[str] = Field(default_factory=list)
    errores_comunes: List[str] = Field(default_factory=list)


class ProtocolGuideResponse(BaseModel):
    found: bool
    protocol_id: Optional[str] = None
    protocol_name: Optional[str] = None
    answer: str
    confidence: str
    objetivo: Optional[str] = None
    descripcion: Optional[str] = None
    cuando_usarlo: List[str] = Field(default_factory=list)
    prerequisitos: List[str] = Field(default_factory=list)
    pasos: List[ProtocolStep] = Field(default_factory=list)
    observaciones: List[str] = Field(default_factory=list)
    advertencias: List[str] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)
