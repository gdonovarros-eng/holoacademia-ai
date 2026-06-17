"""Recuperación híbrida del conocimiento de HoloacademIA desde Supabase.

Fuente única para el Sinodal y el Motor Terapéutico. Combina búsqueda semántica
(pgvector) y por palabra clave (full-text), vía la función SQL match_holos.

Diseño seguro: si faltan SUPABASE_DB_URL u OPENAI_API_KEY, retrieve() devuelve []
sin romper nada. Así el deploy sigue vivo aunque el RAG no esté configurado todavía.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger("holos_rag")

EMBED_MODEL = os.getenv("HOLOS_EMBED_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small"


def rag_enabled() -> bool:
    return bool(os.getenv("SUPABASE_DB_URL", "").strip())


@lru_cache(maxsize=1)
def _pool():
    """Pool de conexiones a Supabase (perezoso). None si no está configurado."""
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not url:
        return None
    try:
        from psycopg2.pool import SimpleConnectionPool
        return SimpleConnectionPool(1, 4, dsn=url)
    except Exception as exc:  # pragma: no cover
        logger.error("No se pudo abrir el pool a Supabase: %s", exc)
        return None


@lru_cache(maxsize=1)
def _embed_client():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception as exc:  # pragma: no cover
        logger.error("No se pudo crear el cliente de embeddings: %s", exc)
        return None


def _embed_vector(query: str):
    """Embebe la consulta y devuelve la lista de floats (o None si no se puede)."""
    client = _embed_client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(model=EMBED_MODEL, input=query[:8000])
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding de consulta falló (sigo con palabra clave): %s", exc)
        return None


def _embed(query: str):
    """Versión literal para pgvector (Supabase)."""
    vec = _embed_vector(query)
    if vec is None:
        return None
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


def retrieve(query: str, k: int = 6, course_ids: list[str] | None = None) -> list[dict]:
    """Devuelve los fragmentos más relevantes del material propio.

    Funciona híbrido: si hay embeddings, semántica + palabra clave; si no hay
    key de embeddings, cae a solo palabra clave. [] si no hay nada configurado.
    """
    query = (query or "").strip()
    if not query:
        return []
    if not rag_enabled():
        return _retrieve_local(query, k, course_ids)
    pool = _pool()
    if pool is None:
        return _retrieve_local(query, k, course_ids)
    emb = _embed(query)  # puede ser None → la función SQL usa solo full-text
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                "select chunk_id, course_name, source_file, heading, text, score "
                "from match_holos(%s::vector, %s, %s, %s, %s, %s, %s)",
                (emb, query, k, 1.0, 1.0, 50, course_ids),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as exc:
        logger.error("Búsqueda en Supabase falló: %s", exc)
        return []
    finally:
        if conn is not None:
            pool.putconn(conn)


def _sr_to_dict(r, score: float) -> dict:
    return {
        "chunk_id": r.chunk_id, "course_name": r.course_name,
        "source_file": r.source_file, "heading": r.heading,
        "text": r.text, "score": float(score),
    }


def _merge_rrf(lex: list, sem: list, k: int, rrf_k: int = 50) -> list[dict]:
    """Reciprocal Rank Fusion: combina los dos rankings sin que una escala
    aplaste a la otra. Cada lista aporta 1/(rrf_k + posición)."""
    acc: dict[str, dict] = {}
    for rank, r in enumerate(lex, 1):
        acc.setdefault(r.chunk_id, {"r": r, "s": 0.0})["s"] += 1.0 / (rrf_k + rank)
    for rank, r in enumerate(sem, 1):
        acc.setdefault(r.chunk_id, {"r": r, "s": 0.0})["s"] += 1.0 / (rrf_k + rank)
    ordered = sorted(acc.values(), key=lambda x: x["s"], reverse=True)[:k]
    return [_sr_to_dict(x["r"], x["s"]) for x in ordered]


def _retrieve_local(query: str, k: int, course_ids: list[str] | None) -> list[dict]:
    """Búsqueda HÍBRIDA en el proceso, sobre el Library KB ya desplegado:
    léxica (palabra clave) + semántica (embeddings de la consulta vs. los
    vectores cargados), fusionadas con RRF. Si no hay embeddings o numpy,
    cae a solo léxica. Sin servicio externo, sin costo de hosting."""
    try:
        from api.main import get_knowledge_base
        kb = get_knowledge_base()
    except Exception as exc:
        logger.warning("Library KB no disponible: %s", exc)
        return []
    cid = course_ids[0] if course_ids else None

    try:
        lex = kb.search(query, course_id=cid, limit=k * 3)
    except Exception as exc:
        logger.error("Búsqueda léxica falló: %s", exc)
        lex = []

    sem = []
    try:
        if getattr(kb, "semantic_ready", False):
            vec = _embed_vector(query)
            if vec is not None:
                sem = kb.semantic_search_by_vector(vec, course_id=cid, limit=k * 3)
    except Exception as exc:
        logger.warning("Búsqueda semántica falló (sigo con léxica): %s", exc)

    if not sem:
        return [_sr_to_dict(r, r.score) for r in lex[:k]]
    return _merge_rrf(lex, sem, k)


def format_context(chunks: list[dict], max_chars: int = 6000) -> str:
    """Arma el bloque de contexto para inyectar en el prompt.

    Motor propio: NO expone nombres de cursos, autores ni archivos. Solo el
    texto del material, numerado como fragmentos de referencia neutros.
    """
    if not chunks:
        return ""
    parts, used = [], 0
    for i, c in enumerate(chunks, 1):
        texto = (c.get("text") or "").strip()
        if not texto:
            continue
        bloque = f"[Fragmento {i}]\n{texto}"
        if used + len(bloque) > max_chars:
            bloque = bloque[: max(0, max_chars - used)]
        parts.append(bloque)
        used += len(bloque)
        if used >= max_chars:
            break
    return "\n\n".join(parts)
