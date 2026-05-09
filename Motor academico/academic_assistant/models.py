from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Concept:
    id: str
    termino: str
    aliases: list[str] = field(default_factory=list)
    definicion: str = ""
    explicacion_simple: str = ""
    explicacion_extendida: str = ""
    modulo: str = ""
    curso: str = ""
    linea: str = ""
    source: str = "merged"
    confidence: str = "low"
    relacionado_protocolos: list[str] = field(default_factory=list)
    relacionado_reasoning: list[str] = field(default_factory=list)
    relacionado_conceptos: list[str] = field(default_factory=list)
    cuando_se_aplica: str = ""
    errores_comunes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Concept":
        return cls(
            id=str(data.get("id", "")),
            termino=str(data.get("termino", "")),
            aliases=[str(item) for item in data.get("aliases", []) if item],
            definicion=str(data.get("definicion", "")),
            explicacion_simple=str(data.get("explicacion_simple", "")),
            explicacion_extendida=str(data.get("explicacion_extendida", "")),
            modulo=str(data.get("modulo", "")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            relacionado_protocolos=[str(item) for item in data.get("relacionado_protocolos", []) if item],
            relacionado_reasoning=[str(item) for item in data.get("relacionado_reasoning", []) if item],
            relacionado_conceptos=[str(item) for item in data.get("relacionado_conceptos", []) if item],
            cuando_se_aplica=str(data.get("cuando_se_aplica", "")),
            errores_comunes=[str(item) for item in data.get("errores_comunes", []) if item],
        )


@dataclass
class GlossaryEntry:
    id: str
    termino: str
    definicion_corta: str = ""
    curso: str = ""
    linea: str = ""
    source: str = "merged"
    confidence: str = "low"
    referencia_concepto: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlossaryEntry":
        return cls(
            id=str(data.get("id") or data.get("referencia_concepto") or data.get("termino", "")),
            termino=str(data.get("termino", "")),
            definicion_corta=str(data.get("definicion_corta", "")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            referencia_concepto=str(data.get("referencia_concepto", "")),
        )


@dataclass
class ModuleSummary:
    id: str
    titulo: str
    resumen: str = ""
    temas_clave: list[str] = field(default_factory=list)
    curso: str = ""
    linea: str = ""
    source: str = "merged"
    confidence: str = "low"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleSummary":
        return cls(
            id=str(data.get("id", "")),
            titulo=str(data.get("titulo", "")),
            resumen=str(data.get("resumen", "")),
            temas_clave=[str(item) for item in data.get("temas_clave", []) if item],
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
        )


@dataclass
class FAQCandidate:
    id: str
    pregunta: str
    respuesta: str = ""
    curso: str = ""
    linea: str = ""
    source: str = "merged"
    confidence: str = "low"
    relacionado_conceptos: list[str] = field(default_factory=list)
    relacionado_protocolos: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FAQCandidate":
        return cls(
            id=str(data.get("id", "")),
            pregunta=str(data.get("pregunta", "")),
            respuesta=str(data.get("respuesta", "")),
            curso=str(data.get("curso", "")),
            linea=str(data.get("linea", "")),
            source=str(data.get("source", "merged")),
            confidence=str(data.get("confidence", "low")),
            relacionado_conceptos=[str(item) for item in data.get("relacionado_conceptos", []) if item],
            relacionado_protocolos=[str(item) for item in data.get("relacionado_protocolos", []) if item],
        )


@dataclass
class RetrievalHit:
    id: str
    source_type: str
    score: float
    title: str
    content: str
    modulo: str = ""
    source: str = "merged"
    confidence: str = "low"
    curso: str = ""
    linea: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_trace(self) -> dict[str, Any]:
        return {
            "source": self.source_type,
            "id": self.id,
            "score": round(self.score, 4),
            "modulo": self.modulo,
        }


@dataclass
class AcademicContext:
    query: str
    main_concepts: list[dict[str, Any]] = field(default_factory=list)
    supporting_glossary: list[dict[str, Any]] = field(default_factory=list)
    module_summaries: list[dict[str, Any]] = field(default_factory=list)
    faq_support: list[dict[str, Any]] = field(default_factory=list)
    course_context: dict[str, Any] = field(default_factory=dict)
    citations: list[dict[str, Any]] = field(default_factory=list)
    retrieval_trace: list[dict[str, Any]] = field(default_factory=list)
    raw_results: list[RetrievalHit] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["raw_results"] = [asdict(item) for item in self.raw_results]
        return payload


@dataclass
class AcademicAnswer:
    answer: str
    confidence: str
    sources_used: list[dict[str, Any]]
    concepts_used: list[str]
    suggested_followups: list[str]
    retrieval_trace: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AcademicKnowledgeBase:
    course_dir: Path
    course_id: str
    line: str
    concepts: list[Concept] = field(default_factory=list)
    glossary: list[GlossaryEntry] = field(default_factory=list)
    module_summaries: list[ModuleSummary] = field(default_factory=list)
    faq_candidates: list[FAQCandidate] = field(default_factory=list)
    course_overview: dict[str, Any] = field(default_factory=dict)
    course_manifest: dict[str, Any] = field(default_factory=dict)
    transcript_inventory: list[dict[str, Any]] = field(default_factory=list)
    module_inventory: list[dict[str, Any]] = field(default_factory=list)
    clean_fallback_texts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
