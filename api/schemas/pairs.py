from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PairsInterpretRequest(BaseModel):
    pares_encontrados: List[str] = Field(..., min_length=1, description="Nombres de los pares encontrados en el rastreo")
    notas: Optional[str] = Field(default=None, description="Notas opcionales del caso para contextualizar la lectura")


class PairInterpretation(BaseModel):
    par_ingresado: str
    par_encontrado: str
    tipo: str
    tipo_raw: str = ""
    condiciones: str = ""
    significado_emocional: str = ""
    sistemas_afectados: List[str] = Field(default_factory=list)


class PairsInterpretResponse(BaseModel):
    interpretaciones: List[PairInterpretation] = Field(default_factory=list)
    patron_general: str = ""
    sistemas_dominantes: List[str] = Field(default_factory=list)
    tipos_presentes: List[str] = Field(default_factory=list)
    encontrados: int = 0
    no_encontrados: List[str] = Field(default_factory=list)
