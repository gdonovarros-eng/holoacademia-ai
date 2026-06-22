from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel

from api.schemas.therapeutic import TherapeuticRequest, TherapeuticResponse
from api.services.therapeutic_service import run_therapeutic_analysis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/therapeutic", tags=["Therapeutic"])


class HolosRequest(BaseModel):
    prompt: str
    # Consulta opcional para recuperar material propio (RAG). Si viene, se
    # buscan fragmentos relevantes y se inyectan al prompt con prioridad.
    query: str | None = None


class HolosResponse(BaseModel):
    answer: str
    ok: bool = True
    error: str | None = None
    fuentes: int = 0


def _inyectar_material(prompt: str, query: str | None) -> tuple[str, int]:
    """Recupera material propio relevante y lo antepone al prompt con prioridad.
    Motor propio: instruye no citar cursos ni autores. Si no hay material o el
    RAG no está disponible, devuelve el prompt sin cambios."""
    if not query:
        return prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(query, k=10)
        ctx = format_context(chunks, max_chars=8000)
    except Exception:  # nunca romper la respuesta por el RAG
        return prompt, 0
    if not ctx:
        return prompt, 0
    prefijo = (
        "MATERIAL PROPIO DE REFERENCIA. Cuando sea pertinente a la pregunta, da PRIORIDAD a estos "
        "fragmentos sobre tu conocimiento general y respeta sus definiciones y enfoque. "
        "Si un fragmento NO es relevante a lo que se pregunta, ignóralo: responde SIEMPRE a la "
        "pregunta concreta, no resumas el material. "
        "NUNCA menciones cursos, autores, maestros ni nombres propios que aparezcan en el material; "
        "intégralo como conocimiento propio.\n\n" + ctx + "\n\n====\n\n"
    )
    return prefijo + prompt, len(chunks)


class BiodescoRequest(BaseModel):
    prompt: str
    query: str | None = None


# El motor dedicado se ancla SOLO en el corpus de libros de biodescodificación.
_BIODESCO_COURSE_IDS = ["libros-biodescodificacion"]


@router.post("/biodescodificacion", response_model=HolosResponse)
def motor_biodescodificacion(request: BiodescoRequest) -> HolosResponse:
    """Motor dedicado de Biodescodificación: razona en clave de descodificación
    biológica, anclado únicamente en el corpus de libros de biodescodificación."""
    from api.chat_service import generar_respuesta_biodescodificacion

    started = time.monotonic()
    q = (request.query or request.prompt or "").strip()
    prompt, fuentes = request.prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        # Recuperación separada: material de biodescodificación y material de NMG,
        # para alimentar cada una de las dos lecturas.
        bio = retrieve(q, k=10, course_ids=["libros-biodescodificacion"])
        nmg = retrieve(q, k=10, course_ids=["libros-nmg"])
        ctx_bio = format_context(bio, max_chars=7000)
        ctx_nmg = format_context(nmg, max_chars=7000)
        fuentes = len(bio) + len(nmg)
        if ctx_bio or ctx_nmg:
            prompt = (
                "MATERIAL DE BIODESCODIFICACIÓN (para la Lectura de Biodescodificación):\n\n"
                + (ctx_bio or "(sin material específico; usa tu marco)") +
                "\n\n========\n\nMATERIAL DE NUEVA MEDICINA GERMÁNICA / 5 LEYES (para la segunda lectura):\n\n"
                + (ctx_nmg or "(sin material específico; usa tu marco)") +
                "\n\n========\n\nNunca menciones autores, libros ni cursos que aparezcan en el material.\n\n"
                + request.prompt
            )
    except Exception:
        pass
    result = generar_respuesta_biodescodificacion(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("biodescodificacion elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


_BIOMAG_COURSE_IDS = [
    "curso-holobiomagnetismo-parte-1", "curso-holobiomagnetismo-parte-2",
    "curso-holobiomagnetismo-2021", "curso-holobiomagnetismo-2021-transcripcion",
    "libros-biomagnetismo",
]

_HERBOLARIA_COURSE_IDS = [
    "libros-flores-bach", "libros-elixires-aztecas", "libros-herbolaria-mexicana",
    "libros-fitoterapia", "libros-herbolaria-tradicional",
]


@router.post("/herbolaria", response_model=HolosResponse)
def motor_herbolaria(request: BiodescoRequest) -> HolosResponse:
    """Motor dedicado de Herbolaria/Fitoterapia/Terapia floral, anclado al corpus herbal."""
    from api.chat_service import generar_respuesta_herbolaria

    started = time.monotonic()
    q = (request.query or request.prompt or "").strip()
    prompt, fuentes = request.prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=14, course_ids=_HERBOLARIA_COURSE_IDS)
        ctx = format_context(chunks, max_chars=11000)
        if ctx:
            prompt = (
                "MATERIAL DE HERBOLARIA Y FITOTERAPIA (base prioritaria; respeta sus plantas, "
                "preparaciones, dosis y contraindicaciones; nunca menciones autores, libros ni "
                "cursos que aparezcan en él):\n\n" + ctx + "\n\n====\n\n" + request.prompt
            )
            fuentes = len(chunks)
    except Exception:
        pass
    result = generar_respuesta_herbolaria(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("herbolaria elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


@router.post("/biomagnetismo", response_model=HolosResponse)
def motor_biomagnetismo(request: BiodescoRequest) -> HolosResponse:
    """Motor dedicado de Biomagnetismo: razona en clave de par biomagnético y
    rastreo, anclado únicamente en el corpus de biomagnetismo."""
    from api.chat_service import generar_respuesta_biomagnetismo

    started = time.monotonic()
    q = (request.query or request.prompt or "").strip()
    prompt, fuentes = request.prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=14, course_ids=_BIOMAG_COURSE_IDS)
        ctx = format_context(chunks, max_chars=11000)
        if ctx:
            prompt = (
                "MATERIAL DE BIOMAGNETISMO (base prioritaria; respeta sus pares, polos y "
                "ubicaciones; nunca menciones autores, libros ni cursos que aparezcan en él):\n\n"
                + ctx + "\n\n====\n\n" + request.prompt
            )
            fuentes = len(chunks)
    except Exception:
        pass
    result = generar_respuesta_biomagnetismo(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("biomagnetismo elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


@router.post("/constelaciones", response_model=HolosResponse)
def motor_constelaciones(request: BiodescoRequest) -> HolosResponse:
    """Motor dedicado de Constelaciones Familiares y Transgeneracional, anclado
    en su corpus (Órdenes del Amor, dinámicas sistémicas, psicogenealogía)."""
    from api.chat_service import generar_respuesta_constelaciones

    started = time.monotonic()
    q = (request.query or request.prompt or "").strip()
    prompt, fuentes = request.prompt, 0
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=14, course_ids=["libros-constelaciones"])
        ctx = format_context(chunks, max_chars=11000)
        if ctx:
            prompt = (
                "MATERIAL DE CONSTELACIONES FAMILIARES Y TRANSGENERACIONAL (base prioritaria; "
                "de aquí extraes las dinámicas, frases sanadoras y ejercicios; nunca menciones "
                "autores, libros ni cursos que aparezcan en él):\n\n"
                + ctx + "\n\n====\n\n" + request.prompt
            )
            fuentes = len(chunks)
    except Exception:
        pass
    result = generar_respuesta_constelaciones(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("constelaciones elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


class HerramientaRequest(BaseModel):
    funcion: str          # protocolo | ejercicios | diccionario | frases
    query: str


_FUNC_INSTR = {
    "protocolo": (
        "Genera un PROTOCOLO de trabajo sistémico/transgeneracional paso a paso para el "
        "tema o caso indicado. Estructura con ##: ## Objetivo terapéutico ## Fases o sesiones "
        "(cada una con sus pasos, qué representar/constelar y en qué orden) ## Frases clave por "
        "fase ## Señales de avance y cierre. Concreto y accionable."
    ),
    "ejercicios": (
        "Propón de 4 a 6 EJERCICIOS concretos para el tema (psicogenealogía, movimientos "
        "sistémicos, rituales de reconexión, trabajo con representantes o muñecos). Para cada uno, "
        "con ###: nombre del ejercicio, para qué sirve, y cómo se hace paso a paso."
    ),
    "diccionario": (
        "Define el término o concepto en clave de constelaciones familiares y transgeneracional. "
        "Estructura con ##: ## Definición ## De dónde viene y para qué sirve ## Cómo se reconoce "
        "en un caso ## Ejemplo claro. Preciso y didáctico."
    ),
    "frases": (
        "Entrega FRASES SANADORAS para la situación indicada, agrupadas por intención con ### "
        "(reconocimiento, honra a los que vinieron antes, tomar el lugar, pertenencia, despedida y "
        "orden). De 3 a 5 frases por grupo, listas para decir en sesión."
    ),
}


@router.post("/herramienta", response_model=HolosResponse)
def herramienta_constelaciones(request: HerramientaRequest) -> HolosResponse:
    """Herramientas del workspace de Constelaciones: protocolo, ejercicios,
    diccionario y frases sanadoras, ancladas en el corpus."""
    from api.chat_service import _generar_con_sistema, CONSTELACIONES_SYSTEM_PROMPT

    started = time.monotonic()
    funcion = (request.funcion or "").strip().lower()
    q = (request.query or "").strip()
    instr = _FUNC_INSTR.get(funcion)
    if not instr or not q:
        return HolosResponse(answer="", ok=False, error="parametros_invalidos")

    fuentes = 0
    ctx = ""
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=12, course_ids=["libros-constelaciones"])
        ctx = format_context(chunks, max_chars=9000)
        fuentes = len(chunks)
    except Exception:
        pass

    prompt = (
        instr + "\n\n"
        + (f"MATERIAL DE REFERENCIA (no menciones autores ni libros):\n\n{ctx}\n\n========\n\n" if ctx else "")
        + f"TEMA / CONSULTA: {q}"
    )
    result = _generar_con_sistema(CONSTELACIONES_SYSTEM_PROMPT, prompt, f"Constel-{funcion}", 0.45, max_tokens=4500)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("constel_herramienta=%s elapsed_ms=%.2f ok=%s fuentes=%d", funcion, elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


class GenogramaRequest(BaseModel):
    datos: dict[str, str] = {}
    motivo: str | None = None


@router.post("/genograma", response_model=HolosResponse)
def motor_genograma(request: GenogramaRequest) -> HolosResponse:
    """Lee un genograma capturado en el formulario y devuelve análisis sistémico,
    raíz transgeneracional, protocolo de trabajo y ejercicios."""
    from api.chat_service import generar_genograma

    started = time.monotonic()
    datos = {k: v for k, v in (request.datos or {}).items() if v and str(v).strip()}
    motivo = (request.motivo or "").strip()
    sistema = "\n".join(f"- {k}: {v}" for k, v in datos.items()) or "(sin datos capturados)"
    q = (motivo + " " + " ".join(list(datos.values())[:6]))[:400].strip() \
        or "genograma transgeneracional lealtad invisible exclusión síndrome de aniversario"

    fuentes = 0
    ctx = ""
    try:
        from api.holos_rag import retrieve, format_context
        chunks = retrieve(q, k=12, course_ids=["libros-constelaciones"])
        ctx = format_context(chunks, max_chars=9000)
        fuentes = len(chunks)
    except Exception:
        pass

    prompt = (
        (f"MATERIAL DE CONSTELACIONES Y TRANSGENERACIONAL (base para dinámicas, protocolos, "
         f"ejercicios y frases; no menciones autores ni libros):\n\n{ctx}\n\n========\n\n" if ctx else "")
        + f"MOTIVO / SÍNTOMA DEL CONSULTANTE: {motivo or '(no especificado)'}\n\n"
        + f"SISTEMA FAMILIAR (GENOGRAMA) DEL CONSULTANTE:\n{sistema}"
    )
    result = generar_genograma(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("genograma elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


@router.get("/rag-status")
def rag_status() -> dict:
    """Diagnóstico del RAG: backend (neon/local) y conteo de chunks."""
    from api.holos_rag import status
    return status()


@router.post("/holos", response_model=HolosResponse)
def generar_cuadro_holos(request: HolosRequest) -> HolosResponse:
    """Genera el Cuadro Holos con razonamiento terapéutico libre (no pasa por
    el motor académico). Si llega `query`, se ancla en el material propio (RAG)."""
    from api.chat_service import generar_respuesta_holos

    started = time.monotonic()
    prompt, fuentes = _inyectar_material(request.prompt, request.query)
    result = generar_respuesta_holos(prompt)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info("therapeutic_holos elapsed_ms=%.2f ok=%s fuentes=%d", elapsed_ms, bool(result.get("ok")), fuentes)
    return HolosResponse(fuentes=fuentes, **result)


@router.post("/analyze", response_model=TherapeuticResponse)
def analyze_case(request: TherapeuticRequest) -> TherapeuticResponse:
    started = time.monotonic()
    data = request.model_dump(exclude_none=True)
    result = run_therapeutic_analysis(data)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "therapeutic_analyze elapsed_ms=%.2f error=%s",
        elapsed_ms,
        bool(result.get("trace", {}).get("error")),
    )
    return TherapeuticResponse(**result)
