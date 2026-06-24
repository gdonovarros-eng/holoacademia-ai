#!/usr/bin/env python3
"""Ingesta las transcripciones de cursos (conocimiento_sinodal) a Neon, troceando
por MÓDULO (separadores BLOQUE) y etiquetando por curso/categoría. Todo en
español, sin traducción. Idempotente y reanudable por curso.

El Sinodal recupera de toda la base sin filtro, así que con esto queda disponible.

Uso:
  python3.14 scripts/ingerir_sinodal.py --dir /tmp/sinodal/conocimiento_sinodal [--solo "NOMBRE"]
"""
from __future__ import annotations
import os, sys, re, csv, argparse, unicodedata
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from ingerir_libros import limpiar, trozos  # noqa: E402
from openai import OpenAI                     # noqa: E402

EMBED_MODEL = "text-embedding-3-small"
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

HDR = re.compile(
    r"BLOQUE:[^\n]*\nL[IÍ]NEA:\s*([^\n]*)\nCURSO:\s*([^\n]*)\nM[OÓ]DULO:\s*([^\n]*)\nFECHA[^\n]*\n",
    re.IGNORECASE)


def _slug(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:70]


def _conn():
    import psycopg2
    return psycopg2.connect(os.environ["KNOWLEDGE_DB_URL"])


def _vec(v):
    v = np.asarray(v, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
    return "[" + ",".join(f"{float(x):.7f}" for x in v) + "]"


def _strip_eq(s):
    return "\n".join(ln for ln in s.split("\n") if set(ln.strip()) != {"="}).strip()


def _bloques(texto):
    """Devuelve [(modulo, cuerpo)] partiendo por encabezados BLOQUE."""
    ms = list(HDR.finditer(texto))
    if not ms:
        return [("", texto)]
    out = []
    for i, m in enumerate(ms):
        modulo = (m.group(3) or "").strip()
        ini = m.end()
        fin = ms[i + 1].start() if i + 1 < len(ms) else len(texto)
        cuerpo = _strip_eq(texto[ini:fin])
        if len(cuerpo) > 80:
            out.append((modulo, cuerpo))
    return out


def _upsert(rows):
    from psycopg2.extras import execute_values
    sql = """insert into holos_chunks
      (chunk_id, course_id, course_name, linea, tipo, audiencia, idioma,
       source_id, source_type, source_file, heading, text, char_count, embedding)
      values %s on conflict (chunk_id) do update set
      text=excluded.text, embedding=excluded.embedding"""
    tpl = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)"
    for intento in range(2):
        try:
            c = _conn(); cur = c.cursor()
            execute_values(cur, sql, rows, template=tpl, page_size=200)
            c.commit(); cur.close(); c.close(); return
        except Exception as e:
            if intento == 0:
                print(f"    reintento DB: {e}", flush=True); continue
            raise


def ingestar_curso(categoria, curso, fpath):
    cslug = _slug(curso)
    cid = f"sinodal-{cslug}"
    c = _conn(); cur = c.cursor()
    cur.execute("select 1 from holos_chunks where chunk_id=%s", (f"{cid}::000::0000",))
    ya = cur.fetchone() is not None
    cur.close(); c.close()
    if ya:
        print(f"= ya estaba: {curso}", flush=True); return 0
    texto = limpiar(open(fpath, encoding="utf-8", errors="ignore").read())
    bloques = _bloques(texto)
    total = 0
    rows = []
    for bi, (modulo, cuerpo) in enumerate(bloques):
        chunks = trozos(cuerpo)
        for ci in range(0, len(chunks), 256):
            part = chunks[ci:ci + 256]
            resp = _emb.embeddings.create(model=EMBED_MODEL, input=part)
            for j, (ch, e) in enumerate(zip(part, resp.data), start=ci):
                rows.append((
                    f"{cid}::{bi:03d}::{j:04d}", cid, curso, categoria, "Transcripción",
                    "Alumnos", "es", f"curso-{cslug}", "transcripcion",
                    os.path.basename(fpath), modulo or curso, ch, len(ch), _vec(e.embedding)))
            if len(rows) >= 400:
                _upsert(rows); total += len(rows); rows = []
    if rows:
        _upsert(rows); total += len(rows)
    print(f"  + {curso}: {len(bloques)} módulos, {total} chunks", flush=True)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    idx = os.path.join(a.dir, "INDICE_CURSOS.csv")
    rows = list(csv.DictReader(open(idx, encoding="utf-8")))
    if a.solo:
        rows = [r for r in rows if a.solo.lower() in r["curso"].lower()]
    print(f"cursos a procesar: {len(rows)}", flush=True)
    gran = 0
    for n, r in enumerate(rows, 1):
        fpath = os.path.join(a.dir, r["archivo"])
        if not os.path.exists(fpath):
            print(f"! falta archivo: {r['archivo']}", flush=True); continue
        print(f"[{n}/{len(rows)}] {r['curso']} ({int(r['palabras']):,} pal)", flush=True)
        try:
            gran += ingestar_curso(r["categoria"], r["curso"], fpath)
        except Exception as e:
            print(f"  ! error en {r['curso']}: {e}", flush=True)
    cf = _conn(); curf = cf.cursor(); curf.execute("select count(*) from holos_chunks"); tot = curf.fetchone()[0]; cf.close()
    print(f"\nLISTO. +{gran} chunks de transcripciones. Total Neon: {tot}", flush=True)


if __name__ == "__main__":
    main()
