#!/usr/bin/env python3
"""Ingesta genérica de una colección de libros a Neon, traduciendo al español
lo que esté en otro idioma. Extrae (txt/pdf con OCR) -> traduce si no es
español (caché reanudable) -> trocea -> embebe -> upsert a Neon.

Guardado e idempotente por libro.

Uso:
  KNOWLEDGE_DB_URL=... OPENAI_API_KEY=... \
  python3.14 scripts/ingerir_coleccion_neon.py \
    --dir "/ruta" --col-id constelaciones --col-name "Constelaciones Familiares y Transgeneracional" \
    [--exclude "Guia_Sitio,otra"] [--max-mb 40]
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ingerir_libros import extraer, limpiar, trozos, _slug

EMBED_MODEL = "text-embedding-3-small"
WINDOW = 4000
CACHE_DIR = "/tmp/trad_cache"
from openai import OpenAI
_emb = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_llm = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
TRAD_MODEL = os.getenv("HOLOS_MODEL", "google/gemini-2.5-flash")

SYS_TRAD = (
    "Traduce fielmente al español el siguiente texto (terapia, constelaciones "
    "familiares, transgeneracional, trauma). Conserva los términos técnicos. "
    "No resumas ni comentes: devuelve solo la traducción al español."
)


def _conn():
    import psycopg2
    return psycopg2.connect(os.environ["KNOWLEDGE_DB_URL"])


def _vec(v):
    v = np.asarray(v, dtype=np.float32); v = v / (np.linalg.norm(v) or 1.0)
    return "[" + ",".join(f"{float(x):.7f}" for x in v) + "]"


def _es(t: str) -> bool:
    s = t[:2500].lower()
    es = len(re.findall(r"\b(que|del|los|las|para|según|familia|amor|conflicto|porque)\b", s))
    en = len(re.findall(r"\b(the|and|of|with|that|family|trauma|which|from)\b", s))
    pt = len(re.findall(r"\b(que|não|para|você|família|também|porque)\b", s))
    return es >= en and es >= pt


def _traducir(texto: str, bid: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = f"{CACHE_DIR}/{bid}.jsonl"; cache = {}
    if os.path.exists(cp):
        for ln in open(cp):
            d = json.loads(ln); cache[d["h"]] = d["t"]
    vent = [texto[i:i+WINDOW] for i in range(0, len(texto), WINDOW)]
    pend = [v for v in vent if hashlib.md5(v.encode()).hexdigest() not in cache]
    print(f"    traduciendo {len(pend)}/{len(vent)} ventanas…", flush=True)

    def _tr(v):
        for _ in range(3):
            try:
                r = _llm.chat.completions.create(model=TRAD_MODEL, temperature=0.1, max_tokens=3000,
                    messages=[{"role": "system", "content": SYS_TRAD}, {"role": "user", "content": v}])
                return (r.choices[0].message.content or "").strip()
            except Exception:
                continue
        return ""
    with open(cp, "a") as cf, ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(_tr, v): v for v in pend}; done = 0
        for fut in as_completed(futs):
            v = futs[fut]; h = hashlib.md5(v.encode()).hexdigest()
            cache[h] = fut.result(); cf.write(json.dumps({"h": h, "t": cache[h]}) + "\n"); cf.flush()
            done += 1
            if done % 50 == 0: print(f"      {done}/{len(pend)}…", flush=True)
    return "\n\n".join(cache.get(hashlib.md5(v.encode()).hexdigest(), "") for v in vent)


def _upsert(cur, rows):
    from psycopg2.extras import execute_values
    execute_values(cur, """insert into holos_chunks
      (chunk_id, course_id, course_name, linea, tipo, audiencia, idioma,
       source_id, source_type, source_file, heading, text, char_count, embedding)
      values %s on conflict (chunk_id) do update set
      text=excluded.text, embedding=excluded.embedding""",
      rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)", page_size=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--col-id", required=True, dest="col_id")
    ap.add_argument("--col-name", required=True, dest="col_name")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--max-mb", type=float, default=120, dest="max_mb")
    a = ap.parse_args()
    col = _slug(a.col_id)
    excl = [e.strip().lower() for e in a.exclude.split(",") if e.strip()]

    files = sorted([p for p in glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)
                    if p.lower().rsplit(".", 1)[-1] in ("pdf", "txt", "md")])
    conn = _conn(); conn.autocommit = False; cur = conn.cursor()
    cur.execute("select chunk_id from holos_chunks where course_id=%s", (f"libros-{col}",))
    existentes = {r[0] for r in cur.fetchall()}
    print(f"ya en Neon ({col}): {len(existentes)} chunks", flush=True)

    total, hechos, saltados = 0, 0, []
    for fpath in files:
        titulo = os.path.splitext(os.path.basename(fpath))[0]
        if any(x in titulo.lower() for x in excl):
            print(f"~ excluido: {titulo}", flush=True); continue
        mb = os.path.getsize(fpath) / 1e6
        if mb > a.max_mb:
            saltados.append(f"{titulo} ({mb:.0f}MB)"); print(f"~ muy grande ({mb:.0f}MB), salto: {titulo}", flush=True); continue
        bid = _slug(titulo)
        if f"libro-{col}::{bid}::0000" in existentes:
            print(f"= ya estaba: {titulo}", flush=True); continue
        print(f"procesando: {titulo} ({mb:.0f}MB)", flush=True)
        try:
            texto = limpiar(extraer(fpath))
        except Exception as e:
            print(f"  ! error: {e}", flush=True); continue
        if len(texto) < 200:
            saltados.append(f"{titulo} (sin texto)"); print(f"  sin texto: {titulo}", flush=True); continue
        if not _es(texto):
            print("  idioma no español -> traduciendo", flush=True)
            texto = _traducir(texto, bid)
        chunks = trozos(texto)
        if not chunks:
            continue
        rows = []
        for s in range(0, len(chunks), 256):
            part = chunks[s:s+256]
            resp = _emb.embeddings.create(model=EMBED_MODEL, input=part)
            for i, (ch, e) in enumerate(zip(part, resp.data), start=s):
                rows.append((f"libro-{col}::{bid}::{i:04d}", f"libros-{col}", a.col_name,
                    "Libros de referencia", "Libro", "Terapeutas", "es", f"libro-{bid}",
                    "libro", os.path.basename(fpath), titulo, ch, len(ch), _vec(e.embedding)))
        _upsert(cur, rows); conn.commit()
        total += len(rows); hechos += 1
        print(f"  + {titulo}: {len(rows)} chunks", flush=True)

    cur.execute("select count(*) from holos_chunks"); n = cur.fetchone()[0]
    cur.close(); conn.close()
    print(f"\nLISTO: {hechos} libros, +{total} chunks. Total Neon: {n}", flush=True)
    if saltados:
        print("Saltados: " + "; ".join(saltados), flush=True)


if __name__ == "__main__":
    main()
