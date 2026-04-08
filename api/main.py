from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHUNKS_PATH = BASE_DIR / "data" / "chunks" / "library_chunks.jsonl"
THERAPY_STATIC_DIR = BASE_DIR / "api" / "static"
PAIR_VISUALS_DIR = BASE_DIR / "data" / "pair_visuals"
THERAPY_LOGO_PATH = BASE_DIR / "data" / "LOGO-IA.png"

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ConfigDict
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")

from api.assistant import AssistantOutput, NaturalAssistant, VisualAid
from api.knowledge_base import KnowledgeBase, trim_excerpt
from api.pair_engine import interpret_pairs
from api.radionic_table import build_radionic_pair_table
from api.therapy_engine import analyze_case
from api.therapy_report_engine import build_therapy_report
from api.teacher_memory import get_teacher_memory


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Pregunta del usuario")
    course_id: Optional[str] = Field(default=None, description="Filtra por un curso")
    linea: Optional[str] = Field(default=None, description="Filtra por una línea de estudio")
    history: list[dict] = Field(default_factory=list, description="Historial conversacional")
    want_visual: bool = Field(default=True, description="Si se desea apoyo visual")
    render_image: bool = Field(
        default=False,
        description="Si se debe generar una imagen real cuando el modelo lo sugiera",
    )
    max_results: int = Field(default=4, ge=1, le=8)


class SourceItem(BaseModel):
    course_id: str
    course_name: str
    linea: str
    heading: str
    source_file: str
    excerpt: str
    score: float


class VisualResponse(BaseModel):
    title: str
    type: str
    format: str
    content: str
    image_prompt: Optional[str] = None
    image_data_url: Optional[str] = None


class AskResponse(BaseModel):
    ok: bool
    answer: str
    visual: Optional[VisualResponse] = None
    generation_mode: str
    sources: list[SourceItem]


class CurrentSymptomItem(BaseModel):
    symptom_name: str = ""
    symptom_characteristics: str = ""
    therapist_notes: str = ""
    onset_age_or_date: str = ""
    frequency: str = ""
    triggering_factors: str = ""


class HistoryEventItem(BaseModel):
    event_name: str = ""
    event_characteristics: str = ""
    event_notes: str = ""
    onset_age_or_date: str = ""
    frequency: str = ""


class TherapyCasePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    patient_name: str = ""
    patient_birth_date: str = ""
    consultation_reason: str = ""
    session_goal: str = ""
    main_emotion: str = ""
    recent_trigger: str = ""
    current_emotional_context: str = ""
    emotional_context_at_onset: str = ""
    what_bothers_today: str = ""
    perceived_impediments: str = ""
    family_conflicts_notes: str = ""
    family_secrets_notes: str = ""
    transgenerational_patterns_notes: str = ""
    important_relationships_notes: str = ""
    free_case_notes: str = ""
    current_symptoms: list[CurrentSymptomItem] = Field(default_factory=list)
    history_events: list[HistoryEventItem] = Field(default_factory=list)


class PairInputItem(BaseModel):
    pair_name: str = Field(..., min_length=2)
    therapist_note: str = ""


class TherapyAnalyzeRequest(BaseModel):
    case_payload: TherapyCasePayload


class TherapyPairsRequest(BaseModel):
    case_payload: TherapyCasePayload
    pairs: list[PairInputItem] = Field(default_factory=list)


class TherapyReportRequest(BaseModel):
    case_payload: TherapyCasePayload
    pairs: list[PairInputItem] = Field(default_factory=list)


class TherapyAnalyzeResponse(BaseModel):
    ok: bool
    analysis: dict


class TherapyPairsResponse(BaseModel):
    ok: bool
    pair_analysis: dict


class TherapyReportResponse(BaseModel):
    ok: bool
    report: dict


def build_answer(question: str, sources: list[SourceItem]) -> str:
    if not sources:
        return (
            "No encontré una respuesta confiable en la biblioteca actual. "
            "Intenta ser más específico o filtra por curso."
        )

    top = sources[0]
    parts = [
        f"Encontré contenido relacionado con tu pregunta sobre {top.course_name}.",
        f"La fuente más relevante es {top.source_file}.",
    ]
    if top.heading:
        parts.append(f"La sección detectada es {top.heading}.")
    parts.append(f"Extracto clave: {top.excerpt}")
    return " ".join(parts)


def _pair_visual_path_to_url(path_value: str) -> str:
    try:
        relative = Path(path_value).resolve().relative_to(PAIR_VISUALS_DIR.resolve())
        return f"/therapy-assets/{relative.as_posix()}"
    except Exception:
        return path_value


def _rewrite_visual_asset_paths(value):
    if isinstance(value, dict):
        rewritten = {}
        for key, item in value.items():
            if key == "image_candidates" and isinstance(item, list):
                rewritten[key] = [
                    _pair_visual_path_to_url(candidate) if isinstance(candidate, str) else candidate
                    for candidate in item
                ]
            else:
                rewritten[key] = _rewrite_visual_asset_paths(item)
        return rewritten
    if isinstance(value, list):
        return [_rewrite_visual_asset_paths(item) for item in value]
    return value


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    chunks_path = Path(os.getenv("CHUNKS_PATH", DEFAULT_CHUNKS_PATH)).expanduser().resolve()
    return KnowledgeBase(chunks_path)


@lru_cache
def get_assistant() -> NaturalAssistant:
    return NaturalAssistant()


app = FastAPI(
    title="HoloAcademia AI API",
    version="0.1.0",
    description="API externa inicial para consultar la biblioteca procesada de cursos.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if THERAPY_STATIC_DIR.exists():
    app.mount("/therapy-static", StaticFiles(directory=THERAPY_STATIC_DIR), name="therapy-static")

if PAIR_VISUALS_DIR.exists():
    app.mount("/therapy-assets", StaticFiles(directory=PAIR_VISUALS_DIR), name="therapy-assets")


@app.on_event("startup")
async def warm_caches() -> None:
    get_knowledge_base()
    get_assistant()
    get_teacher_memory()


@app.get("/health")
async def health() -> dict:
    kb = get_knowledge_base()
    assistant = get_assistant()
    teacher_memory = get_teacher_memory()
    return {
        "ok": True,
        "courses": len(kb.catalog),
        "chunks": len(kb.records),
        "llm_enabled": assistant.enabled,
        "llm_provider": assistant.provider,
        "model": assistant.model,
        "course_assistant_use_model": assistant.course_use_model,
        "teacher_pairs": assistant.teacher.pair_count_unique,
        "teacher_protocols": assistant.teacher.protocol_count,
        "teacher_courses": assistant.teacher.course_count,
        "teacher_concepts": assistant.teacher.concept_count,
        "teacher_memory_ready": bool(teacher_memory and teacher_memory.ready),
        "teacher_memory_courses": teacher_memory.course_count if teacher_memory else 0,
        "teacher_memory_sources": teacher_memory.source_count if teacher_memory else 0,
        "semantic_index_ready": kb.semantic_ready,
    }


@app.get("/courses")
async def list_courses() -> dict:
    kb = get_knowledge_base()
    return {"ok": True, "courses": kb.catalog}


@app.get("/therapy/app")
async def therapy_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "therapy.html")


@app.get("/therapy/logo")
async def therapy_logo() -> FileResponse:
    return FileResponse(THERAPY_LOGO_PATH)


@app.post("/therapy/analyze", response_model=TherapyAnalyzeResponse)
async def therapy_analyze(payload: TherapyAnalyzeRequest) -> TherapyAnalyzeResponse:
    analysis = analyze_case(payload.case_payload.model_dump())
    return TherapyAnalyzeResponse(ok=True, analysis=analysis)


@app.post("/therapy/pairs", response_model=TherapyPairsResponse)
async def therapy_pairs(payload: TherapyPairsRequest) -> TherapyPairsResponse:
    case_analysis = analyze_case(payload.case_payload.model_dump())
    pairs_payload = [item.model_dump() for item in payload.pairs]
    pair_analysis = interpret_pairs(case_analysis, pairs_payload)
    pair_analysis["radionic_pair_table"] = build_radionic_pair_table(
        payload.case_payload.model_dump(),
        [item.get("pair_name", "") for item in pair_analysis.get("interpreted_pairs", [])],
        title="Tabla radiónica para pares interpretados",
    )
    return TherapyPairsResponse(ok=True, pair_analysis=_rewrite_visual_asset_paths(pair_analysis))


@app.post("/therapy/report", response_model=TherapyReportResponse)
async def therapy_report(payload: TherapyReportRequest) -> TherapyReportResponse:
    pairs_payload = [item.model_dump() for item in payload.pairs]
    report = build_therapy_report(
        case_payload=payload.case_payload.model_dump(),
        pairs_input=pairs_payload,
    )
    return TherapyReportResponse(ok=True, report=_rewrite_visual_asset_paths(report))


@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    kb = get_knowledge_base()
    assistant = get_assistant()
    merged_by_chunk = {}
    if not assistant.should_skip_search(payload.question, payload.history):
        search_queries = assistant.resolve_search_queries(payload.question, payload.history)
        use_semantic_search = False
        for search_query in search_queries:
            if use_semantic_search:
                try:
                    query_vector = assistant.embed_query(search_query)
                    partial_results = kb.semantic_search_by_vector(
                        query_vector=query_vector,
                        course_id=payload.course_id,
                        linea=payload.linea,
                        limit=payload.max_results,
                    )
                except Exception:
                    partial_results = kb.search(
                        question=search_query,
                        course_id=payload.course_id,
                        linea=payload.linea,
                        limit=payload.max_results,
                    )
            else:
                partial_results = kb.search(
                    question=search_query,
                    course_id=payload.course_id,
                    linea=payload.linea,
                    limit=payload.max_results,
                )
            for item in partial_results:
                existing = merged_by_chunk.get(item.chunk_id)
                if existing is None or item.score > existing.score:
                    merged_by_chunk[item.chunk_id] = item

    results = sorted(merged_by_chunk.values(), key=lambda item: item.score, reverse=True)[: payload.max_results]

    if results and not payload.course_id and assistant.should_focus_primary_course(payload.question):
        top_course_id = results[0].course_id
        same_course_results = [item for item in results if item.course_id == top_course_id]
        if len(same_course_results) >= 2:
            results = same_course_results[: payload.max_results]

    sources = [
        SourceItem(
            course_id=item.course_id,
            course_name=item.course_name,
            linea=item.linea,
            heading=item.heading,
            source_file=item.source_file,
            excerpt=trim_excerpt(item.text),
            score=round(item.score, 4),
        )
        for item in results
    ]

    generated: AssistantOutput = assistant.answer(
        question=payload.question,
        results=results,
        history=payload.history,
        want_visual=payload.want_visual,
        render_image=payload.render_image,
    )

    visual_payload = None
    if generated.visual:
        visual_payload = {
            "title": generated.visual.title,
            "type": generated.visual.type,
            "format": generated.visual.format,
            "content": generated.visual.content,
            "image_prompt": generated.visual.image_prompt,
            "image_data_url": generated.visual.image_data_url,
        }

    return AskResponse(
        ok=bool(generated.answer.strip()),
        answer=generated.answer,
        visual=visual_payload,
        generation_mode=generated.mode,
        sources=sources,
    )
