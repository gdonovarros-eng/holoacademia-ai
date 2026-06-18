#!/usr/bin/env python3
"""Ingesta del conocimiento de HoloacademIA a Supabase (pgvector).

Es la tubería única para alimentar el Sinodal y el Motor Terapéutico. No depende
de la computadora: escribe a Supabase, que vive en la nube.

Uso:
  # 1) Migrar lo que YA está embebido (8,825 chunks) reusando sus vectores:
  python scripts/ingest_holos.py migrate \
      --chunks data/chunks/library_chunks.jsonl \
      --vectors data/embeddings/library_vectors.npy

  # 2) Alimentar un curso NUEVO desde transcripciones (.txt / .md):
  python scripts/ingest_holos.py ingest \
      --dir "ruta/a/transcripciones_del_curso" \
      --course-name "Curso Medicina China 2024" \
      --course-id curso-medicina-china-2024 \
      --source-type transcripcion

Variables de entorno necesarias:
  KNOWLEDGE_DB_URL   Connection string (URI) de Supabase  (Settings → Database)
  OPENAI_API_KEY    Para embeddings de contenido nuevo (text-embedding-3-small)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
BATCH = 256


def _db():
    import psycopg2
    url = os.getenv("KNOWLEDGE_DB_URL", "").strip()
    if not url:
        sys.exit("Falta KNOWLEDGE_DB_URL (Settings → Database → Connection string).")
    return psycopg2.connect(url)


def _openai():
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        sys.exit("Falta OPENAI_API_KEY para generar embeddings.")
    return OpenAI(api_key=key)


def _vec_literal(vec) -> str:
    """pgvector acepta el formato '[0.1,0.2,...]' como texto."""
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


def _upsert(cur, rows):
    """rows: list de (campos..., embedding_literal_or_None)."""
    from psycopg2.extras import execute_values
    sql = """
        insert into holos_chunks
          (chunk_id, course_id, course_name, linea, tipo, audiencia, idioma,
           source_id, source_type, source_file, heading, text, char_count, embedding)
        values %s
        on conflict (chunk_id) do update set
          course_id=excluded.course_id, course_name=excluded.course_name,
          linea=excluded.linea, tipo=excluded.tipo, audiencia=excluded.audiencia,
          idioma=excluded.idioma, source_id=excluded.source_id,
          source_type=excluded.source_type, source_file=excluded.source_file,
          heading=excluded.heading, text=excluded.text, char_count=excluded.char_count,
          embedding=coalesce(excluded.embedding, holos_chunks.embedding)
    """
    template = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)"
    execute_values(cur, sql, rows, template=template, page_size=BATCH)


# ── Modo migrate: reusa los vectores ya calculados ──────────────────────────
def migrate(args):
    import numpy as np
    chunks_path = Path(args.chunks)
    vectors = np.load(args.vectors, mmap_mode="r") if args.vectors else None
    if vectors is not None and vectors.shape[1] != EMBED_DIM:
        sys.exit(f"Dimensión inesperada en vectores: {vectors.shape}")

    conn = _db(); cur = conn.cursor()
    total = 0; buf = []
    with chunks_path.open() as fh:
        for i, line in enumerate(fh):
            d = json.loads(line)
            emb = _vec_literal(vectors[i]) if vectors is not None else None
            buf.append((
                d["chunk_id"], d.get("course_id"), d.get("course_name"),
                d.get("linea"), d.get("tipo"), d.get("audiencia"), d.get("idioma", "es"),
                d.get("source_id"), d.get("source_type"), d.get("source_file"),
                d.get("heading"), d["text"], d.get("char_count"), emb,
            ))
            if len(buf) >= BATCH:
                _upsert(cur, buf); conn.commit(); total += len(buf); buf = []
                print(f"  migrados {total}…", flush=True)
    if buf:
        _upsert(cur, buf); conn.commit(); total += len(buf)
    cur.close(); conn.close()
    print(f"Listo: {total} chunks migrados a Supabase (sin re-embeber).")


# ── Modo ingest: contenido nuevo desde transcripciones ──────────────────────
def _chunk_text(text: str, target=1400, overlap=150):
    """Trozos por párrafos, ~1400 chars, con solape para no cortar ideas."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= target:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
            cur = (cur[-overlap:] + "\n\n" + p) if cur else p
            while len(cur) > target * 1.5:
                chunks.append(cur[:target]); cur = cur[target - overlap:]
    if cur:
        chunks.append(cur)
    return chunks


def ingest(args):
    src_dir = Path(args.dir)
    files = sorted([p for p in src_dir.rglob("*") if p.suffix.lower() in (".txt", ".md")])
    if not files:
        sys.exit(f"No encontré .txt/.md en {src_dir}")
    client = _openai()
    conn = _db(); cur = conn.cursor()

    records = []
    for si, fp in enumerate(files, 1):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        source_id = f"{args.course_id}-source-{si:03d}"
        for ci, chunk in enumerate(_chunk_text(text)):
            records.append({
                "chunk_id": f"{args.course_id}::{source_id}::{ci:04d}",
                "course_id": args.course_id, "course_name": args.course_name,
                "linea": args.linea, "tipo": args.tipo, "audiencia": args.audiencia,
                "idioma": "es", "source_id": source_id, "source_type": args.source_type,
                "source_file": fp.name, "heading": fp.stem, "text": chunk,
                "char_count": len(chunk),
            })
    print(f"{len(records)} chunks desde {len(files)} archivos. Embebiendo…", flush=True)

    total = 0
    for start in range(0, len(records), BATCH):
        batch = records[start:start + BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=[r["text"] for r in batch])
        rows = []
        for r, e in zip(batch, resp.data):
            rows.append((
                r["chunk_id"], r["course_id"], r["course_name"], r["linea"], r["tipo"],
                r["audiencia"], r["idioma"], r["source_id"], r["source_type"],
                r["source_file"], r["heading"], r["text"], r["char_count"],
                _vec_literal(e.embedding),
            ))
        _upsert(cur, rows); conn.commit(); total += len(rows)
        print(f"  ingeridos {total}/{len(records)}…", flush=True)
    cur.close(); conn.close()
    print(f"Listo: '{args.course_name}' ingerido ({total} chunks) y disponible para los motores.")


def main():
    ap = argparse.ArgumentParser(description="Ingesta de conocimiento HoloacademIA → Supabase")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("migrate", help="Migrar chunks ya embebidos reusando sus vectores")
    m.add_argument("--chunks", default="data/chunks/library_chunks.jsonl")
    m.add_argument("--vectors", default="data/embeddings/library_vectors.npy")
    m.set_defaults(func=migrate)

    g = sub.add_parser("ingest", help="Ingerir un curso nuevo desde transcripciones")
    g.add_argument("--dir", required=True)
    g.add_argument("--course-name", required=True, dest="course_name")
    g.add_argument("--course-id", required=True, dest="course_id")
    g.add_argument("--linea", default="Cursos")
    g.add_argument("--tipo", default="Curso")
    g.add_argument("--audiencia", default="Alumnos")
    g.add_argument("--source-type", default="transcripcion", dest="source_type")
    g.set_defaults(func=ingest)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
