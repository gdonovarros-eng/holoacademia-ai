#!/usr/bin/env python3
"""Ingiere libros (PDF/txt/md) DIRECTO a Neon (Postgres + pgvector).

Reusa la extracción + OCR + troceo de ingerir_libros.py, pero en vez de escribir
a los archivos locales del índice, hace upsert a Neon. Así el material nuevo
escala sin crecer en git. Guardado por libro (reanudable) e idempotente:
salta libros cuyo chunk_id ya existe en Neon.

Uso:
  KNOWLEDGE_DB_URL=... OPENAI_API_KEY=... \
  python3.14 scripts/ingerir_libros_neon.py --dir "/ruta/libros" --coleccion "Biodescodificación"
"""
from __future__ import annotations
import argparse, glob, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ingerir_libros import extraer, limpiar, trozos, _slug  # reusa extracción/OCR/troceo

EMBED_MODEL = "text-embedding-3-small"
from openai import OpenAI


def _conn():
    import psycopg2
    url = os.getenv("KNOWLEDGE_DB_URL", "").strip()
    if not url:
        sys.exit("Falta KNOWLEDGE_DB_URL")
    return psycopg2.connect(url)


def _vec(v):
    v = np.asarray(v, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
    return "[" + ",".join(f"{float(x):.7f}" for x in v) + "]"


def _upsert(cur, rows):
    from psycopg2.extras import execute_values
    sql = """insert into holos_chunks
      (chunk_id, course_id, course_name, linea, tipo, audiencia, idioma,
       source_id, source_type, source_file, heading, text, char_count, embedding)
      values %s on conflict (chunk_id) do update set
      text=excluded.text, embedding=excluded.embedding, char_count=excluded.char_count"""
    execute_values(cur, sql, rows,
        template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)", page_size=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--coleccion", required=True)
    ap.add_argument("--linea", default="Libros de referencia")
    a = ap.parse_args()

    emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    col = _slug(a.coleccion)
    conn = _conn(); conn.autocommit = False; cur = conn.cursor()

    cur.execute("select chunk_id from holos_chunks where source_type='libro' and course_id=%s",
                (f"libros-{col}",))
    existentes = {r[0] for r in cur.fetchall()}
    print(f"ya en Neon (col {col}): {len(existentes)} chunks de libros", flush=True)

    files = sorted([p for p in glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)
                    if p.lower().rsplit(".", 1)[-1] in ("pdf", "txt", "md")])
    total, hechos, vacios = 0, 0, []
    for fpath in files:
        titulo = os.path.splitext(os.path.basename(fpath))[0]
        bid = _slug(titulo)
        if f"libro-{col}::{bid}::0000" in existentes:
            print(f"= ya estaba: {titulo}", flush=True); continue
        print(f"extrayendo: {titulo}", flush=True)
        try:
            chunks = trozos(limpiar(extraer(fpath)))
        except Exception as e:
            print(f"  ! error: {e}", flush=True); continue
        if not chunks:
            vacios.append(titulo); print(f"  sin texto: {titulo}", flush=True); continue
        rows = []
        # embeber en lotes de 256
        for s in range(0, len(chunks), 256):
            part = chunks[s:s+256]
            resp = emb.embeddings.create(model=EMBED_MODEL, input=part)
            for i, (ch, e) in enumerate(zip(part, resp.data), start=s):
                rows.append((
                    f"libro-{col}::{bid}::{i:04d}", f"libros-{col}", a.coleccion,
                    a.linea, "Libro", "Terapeutas", "es", f"libro-{bid}", "libro",
                    os.path.basename(fpath), titulo, ch, len(ch), _vec(e.embedding),
                ))
        _upsert(cur, rows); conn.commit()
        total += len(rows); hechos += 1
        print(f"  + {titulo}: {len(rows)} chunks", flush=True)

    cur.execute("select count(*) from holos_chunks"); n = cur.fetchone()[0]
    cur.close(); conn.close()
    print(f"\nLISTO: {hechos} libros nuevos, +{total} chunks. Total en Neon: {n}", flush=True)
    if vacios:
        print("Sin texto: " + "; ".join(vacios), flush=True)


if __name__ == "__main__":
    main()
