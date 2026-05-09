from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AcademicRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = Field(default_factory=list)


class AcademicResponse(BaseModel):
    answer: str
    confidence: str
    sources_used: List[str] = Field(default_factory=list)
    concepts_used: List[str] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    retrieval_trace: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    intent: Optional[str] = None
    mode_used: Optional[str] = None
    used_fallback: Optional[bool] = False
    concept_resolution: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_resolution_trace: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    timings: Optional[Dict[str, Any]] = Field(default_factory=dict)
