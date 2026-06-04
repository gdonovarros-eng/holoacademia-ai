from __future__ import annotations

import os
import secrets
import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional

from api.db import (
    init_db, upsert_user, get_usage, try_consume,
    sign_session, verify_session, PLAN_LIMITS, PLAN_NAMES,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHUNKS_PATH = BASE_DIR / "data" / "chunks" / "library_chunks.jsonl"

# DB en disco persistente de Render (/data) o local en desarrollo
_DB_PATH = Path(os.getenv("DB_PATH", "/data/holoacademia.db"))
if not _DB_PATH.parent.exists():
    _DB_PATH = BASE_DIR / "holoacademia.db"
THERAPY_STATIC_DIR = BASE_DIR / "api" / "static"
PAIR_VISUALS_DIR = BASE_DIR / "data" / "pair_visuals"
THERAPY_LOGO_PATH = BASE_DIR / "data" / "LOGO-IA.png"

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
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
from api.routes.academic import router as academic_router
from api.routes.pairs import router as pairs_router
from api.routes.protocols import router as protocols_router
from api.routes.therapeutic import router as therapeutic_router
from api.routes.therapeutic_akinator import router as therapeutic_akinator_router
from api.routes.astro import router as astro_router
from api.routes.numerology import router as numerology_router
from api.routes.tarot import router as tarot_router
from api.routes.horoscopo import router as horoscopo_router
from api.therapy_engine import analyze_case
from api.therapy_report_engine import build_therapy_report
from api.therapy_reasoner import build_therapy_reasoning
from api.teacher_memory import get_teacher_memory
from api.chat_service import stream_chat, set_shared_kb


logger = logging.getLogger(__name__)


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


class TherapyPairCapture(BaseModel):
    pair_name: str = Field(..., min_length=2)
    validated_by_therapist: bool = False
    validated: bool = False
    applied: bool = False
    application_minutes: int = 0
    application_start_time: str = ""
    therapist_note: str = ""
    notes: str = ""
    patient_response: str = ""
    followup_needed: bool = False
    pair_type: str = ""
    body_location_1: str = ""
    body_location_2: str = ""
    related_system: str = ""
    related_condition_hint: str = ""


class TherapyAnalyzeRequest(BaseModel):
    case_payload: TherapyCasePayload


class TherapyPairsRequest(BaseModel):
    case_payload: TherapyCasePayload
    pairs: list[TherapyPairCapture] = Field(default_factory=list)
    analysis: Optional[dict] = None


class TherapyReportRequest(BaseModel):
    case_payload: TherapyCasePayload
    pairs: list[TherapyPairCapture] = Field(default_factory=list)
    analysis: Optional[dict] = None
    pair_analysis: Optional[dict] = None
    precomputed_case_analysis: Optional[dict] = None
    precomputed_pair_analysis: Optional[dict] = None


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
    parts = ["Encontré contenido relevante para tu pregunta."]
    if top.heading:
        parts.append(f"La sección más relacionada es: {top.heading}.")
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


def _warm_caches_safe() -> None:
    for label, loader in (
        ("knowledge_base", get_knowledge_base),
        ("assistant", get_assistant),
        ("teacher_memory", get_teacher_memory),
    ):
        try:
            result = loader()
            # Compartir el KB con chat_service para evitar carga duplicada
            if label == "knowledge_base":
                set_shared_kb(result)
        except Exception:
            logger.exception("No se pudo precalentar %s durante el arranque.", label)


app = FastAPI(
    title="HoloAcademia AI API",
    version="0.1.0",
    description="API externa inicial para consultar la biblioteca procesada de cursos.",
)

app.include_router(academic_router)
app.include_router(pairs_router)
app.include_router(protocols_router)
app.include_router(therapeutic_router)
app.include_router(therapeutic_akinator_router)
app.include_router(astro_router)
app.include_router(numerology_router)
app.include_router(tarot_router)
app.include_router(horoscopo_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Control de acceso + sesión de usuario ─────────────────────────────────────
# Variables de entorno en Render:
#   EMBED_SECRET  — secreto compartido con Wix (requerido)
#   LOGIN_URL     — URL de login en Wix (destino del redirect)
#
# URL del iframe en Wix Velo:
#   https://holoacademia-ai.onrender.com/?embed=1&uid=WIX_UID&plan=elite_pro&token=EMBED_SECRET
#
# Flujo:
#   1. Wix pasa uid + plan + token en la URL del iframe
#   2. Middleware valida token, crea/actualiza usuario en DB, setea cookie firmada
#   3. Navegación posterior usa la cookie — sin token en URL
#   4. Acceso directo sin cookie/token → redirect a LOGIN_URL
_EMBED_SECRET  = os.getenv("EMBED_SECRET", "")
_SESSION_COOKIE = "holo_sess"
_SESSION_MAX_AGE = 60 * 60 * 24 * 7   # 7 días
_LOGIN_REDIRECT  = os.getenv("LOGIN_URL", "https://www.holoacademia.com/asistenteia")

_PROTECTED_PATHS = {"/", "/intake", "/terapeuta", "/alumno", "/pares", "/tablas", "/rastreo", "/astro", "/astro-home", "/sinastria", "/transitos", "/progresiones", "/salud", "/numerologia", "/tarot", "/horoscopo", "/holograma", "/eft-pro", "/creencias", "/emociones-atrapadas", "/guia-clinica"}


def _get_session_user(request: Request) -> tuple[str, str] | None:
    """
    Extract (user_id, plan) from the signed session cookie.
    Returns None if missing or tampered.
    """
    cookie = request.cookies.get(_SESSION_COOKIE, "")
    if not cookie or not _EMBED_SECRET:
        return None
    return verify_session(cookie, _EMBED_SECRET)


@app.middleware("http")
async def session_guard(request: Request, call_next):
    """
    Protege páginas HTML. En la primera carga (token en URL) crea/actualiza
    el usuario en la DB y emite una cookie firmada con uid|plan.
    Navegaciones posteriores usan la cookie.
    APIs, assets y /health siempre pasan.
    """
    if not _EMBED_SECRET:
        return await call_next(request)

    path = request.url.path.rstrip("/") or "/"
    if path not in _PROTECTED_PATHS:
        return await call_next(request)

    token  = request.query_params.get("token", "")
    uid    = request.query_params.get("uid", "").strip()
    plan   = request.query_params.get("plan", "holoconexion").strip()
    cookie = request.cookies.get(_SESSION_COOKIE, "")

    token_ok  = bool(token) and bool(uid) and secrets.compare_digest(token, _EMBED_SECRET)
    cookie_ok = bool(cookie) and verify_session(cookie, _EMBED_SECRET) is not None

    if not token_ok and not cookie_ok:
        # Si viene desde un iframe embed, mostrar página inline en vez de redirigir
        if request.query_params.get("embed") == "1" or request.cookies.get("embed_hint") == "1":
            from fastapi.responses import HTMLResponse
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<style>body{font-family:sans-serif;display:flex;align-items:center;"
                "justify-content:center;height:100vh;margin:0;background:#f5f0ff;}"
                ".box{text-align:center;padding:2rem;}"
                "h2{color:#6b21a8;}p{color:#555;}a{color:#7c3aed;}"
                "</style></head><body><div class='box'>"
                "<h2>🔒 Acceso restringido</h2>"
                "<p>Por favor <a href='" + _LOGIN_REDIRECT + "' target='_top'>inicia sesión</a>"
                " para acceder a Holoacadem-iA.</p></div></body></html>"
            )
            return HTMLResponse(html, status_code=200)
        return RedirectResponse(_LOGIN_REDIRECT, status_code=302)

    response = await call_next(request)

    if token_ok:
        # Primer acceso válido desde Wix — registrar/actualizar usuario
        if plan not in PLAN_LIMITS:
            plan = "holoconexion"
        upsert_user(_DB_PATH, uid, plan)
        signed = sign_session(uid, plan, _EMBED_SECRET)
        response.set_cookie(
            _SESSION_COOKIE,
            signed,
            max_age=_SESSION_MAX_AGE,
            httponly=True,
            samesite="none",
            secure=True,
        )

    return response

if THERAPY_STATIC_DIR.exists():
    app.mount("/therapy-static", StaticFiles(directory=THERAPY_STATIC_DIR), name="therapy-static")

if PAIR_VISUALS_DIR.exists():
    app.mount("/therapy-assets", StaticFiles(directory=PAIR_VISUALS_DIR), name="therapy-assets")

TABLAS_IMAGES_DIR = BASE_DIR / "data" / "tablas_images"
if TABLAS_IMAGES_DIR.exists():
    app.mount("/tablas-assets", StaticFiles(directory=TABLAS_IMAGES_DIR), name="tablas-assets")


@app.on_event("startup")
async def warm_caches() -> None:
    # Inicializar DB de usuarios (crea tablas si no existen)
    try:
        init_db(_DB_PATH)
        logging.getLogger(__name__).info("Usage DB ready: %s", _DB_PATH)
    except Exception as exc:
        logging.getLogger(__name__).warning("Usage DB init failed: %s", exc)
    # Pre-calentamiento activado en Standard (2 GB).
    # Los caches se cargan en background al arrancar para servir la primera solicitud sin latencia.
    threading.Thread(target=_warm_caches_safe, name="warm-caches", daemon=True).start()


@app.get("/health")
async def health() -> dict:
    """Health check ligero — solo confirma que el proceso está vivo."""
    return {"ok": True, "status": "up"}


@app.get("/health/full")
async def health_full() -> dict:
    """Health check completo — carga KB, assistant y teacher memory."""
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


def _therapy_app_response() -> FileResponse:
    return FileResponse(
        THERAPY_STATIC_DIR / "therapy.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
    )


def _no_cache_headers(allow_iframe: bool = False) -> dict:
    headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    if allow_iframe:
        # Permite que Wix (u otros orígenes) embeba la página en un iframe
        headers["X-Frame-Options"] = "ALLOWALL"
        headers["Content-Security-Policy"] = "frame-ancestors *"
    return headers


@app.get("/", include_in_schema=False)
async def root_landing() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "index.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/landing", include_in_schema=False)
async def landing_page() -> FileResponse:
    """Landing page optimizada para embed en Wix (sin nav/footer duplicados)."""
    return FileResponse(THERAPY_STATIC_DIR / "landing.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/intake", include_in_schema=False)
async def intake_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "intake.html", headers=_no_cache_headers())


@app.get("/terapeuta", include_in_schema=False)
async def terapeuta_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "terapeuta.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/alumno", include_in_schema=False)
async def alumno_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "alumno.html", headers=_no_cache_headers())


@app.get("/pares", include_in_schema=False)
async def pares_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "pares.html", headers=_no_cache_headers())


@app.get("/tablas", include_in_schema=False)
async def tablas_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "tablas.html", headers=_no_cache_headers())


@app.get("/api/pares-db", include_in_schema=False)
async def pares_db():
    """Sirve la base de datos completa de pares biomagnéticos."""
    import json as _json
    db_path = BASE_DIR / "data" / "biomagnetic_pairs_db.json"
    if not db_path.exists():
        return {"ok": False, "pairs": []}
    with open(db_path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/conflictologia-db", include_in_schema=False)
async def conflictologia_db():
    """Sirve la base de datos de conflictología psicosomática por sistema."""
    import json as _json
    db_path = BASE_DIR / "data" / "conflictologia_db.json"
    if not db_path.exists():
        return {"ok": False, "systems": {}}
    with open(db_path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/tablas-images", include_in_schema=False)
async def tablas_images_manifest():
    """Sirve el manifest de imágenes de tablas de rastreo."""
    import json as _json
    manifest_path = BASE_DIR / "data" / "tablas_images" / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "categories": {}}
    with open(manifest_path, encoding="utf-8") as f:
        data = _json.load(f)
    return {"ok": True, "categories": data}


@app.get("/api/pares-clasificacion", include_in_schema=False)
async def pares_clasificacion():
    """Sirve clasificación por par (tipo + patógeno + enfermedades + transmisión)."""
    import json as _json
    path = BASE_DIR / "data" / "pares_clasificacion.json"
    if not path.exists():
        return {"ok": False, "clasificaciones": []}
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/pares-fichas-mapping", include_in_schema=False)
async def pares_fichas_mapping():
    """Sirve el mapeo de fichas Symbelia (ficha PNG ↔ par DB)."""
    import json as _json
    path = BASE_DIR / "data" / "fichas_mapping.json"
    if not path.exists():
        return {"ok": False, "mappings": []}
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/point-to-maps", include_in_schema=False)
async def point_to_maps():
    """Sirve el índice de PUNTO → mapa anatómico (donde está cada órgano/punto)."""
    import json as _json
    path = BASE_DIR / "data" / "point_to_maps.json"
    if not path.exists():
        return {"ok": False, "puntos": {}}
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/pares-lista-completa", include_in_schema=False)
async def pares_lista_completa():
    """Sirve la lista maestra ordenada por bloques (con matriz de análisis por par)."""
    import json as _json
    path = BASE_DIR / "data" / "lista_pares_completa.json"
    if not path.exists():
        return {"ok": False, "entries": []}
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)
    return data


@app.get("/api/fichas/{ficha_filename}", include_in_schema=False)
async def get_ficha(ficha_filename: str):
    """Sirve una ficha individual aprobada (PNG)."""
    from fastapi import HTTPException
    safe = ficha_filename.replace("..", "").replace("/", "").replace("\\", "")
    if not safe.endswith(".png"):
        raise HTTPException(404, "Not found")
    path = BASE_DIR / "data" / "fichas_pares" / safe
    if not path.exists():
        raise HTTPException(404, "Ficha no encontrada")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/mapas-anatomicos/{zone_filename}", include_in_schema=False)
async def get_mapa_anatomico(zone_filename: str):
    """Sirve un mapa anatómico por zona (PNG)."""
    from fastapi import HTTPException
    safe = zone_filename.replace("..", "").replace("/", "").replace("\\", "")
    if not safe.endswith(".png"):
        raise HTTPException(404, "Not found")
    path = BASE_DIR / "data" / "mapas_anatomicos" / safe
    if not path.exists():
        raise HTTPException(404, "Mapa no encontrado")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/pares-thumbnails/{thumb_filename}", include_in_schema=False)
async def get_thumbnail(thumb_filename: str):
    """Sirve un thumbnail por par (PNG)."""
    from fastapi import HTTPException
    safe = thumb_filename.replace("..", "").replace("/", "").replace("\\", "")
    if not safe.endswith(".png"):
        raise HTTPException(404, "Not found")
    path = BASE_DIR / "data" / "thumbnails" / safe
    if not path.exists():
        raise HTTPException(404, "Thumbnail no encontrado")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/rastreo", include_in_schema=False)
async def rastreo_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "rastreo.html", headers=_no_cache_headers())


# ── Astrolog iA ────────────────────────────────────────────────────────────────

@app.get("/astro", include_in_schema=False)
async def astro_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "astro.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/astro-home", include_in_schema=False)
async def astro_home_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "astro-home.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/sinastria", include_in_schema=False)
async def sinastria_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "sinastria.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/transitos", include_in_schema=False)
async def transitos_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "transitos.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/progresiones", include_in_schema=False)
async def progresiones_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "progresiones.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/salud", include_in_schema=False)
async def salud_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "salud.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/numerologia", include_in_schema=False)
async def numerologia_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "numerologia.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/holograma", include_in_schema=False)
async def holograma_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "holograma.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/eft-pro", include_in_schema=False)
async def eft_pro_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "eft-pro.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/creencias", include_in_schema=False)
async def creencias_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "creencias.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/api/creencias/inventario", include_in_schema=False)
async def api_creencias_inventario():
    """Inventario de 100 creencias del Método Lavín."""
    import json as _json
    from fastapi.responses import JSONResponse
    inv_path = THERAPY_STATIC_DIR.parent.parent / "data" / "creencias_inventario.json"
    try:
        with open(inv_path, encoding="utf-8") as f:
            return JSONResponse(_json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)


@app.get("/api/holograma/tablas", include_in_schema=False)
async def holograma_tablas():
    """Tablas de rastreo del Método Lavín (emociones, capas embrionarias, chakras, meridianos, hormonas, cromosomas, microbios)."""
    import json as _json
    from fastapi.responses import JSONResponse
    tablas_path = THERAPY_STATIC_DIR.parent.parent / "data" / "holograma_tablas.json"
    try:
        with open(tablas_path, encoding="utf-8") as f:
            return JSONResponse(_json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "tablas_not_found"}, status_code=404)


@app.get("/emociones-atrapadas", include_in_schema=False)
async def emociones_atrapadas_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "emociones-atrapadas.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/api/emociones/tabla", include_in_schema=False)
async def api_emociones_tabla():
    """Tabla de las 60 emociones atrapadas del Código de la Emoción (Bradley Nelson)."""
    import json as _json
    from fastapi.responses import JSONResponse
    p = THERAPY_STATIC_DIR.parent.parent / "data" / "emociones_atrapadas.json"
    try:
        with open(p, encoding="utf-8") as f:
            return JSONResponse(_json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)


@app.get("/api/vortices/catalogo", include_in_schema=False)
async def api_vortices_catalogo():
    """Catálogo de puntos vórtice para terapia biomagnética avanzada."""
    from fastapi.responses import Response
    p = THERAPY_STATIC_DIR.parent.parent / "data" / "vortices_db.json"
    if not p.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Catálogo de vórtices no encontrado")
    return Response(
        content=p.read_bytes(),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/pares/catalogo", include_in_schema=False)
async def api_pares_catalogo():
    """Catálogo de pares biomagnéticos del Motor HoloacademIA."""
    from fastapi.responses import Response
    p = THERAPY_STATIC_DIR.parent.parent / "data" / "pares_biomagneticos.json"
    if not p.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Catálogo de pares no encontrado")
    return Response(
        content=p.read_bytes(),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/guia-clinica", include_in_schema=False)
async def guia_clinica_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "guia-clinica.html", headers=_no_cache_headers(allow_iframe=True))


@app.get("/api/guia-clinica/datos", include_in_schema=False)
async def api_guia_clinica():
    """Guía clínica del terapeuta · Módulo 6 Terapéutica · Método Lavín."""
    import json as _json
    from fastapi.responses import JSONResponse
    p = THERAPY_STATIC_DIR.parent.parent / "data" / "guia_clinica.json"
    try:
        with open(p, encoding="utf-8") as f:
            return JSONResponse(_json.load(f))
    except FileNotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)


@app.get("/tarot", include_in_schema=False)
async def tarot_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "tarot.html", headers=_no_cache_headers(allow_iframe=True))

@app.get("/horoscopo", include_in_schema=False)
async def horoscopo_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "horoscopo.html", headers=_no_cache_headers(allow_iframe=True))


# ── Legacy routes (mantener compatibilidad) ────────────────────────────────────

@app.get("/therapy", include_in_schema=False)
async def therapy_root_redirect() -> FileResponse:
    return _therapy_app_response()


@app.get("/therapy/app")
async def therapy_app() -> FileResponse:
    return _therapy_app_response()


@app.get("/index.html", include_in_schema=False)
async def therapy_index_html() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "index.html", headers=_no_cache_headers())


# ── Nuevo endpoint de chat con streaming ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list)
    mode: str = Field(default="alumno")


# ── Endpoints de uso ───────────────────────────────────────────────────────────

@app.get("/api/usage", include_in_schema=False)
async def api_usage(request: Request):
    """Devuelve el uso mensual del usuario actual (para mostrar el contador en la UI)."""
    from fastapi.responses import JSONResponse
    sess = _get_session_user(request)
    if not sess:
        return JSONResponse({"error": "no_session"}, status_code=401)
    user_id, _plan = sess
    return JSONResponse(get_usage(_DB_PATH, user_id))


# ── Chat con streaming + control de límites ────────────────────────────────────

def _usage_blocked_stream(used: int, limit: int, plan: str):
    """SSE stream que notifica al cliente que el límite mensual fue alcanzado."""
    plan_name = PLAN_NAMES.get(plan, plan)
    msg = (
        f"⛔ **Límite mensual alcanzado**\n\n"
        f"Has usado {used} de {limit} sesiones de este mes en tu plan **{plan_name}**.\n\n"
        f"Actualiza tu suscripción en Holoacademia para continuar."
    )
    import json
    yield f"data: {json.dumps({'token': msg})}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/chat", include_in_schema=False)
async def chat_endpoint(request: Request, payload: ChatRequest) -> StreamingResponse:
    mode = payload.mode if payload.mode in ("terapeuta", "alumno", "pares") else "alumno"

    # Verificar límite solo en el primer mensaje de la sesión (history vacío)
    if not payload.history and _EMBED_SECRET:
        sess = _get_session_user(request)
        if sess:
            user_id, plan = sess
            allowed, used, limit = try_consume(_DB_PATH, user_id, mode)
            if not allowed:
                return StreamingResponse(
                    _usage_blocked_stream(used, limit, plan),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

    return StreamingResponse(
        stream_chat(payload.message, payload.history, mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/cv")
async def cv_app() -> FileResponse:
    return FileResponse(THERAPY_STATIC_DIR / "cv.html")


@app.get("/therapy/logo")
async def therapy_logo() -> FileResponse:
    return FileResponse(THERAPY_LOGO_PATH)


@app.post("/therapy/analyze", response_model=TherapyAnalyzeResponse)
async def therapy_analyze(payload: TherapyAnalyzeRequest) -> TherapyAnalyzeResponse:
    analysis = analyze_case(payload.case_payload.model_dump())
    return TherapyAnalyzeResponse(ok=True, analysis=analysis)


@app.post("/therapy/pairs", response_model=TherapyPairsResponse)
async def therapy_pairs(payload: TherapyPairsRequest) -> TherapyPairsResponse:
    case_payload_dict = payload.case_payload.model_dump()
    case_analysis = payload.analysis or analyze_case(case_payload_dict)
    pairs_payload = [item.model_dump() for item in payload.pairs]
    pair_analysis = interpret_pairs(case_analysis, pairs_payload)
    pair_analysis["radionic_pair_table"] = build_radionic_pair_table(
        case_payload_dict,
        [item.get("pair_name", "") for item in pair_analysis.get("interpreted_pairs", [])],
        title="Tabla radiónica para pares interpretados",
    )
    pair_analysis["reasoning_state"] = build_therapy_reasoning(
        case_payload=case_payload_dict,
        case_analysis=case_analysis,
        pair_analysis=pair_analysis,
    )
    pair_analysis["case_analysis"] = case_analysis
    return TherapyPairsResponse(ok=True, pair_analysis=_rewrite_visual_asset_paths(pair_analysis))


@app.post("/therapy/report", response_model=TherapyReportResponse)
async def therapy_report(payload: TherapyReportRequest) -> TherapyReportResponse:
    case_payload_dict = payload.case_payload.model_dump()
    pairs_payload = [item.model_dump() for item in payload.pairs]
    report = build_therapy_report(
        case_payload=case_payload_dict,
        pairs_input=pairs_payload,
        precomputed_case_analysis=payload.precomputed_case_analysis or payload.analysis,
        precomputed_pair_analysis=payload.precomputed_pair_analysis or payload.pair_analysis,
    )
    return TherapyReportResponse(ok=True, report=_rewrite_visual_asset_paths(report))


@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    kb = get_knowledge_base()
    assistant = get_assistant()

    merged_by_chunk = {}
    skip_search = assistant.should_skip_search(payload.question, payload.history)

    if not skip_search:
        search_queries = assistant.resolve_search_queries(payload.question, payload.history)

        per_query_limit = max(payload.max_results * 3, 8)
        use_semantic_search = kb.semantic_ready and getattr(assistant, "can_embed_queries", lambda: False)()

        for search_query in search_queries:
            partial_results = []

            lexical_results = kb.search(
                question=search_query,
                course_id=payload.course_id,
                linea=payload.linea,
                limit=per_query_limit,
            )
            partial_results.extend(lexical_results)

            if use_semantic_search:
                try:
                    query_vector = assistant.embed_query(search_query)
                    semantic_results = kb.semantic_search_by_vector(
                        query_vector=query_vector,
                        course_id=payload.course_id,
                        linea=payload.linea,
                        limit=per_query_limit,
                    )
                    partial_results.extend(semantic_results)
                except Exception:
                    pass

            for item in partial_results:
                existing = merged_by_chunk.get(item.chunk_id)
                if existing is None or item.score > existing.score:
                    merged_by_chunk[item.chunk_id] = item

    results = sorted(
        merged_by_chunk.values(),
        key=lambda item: item.score,
        reverse=True,
    )[: payload.max_results]

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
