#!/usr/bin/env python3
"""Ingiere la Nueva Medicina Germánica a Neon, traduciendo al español lo que
esté en alemán/italiano (el material original más valioso).

Por archivo: detecta idioma -> si no es español, traduce por ventanas con IA
(caché reanudable) -> trocea -> embebe -> upsert a Neon (course_id 'libros-nmg').
Guardado e idempotente por libro.

Uso:
  KNOWLEDGE_DB_URL=... OPENAI_API_KEY=... \
  python3.14 scripts/ingerir_nmg_neon.py --dir "/Volumes/.../Nueva Medicina Germánica"
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ingerir_libros import extraer, limpiar, trozos, _slug

EMBED_MODEL = "text-embedding-3-small"
COL = "nmg"
COL_NAME = "Nueva Medicina Germánica"
WINDOW = 4000
CACHE_DIR = "/tmp/nmg_trad_cache"
from openai import OpenAI
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_llm = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
TRAD_MODEL = os.getenv("HOLOS_MODEL", "google/gemini-2.5-flash")

SYS_TRAD = (
    "Traduce fielmente al español el siguiente texto de la Nueva Medicina Germánica "
    "(Dr. Hamer). Conserva con precisión los términos técnicos (capa embrionaria, foco "
    "de Hamer, conflicto biológico, fase activa/PCL, vagotonía, simpaticotonía, etc.). "
    "No resumas, no comentes, no agregues nada: devuelve solo la traducción al español."
)


def _conn():
    import psycopg2
    return psycopg2.connect(os.environ["KNOWLEDGE_DB_URL"])


def _vec(v):
    v = np.asarray(v, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
    return "[" + ",".join(f"{float(x):.7f}" for x in v) + "]"


def _es(texto: str) -> bool:
    s = texto[:2500].lower()
    es = len(re.findall(r"\b(que|del|los|las|conflicto|enfermedad|biológic|sentido|según)\b", s))
    de = len(re.findall(r"\b(der|die|und|nicht|ich|krankheit|sich|werden)\b", s))
    it = len(re.findall(r"\b(che|della|sono|questo|malattia|nuova|delle)\b", s))
    return es >= de and es >= it


def _traducir_texto(texto: str, bid: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = f"{CACHE_DIR}/{bid}.jsonl"
    cache = {}
    if os.path.exists(cache_path):
        for ln in open(cache_path):
            d = json.loads(ln); cache[d["h"]] = d["t"]
    ventanas = [texto[i:i+WINDOW] for i in range(0, len(texto), WINDOW)]
    pend = [(i, v) for i, v in enumerate(ventanas) if hashlib.md5(v.encode()).hexdigest() not in cache]
    print(f"    traduciendo {len(pend)}/{len(ventanas)} ventanas…", flush=True)

    def _tr(v):
        for _ in range(3):
            try:
                r = _llm.chat.completions.create(model=TRAD_MODEL, temperature=0.1, max_tokens=3000,
                    messages=[{"role": "system", "content": SYS_TRAD}, {"role": "user", "content": v}])
                return (r.choices[0].message.content or "").strip()
            except Exception:
                continue
        return ""

    with open(cache_path, "a") as cf, ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(_tr, v): v for _, v in pend}
        done = 0
        for fut in as_completed(futs):
            v = futs[fut]; t = fut.result(); h = hashlib.md5(v.encode()).hexdigest()
            cache[h] = t; cf.write(json.dumps({"h": h, "t": t}) + "\n"); cf.flush()
            done += 1
            if done % 50 == 0:
                print(f"      {done}/{len(pend)}…", flush=True)
    return "\n\n".join(cache.get(hashlib.md5(v.encode()).hexdigest(), "") for v in ventanas)


def _upsert(cur, rows):
    from psycopg2.extras import execute_values
    sql = """insert into holos_chunks
      (chunk_id, course_id, course_name, linea, tipo, audiencia, idioma,
       source_id, source_type, source_file, heading, text, char_count, embedding)
      values %s on conflict (chunk_id) do update set
      text=excluded.text, embedding=excluded.embedding"""
    execute_values(cur, sql, rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)", page_size=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    files = sorted([p for p in glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)
                    if p.lower().rsplit(".", 1)[-1] in ("pdf", "txt", "md")])
    conn = _conn(); conn.autocommit = False; cur = conn.cursor()
    cur.execute("select chunk_id from holos_chunks where course_id=%s", (f"libros-{COL}",))
    existentes = {r[0] for r in cur.fetchall()}
    print(f"ya en Neon (NMG): {len(existentes)} chunks", flush=True)

    total, hechos = 0, 0
    for fpath in files:
        titulo = os.path.splitext(os.path.basename(fpath))[0]
        bid = _slug(titulo)
        if f"libro-{COL}::{bid}::0000" in existentes:
            print(f"= ya estaba: {titulo}", flush=True); continue
        print(f"procesando: {titulo}", flush=True)
        try:
            texto = limpiar(extraer(fpath))
        except Exception as e:
            print(f"  ! error: {e}", flush=True); continue
        if not _es(texto):
            print(f"  idioma no español -> traduciendo", flush=True)
            texto = _traducir_texto(texto, bid)
        chunks = trozos(texto)
        if not chunks:
            print(f"  sin texto: {titulo}", flush=True); continue
        rows = []
        for s in range(0, len(chunks), 256):
            part = chunks[s:s+256]
            resp = _emb.embeddings.create(model=EMBED_MODEL, input=part)
            for i, (ch, e) in enumerate(zip(part, resp.data), start=s):
                rows.append((f"libro-{COL}::{bid}::{i:04d}", f"libros-{COL}", COL_NAME,
                    "Libros de referencia", "Libro", "Terapeutas", "es", f"libro-{bid}",
                    "libro", os.path.basename(fpath), titulo, ch, len(ch), _vec(e.embedding)))
        _upsert(cur, rows); conn.commit()
        total += len(rows); hechos += 1
        print(f"  + {titulo}: {len(rows)} chunks", flush=True)

    cur.execute("select count(*) from holos_chunks"); n = cur.fetchone()[0]
    cur.close(); conn.close()
    print(f"\nLISTO: {hechos} libros NMG, +{total} chunks. Total Neon: {n}", flush=True)


if __name__ == "__main__":
    main()
